#!/usr/bin/env python3
"""Nihil Pixel — Terminess Nerd Font (Terminus, OFL 1.1) с русскими строчными, курсивом в ячейке
и пиксельными лигатурами.

Terminess — это Terminus: контуры, обведённые по битмапу 16×32 (em 1000 = 32 пикселя по 31.25 ед.,
базовая линия на y=20), плюс встроенные битмапы Terminus 12–32 px (EBDT/EBLC), которые FreeType
берёт на этих размерах вместо контуров. Поэтому каждая правка делается и в контурах, и во всех
встроенных размерах — иначе на 32 px (ghostty 12 pt при масштабе 2) видна старая буква.

1. Русские строчные. По умолчанию Terminus рисует «в» как маленькую «B» в рост прописной, «д» как «g»
   (болгарские формы), а «и й» как «u ŭ». «в д» берутся из официального варианта Terminus alt/dv1
   (каждого размера), «и й» строятся из «И» того же размера: убираются прямые ряды над и под
   диагональю, пока буква не встанет на высоту строчных. Остальная кириллица не трогается.
2. Курсив. В Terminess Italic наклонённые глифы выходят за ячейку, и терминал их обрезает. Здесь
   Italic/BoldItalic строятся из Regular/Bold ступенчатым сдвигом строк вправо, сдвиг ограничен
   свободным местом в ячейке — глиф никогда из неё не выходит. Псевдографика и значки не наклоняются.
3. Лигатуры (calt, как у Fira Code): первые знаки заменяются пустыми глифами-спейсерами ширины
   ячейки, последний — глифом лигатуры, нарисованным влево на всю группу; число глифов не меняется,
   поэтому лигатуры работают в терминалах. Рисуются из пикселей самого шрифта: стрелки из «-»/«=» и
   «>», ≠ — перечёркнутое «==», ≤ ≥, сближенные «::» «//» «||». Только контурами: во встроенных
   битмапах метрики постоянные, глиф не может рисовать в соседних ячейках.

Изменённую версию нельзя называть Terminus/Terminess — семейство «Nihil Pixel».

    uv run --with fonttools scripts/nihil-pixel.py <Terminess-Regular.ttf> <Terminess-Bold.ttf> <каталог вывода>

Исходники Terminus скачиваются с SourceForge (sha256 сверяется) в ~/.cache/nihil-fonts.
"""
import copy
import hashlib
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FAMILY = "Nihil Pixel"
PX = 31.25
BASE = 20  # y базовой линии контуров в единицах шрифта
TERMINUS = ("https://downloads.sourceforge.net/project/terminus-font/terminus-font-4.49/terminus-font-4.49.1.tar.gz",
            "d961c1b781627bf417f9b340693d64fc219e0113ad3a3af1a3424c7aa373ef79")
CACHE = os.path.expanduser("~/.cache/nihil-fonts")

# Где курсив уместен: буквы, цифры, знаки. Псевдографика и значки Nerd Font — нет.
TEXT_RANGES = ((0x21, 0x24F), (0x370, 0x52F), (0x1E00, 0x1EFF), (0x2010, 0x205E), (0x20A0, 0x20C0),
               (0x2100, 0x215F), (0x2190, 0x21FF), (0x2200, 0x22FF))

# Лигатуры: знаки → вид. Длинные раньше коротких.
LIGATURES = [
    ("!==", "neq"), ("===", "eq"), ("!=", "neq"), ("==", "eq"),
    ("->", "arrow"), ("<-", "arrow_l"), ("=>", "darrow"), ("<=", "le"), (">=", "ge"),
    ("--", "bar"), ("::", "tight"), ("//", "tight"), ("||", "tight"),
    ("++", "tight"), (">>", "tight"), ("<<", "tight"),
]


# --- исходники Terminus ---------------------------------------------------------

