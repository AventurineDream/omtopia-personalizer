#!/usr/bin/env python3
"""Nihil Dot — Doto с кириллицей.

Doto (OFL 1.1, Reserved Font Name «Doto») рисует буквы точками на сетке: шаг 100 единиц, заглавные 5×7
(ряды 0–6), строчные 5×5 (ряды 0–4), выносные элементы до ряда 6 и −2, диакритика на ряду 7. Шрифт
переменный (wght 100–900, ROND 0–100). Новая буква собирается из копий одной точки Doto вместе с её
дельтами gvar: дельты не зависят от сдвига, поэтому кириллица меняет толщину и округлость точек ровно
так же, как латиница.

Лигатуры == === != !== -> <- => :: нарисованы точками той же сетки (calt, спейсеры как у Fira Code).

Изменённая версия OFL-шрифта не может называться Doto — семейство переименовано в «Nihil Dot».

    uv run --with fonttools scripts/nihil-dot.py [Doto.ttf] [NihilDot.ttf]
"""
import copy
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(FONTS, "Doto.ttf")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(FONTS, "NihilDot.ttf")
FAMILY = "Nihil Dot"
PITCH = 100

# Кириллица, совпадающая с латиницей по форме, берёт глиф Doto как есть.
SAME = {
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "Ё": "Ë", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "ё": "ë",
}

# Точечные карты: (верхний ряд, строки сверху вниз). 5 колонок, «#» — точка.
CAPS = {
    "Б": (6, ["#####", "#....", "#....", "####.", "#...#", "#...#", "####."]),
    "Г": (6, ["#####", "#....", "#....", "#....", "#....", "#....", "#...."]),
    "Д": (6, [".###.", ".#.#.", ".#.#.", ".#.#.", ".#.#.", ".#.#.", "#####", "#...#"]),
    "Ж": (6, ["#.#.#", "#.#.#", ".###.", "..#..", ".###.", "#.#.#", "#.#.#"]),
    "З": (6, [".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."]),
    "И": (6, ["#...#", "#...#", "#..##", "#.#.#", "##..#", "#...#", "#...#"]),
    "Й": (7, [".###.", "#...#", "#...#", "#..##", "#.#.#", "##..#", "#...#", "#...#"]),
    "Л": (6, [".####", ".#..#", ".#..#", ".#..#", ".#..#", ".#..#", "#...#"]),
    "П": (6, ["#####", "#...#", "#...#", "#...#", "#...#", "#...#", "#...#"]),
    "У": (6, ["#...#", "#...#", "#...#", ".####", "....#", "#...#", ".###."]),
    "Ф": (6, ["..#..", ".###.", "#.#.#", "#.#.#", "#.#.#", ".###.", "..#.."]),
    "Ц": (6, ["#..#.", "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", "#####", "....#"]),
    "Ч": (6, ["#...#", "#...#", "#...#", ".####", "....#", "....#", "....#"]),
    "Ш": (6, ["#.#.#", "#.#.#", "#.#.#", "#.#.#", "#.#.#", "#.#.#", "#####"]),
    "Щ": (6, ["#.#.#", "#.#.#", "#.#.#", "#.#.#", "#.#.#", "#.#.#", "#####", "....#"]),
    "Ъ": (6, ["##...", ".#...", ".#...", ".###.", ".#..#", ".#..#", ".###."]),
    "Ы": (6, ["#...#", "#...#", "#...#", "###.#", "#.#.#", "#.#.#", "###.#"]),
    "Ь": (6, ["#....", "#....", "#....", "####.", "#...#", "#...#", "####."]),
    "Э": (6, [".###.", "#...#", "....#", ".####", "....#", "#...#", ".###."]),
    "Ю": (6, ["#..#.", "#.#.#", "#.#.#", "###.#", "#.#.#", "#.#.#", "#..#."]),
    "Я": (6, [".####", "#...#", "#...#", ".####", ".#..#", "#...#", "#...#"]),
}
LOWER = {
    "б": (6, ["..###", ".#...", "#.##.", "##..#", "#...#", "#...#", ".###."]),
    "в": (4, ["####.", "#...#", "####.", "#...#", "####."]),
    "г": (4, ["#####", "#....", "#....", "#....", "#...."]),
    "д": (4, [".###.", ".#.#.", ".#.#.", ".#.#.", "#####", "#...#"]),
    "ж": (4, ["#.#.#", ".###.", "..#..", ".###.", "#.#.#"]),
    "з": (4, [".###.", "#...#", "..##.", "#...#", ".###."]),
    "и": (4, ["#...#", "#..##", "#.#.#", "##..#", "#...#"]),
    "й": (6, ["#...#", ".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#"]),
    "к": (4, ["#...#", "#..#.", "###..", "#..#.", "#...#"]),
    "л": (4, [".####", ".#..#", ".#..#", ".#..#", "#...#"]),
    "м": (4, ["#...#", "##.##", "#.#.#", "#...#", "#...#"]),
    "н": (4, ["#...#", "#...#", "#####", "#...#", "#...#"]),
    "п": (4, ["#####", "#...#", "#...#", "#...#", "#...#"]),
    "т": (4, ["#####", "..#..", "..#..", "..#..", "..#.."]),
    "ф": (6, ["..#..", "..#..", ".###.", "#.#.#", "#.#.#", "#.#.#", ".###.", "..#..", "..#.."]),
    "ц": (4, ["#..#.", "#..#.", "#..#.", "#..#.", "#####", "....#"]),
    "ч": (4, ["#...#", "#...#", ".####", "....#", "....#"]),
    "ш": (4, ["#.#.#", "#.#.#", "#.#.#", "#.#.#", "#####"]),
    "щ": (4, ["#.#.#", "#.#.#", "#.#.#", "#.#.#", "#####", "....#"]),
    "ъ": (4, ["##...", ".#...", ".###.", ".#..#", ".###."]),
    "ы": (4, ["#...#", "#...#", "###.#", "#.#.#", "###.#"]),
    "ь": (4, ["#....", "#....", "####.", "#...#", "####."]),
    "э": (4, [".###.", "#...#", "..###", "#...#", ".###."]),
    "ю": (4, ["#..#.", "#.#.#", "###.#", "#.#.#", "#..#."]),
    "я": (4, [".####", "#...#", ".####", ".#..#", "#...#"]),
}
# Ещё знаки, которых нет в Doto и которые встречаются в русском тексте.
EXTRA = {
    "№": (6, ["#..#.", "##.#.", "#.##.", "#..#.", "#..##", "#..#.", "#..##"]),
}


