"""Что стоит сейчас: тема, скин и раскладка бара, экран блокировки, пресет, стиль — как в customizer.sh.

Ответы, которые дорого считать (скин бара, прозрачность), запоминаются до конца запроса:
`reset()` зовёт commands.run перед каждой командой — значения не протухают между запросами."""
import json
import os
import re

from . import fsutil, i18n, jsonio, paths

P = paths.CONFIG
PLUGINS = P / "plugins"
BAR_DIR = PLUGINS / "kamradsmeshnyavy.bar"
LOCK_PLUGIN = PLUGINS / "kamradsmeshnyavy.lock"
MENU_PLUGIN = PLUGINS / "kamradsmeshnyavy.menu"
USER_SKINS = P / "bar-skins"
USER_LAYOUTS = P / "bar-layouts"
USER_PRESETS = P / "customizer/presets"
USER_STYLES = P / "customizer/styles"
PRESET_DIR = paths.PLUGIN / "presets"
STYLE_DIR = paths.PLUGIN / "styles"
PRESET_CFG = P / "customizer/preset-apply.json"
STYLE_CFG = P / "customizer/style-apply.json"
LOCK_CFG = P / "lock-design.json"
MENU_CFG = P / "extensions/menu-skin.json"
GLYPH_CFG = P / "glyph.json"
SOUND_CFG = P / "sounds.json"
FX_CFG = P / "wallpaper-transition.json"
PICKER_CFG = P / "image-picker.json"
ACTIVE_PRESET = paths.STATE / "active-preset"
ACTIVE_STYLE = paths.STATE / "active-style"
LAST_PRESET = paths.STATE / "last-preset.json"
ANIM_ACTIVE = paths.STATE / "animations.lua"
OPACITY = paths.PLUGIN / "scripts/opacity.sh"
BLUR = paths.PLUGIN / "scripts/blur.sh"
TOGGLE = paths.PLUGIN / "scripts/crt-toggle.sh"

_memo = {}


def reset():
    _memo.clear()


def _cached(name, fn):
    if name not in _memo:
        _memo[name] = fn()
    return _memo[name]


def alt(*values):
    """jq `a // b`: первое, что не null и не false."""
    for v in values:
        if v is not None and v is not False:
            return v
    return values[-1] if values else None


def plugin_enabled(pid: str) -> bool:
    """Плагин включён в shell.json (.plugins или сам бар): установленный, но выключенный ничего не делает."""
    shell = jsonio.read_object(paths.SHELL_JSON)
    bar = shell.get("bar")
    if isinstance(bar, dict) and bar.get("id") == pid:
        return True
    plugins = shell.get("plugins")
    return isinstance(plugins, list) and any(isinstance(p, dict) and p.get("id") == pid for p in plugins)


def theme_name() -> str:
    v = fsutil.read_text(paths.THEME_NAME)
    return "default" if v is None else v


def current_bg() -> str:
    """readlink -f current/background: все компоненты, кроме последнего, должны существовать —
    тогда путь канонизируется, даже если самой ссылки нет."""
    try:
        return os.path.realpath(paths.CURRENT_BG) if os.path.isdir(os.path.dirname(paths.CURRENT_BG)) else ""
    except OSError:
        return ""


def lock_current() -> str:
    data = jsonio.read(LOCK_CFG)
    if not isinstance(data, dict):
        return "classic"
    return jsonio.tostring(alt(data.get("design"), "classic"))


def lock_thumb_name(design_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._\n-]", "-", design_id)


def launcher_current() -> str:
    data = jsonio.read(MENU_CFG)
    if not isinstance(data, dict):
        return "constellation"
    return jsonio.tostring(alt(data.get("skin"), "constellation"))


def glyph_status() -> str:
    return "on" if jsonio.read_object(GLYPH_CFG).get("glyphEnabled") is True else "off"


def _no_note(obj):
    return {k: v for k, v in obj.items() if not re.match(r"^note(_[a-z]+)?$", k)} if isinstance(obj, dict) else obj


def current_skin() -> str:
    def compute():
        if not fsutil.nonempty(paths.BAR_SKIN):
            return "stock"
        cur = _no_note(jsonio.read(paths.BAR_SKIN))
        for f in fsutil.glob_sorted(USER_SKINS, ".json") + fsutil.glob_sorted(BAR_DIR / "skins", ".json"):
            if _no_note(jsonio.read(f)) == cur and cur is not None:
                return os.path.basename(f)[:-5]
        return "custom"
    return _cached("skin", compute)