def terminus_source():
    """Каталог исходников Terminus с вариантом alt/dv1 (русские «в д»)."""
    src = os.path.join(CACHE, "terminus-dv1", "terminus-font-4.49.1")
    if os.path.isfile(os.path.join(src, ".dv1")):
        return src
    os.makedirs(CACHE, exist_ok=True)
    tarball = os.path.join(CACHE, "terminus-font-4.49.1.tar.gz")
    if not os.path.isfile(tarball):
        urllib.request.urlretrieve(TERMINUS[0], tarball + ".part")
        os.replace(tarball + ".part", tarball)
    with open(tarball, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != TERMINUS[1]:
            raise SystemExit(f"{tarball}: sha256 не совпадает")
    # Распаковка во временный каталог и переименование: недоделанный каталог не выдаст себя за готовый.
    work = tempfile.mkdtemp(prefix="terminus-", dir=CACHE)
    with tarfile.open(tarball) as t:
        t.extractall(work, filter="data")
    tmp_src = os.path.join(work, "terminus-font-4.49.1")
    subprocess.run(["patch", "-p1", "-s", "-i", "alt/dv1.diff"], cwd=tmp_src, check=True)
    open(os.path.join(tmp_src, ".dv1"), "w").close()
    os.replace(work, os.path.join(CACHE, "terminus-dv1"))
    return src


def load_bdf(path):
    """BDF → ({код: строки 0/1 на всю ячейку сверху вниз}, ширина, высота)."""
    glyphs, cur, bits = {}, None, None
    for line in open(path, encoding="latin-1"):
        p = line.split()
        if not p:
            continue
        if p[0] == "FONTBOUNDINGBOX":
            W, H, _, fy = map(int, p[1:])
        elif p[0] == "ENCODING":
            cur = {"cp": int(p[1])}
        elif p[0] == "BBX":
            cur["bbx"] = list(map(int, p[1:]))
        elif p[0] == "BITMAP":
            bits = []
        elif p[0] == "ENDCHAR":
            w, h, xo, yo = cur["bbx"]
            cell = [[0] * W for _ in range(H)]
            top = (H + fy) - (h + yo)
            for r, b in enumerate(bits):
                for c in range(w):
                    if (int(b, 16) >> (len(b) * 4 - 1 - c)) & 1 and 0 <= top + r < H and 0 <= xo + c < W:
                        cell[top + r][xo + c] = 1
            glyphs[cur["cp"]] = cell
            bits = None
        elif bits is not None:
            bits.append(p[0])
    return glyphs, W, H


# --- русские строчные: «и» из «И» ----------------------------------------------

def lower_i(cap, n):
    """«И» → строчная «и»: прямые ряды над и под диагональю убираются, пока высота не станет как у «н»."""
    rows = [i for i, r in enumerate(cap) if any(r)]
    x_rows = [i for i, r in enumerate(n) if any(r)]
    top, bottom = rows[0], rows[-1]
    keep = cap[top:bottom + 1]
    k = len(keep) - len(x_rows)
    while k > 0:
        lead = next(i for i, r in enumerate(keep) if r != keep[0])
        trail = next(i for i, r in enumerate(reversed(keep)) if r != keep[-1])
        if max(lead, trail) <= 1:  # прямых рядов не осталось — убрать ряд из середины диагонали
            del keep[len(keep) // 2]
        elif lead >= trail:
            del keep[0]
        else:
            del keep[-1]
        k -= 1
    out = [[0] * len(cap[0]) for _ in cap]
    for i, r in enumerate(keep):
        out[x_rows[0] + i] = list(r)
    return out


def russian(bdf):
    """Новые битмапы ячеек для «в д и й» из BDF одного размера (уже с dv1)."""
    g = bdf
    i = lower_i(g[ord("И")], g[ord("н")])
    x_top = next(r for r, row in enumerate(g[ord("н")]) if any(row))
    breve = [row if r < x_top else [0] * len(row) for r, row in enumerate(g[ord("й")])]
    j = [[a | b for a, b in zip(r1, r2)] for r1, r2 in zip(i, breve)]
    return {"в": g[ord("в")], "д": g[ord("д")], "и": i, "й": j}


# --- контуры --------------------------------------------------------------------

def to_pixels(cell, asc):
    """Строки ячейки → пиксели (col, py), py — высота строки над базовой линией."""
    return {(c, asc - 1 - r) for r, row in enumerate(cell) for c, v in enumerate(row) if v}


def raster(font, name):
    """Глиф-контур Terminess → пиксели (col, py) на сетке 16×32."""
    glyf = font["glyf"]
    g = glyf[name]
    if g.isComposite():
        out = set()
        for comp in g.components:
            dx, dy = round(comp.x / PX), round(comp.y / PX)
            out |= {(c + dx, p + dy) for c, p in raster(font, comp.glyphName)}
        return out
    if g.numberOfContours <= 0:
        return set()
    coords, ends, _ = g.getCoordinates(glyf)
    contours, start = [], 0
    for end in ends:
        contours.append(list(coords[start:end + 1]))
        start = end + 1
    out = set()
    for py in range(-8, 28):
        y = BASE + (py + 0.5) * PX
        for col in range(int(g.xMin // PX) - 1, int(g.xMax // PX) + 2):
            x = (col + 0.5) * PX
            inside = False
            for pts in contours:
                for i in range(len(pts)):
                    (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
                    if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                        inside = not inside
            if inside:
                out.add((col, py))
    return out


def draw(pixels):
    """Пиксели → глиф TrueType: отрезки строк, одинаковые в соседних строках, сливаются в прямоугольники."""
    pen = TTGlyphPen(None)
    runs = {}
    for py in sorted({p for _, p in pixels}):
        cols = sorted(c for c, p in pixels if p == py)
        start = None
        for i, c in enumerate(cols):
            start = c if start is None else start
            if i == len(cols) - 1 or cols[i + 1] != c + 1:
                runs.setdefault((start, c), []).append(py)
                start = None
    for (c0, c1), rows in sorted(runs.items()):
        r0 = rows[0]
        for i, r in enumerate(rows):
            if i == len(rows) - 1 or rows[i + 1] != r + 1:
                x0, x1 = round(c0 * PX), round((c1 + 1) * PX)
                y0, y1 = round(BASE + r0 * PX), round(BASE + (r + 1) * PX)
                pen.moveTo((x0, y0))
                pen.lineTo((x0, y1))
                pen.lineTo((x1, y1))
                pen.lineTo((x1, y0))
                pen.closePath()
                if i < len(rows) - 1:
                    r0 = rows[i + 1]
    return pen.glyph()


def set_outline(font, name, pixels, advance=None):
    glyf = font["glyf"]
    g = draw(pixels)
    glyf[name] = g  # новое имя glyf сам дописывает в порядок глифов
    g.recalcBounds(glyf)
    adv = advance if advance is not None else font["hmtx"][name][0]
    font["hmtx"][name] = (adv, g.xMin if g.numberOfContours else 0)


# --- встроенные битмапы (EBDT формат 5: постоянные метрики, ячейка целиком) ----------

def strikes(font):
    """[(ppem, ширина, высота, ascent, {имя: объект битмапа})]."""
    out = []
    for s, data in zip(font["EBLC"].strikes, font["EBDT"].strikeData):
        m = s.indexSubTables[0].metrics
        out.append((s.bitmapSizeTable.ppemY, m.width, m.height, m.horiBearingY, data))
    return out


def get_bits(obj, w, h):
    bits = obj.imageData
    return [[(bits[(r * w + c) // 8] >> (7 - (r * w + c) % 8)) & 1 for c in range(w)] for r in range(h)]


def set_bits(obj, cell):
    w, h = len(cell[0]), len(cell)
    out = bytearray((w * h + 7) // 8)
    for r in range(h):
        for c in range(w):
            if cell[r][c]:
                i = r * w + c
                out[i // 8] |= 0x80 >> (i % 8)
    obj.imageData = bytes(out)


def load_strike_glyph(obj):
    if not hasattr(obj, "imageData"):
        obj.decompile()


# --- 1. русские строчные -------------------------------------------------------------

def fix_cyrillic(font, src, weight):
    cmap = font.getBestCmap()
    suffix = "n" if weight == "Regular" else "b"
    for ppem, w, h, asc, data in strikes(font):
        bdf, _, _ = load_bdf(os.path.join(src, f"ter-u{ppem}{suffix}.bdf"))
        for ch, cell in russian(bdf).items():
            obj = data.get(cmap[ord(ch)])
            if obj is not None:
                load_strike_glyph(obj)
                set_bits(obj, cell)
        if ppem == 32:  # контуры обведены по 32 px
            for ch, cell in russian(bdf).items():
                set_outline(font, cmap[ord(ch)], to_pixels(cell, asc))


# --- 2. курсив ------------------------------------------------------------------------

def slant_rows(pixels, lo, hi, asc):
    """Сдвиг строк вправо, ступенька ≈ треть высоты над базовой линией; сжимается до свободного места."""
    step = max(2, round(asc * 0.35))
    raw = {(c, p): (p + round(asc * 0.08)) // step for c, p in pixels}
    span = max(raw.values()) - min(raw.values())
    cols = [c for c, _ in pixels]
    room = (hi - lo) - (max(cols) - min(cols))
    if span > room:
        if room <= 0:
            return None
        raw = {k: v * room // span for k, v in raw.items()}
    moved = {(c + raw[(c, p)], p) for c, p in pixels}
    cmin, cmax = min(c for c, _ in moved), max(c for c, _ in moved)
    if cmax > hi:
        moved = {(c - (cmax - hi), p) for c, p in moved}
    if cmin < lo:
        moved = {(c + (lo - cmin), p) for c, p in moved}
    return moved


def text_glyphs(font):
    names = {n for cp, n in font.getBestCmap().items() if any(a <= cp <= b for a, b in TEXT_RANGES)}
    return names | {n for n in font.getGlyphOrder() if n.endswith(".liga")}


def italicize(font):
    names = text_glyphs(font)
    for name in sorted(names):
        pixels = raster(font, name)
        if not pixels:
            continue
        lo = -((len(name.split("_")) - 1) * 16) if name.endswith(".liga") else 0
        moved = slant_rows(pixels, lo, 15, 26)
        if moved:
            set_outline(font, name, moved, advance=font["hmtx"][name][0])
    for ppem, w, h, asc, data in strikes(font):
        for name in names:
            obj = data.get(name)
            if obj is None:
                continue
            load_strike_glyph(obj)
            pixels = to_pixels(get_bits(obj, w, h), asc)
            if not pixels:
                continue
            moved = slant_rows(pixels, 0, w - 1, asc)
            if moved:
                cell = [[0] * w for _ in range(h)]
                for c, p in moved:
                    r = asc - 1 - p
                    if 0 <= r < h and 0 <= c < w:
                        cell[r][c] = 1
                set_bits(obj, cell)


# --- 3. лигатуры (контуры) -----------------------------------------------------------

def rows_of(pixels):
    return sorted({p for _, p in pixels})


def ligature_pixels(font, chars, kind):
    """Пиксели лигатуры на холсте len(chars) ячеек по 16 px (col 0 — левый край первой ячейки)."""
    cmap = font.getBestCmap()
    g = {ch: raster(font, cmap[ord(ch)]) for ch in set(chars) | {"-", "=", "<", ">"}}
    n, cell = len(chars), 16
    width = n * cell

    def at(ch, offset, dy=0):
        return {(c + offset, p + dy) for c, p in g[ch]}

    def bars(proto, start, end):
        return {(c, p) for p in rows_of(g[proto]) for c in range(start, end + 1)}

    left = min(c for c, _ in g["="])
    right = width - 1 - left
    thick = len(rows_of(g["-"]))  # толщина штриха как у «-»: 2 px, в Bold 3
    if kind == "eq":
        return bars("=", left, right)
    if kind == "bar":
        return bars("-", left, right)
    if kind == "neq":
        out = bars("=", left, right)
        lo, hi = min(rows_of(g["="])) - 4, max(rows_of(g["="])) + 4
        mid = width // 2
        for p in range(lo, hi + 1):
            c = mid - (hi - lo) // 4 + (p - lo) // 2
            out |= {(c + i, p) for i in range(thick)}
        return out
    if kind in ("arrow", "darrow"):
        head = at(">", (n - 1) * cell + 1)
        out = set(head)
        for p in rows_of(g["-" if kind == "arrow" else "="]):
            head_cols = [c for c, q in head if q == p]
            stop = (min(head_cols) - 1) if head_cols else max(c for c, _ in head) - 2
            out |= {(c, p) for c in range(left, stop + 1)}
        return out
    if kind == "arrow_l":
        head = at("<", -1)
        out = set(head)
        for p in rows_of(g["-"]):
            head_cols = [c for c, q in head if q == p]
            begin = (max(head_cols) + 1) if head_cols else min(c for c, _ in head) + 2
            out |= {(c, p) for c in range(begin, right + 1)}
        return out
    if kind in ("le", "ge"):
        shape = at("<" if kind == "le" else ">", cell // 2, dy=thick + 1)
        cols = [c for c, _ in shape]
        bottom = min(p for _, p in shape) - thick - 2
        return shape | {(c, bottom + i) for i in range(thick) for c in range(min(cols), max(cols) + 1)}
    if kind == "tight":
        a, b = chars
        shift = 4 if a == ":" else 3
        return at(a, shift) | at(b, cell - shift)
    raise ValueError(kind)


def add_ligatures(font):
    cmap = font.getBestCmap()
    glyf, hmtx = font["glyf"], font["hmtx"]
    adv = hmtx[cmap[ord("a")]][0]
    spacer = "LIG"
    if spacer not in glyf:
        glyf[spacer] = TTGlyphPen(None).glyph()
        hmtx[spacer] = (adv, 0)
    rules = []
    for chars, kind in LIGATURES:
        names = [cmap[ord(c)] for c in chars]
        lig = "_".join(names) + ".liga"
        shift = (len(chars) - 1) * 16  # глиф стоит на месте последнего знака и рисует влево
        set_outline(font, lig, {(c - shift, p) for c, p in ligature_pixels(font, chars, kind)}, advance=adv)
        n = len(names)
        mark = " ".join(x + "'" for x in names)
        lines = [f"    ignore sub {names[0]} {mark};", f"    ignore sub {mark} {names[-1]};"]
        for i in range(n):
            ctx = [spacer] * i + [names[i] + "'"] + names[i + 1:]
            lines.append(f"    sub {' '.join(ctx)} by {spacer if i < n - 1 else lig};")
        rules.append(lines)
    font.setGlyphOrder(list(glyf.glyphOrder))
    fea = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", "languagesystem cyrl dflt;",
           "feature calt {"]
    for i, lines in enumerate(rules):
        fea += [f"  lookup L{i} {{", *lines, f"  }} L{i};"]
    fea.append("} calt;")
    addOpenTypeFeaturesFromString(font, "\n".join(fea))


# --- имена ------------------------------------------------------------------------------

def rename(font, style):
    names = font["name"]
    full = FAMILY if style == "Regular" else f"{FAMILY} {style}"
    ps = f"NihilPixel-{style.replace(' ', '')}"
    for nid in (16, 17, 21, 22, 25):
        names.removeNames(nameID=nid)
    for nid, text in ((1, FAMILY), (2, style), (3, f"{ps};nihil"), (4, full), (6, ps)):
        names.setName(text, nid, 3, 1, 0x409)
        names.setName(text, nid, 1, 0, 0)
    names.setName("Nihil Pixel is a modified version of Terminess Nerd Font / Terminus (OFL 1.1): Russian "
                  "lowercase forms, cell-bound italics and pixel ligatures for the Nihil Omarchy style.",
                  10, 3, 1, 0x409)
    italic, bold = "Italic" in style, "Bold" in style
    os2 = font["OS/2"]
    os2.fsSelection = (os2.fsSelection & ~0b1100001) | (1 if italic else 0) | (32 if bold else 0) | \
        (64 if not (italic or bold) else 0)
    font["head"].macStyle = (1 if bold else 0) | (2 if italic else 0)
    font["post"].italicAngle = -6.0 if italic else 0.0
    font["hhea"].caretSlopeRise, font["hhea"].caretSlopeRun = (9, 1) if italic else (1, 0)
    for tag in ("BDF ", "PfEd"):  # метаданные исходного BDF-шрифта (имя Terminus) — не нужны
        if tag in font:
            del font[tag]


def build(path, src, weight, dst):
    base = TTFont(path)
    fix_cyrillic(base, src, weight)
    add_ligatures(base)
    out = []
    for italic in (False, True):
        font = copy.deepcopy(base) if italic else base
        style = ("Bold " if weight == "Bold" else "") + ("Italic" if italic else "")
        style = style.strip() or "Regular"
        if italic:
            italicize(font)
        rename(font, style)
        target = os.path.join(dst, f"NihilPixel-{style.replace(' ', '')}.ttf")
        font.save(target)
        out.append(target)
    return out


def main():
    regular, bold, dst = sys.argv[1:4]
    os.makedirs(dst, exist_ok=True)
    src = terminus_source()
    for path in build(regular, src, "Regular", dst) + build(bold, src, "Bold", dst):
        print(path)


if __name__ == "__main__":
    main()
