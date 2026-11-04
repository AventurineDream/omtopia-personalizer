#!/usr/bin/env python3
"""Точечные шрифты «точки везде»: каждый знак DotMatrix Pixel (Terminus) набран круглыми точками.

DotMatrix LED — Terminus 8×16: штрих в одну крупную точку, как у светодиодного табло. С --halftone
дополнительно DotMatrix Halftone — 16×32: мелкие точки в два ряда (по умолчанию не собирается: ~28 МБ
на начертание).

Точка — скруглённый квадрат, 96 % шага сетки (у жирных 99 %), как ячейка светодиодной матрицы: круглые
точки закрывали ~65 % того, что закрывает DotMatrix Pixel, текст на обычном кегле выходил бледным, и на
тёмной теме весь экран казался темнее; скруглённые квадраты — ~85 %, вблизи точки так же раздельные.

Дальше — про LED; Halftone устроен так же, только на 32 px.

DotMatrix Pixel (Terminus) покрывает латиницу, кириллицу, греческий, символы, псевдографику и значки
Nerd Font. Здесь каждый глиф растеризуется FreeType на 16 px — размере Terminus 8×16, где штрих в один
пиксель (на 32 px он двойной, и буквы выходили двойными рядами точек): для букв это встроенные битмапы
самого Terminus, для значков и пиксельных лигатур (их нет в битмапах) — контур на той же сетке, — и каждый
пиксель заменяется точкой, как у светодиодной матрицы. Знаков, которых в Terminus нет (₽ и ещё ~2300),
добавляются из DejaVu Sans Mono — растеризуются на той же сетке и встают по центру ячейки. Получается
точечный шрифт, где точками набран абсолютно любой знак, а не только то, что есть в Doto.

Точка — один глиф «.dot», знаки — составные глифы из ссылок на него (иначе по кругу на пиксель —
десятки мегабайт). Встроенные битмапы и хинтинг удаляются: иначе FreeType на 12–32 px рисовал бы
прежние квадраты. Жирные начертания — из DotMatrix Pixel Bold, точки чуть крупнее. Лигатуры (calt)
и метрики остаются от DotMatrix Pixel — шрифт моноширинный, годится и для терминала.

Производная Terminus (OFL 1.1) — не называется Terminus / Terminess.

    uv run --with fonttools --with freetype-py scripts/dotmatrix-dots.py <каталог с DotMatrixPixel-*.ttf> <каталог вывода> \
        [DejaVuSansMono.ttf DejaVuSansMono-Bold.ttf] [--halftone]   # DotMatrixLED-*.ttf (+ DotMatrixHalftone-*.ttf)
"""
import math
import os
import sys

import freetype
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent, Glyph

# Варианты: (семейство, PostScript-имя, размер растра Terminus в px).
VARIANTS = [("DotMatrix LED", "DotMatrixLED", 16)]
HALFTONE = ("DotMatrix Halftone", "DotMatrixHalftone", 32)
DOT, DOT_BOLD = 0.48, 0.495  # половина стороны точки в долях шага сетки (сторона 96 % / 99 %)
DOT_CORNER = 0.30            # скругление углов точки — доля стороны
STYLES = {          # файл DotMatrix Pixel → (стиль, жирный ли — радиус и запасной шрифт: 0 обычный / 1 жирный)
    "Regular": ("Regular", 0),
    "Bold": ("Bold", 1),
    "Italic": ("Italic", 0),
    "BoldItalic": ("Bold Italic", 1),
}
FAMILY_OLD, PS_OLD = "DotMatrix Pixel", "DotMatrixPixel"
PPEM, STEP, CELL = 16, 62.5, 8  # задаются set_grid()


def set_grid(ppem):
    global PPEM, STEP, CELL
    PPEM, STEP, CELL = ppem, 1000 / ppem, ppem // 2  # ячейка — advance 500 = пол-em
DROP = ("EBDT", "EBLC", "EBSC", "hdmx", "LTSH", "VDMX", "fpgm", "prep", "cvt ", "gasp")


def dot_glyph(r, corner=None):
    """Точка с центром в (0, 0): круг радиуса r или (corner — доля стороны) скруглённый квадрат стороной 2r.
    Скруглённый квадрат закрывает ячейку плотнее круга (~85 % против ~70 %) — текст на обычном кегле ярче,
    вблизи точки всё так же раздельные, как у светодиодной матрицы."""
    if corner is not None:
        h, c = r, max(1, round(2 * r * corner))
        pen = TTGlyphPen(None)
        pen.moveTo((round(h - c), round(-h)))
        pen.qCurveTo((round(h), round(-h)), (round(h), round(-h + c)))
        pen.lineTo((round(h), round(h - c)))
        pen.qCurveTo((round(h), round(h)), (round(h - c), round(h)))
        pen.lineTo((round(-h + c), round(h)))
        pen.qCurveTo((round(-h), round(h)), (round(-h), round(h - c)))
        pen.lineTo((round(-h), round(-h + c)))
        pen.qCurveTo((round(-h), round(-h)), (round(-h + c), round(-h)))
        pen.closePath()
        return pen.glyph()
    k = r / math.cos(math.pi / 8)
    pts = [(round(k * math.cos(math.pi / 8 * (2 * i + 1))), round(k * math.sin(math.pi / 8 * (2 * i + 1))))
           for i in range(8)]
    pen = TTGlyphPen(None)
    pen.qCurveTo(*pts, None)
    pen.closePath()
    return pen.glyph()


