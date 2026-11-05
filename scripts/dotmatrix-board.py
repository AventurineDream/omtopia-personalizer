#!/usr/bin/env python3
"""DotMatrix Board — точечный шрифт на сетке 5×7, как у светодиодного табло.

Почему не DotMatrix LED: тот набран на сетке Terminus 8×16 — 16 точек на em. На обычном кегле терминала
(14 pt при масштабе 2 = 37 px) шаг точки 2.3 px, и между точками не остаётся зазора: глаз видит обычный
пиксельный шрифт. Настоящие табло (Nothing Ndot, Doto, символьные LCD) — 5×7: точка на 10 % кегля, на тех же
37 px шаг 3.7 px, и точки раздельные.

Источник глифов — Matrix Sans / Matrix Mono (FriedOrange, OFL 1.1, https://github.com/FriedOrange/MatrixSans):
5×7 со строчными, полная кириллица, моноширинная версия. Берётся вариант Screen: в нём каждая точка — отдельный
квадрат 86×86 с центром на сетке 100 единиц, так что из контуров точно снимаются центры точек. Каждая точка
заменяется ссылкой на один глиф «.dot» — его размер и форма задаются здесь (--dot, --shape), жирное — крупнее
точка, курсив — сдвиг рядов вправо (наклон по рядам; точки остаются круглыми).

Чего в Matrix нет:
- псевдографика (U+2500–257F), блоки (U+2580–259F) и Брайль (U+2800–28FF, графики btop) — строятся здесь на той же
  сетке, линии соседних ячеек стыкуются (kitty и ghostty рисуют псевдографику сами, это для VS Code и сайтов);
- остальное (стрелки, математика, …) — из DejaVu Sans Mono, растеризуется на 8 ppem в ячейку 5 точек;
- значки Nerd Font не трогаем: на 5×7 они нечитаемы, терминалы берут их из Symbols Nerd Font.

Производная Matrix Sans (OFL 1.1, без Reserved Font Name) — называется DotMatrix Board.

Для DotMatrix Lumen (профиль dots-all-lumen) ещё два параметра:
- --track N — разрядка пропорционального Sans: +N единиц к ширине знака, точки по центру (50 = полточки);
- --ligatures — лигатуры Mono точками на сетке двух ячеек: -> <- => == != (calt; ячейки терминала не ломаются:
  первый знак рисует обе половины, второй — пустой).

    uv run --with fonttools --with freetype-py dotmatrix-board.py <каталог fonts/ttf релиза Matrix Sans> <каталог вывода> \\
        [DejaVuSansMono.ttf DejaVuSansMono-Bold.ttf] [--dot 0.72] [--bold 0.84] [--shape round|square] \\
        [--family "DotMatrix Board"] [--only mono|sans] [--track 0] [--ligatures]
"""
import argparse
import io
import math
import os
import unicodedata

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent

STEP = 100                 # шаг сетки Matrix в единицах (UPM 1000)
DOT_SRC = 86               # сторона точки-квадрата в варианте Screen
CELL_X = range(0, 600, STEP)          # центры точек ячейки 600 по x: 0…500 (буквы — 100…500)
CELL_Y = range(-250, 1000, STEP)      # центры по y: от низа (descent 300) до верха (ascent 1000)
MID_X, MID_Y = 300, 350               # центр ячейки — пересечение линий псевдографики
SLANT = 0.2                           # курсив: сдвиг по x на единицу высоты
DROP = ("hdmx", "LTSH", "VDMX", "fpgm", "prep", "cvt ", "gasp")
SOURCES = {"mono": ("MatrixMonoScreen-Regular.ttf", "Mono"), "sans": ("MatrixSansScreen-Regular.ttf", "Sans")}
STYLES = (("Regular", False, False), ("Bold", True, False), ("Italic", False, True), ("BoldItalic", True, True))


