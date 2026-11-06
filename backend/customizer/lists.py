"""`list <категория>` — строки для overlay. Перенесённые категории — здесь; остальные пока отдаёт
bash (customizer.sh с CUSTOMIZER_LEGACY=1), см. commands.py."""
from . import jsonio, paths, tweaks
from .i18n import t

FX_CFG = paths.CONFIG / "wallpaper-transition.json"

_FX_EFFECTS = [
    ("slant", "Slanted wipe from the centre — stock Omarchy"), ("fade", "Smooth cross-fade"),
    ("wipe", "Wipe along the “Angle”"), ("wave", "Wipe with a wavy edge"),
    ("grow", "A circle grows from a point (center / cursor / random)"),
    ("outer", "A circle shrinks to a point — the new wallpaper comes from the edges"),
    ("diamond", "A diamond from a point"), ("clock", "Radial sweep, like a clock hand"), ("blinds", "Blinds"),
    ("doors", "Doors opening from the middle"), ("mosaic", "Squares in random order"), ("dissolve", "Pixel noise"),
    ("pixelize", "Pixels grow and shrink back"), ("ripple", "Ripples on water"), ("swirl", "Swirl into the centre"),
    ("crosszoom", "Radial blur with zoom"), ("slide", "The new wallpaper pushes the old one out (along the “Angle”)"),
    ("zoom", "The old one flies forward, the new one fades in"), ("glitch", "Torn stripes and channel split"),
    ("burn", "Burns through in spots with a glowing edge"), ("waterdrop", "A drop: waves from a point, fading out"),
    ("hexagon", "Honeycomb opening from the centre"), ("random", "A random effect every time"), ("none", "No animation"),
]


def _wallpaper_fx():
    out = tweaks.prefixed(tweaks.list_tweaks("FX_TWEAKS"))
    cur = jsonio.read_object(FX_CFG).get("type") or "slant"
    for e, desc in _FX_EFFECTS:
        out.append(f"{e}\t{e}\t\t{1 if e == cur else 0}\t{t(desc)}\\n\\n{t('⏎ — select · p — play it on the desktop')}")
    return out


def _glyph():
    rows = [
        (t("⚡ Test notification sweep  (p)"), "test:normal", t("Run a single perimeter Glyph light sweep around the screen.")),
        (t("🔴 Test critical alert sweep"), "test:critical", t("Run a double signal-red perimeter Glyph sweep around the screen.")),
        (t("🔋 Test charger rising beams"), "test:charge", t("Run dual rising light beams from the bottom corners.")),
    ]
    return [f"{a}\t{b}\t\t0\t{c}" for a, b, c in rows] + tweaks.prefixed(tweaks.list_tweaks("GLYPH_TWEAKS"))


LISTS = {
    "bar-tweaks": lambda: tweaks.list_tweaks("TWEAKS"),
    "lock-tweaks": lambda: tweaks.list_tweaks("LOCK_TWEAKS"),
    "widgets": lambda: tweaks.list_tweaks("WIDGET_TWEAKS") + tweaks.list_tweaks("DOTMATRIX_TWEAKS"),
    "dashboard": lambda: tweaks.list_tweaks("DASH_TWEAKS"),
    "osd": lambda: tweaks.list_tweaks("OSD_TWEAKS"),
    "notifications": lambda: tweaks.list_tweaks("NOTIFY_TWEAKS"),
    "wallpaper-fx": _wallpaper_fx,
    "glyph": _glyph,
}


from . import lists_more as _m  # noqa: E402

LISTS.update({
    "presets": _m.presets, "styles": _m.styles, "windows": _m.windows, "sounds": _m.sounds, "fonts": _m.fonts,
    "dotify": _m.dotify, "walls": _m.walls, "themes": _m.themes, "anims": _m.anims, "opacity": _m.opacity,
    "blur": _m.blur, "shaders": _m.shaders, "bar-layouts": _m.bar_layouts, "bar-skins": _m.bar_skins,
    "bar-widgets": _m.bar_widgets, "lock": _m.lock, "launcher": _m.launcher, "theme-switcher": _m.theme_switcher,
})


def list_category(category: str, extra: str = ""):
    """Строки категории или None, если она ещё не перенесена."""
    if category == "theme-walls":
        return _m.theme_walls(extra)
    fn = LISTS.get(category)
    return None if fn is None else fn()