def pixels(face, gid):
    """Закрашенные пиксели глифа на PPEM px: [(x, y)] в пикселях от начала глифа и базовой линии."""
    try:
        face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    except freetype.FT_Exception:
        return []
    slot = face.glyph
    bm = slot.bitmap
    if bm.width == 0 or bm.rows == 0:
        return []
    buf, pitch = bm.buffer, bm.pitch
    out = []
    for row in range(bm.rows):
        for col in range(bm.width):
            if buf[row * pitch + (col >> 3)] & (0x80 >> (col & 7)):
                out.append((slot.bitmap_left + col, slot.bitmap_top - row - 1))
    return out


def fallback_pixels(face):
    """Запасной шрифт: кегль, при котором его моноширинный знак помещается в ячейку 8 px, и сдвиг к центру."""
    adv = face.max_advance_width / face.units_per_EM  # доля em
    ppem = int(CELL / adv)
    face.set_pixel_sizes(0, ppem)
    shift = (CELL - adv * ppem) / 2
    return ppem, shift


def dots_glyph(points, dx=0.0):
    comps = []
    for px, py in points:
        c = GlyphComponent()
        c.glyphName = ".dot"
        c.x = round((px + dx + 0.5) * STEP)
        c.y = round((py + 0.5) * STEP)
        c.flags = 0x4  # ROUND_XY_TO_GRID
        comps.append(c)
    g = Glyph()
    if comps:
        g.numberOfContours = -1
        g.components = comps
    else:
        g.numberOfContours = 0
    return g, len(comps)


def build(src, dst, style, radius, family, ps, extra=None, corner=None):
    font = TTFont(src)
    for tag in DROP:
        if tag in font:
            del font[tag]
    glyf = font["glyf"]
    order = font.getGlyphOrder()
    face = freetype.Face(src)
    face.set_pixel_sizes(0, PPEM)

    dot = dot_glyph(radius, corner)
    glyf.glyphs[".dot"] = dot
    font["hmtx"].metrics[".dot"] = (0, -round(radius))
    font.setGlyphOrder(order + [".dot"])
    glyf.glyphOrder = font.getGlyphOrder()

    total = 0
    for gid, name in enumerate(order):
        g, n = dots_glyph(pixels(face, gid))
        glyf.glyphs[name] = g
        total += n

    # Знаки, которых нет в Terminus, — из запасного моноширинного шрифта, на той же сетке.
    added = 0
    if extra:
        cmap = font.getBestCmap()
        fb = TTFont(extra)
        fface = freetype.Face(extra)
        _, shift = fallback_pixels(fface)
        new = []
        for cp, fname in sorted(fb.getBestCmap().items()):
            if cp in cmap or cp < 0x20:
                continue
            g, n = dots_glyph(pixels(fface, fb.getGlyphID(fname)), shift)
            if not n and fname not in ("space", "uni00A0"):
                continue
            name = f"dm.u{cp:04X}"
            glyf.glyphs[name] = g
            font["hmtx"].metrics[name] = (500, 0)
            new.append((cp, name))
            total += n
        font.setGlyphOrder(font.getGlyphOrder() + [n for _, n in new])
        glyf.glyphOrder = font.getGlyphOrder()
        for t in font["cmap"].tables:
            if t.isUnicode():
                for cp, name in new:
                    if cp <= 0xFFFF or t.format in (12, 13):
                        t.cmap[cp] = name
        added = len(new)

    # Имена: семейство и PostScript-имя варианта (DotMatrix LED / DotMatrixLED-<стиль> и т.д.).
    for rec in font["name"].names:
        try:
            s = rec.toUnicode()
        except UnicodeDecodeError:
            continue
        s2 = s.replace(FAMILY_OLD, family).replace(PS_OLD, ps)
        if s2 != s:
            rec.string = s2
    font["maxp"].maxComponentElements = max(len(glyf[n].components) if glyf[n].isComposite() else 0
                                            for n in font.getGlyphOrder())
    font["maxp"].maxComponentDepth = 1
    font.save(dst)
    return len(order) + added, total


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src_dir, out_dir = args[0], args[1]
    fallbacks = args[2:4]
    variants = VARIANTS + ([HALFTONE] if "--halftone" in sys.argv else [])
    os.makedirs(out_dir, exist_ok=True)
    for family, ps, ppem in variants:
        set_grid(ppem)
        for key, (style, bold) in STYLES.items():
            src = os.path.join(src_dir, f"DotMatrixPixel-{key}.ttf")
            if not os.path.isfile(src):
                sys.exit(f"нет {src} — сначала omarchy-font-profile build-fonts")
            dst = os.path.join(out_dir, f"{ps}-{key}.ttf")
            extra = fallbacks[bold] if len(fallbacks) > bold and os.path.isfile(fallbacks[bold]) else None
            radius = round((DOT_BOLD if bold else DOT) * STEP, 1)
            n, dots = build(src, dst, style, radius, family, ps, extra, DOT_CORNER)
            print(f"{os.path.basename(dst)}: {n} глифов, {dots} точек, {os.path.getsize(dst) // 1024} КБ")


if __name__ == "__main__":
    main()