def dot_glyph(r, shape):
    """Точка с центром в (0, 0): круг радиуса r или скруглённый квадрат стороной 2r (как ячейка LCD)."""
    pen = TTGlyphPen(None)
    if shape == "square":
        h, c = r, max(1, round(2 * r * 0.3))
        pen.moveTo((round(h - c), round(-h)))
        pen.qCurveTo((round(h), round(-h)), (round(h), round(-h + c)))
        pen.lineTo((round(h), round(h - c)))
        pen.qCurveTo((round(h), round(h)), (round(h - c), round(h)))
        pen.lineTo((round(-h + c), round(h)))
        pen.qCurveTo((round(-h), round(h)), (round(-h), round(h - c)))
        pen.lineTo((round(-h), round(-h + c)))
        pen.qCurveTo((round(-h), round(-h)), (round(-h + c), round(-h)))
    else:
        k = r / math.cos(math.pi / 8)
        pts = [(round(k * math.cos(math.pi / 8 * (2 * i + 1))), round(k * math.sin(math.pi / 8 * (2 * i + 1))))
               for i in range(8)]
        pen.qCurveTo(*pts, None)
    pen.closePath()
    return pen.glyph()


def dots_glyph(centers, italic):
    g = Glyph()
    comps = []
    for x, y in sorted(set(centers)):
        c = GlyphComponent()
        c.glyphName = ".dot"
        c.x = round(x + (y * SLANT if italic else 0))
        c.y = round(y)
        c.flags = 0x4  # ROUND_XY_TO_GRID
        comps.append(c)
    if comps:
        g.numberOfContours = -1
        g.components = comps
    else:
        g.numberOfContours = 0
    return g


def contours(glyphset, name):
    """Контуры глифа (составные раскрыты): [[(x, y), …], …] и сырая запись для не-точечных глифов."""
    pen = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(pen)
    out, cur = [], []
    for op, pts in pen.value:
        cur += list(pts)
        if op in ("closePath", "endPath"):
            out.append(cur)
            cur = []
    return out, pen


def dot_centers(conts):
    """Центры точек, если глиф целиком из точек-квадратов Screen; иначе None."""
    centers = []
    for c in conts:
        xs, ys = [p[0] for p in c], [p[1] for p in c]
        if abs(max(xs) - min(xs) - DOT_SRC) > 2 or abs(max(ys) - min(ys) - DOT_SRC) > 2:
            return None
        centers.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2))
    return centers


# ── псевдографика, блоки, Брайль ──────────────────────────────────────────────────────────────────────────

def line_x(x0, x1, y):
    return [(x, y) for x in CELL_X if x0 <= x <= x1]


def line_y(y0, y1, x):
    return [(x, y) for y in CELL_Y if y0 <= y <= y1]


def box(cp):
    """Линии псевдографики по имени Unicode: плечи up/down/left/right, двойные — две линии через шаг."""
    try:
        name = unicodedata.name(chr(cp))
    except ValueError:
        return None
    if not name.startswith("BOX DRAWINGS"):
        return None
    words = name.split()
    double = "DOUBLE" in words and "SINGLE" not in words
    if "DIAGONAL" in words:
        pts = []
        rising = "RISING" in words or "CROSS" in words
        falling = "FALLING" in words or "CROSS" in words
        for y in CELL_Y:
            t = (y - CELL_Y[0]) / (CELL_Y[-1] - CELL_Y[0])
            if rising:
                pts.append((round(t * 5) * STEP, y))
            if falling:
                pts.append((round((1 - t) * 5) * STEP, y))
        return pts
    arms = set()
    rest = words[2:]
    if "HORIZONTAL" in rest:
        arms |= {"left", "right"}
    if "VERTICAL" in rest:
        arms |= {"up", "down"}
    for w, a in (("UP", "up"), ("DOWN", "down"), ("LEFT", "left"), ("RIGHT", "right")):
        if w in rest:
            arms.add(a)
    if not arms:
        return None
    # половинные линии «LIGHT LEFT» и т.п. — одно плечо; «LIGHT LEFT AND HEAVY RIGHT» — оба.
    offs = (-STEP, STEP) if double else (0,)
    pts = []
    for o in offs:
        if "left" in arms:
            pts += line_x(CELL_X[0], MID_X, MID_Y + o)
        if "right" in arms:
            pts += line_x(MID_X, CELL_X[-1], MID_Y + o)
        if "up" in arms:
            pts += line_y(MID_Y, CELL_Y[-1], MID_X + o)
        if "down" in arms:
            pts += line_y(CELL_Y[0], MID_Y, MID_X + o)
    return pts