def dot_source(font):
    """Контур нижней левой точки «H» (ячейка 0,0), его точки и полные дельты всех вариаций."""
    name = font.getBestCmap()[ord("H")]
    glyf = font["glyf"][name]
    coords = glyf.getCoordinates(font["glyf"])[0]
    ends = glyf.endPtsOfContours
    start = 0
    for ci, end in enumerate(ends):
        pts = list(coords[start:end + 1])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < PITCH and max(ys) < PITCH:
            flags = list(glyf.flags[start:end + 1])
            deltas = []
            for tv in font["gvar"].variations[name]:
                full = tv.coordinates
                if any(c is None for c in full):
                    # calcInferredDeltas меняет вариацию на месте — считаем на копии, «H» не трогаем.
                    tmp = copy.deepcopy(tv)
                    tmp.calcInferredDeltas(list(coords) + [(0, 0)] * 4, list(ends))
                    full = tmp.coordinates
                deltas.append((tv.axes, [(round(dx), round(dy)) for dx, dy in full[start:end + 1]]))
            return pts, flags, deltas
        start = end + 1
    raise SystemExit("no dot in H")


def build_glyph(rows, top, dot):
    pts, flags, deltas = dot
    coords, gflags, ends = [], [], []
    for r, row in enumerate(rows):
        y = (top - r) * PITCH
        for c, ch in enumerate(row):
            if ch != "#":
                continue
            x = c * PITCH
            coords += [(px + x, py + y) for px, py in pts]
            gflags += flags
            ends.append(len(coords) - 1)
    g = Glyph()
    g.numberOfContours = len(ends)
    g.coordinates = GlyphCoordinates(coords)
    g.flags = bytearray(gflags)
    g.endPtsOfContours = ends
    g.program = ttProgram.Program()
    g.program.fromBytecode(b"")
    variations = []
    for axes, d in deltas:
        per_point = []
        for _ in ends:
            per_point += d
        variations.append(TupleVariation(axes, per_point + [(0, 0)] * 4))
    return g, variations


# Лигатуры (calt, как у Fira Code): первые знаки → пустые спейсеры шириной ячейки, последний → глиф,
# нарисованный влево на всю группу. Ячейка — 6 колонок точек (5 + промежуток), ряды 0–6.
def _bars(rows, width):
    return {(c, r) for r in rows for c in range(width)}


def _diagonal(c0):
    return {(c0 + i, i) for i in range(7)}


_HEAD_R = {(-3, 6), (-2, 5), (-1, 4), (0, 3), (-1, 2), (-2, 1), (-3, 0)}  # «>», остриё в (0, 3)
LIGATURES = {
    "!==": _bars((2, 4), 17) | _diagonal(5),
    "===": _bars((2, 4), 17),
    "!=": _bars((2, 4), 11) | _diagonal(2),
    "==": _bars((2, 4), 11),
    "->": {(c, 3) for c in range(10)} | {(c + 10, r) for c, r in _HEAD_R},
    "<-": {(c, 3) for c in range(1, 11)} | {(-c, r) for c, r in _HEAD_R},
    "=>": {(c, r) for r in (2, 4) for c in range(9)} | {(c + 10, r) for c, r in _HEAD_R},
    "::": {(c + 1, r) for c, r in ((1, 5), (0, 4), (1, 4), (2, 4), (1, 3), (1, 1), (0, 0), (1, 0), (2, 0), (1, -1))}
          | {(c + 6, r) for c, r in ((1, 5), (0, 4), (1, 4), (2, 4), (1, 3), (1, 1), (0, 0), (1, 0), (2, 0), (1, -1))},
}


