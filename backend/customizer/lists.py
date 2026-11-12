"""`list <категория>` — строки для overlay (категории настроек и простые списки; остальное —
lists_more.py)."""
import shutil

from . import jsonio, paths, state, tweaks
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
    ("hexagon", "Honeycomb opening from the centre"),
    ("contagion", "Pixel colonies eat through the old wallpaper, the front flashes in the new theme's brightest colour"),
    ("outline", "Draws the picture's own lines, then the world grows out of them. Light: no model, no background work"),
    ("outline-cut", "Outline with cut-out: draws the character's outline, fills it in, then the world grows out of it. The character is found by BiRefNet in the background (NPU / GPU); until a wallpaper is cut out, its own lines are drawn"),
    ("random", "A random effect every time"), ("none", "No animation"),
]

# Карты outline режет scripts/wallpaper-fx-outline плагина обоев (venv с BiRefNet, ставится по запросу).
FX_OUTLINE_VENV = paths.HOME / ".local/share/wallpaper-fx/venv/bin/python"
FX_OUTLINE_CACHE = paths.CACHE / "wallpaper-fx"


def _outline_status():
    """Устройство и очередь — из файлов воркера, без запуска python."""
    try:
        device = (FX_OUTLINE_CACHE / "device").read_text().strip()
    except OSError:
        device = "—"
    try:
        queued = sum(1 for l in (FX_OUTLINE_CACHE / "outline/queue").read_text().splitlines() if l)
    except OSError:
        queued = 0
    return t("Device: %s · in queue: %s", device, str(queued))


FX_PLUGIN = "kamradsmeshnyavy.background"


def _wallpaper_fx():
    out = []
    # Установлен, но выключен (например, shell.json переписан обновлением) — переходы молча стоковые.
    if not state.plugin_enabled(FX_PLUGIN):
        out.append(f"{t('⚠ Wallpaper FX is off — ⏎ turn it on')}\tenable-plugin\t\t0\t"
                   f"{t('The plugin is installed but not enabled in shell.json, so wallpapers change with the stock slanted wipe and the effects below do nothing.')}"
                   f"\\n\\n{t('⏎ — enable it (omarchy plugin enable %s)', FX_PLUGIN)}")
    hdr = lambda title, sid: f"{t(title)}\tsection:{sid}\t\t0\t\theader"
    out.append(hdr("Settings", "settings"))
    out += tweaks.prefixed(tweaks.list_tweaks("FX_TWEAKS"))
    # Живые обои (видео / GIF) играет owe — его настройки здесь же, если он установлен.
    if shutil.which("owe"):
        out.append(hdr("Live wallpapers (owe)", "owe"))
        out.append(f"{t('⏯ Pause / resume the live wallpaper now')}\towe-toggle\t\t0\t"
                   + t("Manual pause of the video wallpaper until you resume it (owe pause / owe resume). Pick videos in the wallpaper picker: type live to show only video and GIF wallpapers."))
        out += tweaks.prefixed(tweaks.list_tweaks("OWE_TWEAKS"))
    out.append(hdr("Transitions", "transitions"))
    cur = jsonio.read_object(FX_CFG).get("type") or "slant"
    for e, desc in _FX_EFFECTS:
        out.append(f"{e}\t{e}\t\t{1 if e == cur else 0}\t{t(desc)}\\n\\n{t('⏎ — select · p — play it on the desktop')}")
    # Разовые действия — отдельным разделом и с ⚡ (как ⚡ Cache thumbnails), чтобы не путались с переходами.
    out.append(hdr("Actions", "actions"))
    one_off = t("One-off action for outline-cut — not a transition.")
    if FX_OUTLINE_VENV.exists():
        out.append(f"{t('⚡ Prepare characters for the whole theme')}\toutline-warm\t\t0\t{one_off}\\n\\n"
                   f"{t('Queues every wallpaper of the current theme for cut-out, so the first change to any of them already shows the character instead of lines. Without it, wallpapers are cut out one by one as you switch to them.')}"
                   f"\\n\\n{_outline_status()}\\n\\n{t('⏎ — run')}")
    else:
        out.append(f"{t('⚡ Install the cut-out model')}\toutline-install\t\t0\t{one_off}\\n\\n"
                   f"{t('To find characters, outline-cut needs BiRefNet (onnxruntime) in its own venv: ~/.local/share/wallpaper-fx/venv. Until then it draws the picture own lines.')}"
                   f"\\n\\n{t('⏎ — install in a terminal, then prepare the theme wallpapers')}")
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