def _layout_canon(obj):
    if not isinstance(obj, dict):
        return None
    return {"position": alt(obj.get("position"), "top"), "centerAnchor": alt(obj.get("centerAnchor"), ""),
            "layout": obj.get("layout")}


def current_layout() -> str:
    bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
    cur = _layout_canon(bar if isinstance(bar, dict) else {})
    for f in fsutil.glob_sorted(USER_LAYOUTS, ".json") + fsutil.glob_sorted(BAR_DIR / "layouts", ".json"):
        if _layout_canon(jsonio.read(f)) == cur:
            return os.path.basename(f)[:-5]
    return "custom"


def opacity_current() -> str:
    return _cached("opacity", lambda: fsutil.run([str(OPACITY), "current"]))


def section_on(cfg, key) -> bool:
    data = jsonio.read(cfg)
    if not isinstance(data, dict) or key not in data:
        return True
    return jsonio.tostring(data[key]) != "false"


def _str(v) -> str:
    return "" if v is None or v is False else jsonio.tostring(v)


def preset_matches(path) -> bool:
    d = jsonio.read(path)
    d = d if isinstance(d, dict) else {}
    lock = d.get("lock")
    p_theme, p_skin = _str(d.get("theme")), _str(d.get("barSkin"))
    p_lock = _str(lock.get("design")) if isinstance(lock, dict) else ""
    if section_on(PRESET_CFG, "presetTheme") and p_theme and p_theme != theme_name():
        return False
    if section_on(PRESET_CFG, "presetBar") and p_skin and (BAR_DIR / "manifest.json").is_file() and p_skin != current_skin():
        return False
    if section_on(PRESET_CFG, "presetLock") and p_lock and (LOCK_PLUGIN / "manifest.json").is_file() and p_lock != lock_current():
        return False
    return True


def current_preset_stem() -> str:
    saved = fsutil.read_text(ACTIVE_PRESET) if fsutil.nonempty(ACTIVE_PRESET) else None
    if saved:
        for f in (USER_PRESETS / f"{saved}.json", PRESET_DIR / f"{saved}.json"):
            if f.is_file() and preset_matches(f):
                return saved
    for f in fsutil.glob_sorted(USER_PRESETS, ".json") + fsutil.glob_sorted(PRESET_DIR, ".json"):
        if preset_matches(f):
            return os.path.basename(f)[:-5]
    return "custom"


def style_file_of(stem: str):
    for f in (USER_STYLES / f"{stem}.json", STYLE_DIR / f"{stem}.json"):
        if f.is_file():
            return f
    return None


def style_matches(path) -> bool:
    d = jsonio.read(path)
    d = d if isinstance(d, dict) else {}
    checked = False
    if section_on(STYLE_CFG, "styleBar"):
        v = _str(d.get("barSkin"))
        if v and (BAR_DIR / "manifest.json").is_file():
            if v != current_skin():
                return False
            checked = True
        if isinstance(d.get("barSkinData"), dict):
            if _no_note(d["barSkinData"]) != _no_note(jsonio.read(paths.BAR_SKIN)):
                return False
            checked = True
    if section_on(STYLE_CFG, "styleLock"):
        lock = d.get("lock")
        v = _str(lock.get("design")) if isinstance(lock, dict) else ""
        if v and (LOCK_PLUGIN / "manifest.json").is_file():
            if v != lock_current():
                return False
            checked = True
    if section_on(STYLE_CFG, "styleOpacity"):
        v = _str(d.get("opacity"))
        if v:
            if v != opacity_current():
                return False
            checked = True
    return checked


def current_style_stem() -> str:
    saved = fsutil.read_text(ACTIVE_STYLE) if fsutil.nonempty(ACTIVE_STYLE) else None
    if saved:
        f = style_file_of(saved)
        if f and style_matches(f):
            return saved
    for f in fsutil.glob_sorted(USER_STYLES, ".json") + fsutil.glob_sorted(STYLE_DIR, ".json"):
        if style_matches(f):
            return os.path.basename(f)[:-5]
    return "custom"


# ── Имя, описание и сводка пресета / стиля ──

def meta(path):
    """(имя, описание) на языке интерфейса: name_<lang> / note_<lang>, иначе name / note."""
    base = os.path.basename(str(path))[:-5] if str(path).endswith(".json") else os.path.basename(str(path))
    d = jsonio.read(path)
    if not isinstance(d, dict):
        return base, ""
    lang = i18n.lang()
    name = jsonio.tostring(alt(d.get("name_" + lang), d.get("name"), base))
    note = jsonio.tostring(alt(d.get("note_" + lang), d.get("note"), ""))
    return name.rstrip("\n"), note.rstrip("\n")