def build_cells(cells, dot):
    """Глиф из точек (колонка, ряд от базовой линии) — как build_glyph, но без карты строк."""
    rows = {}
    for c, r in cells:
        rows.setdefault(r, set()).add(c)
    top = max(rows)
    lines, lo = [], min(c for c, _ in cells)
    for r in range(top, min(rows) - 1, -1):
        lines.append("".join("#" if c in rows.get(r, ()) else "." for c in range(lo, max(c for c, _ in cells) + 1)))
    g, variations = build_glyph(lines, top, dot)
    if lo:
        g.coordinates.translate((lo * PITCH, 0))
    return g, variations


def add_ligatures(font, dot):
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    glyf, gvar, hmtx = font["glyf"], font["gvar"], font["hmtx"]
    cmap = font.getBestCmap()
    advance = hmtx[cmap[ord("H")]][0]
    cell = advance // PITCH
    spacer = "LIG"
    empty = Glyph()
    empty.numberOfContours = 0
    glyf[spacer] = empty
    gvar.variations[spacer] = []
    hmtx[spacer] = (advance, 0)
    rules = []
    for chars, cells in sorted(LIGATURES.items(), key=lambda kv: -len(kv[0])):
        names = [cmap[ord(c)] for c in chars]
        lig = "_".join(names) + ".liga"
        shift = (len(chars) - 1) * cell  # глиф на месте последнего знака, рисует влево
        g, variations = build_cells({(c - shift, r) for c, r in cells}, dot)
        glyf[lig] = g
        gvar.variations[lig] = variations
        g.recalcBounds(glyf)
        hmtx[lig] = (advance, g.xMin)
        mark = " ".join(n + "'" for n in names)
        lines = [f"ignore sub {names[0]} {mark};", f"ignore sub {mark} {names[-1]};"]
        for i in range(len(names)):
            ctx = [spacer] * i + [names[i] + "'"] + names[i + 1:]
            lines.append(f"sub {' '.join(ctx)} by {spacer if i < len(names) - 1 else lig};")
        rules.append(lines)
    font.setGlyphOrder(list(glyf.glyphOrder))
    fea = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", "languagesystem cyrl dflt;", "feature calt {"]
    for i, lines in enumerate(rules):
        fea += [f"  lookup L{i} {{"] + ["    " + x for x in lines] + [f"  }} L{i};"]
    fea.append("} calt;")
    addOpenTypeFeaturesFromString(font, "\n".join(fea))


def main():
    font = TTFont(SRC)
    dot = dot_source(font)
    glyf, gvar, hmtx = font["glyf"], font["gvar"], font["hmtx"]
    advance = hmtx[font.getBestCmap()[ord("H")]][0]
    new_cmap = {}
    for ch, (top, rows) in {**CAPS, **LOWER, **EXTRA}.items():
        name = "uni%04X" % ord(ch)
        g, variations = build_glyph(rows, top, dot)
        glyf[name] = g
        gvar.variations[name] = variations
        g.recalcBounds(glyf)
        hmtx[name] = (advance, g.xMin)
        new_cmap[ord(ch)] = name
    cmap = font.getBestCmap()
    for ch, latin in SAME.items():
        new_cmap[ord(ch)] = cmap[ord(latin)]
    # glyf[name] = … сам дописывает имя в порядок глифов; остальные таблицы берут его оттуда.
    font.setGlyphOrder(list(glyf.glyphOrder))
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update(new_cmap)
    add_ligatures(font, dot)
    # HVAR не знает новых глифов; ширина у всех одна (моноширинный), рендеры возьмут её из gvar.
    if "HVAR" in font:
        del font["HVAR"]
    names = font["name"]
    for rec in names.names:
        text = rec.toUnicode()
        if "Doto" in text:
            rec.string = text.replace("Doto", FAMILY if rec.nameID != 6 and rec.nameID != 25 else "NihilDot")
    names.setName(
        "Nihil Dot is a modified version of Doto (OFL 1.1, Reserved Font Name \"Doto\") with Cyrillic "
        "letters and dot ligatures added for the Nihil Omarchy style.", 10, 3, 1, 0x409)
    font["OS/2"].ulCodePageRange1 |= 1 << 2  # 1251 Cyrillic
    font["OS/2"].ulUnicodeRange1 |= 1 << 9  # Cyrillic block
    font.save(DST)
    print(f"{DST}: +{len(CAPS) + len(LOWER) + len(EXTRA)} drawn, +{len(SAME)} shared")


if __name__ == "__main__":
    main()
