#!/usr/bin/env python3
"""DotMatrix Dots — «точки везде»: каждый знак DotMatrix Pixel (Terminus) набран круглыми точками.

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
        [DejaVuSansMono.ttf DejaVuSansMono-Bold.ttf]
"""
import math
import os
import sys

import freetype
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent, Glyph

PPEM = 16           # Terminus 8×16: штрих в один пиксель
STEP = 1000 / PPEM  # 62.5 ед. на пиксель
CELL = 8            # ширина ячейки в пикселях (advance 500)
STYLES = {          # файл DotMatrix Pixel → (стиль, радиус точки в единицах, запасной шрифт: 0 обычный / 1 жирный)
    "Regular": ("Regular", 21, 0),
    "Bold": ("Bold", 25, 1),
    "Italic": ("Italic", 21, 0),
    "BoldItalic": ("Bold Italic", 25, 1),
}
FAMILY_OLD, FAMILY_NEW = "DotMatrix Pixel", "DotMatrix Dots"
PS_OLD, PS_NEW = "DotMatrixPixel", "DotMatrixDots"
DROP = ("EBDT", "EBLC", "EBSC", "hdmx", "LTSH", "VDMX", "fpgm", "prep", "cvt ", "gasp")


def dot_glyph(r):
    """Круг из 8 внеконтурных точек TrueType (окружность квадратичными кривыми), центр в (0, 0)."""
    k = r / math.cos(math.pi / 8)
    pts = [(round(k * math.cos(math.pi / 8 * (2 * i + 1))), round(k * math.sin(math.pi / 8 * (2 * i + 1))))
           for i in range(8)]
    pen = TTGlyphPen(None)
    pen.qCurveTo(*pts, None)
    pen.closePath()
    return pen.glyph()


def pixels(face, gid):
    """Закрашенные пиксели глифа на 32 px: [(x, y)] в пикселях от начала глифа и базовой линии."""
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


def build(src, dst, style, radius, extra=None):
    font = TTFont(src)
    for tag in DROP:
        if tag in font:
            del font[tag]
    glyf = font["glyf"]
    order = font.getGlyphOrder()
    face = freetype.Face(src)
    face.set_pixel_sizes(0, PPEM)

    dot = dot_glyph(radius)
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

    # Имена: семейство DotMatrix Dots, PostScript DotMatrixDots-<стиль>.
    for rec in font["name"].names:
        try:
            s = rec.toUnicode()
        except UnicodeDecodeError:
            continue
        s2 = s.replace(FAMILY_OLD, FAMILY_NEW).replace(PS_OLD, PS_NEW)
        if s2 != s:
            rec.string = s2
    font["maxp"].maxComponentElements = max(len(glyf[n].components) if glyf[n].isComposite() else 0
                                            for n in font.getGlyphOrder())
    font["maxp"].maxComponentDepth = 1
    font.save(dst)
    return len(order) + added, total


def main():
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    fallbacks = sys.argv[3:5]
    os.makedirs(out_dir, exist_ok=True)
    for key, (style, radius, fbi) in STYLES.items():
        src = os.path.join(src_dir, f"DotMatrixPixel-{key}.ttf")
        if not os.path.isfile(src):
            sys.exit(f"нет {src} — сначала omarchy-font-profile build-fonts")
        dst = os.path.join(out_dir, f"DotMatrixDots-{key}.ttf")
        extra = fallbacks[fbi] if len(fallbacks) > fbi and os.path.isfile(fallbacks[fbi]) else None
        n, dots = build(src, dst, style, radius, extra)
        print(f"{os.path.basename(dst)}: {n} глифов, {dots} точек, {os.path.getsize(dst) // 1024} КБ")


if __name__ == "__main__":
    main()