def block(cp):
    """Блоки U+2580–259F на сетке ячейки 6×13."""
    cols, rows = list(CELL_X), list(CELL_Y)
    nx, ny = len(cols), len(rows)

    def rect(c0, c1, r0, r1, keep=lambda i, j: True):  # столбцы [c0, c1), ряды снизу [r0, r1)
        return [(cols[i], rows[j]) for i in range(c0, c1) for j in range(r0, r1) if keep(i, j)]

    half_x, half_y = nx // 2, ny // 2  # 3 столбца, 6 рядов снизу
    if cp == 0x2580:
        return rect(0, nx, half_y, ny)
    if 0x2581 <= cp <= 0x2588:
        return rect(0, nx, 0, max(1, round(ny * (cp - 0x2580) / 8)))
    if 0x2589 <= cp <= 0x258F:
        return rect(0, max(1, round(nx * (0x2590 - cp) / 8)), 0, ny)
    if cp == 0x2590:
        return rect(half_x, nx, 0, ny)
    if cp == 0x2591:
        return rect(0, nx, 0, ny, lambda i, j: i % 2 == 0 and j % 2 == 0)
    if cp == 0x2592:
        return rect(0, nx, 0, ny, lambda i, j: (i + j) % 2 == 0)
    if cp == 0x2593:
        return rect(0, nx, 0, ny, lambda i, j: not (i % 2 == 1 and j % 2 == 1))
    if cp == 0x2594:
        return rect(0, nx, ny - 1, ny)
    if cp == 0x2595:
        return rect(nx - 1, nx, 0, ny)
    quads = {  # квадранты: (верх-лево, верх-право, низ-лево, низ-право)
        0x2596: "0010", 0x2597: "0001", 0x2598: "1000", 0x2599: "1011", 0x259A: "1001",
        0x259B: "1110", 0x259C: "1101", 0x259D: "0100", 0x259E: "0110", 0x259F: "0111",
    }
    if cp in quads:
        q = quads[cp]
        pts = []
        for k, (c0, c1, r0, r1) in enumerate(((0, half_x, half_y, ny), (half_x, nx, half_y, ny),
                                               (0, half_x, 0, half_y), (half_x, nx, 0, half_y))):
            if q[k] == "1":
                pts += rect(c0, c1, r0, r1)
        return pts
    return None


def braille(cp):
    """Брайль — 2×4 точки: биты 0–2 и 6 — левый столбец, 3–5 и 7 — правый (сверху вниз)."""
    bits = cp - 0x2800
    xs, ys = (100, 400), (850, 550, 250, -50)
    where = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (0, 3), 7: (1, 3)}
    return [(xs[c], ys[r]) for b, (c, r) in where.items() if bits >> b & 1]


# ── запасной шрифт ────────────────────────────────────────────────────────────────────────────────────────

def fallback_centers(face, gid):
    """Знак DejaVu Sans Mono на 8 ppem (ширина ≈ 5 точек): пиксель → центр точки на сетке ячейки."""
    import freetype
    try:
        face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    except freetype.FT_Exception:
        return []
    slot, bm = face.glyph, face.glyph.bitmap
    out = []
    for row in range(bm.rows):
        for col in range(bm.width):
            if bm.buffer[row * bm.pitch + (col >> 3)] & (0x80 >> (col & 7)):
                px, py = slot.bitmap_left + col, slot.bitmap_top - row - 1
                out.append(((px + 1) * STEP, (py + 0.5) * STEP))
    return out


# ── лигатуры Mono ─────────────────────────────────────────────────────────────────────────────────────────
# Точки на сетке двух ячеек (x 0…1100): линии соседних ячеек идут без разрыва — шаг тот же, 100. Ряды как у
# самих знаков Matrix: «-» и острия на 350, «=» на 450 и 250.