def preset_name(path) -> str:
    return meta(path)[0]


def preset_summary(path) -> str:
    d = jsonio.read(path)
    if not isinstance(d, dict):
        return ""
    try:
        parts = []
        if alt(d.get("theme")) is not None and d.get("theme") is not False:
            parts.append("theme: " + d["theme"])
        if d.get("style") not in (None, False):
            parts.append("style: " + d["style"])
        if d.get("barSkin") not in (None, False):
            parts.append("bar: " + d["barSkin"])
        elif d.get("barSkinData") not in (None, False):
            parts.append("bar: custom")
        if d.get("barLayout") not in (None, False):
            parts.append("layout: " + d["barLayout"])
        elif d.get("barLayoutData") not in (None, False):
            parts.append("layout: custom")
        lock = d.get("lock")
        if isinstance(lock, dict) and lock.get("design") not in (None, False):
            parts.append("lock: " + lock["design"])
        launcher = d.get("launcher")
        if isinstance(launcher, dict) and launcher.get("skin") not in (None, False):
            parts.append("launcher: " + launcher["skin"])
        if d.get("anims") not in (None, False, ""):
            parts.append("anims: " + d["anims"])
        glyph = d.get("glyph")
        if isinstance(glyph, dict) and glyph.get("glyphEnabled") is True:
            parts.append("glyph: on")
        return "  ·  ".join(parts)
    except TypeError:
        return ""


def style_summary(path) -> str:
    d = jsonio.read(path)
    if not isinstance(d, dict):
        return ""
    try:
        parts = []
        geo = d.get("hyprGeometry")
        if geo not in (None, False):
            parts.append("corners " + jsonio.tostring(geo.get("rounding")) + (" · shadow" if alt(geo.get("shadow")) not in (None, False) else ""))
        if d.get("barSkin") not in (None, False):
            parts.append("bar: " + d["barSkin"])
        elif d.get("barSkinData") not in (None, False):
            parts.append("bar: custom")
        lock = d.get("lock")
        if isinstance(lock, dict) and lock.get("design") not in (None, False):
            parts.append("lock: " + lock["design"])
        launcher = d.get("launcher")
        if isinstance(launcher, dict) and launcher.get("skin") not in (None, False):
            parts.append("launcher: " + launcher["skin"])
        for k in ("opacity", "blur"):
            if d.get(k) not in (None, False):
                parts.append(f"{k}: " + d[k])
        if d.get("anims") not in (None, False, ""):
            parts.append("anims: " + d["anims"])
        if d.get("fonts") not in (None, False):
            parts.append("fonts: " + d["fonts"])
        th = d.get("theme")
        if isinstance(th, dict):
            parts.append("themes: " + th["dark"] + " / " + alt(th.get("light"), th["dark"]))
        return "  ·  ".join(parts)
    except (TypeError, KeyError, AttributeError):
        return ""


def layout_summary(path) -> str:
    d = jsonio.read(path)
    if not isinstance(d, dict):
        return ""
    try:
        lay = d.get("layout") or {}

        def ids(side):
            entries = lay.get(side) if isinstance(lay, dict) else None
            return " ".join(re.sub(r"^[a-z]+\.", "", e["id"]) for e in (entries or []))
        return "  ·  ".join([jsonio.tostring(alt(d.get("position"), "top")),
                              "L: " + ids("left"), "C: " + ids("center"), "R: " + ids("right")])
    except (TypeError, KeyError):
        return ""


def anim_files():
    """Пресеты анимаций по имени: свой с тем же именем перекрывает встроенный."""
    seen, out = {}, []
    for f in fsutil.glob_sorted(P / "customizer/animations", ".lua") + fsutil.glob_sorted(paths.PLUGIN / "animations", ".lua"):
        seen.setdefault(os.path.basename(f), f)
    for name in fsutil.lsort(list(seen)):
        out.append(seen[name])
    return out


def current_shader() -> str:
    out = fsutil.run(["hyprctl", "getoption", "decoration:screen_shader", "-j"])
    try:
        cur = json.loads(out).get("str") or ""
    except (ValueError, AttributeError):
        cur = ""
    if not cur or cur == "[[EMPTY]]":
        return "off"
    base = os.path.basename(cur)
    return base[:-5] if base.endswith(".frag") else base
