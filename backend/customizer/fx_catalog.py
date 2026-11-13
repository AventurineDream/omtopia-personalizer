"""Каталог Wallpaper FX — единственный источник переходов и их пригодности для random.

lists.py строит из него строки раздела Transitions (TSV-формат прежний, tests/compare_*.py
сверяют вывод с bash-эталоном), а scripts/gen_random_candidates.py генерирует из него
ui/RandomCandidates.js. Новый переход добавляется только сюда; после этого JS перегенерируется,
иначе tests/test_transition_metadata.py падает на рассинхроне.
"""

# (значение, описание, random_ok). random_ok=False только у «none»: клавиша r его не подхватывает.
# «random» — настоящий выбор (случайный эффект при каждой смене), остаётся пригодным.
FX_EFFECTS = [
    ("slant", "Slanted wipe from the centre — stock Omarchy", True), ("fade", "Smooth cross-fade", True),
    ("wipe", "Wipe along the “Angle”", True), ("wave", "Wipe with a wavy edge", True),
    ("grow", "A circle grows from a point (center / cursor / random)", True),
    ("outer", "A circle shrinks to a point — the new wallpaper comes from the edges", True),
    ("diamond", "A diamond from a point", True), ("clock", "Radial sweep, like a clock hand", True), ("blinds", "Blinds", True),
    ("doors", "Doors opening from the middle", True), ("mosaic", "Squares in random order", True), ("dissolve", "Pixel noise", True),
    ("pixelize", "Pixels grow and shrink back", True), ("ripple", "Ripples on water", True), ("swirl", "Swirl into the centre", True),
    ("crosszoom", "Radial blur with zoom", True), ("slide", "The new wallpaper pushes the old one out (along the “Angle”)", True),
    ("zoom", "The old one flies forward, the new one fades in", True), ("glitch", "Torn stripes and channel split", True),
    ("burn", "Burns through in spots with a glowing edge", True), ("waterdrop", "A drop: waves from a point, fading out", True),
    ("hexagon", "Honeycomb opening from the centre", True),
    ("hexreveal", "Honeycomb cells each opening from their own middle in a wave, with a lit rim (after Vitreus)", True),
    ("contagion", "Pixel colonies eat through the old wallpaper, the front flashes in the new theme's brightest colour", True),
    ("outline", "Draws the picture's own lines, then the world grows out of them. Light: no model, no background work", True),
    ("outline-cut", "Outline with cut-out: draws the character's outline, fills it in, then the world grows out of it. The character is found by BiRefNet in the background (NPU / GPU); until a wallpaper is cut out, its own lines are drawn", True),
    ("random", "A random effect every time", True), ("none", "No animation", False),
]

# Значения-переходы, доступные случайному выбору, и явно исключённые из него.
FX_RANDOM_OK = tuple(v for v, _d, ok in FX_EFFECTS if ok)
FX_RANDOM_EXCLUDED = tuple(v for v, _d, ok in FX_EFFECTS if not ok)