def _row(y, x0, x1):
    return [(x, y) for x in range(x0, x1 + 1, STEP)]


# Края — как у двух обычных знаков подряд: от колонки 100 первой ячейки до 500 второй (1100), иначе справа
# оставался лишний пустой столбец и лигатура липла к знаку слева. Центр пары — 600.
LIGATURES = {
    ("hyphen", "greater"): _row(350, 100, 1000) + [(1100, 350), (1000, 450), (1000, 250), (900, 550), (900, 150)],
    ("less", "hyphen"): _row(350, 200, 1100) + [(100, 350), (200, 450), (200, 250), (300, 550), (300, 150)],
    ("equal", "greater"): _row(450, 100, 1000) + _row(250, 100, 1000) + [(1100, 350), (900, 550), (900, 150)],
    ("equal", "equal"): _row(450, 100, 1100) + _row(250, 100, 1100),
    # ≠: косая в пять точек ровно по центру, на ряд выше и ниже линий «=».
    ("exclam", "equal"): _row(450, 100, 1100) + _row(250, 100, 1100)
                         + [(400, 150), (500, 250), (600, 350), (700, 450), (800, 550)],
}
# Последовательности, где лигатура выглядела бы неверно: -->, <--, ===, !==, ==>, <==, <=>.
LIG_IGNORE = """
  ignore sub hyphen hyphen' greater;
  ignore sub less' hyphen hyphen;
  ignore sub equal equal' equal;
  ignore sub equal' equal equal;
  ignore sub exclam' equal equal;
  ignore sub equal' equal greater;
  ignore sub less equal' equal;
  ignore sub less equal' greater;
"""


def lig_fea():
    rules = []
    for a, b in LIGATURES:
        n = f"lig.{a}_{b}"
        rules.append(f"  sub {a}' {b} by {n}.l;\n  sub {n}.l {b}' by {n}.r;")
    return "feature calt {\n" + LIG_IGNORE + "\n".join(rules) + "\n} calt;\n"


def _walk(obj, fn, seen):
    """Обход таблиц OpenType: fn вызывается на каждой SubstLookupRecord."""
    if id(obj) in seen:
        return
    seen.add(id(obj))
    if type(obj).__name__ == "SubstLookupRecord":
        fn(obj)
        return
    if isinstance(obj, list):
        for x in obj:
            _walk(x, fn, seen)
    elif hasattr(obj, "__dict__"):
        for v in vars(obj).values():
            if isinstance(v, list) or hasattr(v, "__dict__"):
                _walk(v, fn, seen)


def add_calt(font, fea):
    """Дописывает calt в существующий GSUB: feaLib строит его во временной копии, lookup'ы переносятся со сдвигом
    индексов, а фича включается во всех письменностях (latn, cyrl, …). Свои фичи Matrix (locl, ss01…) остаются."""
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    tmp = TTFont(buf)
    if "GSUB" in tmp:
        del tmp["GSUB"]
    addOpenTypeFeaturesFromString(tmp, fea, tables=["GSUB"])
    src, dst = tmp["GSUB"].table, font["GSUB"].table
    off = len(dst.LookupList.Lookup)

    def shift(rec):
        rec.LookupListIndex += off
    for lk in src.LookupList.Lookup:
        _walk(lk, shift, set())
        dst.LookupList.Lookup.append(lk)
    dst.LookupList.LookupCount = len(dst.LookupList.Lookup)
    new_idx = []
    for fr in src.FeatureList.FeatureRecord:
        fr.Feature.LookupListIndex = [i + off for i in fr.Feature.LookupListIndex]
        dst.FeatureList.FeatureRecord.append(fr)
        new_idx.append(len(dst.FeatureList.FeatureRecord) - 1)
    dst.FeatureList.FeatureCount = len(dst.FeatureList.FeatureRecord)
    for sr in dst.ScriptList.ScriptRecord:
        systems = [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]
        for ls in systems:
            if ls is None:
                continue
            ls.FeatureIndex = list(ls.FeatureIndex) + new_idx
            ls.FeatureCount = len(ls.FeatureIndex)


def track_glyphs(font, track):
    """Разрядка: +track к ширине каждого знака с шириной, сам знак — по центру (сдвиг на track/2)."""
    glyf, hmtx = font["glyf"], font["hmtx"]
    dx = track // 2
    for name in font.getGlyphOrder():
        adv, lsb = hmtx.metrics[name]
        if name == ".dot" or adv == 0:
            continue
        g = glyf[name]
        if g.isComposite():
            for c in g.components:
                c.x += dx
        elif g.numberOfContours > 0:
            g.coordinates.translate((dx, 0))
        hmtx.metrics[name] = (adv + track, lsb + dx)


# ── сборка ────────────────────────────────────────────────────────────────────────────────────────────────

def set_names(font, family, ps, style, bold, italic):
    sub = {"Regular": "Regular", "Bold": "Bold", "Italic": "Italic", "BoldItalic": "Bold Italic"}[style]
    full = family if style == "Regular" else f"{family} {sub}"
    ids = {1: family, 2: sub, 3: f"{ps}-{style};DotMatrixBoard", 4: full, 6: f"{ps}-{style}"}
    name = font["name"]
    for nid in (16, 17, 21, 22, 25):  # типографские имена источника — иначе семейство осталось бы «Matrix …»
        name.removeNames(nameID=nid)
    for nid, s in ids.items():
        name.setName(s, nid, 3, 1, 0x409)
        name.setName(s, nid, 1, 0, 0)
    desc = (f"{family}: Matrix Sans (FriedOrange, OFL 1.1) redrawn as round LED dots on its 5x7 grid "
            "for the DOT-MATRIX style of omarchy dotfiles.")
    name.setName(desc, 10, 3, 1, 0x409)
    os2, head = font["OS/2"], font["head"]
    os2.usWeightClass = 700 if bold else 400
    sel = os2.fsSelection & ~0b1100001  # italic, bold, regular
    sel |= (0x20 if bold else 0) | (0x01 if italic else 0)
    if not bold and not italic:
        sel |= 0x40
    os2.fsSelection = sel
    head.macStyle = (1 if bold else 0) | (2 if italic else 0)
    if italic:
        font["post"].italicAngle = -round(math.degrees(math.atan(SLANT)), 1)
        font["hhea"].caretSlopeRise, font["hhea"].caretSlopeRun = 1000, round(1000 * SLANT)


def build(src, dst, family, ps, style, bold, italic, radius, shape, fallback, mono, track=0, ligatures=False):
    font = TTFont(src)
    for tag in DROP:
        if tag in font:
            del font[tag]
    glyf, hmtx = font["glyf"], font["hmtx"]
    gs = font.getGlyphSet()
    order = font.getGlyphOrder()

    new = {}
    kept = 0
    for name in order:
        conts, rec = contours(gs, name)
        centers = dot_centers(conts)
        if centers is None:  # .notdef и пара служебных — обычные контуры, раскрытые
            pen = TTGlyphPen(None)
            rec.replay(pen)
            new[name] = pen.glyph()
            kept += 1
        else:
            new[name] = dots_glyph(centers, italic)
    for name, g in new.items():
        glyf.glyphs[name] = g

    glyf.glyphs[".dot"] = dot_glyph(radius, shape)
    hmtx.metrics[".dot"] = (0, -round(radius))
    added = []

    # Псевдографика, блоки и Брайль — свои, поверх того, что есть в источнике (там их нет).
    cmap = font.getBestCmap()
    gen = {}
    for cp in list(range(0x2500, 0x25A0)) + list(range(0x2800, 0x2900)):
        if cp in cmap:
            continue
        pts = box(cp) if cp < 0x2580 else block(cp) if cp < 0x25A0 else braille(cp)
        if pts is not None:
            gen[cp] = pts
    adv = 600
    for cp, pts in gen.items():
        n = f"dm.u{cp:04X}"
        glyf.glyphs[n] = dots_glyph(pts, False)  # псевдографика без наклона — иначе линии рвутся
        hmtx.metrics[n] = (adv, 0)
        added.append((cp, n))

    # Остальное — из DejaVu Sans Mono.
    if fallback:
        import freetype
        fb = TTFont(fallback)
        face = freetype.Face(fallback)
        face.set_pixel_sizes(0, 8)
        have = set(cmap) | set(gen)
        for cp, fname in sorted(fb.getBestCmap().items()):
            if cp in have or cp < 0x20 or 0xE000 <= cp <= 0xF8FF:
                continue
            pts = fallback_centers(face, fb.getGlyphID(fname))
            if not pts and fname not in ("space", "uni00A0"):
                continue
            n = f"dm.u{cp:04X}"
            glyf.glyphs[n] = dots_glyph(pts, italic)
            hmtx.metrics[n] = (adv, 0)
            added.append((cp, n))

    ligs = []
    if ligatures:
        for (a, b), pts in LIGATURES.items():
            n = f"lig.{a}_{b}"
            glyf.glyphs[n + ".l"] = dots_glyph(pts, italic)
            glyf.glyphs[n + ".r"] = dots_glyph([], False)
            hmtx.metrics[n + ".l"] = hmtx.metrics[n + ".r"] = (adv, 0)
            ligs += [n + ".l", n + ".r"]
    font.setGlyphOrder(order + [".dot"] + [n for _, n in added] + ligs)
    glyf.glyphOrder = font.getGlyphOrder()
    for t in font["cmap"].tables:
        if t.isUnicode():
            for cp, n in added:
                if cp <= 0xFFFF or t.format in (12, 13):
                    t.cmap[cp] = n

    if track:
        track_glyphs(font, track)
    if ligs:
        add_calt(font, lig_fea())
    set_names(font, family, ps, style, bold, italic)
    if mono:
        font["post"].isFixedPitch = 1
        font["OS/2"].panose.bProportion = 9
    maxp = font["maxp"]
    maxp.maxComponentElements = max((len(glyf[n].components) for n in font.getGlyphOrder()
                                     if glyf[n].isComposite()), default=0)
    maxp.maxComponentDepth = 1
    font.save(dst)
    return len(font.getGlyphOrder()), len(added), kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("fallback", nargs="*")
    ap.add_argument("--dot", type=float, default=0.72, help="диаметр точки, доля шага")
    ap.add_argument("--bold", type=float, default=None, help="диаметр точки жирного (по умолчанию --dot + 0.12)")
    ap.add_argument("--shape", choices=("round", "square"), default="round")
    ap.add_argument("--family", default="DotMatrix Board")
    ap.add_argument("--only", choices=tuple(SOURCES))
    ap.add_argument("--styles", default=",".join(s for s, _, _ in STYLES))
    ap.add_argument("--track", type=int, default=0, help="разрядка Sans, единиц (100 = точка)")
    ap.add_argument("--ligatures", action="store_true", help="лигатуры Mono -> <- => == !=")
    a = ap.parse_args()
    bold_dot = a.bold if a.bold is not None else min(0.98, a.dot + 0.12)
    os.makedirs(a.out, exist_ok=True)
    want = set(a.styles.split(","))
    for kind, (fname, suffix) in SOURCES.items():
        if a.only and kind != a.only:
            continue
        src = os.path.join(a.src, fname)
        if not os.path.isfile(src):
            raise SystemExit(f"нет {src}")
        family = f"{a.family} {suffix}"
        ps = family.replace(" ", "")
        for style, bold, italic in STYLES:
            if style not in want:
                continue
            fb = a.fallback[1 if bold and len(a.fallback) > 1 else 0] if a.fallback else None
            dst = os.path.join(a.out, f"{ps}-{style}.ttf")
            radius = (bold_dot if bold else a.dot) * STEP / 2
            mono = kind == "mono"
            n, added, kept = build(src, dst, family, ps, style, bold, italic, radius, a.shape, fb, mono,
                                   track=0 if mono else a.track, ligatures=mono and a.ligatures)
            print(f"{os.path.basename(dst)}: {n} глифов (+{added} своих и DejaVu), {os.path.getsize(dst) // 1024} КБ")


if __name__ == "__main__":
    main()
