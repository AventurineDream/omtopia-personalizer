"""`apply <категория> <значение>` и долгие фоновые команды (thumbs, picker-cache, lock-thumbs) —
перенос из customizer.sh. Пресеты и стили: снимок текущей настройки, применение разделов формы
(replace — раздел заменяет файл, merge — вливается, как `$cur * .[$k]` в jq).

Файлы пишутся как jq (отступ 2, порядок ключей сохраняется) и на месте (inode тот же)."""
import concurrent.futures
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time

from . import fsutil, jsonio, lists_more, paths, preview_ops, settings, state, tweak_ops
from .i18n import t

P = paths.CONFIG
HYPR_STATE = paths.STATE.parent / "hypr"
NO_GAPS_FLAG = paths.STATE.parent / "omarchy/toggles/hypr/window-no-gaps.lua"
LOOK_CFG = P / "style.json"
WINDOW_CFG = P / "customizer/windows.json"
WIDGET_CFG = P / "widgets.json"
OSD_CFG = P / "osd.json"
NOTIFY_CFG = P / "notify-style.json"
DOTIFY_CFG = P / "dotify.json"
ANIM_USER_DIR = P / "customizer/animations"
ANIM_DIR = paths.PLUGIN / "animations"
ANIM_BACKUP = paths.RUN / "active_animations.lua"
SKIN_BACKUP = paths.RUN / "bar-skin.json"
PLAY_SOUND = paths.PLUGIN / "scripts/play-sound.sh"
RECOLOR = paths.PLUGIN / "scripts/recolor-wallpapers"
DOTIFY = paths.PLUGIN / "scripts/dotify.py"
THUMB_DIR = paths.CACHE / "omarchy-customizer/thumbs"
LOCK_THUMBS = paths.CACHE / "omarchy-customizer/lock"
WINDOW_GEOM_KEYS = ["windowGapsIn", "windowGapsOut", "windowBorder", "windowDecoRounding", "windowShadow", "windowNoGaps"]
OMARCHY_PATH = os.environ.get("OMARCHY_PATH", "")
sh = preview_ops.sh
write = tweak_ops.write_inplace
NOTE_RE = re.compile(r"^note(_[a-z]+)?$")


class Exit(Exception):
    """exit N посреди команды (как в bash)."""

    def __init__(self, code):
        self.code = code


def spawn(args):
    """Запустить и не ждать: свой сеанс, без наших пайпов. sh() ждёт вывод, а отсоединённый
    потомок держал бы его пайп — и apply висел бы, пока тот не закончит."""
    try:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    except OSError:
        pass


def notify(*args):
    sh(["notify-send", *args])


def read_or_empty(path):
    """read_json_or_empty: объект/значение файла, нет или битый — {}."""
    if not fsutil.nonempty(path):
        return {}
    d = jsonio.read(path)
    return {} if d is None else d


def deep_merge(a, b):
    """jq `a * b`: объекты сливаются рекурсивно, остальное — берётся b."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_merge(out[k], v) if k in out else v
        return out
    return b


def jq_str(v) -> str:
    """Значение в строке jq "\\(…)" / -r: строка как есть, null — "null", числа как jq."""
    return jsonio.tostring(v)


def alt(*v):
    return state.alt(*v)


def section_on(cfg, key, is_backup=False):
    return is_backup or state.section_on(cfg, key)


def theme_exists(name):
    return bool(name) and ((P / "themes" / name).is_dir() or os.path.isdir(f"{OMARCHY_PATH or '/usr/share/omarchy'}/themes/{name}"))


def set_no_gaps(want):
    if want == "true" and not NO_GAPS_FLAG.is_file():
        sh(["omarchy-hyprland-toggle", "window-no-gaps", "on"])
    elif want != "true" and NO_GAPS_FLAG.is_file():
        sh(["omarchy-hyprland-toggle", "window-no-gaps", "off"])


def shell_apply_layout(layout):
    """Раскладка бара в shell.json: без note*, клоны из cloneSourceRestores остаются в .plugins."""
    shell = jsonio.read(paths.SHELL_JSON)
    if not isinstance(shell, dict) or not isinstance(shell.get("bar"), dict) or not isinstance(layout, dict):
        return
    shell = dict(shell)
    bar = {k: v for k, v in shell["bar"].items() if not NOTE_RE.match(k)}
    bar.update({k: v for k, v in layout.items() if not NOTE_RE.match(k)})
    # Якорь центра — свойство раскладки: у новой его нет — старый не оставлять (иначе centerBegin / centerEnd
    # молча перестают рисоваться, а виджеты в них пропадают с бара).
    if "centerAnchor" not in layout:
        bar.pop("centerAnchor", None)
    shell["bar"] = bar
    for cid in shell.get("cloneSourceRestores") or []:
        plugins = shell.get("plugins") or []
        if any(not isinstance(p, dict) for p in plugins):
            return   # jq: map(.id) на строке — ошибка, файл не пишется
        if (shell["bar"].get("id") or "") != cid and cid not in [p.get("id") for p in plugins]:
            shell["plugins"] = plugins + [{"id": cid}]
    write(paths.SHELL_JSON, shell)


def stable_wallpaper(wp):
    cur = str(paths.HOME / ".local/state/omarchy/current/theme") + "/"
    if wp.startswith(cur):
        rel, name = wp[len(cur):], state.theme_name()
        for d in (P / "themes" / name, f"{OMARCHY_PATH or '/usr/share/omarchy'}/themes/{name}"):
            if os.path.isfile(f"{d}/{rel}"):
                return f"{d}/{rel}"
    return wp


def _current_or(script, fallback):
    code, out = sh([str(script), "current"], quiet=False)
    out = out.rstrip("\n")
    if code != 0:
        out = (out + "\n" if out else "") + fallback
    return out


# ── Снимок текущей настройки (пресет / резервная копия / основа стиля) ──

def snapshot(out, title="", note=""):
    theme = state.theme_name()
    wp = stable_wallpaper(state.current_bg())
    home = str(paths.HOME) + "/"
    if wp and wp.startswith(home):
        wp = "~/" + wp[len(home):]
    anim = ""
    if fsutil.nonempty(state.ANIM_ACTIVE):
        active = state.ANIM_ACTIVE.read_bytes()
        for f in state.anim_files():
            if open(f, "rb").read() == active:
                anim = os.path.basename(f)[:-4]
                break
    op = _current_or(state.OPACITY, "subtle")
    bl = _current_or(state.BLUR, "medium")
    shader = state.current_shader()
    geom = None
    gfile = HYPR_STATE / "geometry"
    if fsutil.nonempty(gfile):
        _n, gi, go, bs, r, shd = fsutil.read_ws((fsutil.read_text(gfile) or "").split("\n", 1)[0], 6)
        if shd:
            num = jsonio.json.loads
            geom = {"gapsIn": num(gi), "gapsOut": num(go), "borderSize": num(bs), "rounding": num(r),
                    "shadow": int(shd) > 0}
            if NO_GAPS_FLAG.is_file():
                geom["noGaps"] = True
    skin_name = state.current_skin()
    skin_data = None
    if skin_name in ("custom", "stock"):
        skin_name, skin_data = "", read_or_empty(paths.BAR_SKIN)
    layout_name = state.current_layout()
    layout_data = None
    if layout_name == "custom":
        layout_name = ""
        bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
        bar = bar if isinstance(bar, dict) else {}
        layout_data = {"position": bar.get("position"), "centerAnchor": bar.get("centerAnchor"), "layout": bar.get("layout")}
    bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
    bar_tr = bar.get("transparent") if isinstance(bar, dict) and bar.get("transparent") not in (None, False) else False
    style_id = state.current_style_stem()
    style_id = "" if style_id == "custom" else style_id

    doc = {}
    if title:
        doc["name"] = title
    if note:
        doc["note"] = note
    doc["theme"] = theme
    if style_id:
        doc["style"] = style_id
    doc.update({"wallpaper": wp, "anims": anim, "opacity": op, "blur": bl, "shader": shader, "hyprGeometry": geom})
    doc.update({"barSkin": skin_name} if skin_name else {"barSkinData": skin_data})
    doc.update({"barLayout": layout_name} if layout_name else {"barLayoutData": layout_data})
    doc.update({
        "barTransparent": bar_tr, "lock": read_or_empty(state.LOCK_CFG), "launcher": read_or_empty(state.MENU_CFG),
        "wallpaperFx": read_or_empty(state.FX_CFG), "imagePicker": read_or_empty(state.PICKER_CFG),
        "widgets": read_or_empty(WIDGET_CFG), "osd": read_or_empty(OSD_CFG), "notifications": read_or_empty(NOTIFY_CFG),
        "sounds": read_or_empty(state.SOUND_CFG), "glyph": read_or_empty(state.GLYPH_CFG), "look": read_or_empty(LOOK_CFG),
    })
    write(out, doc)


# ── Разделы формы из пресета или стиля ──

FORM_TARGETS = [("lock", "Lock", state.LOCK_CFG), ("launcher", "Launcher", state.MENU_CFG),
                ("wallpaperFx", "WallpaperFx", state.FX_CFG), ("imagePicker", "WallpaperFx", state.PICKER_CFG),
                ("widgets", "Widgets", WIDGET_CFG), ("osd", "Osd", OSD_CFG), ("notifications", "Notifications", NOTIFY_CFG),
                ("sounds", "Sounds", state.SOUND_CFG), ("glyph", "Glyph", state.GLYPH_CFG)]


def apply_form_sections(path, cfg, prefix, is_backup, mode, keep_look=False):
    d = jsonio.read(path)
    d = d if isinstance(d, dict) else {}

    def on(flag):
        return is_backup or state.section_on(cfg, prefix + flag)

    for key, flag, target in FORM_TARGETS:
        if not on(flag) or d.get(key) is None:
            continue
        write(target, deep_merge(read_or_empty(target), d[key]) if mode == "merge" else d[key])

    if on("Bar"):
        if isinstance(d.get("barSkinData"), dict):
            write(paths.BAR_SKIN, d["barSkinData"])
        else:
            bs = jq_str(alt(d.get("barSkin"), ""))
            if bs:
                for f in (state.USER_SKINS / f"{bs}.json", state.BAR_DIR / f"skins/{bs}.json"):
                    if f.is_file():
                        shutil.copyfile(f, paths.BAR_SKIN)
                        break
        if isinstance(d.get("barLayoutData"), dict):
            shell_apply_layout(d["barLayoutData"])
        else:
            bl = jq_str(alt(d.get("barLayout"), ""))
            if bl:
                for f in (state.USER_LAYOUTS / f"{bl}.json", state.BAR_DIR / f"layouts/{bl}.json"):
                    if f.is_file():
                        shell_apply_layout(jsonio.read(f))
                        break
        if "barTransparent" in d:
            tweak_ops.set_transparent(jq_str(alt(d.get("barTransparent"), False)))

    os.makedirs(HYPR_STATE, exist_ok=True)
    if on("Geometry"):
        g = d.get("hyprGeometry")
        if isinstance(g, dict):
            vals = [alt(g.get("gapsIn"), 4), alt(g.get("gapsOut"), 8), alt(g.get("borderSize"), 1), alt(g.get("rounding"), 12)]
            (HYPR_STATE / "geometry").write_text("preset " + " ".join(jq_str(v) for v in vals)
                                                 + f" {1 if g.get('shadow') is True else 0}\n")
            win = read_or_empty(WINDOW_CFG)
            win = dict(win) if isinstance(win, dict) else {}
            win.update({"windowGapsIn": vals[0], "windowGapsOut": vals[1], "windowBorder": vals[2],
                        "windowDecoRounding": vals[3], "windowShadow": g.get("shadow") is True,
                        "windowNoGaps": g.get("noGaps") is True})
            write(WINDOW_CFG, win)
            set_no_gaps(jq_str(alt(g.get("noGaps"), False)))
        elif mode == "replace" and "hyprGeometry" in d:
            (HYPR_STATE / "geometry").write_text("")
            if fsutil.nonempty(WINDOW_CFG):
                win = jsonio.read(WINDOW_CFG)
                if isinstance(win, dict):
                    write(WINDOW_CFG, {k: v for k, v in win.items() if k not in WINDOW_GEOM_KEYS})
            set_no_gaps("false")

    if on("Anims") and "anims" in d:
        anim = jq_str(alt(d.get("anims"), ""))
        if not anim:
            state.ANIM_ACTIVE.write_text("")
        else:
            for f in (ANIM_USER_DIR / f"{anim}.lua", ANIM_DIR / f"{anim}.lua"):
                if f.is_file():
                    shutil.copyfile(f, state.ANIM_ACTIVE)
                    try:
                        shutil.copyfile(f, ANIM_BACKUP)
                    except OSError:
                        pass
                    break
    if on("Opacity"):
        op = jq_str(alt(d.get("opacity"), ""))
        if op:
            sh([str(state.OPACITY), "set", op])
        blr = jq_str(alt(d.get("blur"), ""))
        if blr:
            sh([str(state.BLUR), "set", blr])
    shader = jq_str(alt(d.get("shader"), "")) if on("Shader") else ""
    if shader == "off":
        sh([str(state.TOGGLE), "off"])
    elif shader:
        sh([str(state.TOGGLE), "on", shader])
    if on("Look"):
        if isinstance(d.get("look"), dict):
            look = dict(d["look"])
            if prefix == "style":
                look["id"] = os.path.basename(str(path))[:-5]
            write(LOOK_CFG, look)
        elif mode == "replace" and not keep_look:
            write(LOOK_CFG, {})


def refresh_app_looks():
    procs = []
    for name in ("omarchy-app-themes", "omarchy-firefox-chrome"):
        path = shutil.which(name) or str(paths.HOME / f"dotfiles/omarchy-themes/scripts/{name}")
        if os.access(path, os.X_OK):
            procs.append(subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for p in procs:
        p.wait()


def _now(fmt):
    return time.strftime(fmt)


# ── Пресеты ──

def apply_preset(path):
    path = str(path)
    if not os.path.isfile(path):
        notify("-u", "critical", "Presets", t("Preset not found: %s", path))
        raise Exit(1)
    label = state.preset_name(path)
    is_backup = os.path.realpath(path) == os.path.realpath(state.LAST_PRESET)
    d = jsonio.read(path)
    d = d if isinstance(d, dict) else {}
    theme = jq_str(alt(d.get("theme"), ""))
    if is_backup or state.section_on(state.PRESET_CFG, "presetTheme"):
        if theme and not theme_exists(theme):
            notify("-u", "critical", "Presets", t("Theme %s is not installed — preset not applied. Turn off \"Apply theme\" to use it without the theme.", theme))
            raise Exit(1)
    else:
        theme = ""
    notify("-t", "3000", "Presets", t("Applying preset %s…", label))
    if not is_backup and (not fsutil.nonempty(state.LAST_PRESET) or state.current_preset_stem() == "custom"):
        snapshot(state.LAST_PRESET, t("Previous setup"), t("Automatic backup before applying %s (%s)", label, _now("%F %H:%M")))
    style_ref = jq_str(alt(d.get("style"), ""))
    style_file = state.style_file_of(style_ref) if style_ref else None
    if style_ref and style_file:
        apply_form_sections(style_file, state.PRESET_CFG, "preset", is_backup, "merge")
        if fsutil.nonempty(LOOK_CFG) and section_on(state.PRESET_CFG, "presetLook", is_backup):
            look = jsonio.read(LOOK_CFG)
            if isinstance(look, dict):
                look = dict(look)
                look["id"] = style_ref
                write(LOOK_CFG, look)
        if section_on(state.PRESET_CFG, "presetFonts", is_backup):
            apply_style_fonts(style_file)
    apply_form_sections(path, state.PRESET_CFG, "preset", is_backup, "replace", keep_look=bool(style_ref))
    wp = jq_str(alt(d.get("wallpaper"), "")) if section_on(state.PRESET_CFG, "presetWallpaper", is_backup) else ""
    if wp.startswith("~/"):
        wp = str(paths.HOME) + "/" + wp[2:]
    if theme and theme != state.theme_name():
        if wp and os.path.isfile(wp):
            sh(["omarchy", "theme", "set", theme], env=dict(os.environ, OMARCHY_THEME_SKIP_BACKGROUND="1"))
            sh(["omarchy", "theme", "bg", "set", wp], quiet=False)
        else:
            sh(["omarchy", "theme", "set", theme], quiet=False)
    elif wp and os.path.isfile(wp):
        sh(["omarchy", "theme", "bg", "set", wp], quiet=False)
    sh(["hyprctl", "reload"])
    preview_ops.restore()
    if section_on(state.PRESET_CFG, "presetLook", is_backup):
        refresh_app_looks()
    state.ACTIVE_PRESET.write_text("" if is_backup else os.path.basename(path)[:-5] + "\n")
    state.ACTIVE_STYLE.write_text(style_ref + "\n" if style_ref else "")
    notify("-t", "3000", "Presets", t("Applied preset: %s", label))


def _slug(raw):
    s = raw.translate(str.maketrans({c: c.lower() for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"})).replace(" ", "-")
    return re.sub(r"[^a-z0-9_-]", "", s)


def _zenity(args):
    code, out = sh(["zenity", *args], quiet=False)
    return out.rstrip("\n") if code == 0 else None


def save_user_preset():
    raw = _zenity(["--entry", f"--title={t('Save preset')}", f"--text={t('Preset name:')}", "--entry-text=My Preset"])
    if raw is None:
        return
    slug = _slug(raw) or "preset-" + _now("%Y%m%d-%H%M%S")
    path = state.USER_PRESETS / f"{slug}.json"
    if path.exists() and _zenity(["--question", f"--title={t('Save preset')}", f"--text={t('Preset %s already exists. Overwrite?', slug)}"]) is None:
        return
    note = _zenity(["--entry", f"--title={t('Save preset')}", f"--text={t('Description (optional):')}"]) or ""
    os.makedirs(state.USER_PRESETS, exist_ok=True)
    snapshot(path, raw, note)
    state.ACTIVE_PRESET.write_text(slug + "\n")
    notify("-t", "3000", "Presets", t("Saved %s", raw))


def geometry_reset():
    g = HYPR_STATE / "geometry"
    if fsutil.nonempty(g):
        g.write_text("")
    if fsutil.nonempty(WINDOW_CFG):
        win = jsonio.read(WINDOW_CFG)
        if isinstance(win, dict):
            write(WINDOW_CFG, {k: v for k, v in win.items() if k not in WINDOW_GEOM_KEYS})
    sh(["hyprctl", "reload"])
    out = preview_ops.restore()[1]
    notify("-t", "2000", "Windows", t("Window geometry: Hyprland config"))
    return out


# ── Стили ──

def apply_style_fonts(path):
    fonts = jq_str(alt(read_or_empty(path).get("fonts") if isinstance(read_or_empty(path), dict) else None, ""))
    if not fonts or not fsutil.which("omarchy-font-profile"):
        return
    if fsutil.run(["omarchy-font-profile"]) == fonts:
        return
    sh(["omarchy-font-profile", fonts])


def theme_is_light(name):
    for d in (P / "themes" / name, f"{OMARCHY_PATH or '/usr/share/omarchy'}/themes/{name}"):
        colors = os.path.join(str(d), "colors.toml")
        if not os.path.isfile(colors):
            continue
        bg = ""
        for line in open(colors, encoding="utf-8", errors="replace"):
            if re.match(r"^\s*background\s*=", line):
                m = re.search(r"#[0-9a-fA-F]{6}", line)
                bg = m.group(0) if m else ""
                break
        if not bg:
            return False
        r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        return (299 * r + 587 * g + 114 * b) // 1000 > 128
    return False


def style_theme_for(path):
    cfg = jsonio.read(state.STYLE_CFG)
    mode = jq_str(alt(cfg.get("styleTheme"), "current")) if isinstance(cfg, dict) else "current"
    d = read_or_empty(path)
    th = d.get("theme") if isinstance(d, dict) and isinstance(d.get("theme"), dict) else {}
    dark = jq_str(alt(th.get("dark"), ""))
    light = jq_str(alt(th.get("light"), "")) or dark
    if mode == "dark":
        return dark
    if mode == "light":
        return light
    if mode == "current":
        return light if theme_is_light(state.theme_name()) else dark
    return ""


def apply_style(path):
    path = str(path)
    if not os.path.isfile(path):
        notify("-u", "critical", "Styles", t("Style not found: %s", path))
        raise Exit(1)
    label = state.preset_name(path)
    notify("-t", "3000", "Styles", t("Applying style %s…", label))
    if not fsutil.nonempty(state.LAST_PRESET) or (state.current_preset_stem() == "custom" and state.current_style_stem() == "custom"):
        snapshot(state.LAST_PRESET, t("Previous setup"), t("Automatic backup before applying %s (%s)", label, _now("%F %H:%M")))
    theme = style_theme_for(path)
    if theme and theme != state.theme_name():
        if theme_exists(theme):
            sh(["omarchy", "theme", "set", theme], quiet=False)
        else:
            notify("-u", "critical", "Styles", t("Theme %s is not installed — the style is applied without it.", theme))
    apply_form_sections(path, state.STYLE_CFG, "style", False, "merge")
    state.reset()
    if state.section_on(state.STYLE_CFG, "styleFonts"):
        apply_style_fonts(path)
    if state.section_on(state.STYLE_CFG, "styleLook"):
        refresh_app_looks()
    sh(["hyprctl", "reload"])
    preview_ops.restore()
    state.ACTIVE_STYLE.write_text(os.path.basename(path)[:-5] + "\n")
    notify("-t", "3000", "Styles", t("Applied style: %s", label))


STYLE_CONTENT_KEYS = ["theme", "wallpaper", "style"]
STYLE_CONTENT_NESTED = [("widgets", "clock"), ("widgets", "media"), ("widgets", "visualizer"), ("widgets", "sysinfo"),
                        ("widgets", "edgeHover"), ("widgets", "dashMedia"), ("widgets", "dashCalendar"),
                        ("widgets", "dashWeather"), ("widgets", "dashStats"), ("lock", "clock24"), ("lock", "showSeconds"),
                        ("lock", "showDate"), ("sounds", "sounds"), ("sounds", "soundVolume"), ("imagePicker", "autoCache"),
                        ("glyph", "glyphCharger"), ("glyph", "glyphCriticalRed"), ("osd", "osdShowValue"), ("look", "id")]


def save_user_style():
    raw = _zenity(["--entry", f"--title={t('Save style')}", f"--text={t('Style name:')}", "--entry-text=My Style"])
    if raw is None:
        return
    slug = _slug(raw) or "style-" + _now("%Y%m%d-%H%M%S")
    path = state.USER_STYLES / f"{slug}.json"
    if path.exists() and _zenity(["--question", f"--title={t('Save style')}", f"--text={t('Style %s already exists. Overwrite?', slug)}"]) is None:
        return
    note = _zenity(["--entry", f"--title={t('Save style')}", f"--text={t('Description (optional):')}"]) or ""
    fonts = fsutil.run(["omarchy-font-profile"]) if fsutil.which("omarchy-font-profile") else ""
    tmp = paths.RUN / "style-snapshot.json"
    snapshot(tmp, raw, note)
    d = jsonio.read(tmp)
    for k in STYLE_CONTENT_KEYS:
        d.pop(k, None)
    for a, b in STYLE_CONTENT_NESTED:
        if isinstance(d.get(a), dict):
            d[a] = {k: v for k, v in d[a].items() if k != b}
    if fonts:
        d["fonts"] = fonts
    os.makedirs(state.USER_STYLES, exist_ok=True)
    write(path, d)
    state.ACTIVE_STYLE.write_text(slug + "\n")
    notify("-t", "3000", "Styles", t("Saved %s", raw))


# ── Бар ──

def save_user_skin():
    name = _zenity(["--entry", f"--title={t('Save the bar skin')}", f"--text={t('Skin name (latin letters, digits, - and _):')}",
                    "--entry-text=my-skin"])
    if name is None:
        return
    name = _slug(name)
    if not name:
        notify("-u", "critical", "Bar Skin", t("Empty skin name"))
        raise Exit(1)
    path = state.USER_SKINS / f"{name}.json"
    if path.exists() and _zenity(["--question", f"--title={t('Save the bar skin')}", f"--text={t('Skin %s already exists. Overwrite?', name)}"]) is None:
        return
    note = _zenity(["--entry", f"--title={t('Save the bar skin')}", f"--text={t('Description (optional):')}"]) or ""
    os.makedirs(state.USER_SKINS, exist_ok=True)
    src = jsonio.read(SKIN_BACKUP) if fsutil.nonempty(SKIN_BACKUP) else {}
    src = {k: v for k, v in (src or {}).items() if not NOTE_RE.match(k)}
    write(path, ({"note": note} if note else {}) | src)
    if SKIN_BACKUP.is_file():
        shutil.copyfile(SKIN_BACKUP, paths.BAR_SKIN)
    notify("-t", "3000", "Bar Skin", t("Saved %s", name))


def save_user_layout():
    name = _zenity(["--entry", f"--title={t('Save the bar layout')}", f"--text={t('Layout name (latin letters, digits, - and _):')}",
                    "--entry-text=my-layout"])
    if name is None:
        return
    name = _slug(name)
    if not name:
        notify("-u", "critical", "Bar Layout", t("Empty layout name"))
        raise Exit(1)
    path = state.USER_LAYOUTS / f"{name}.json"
    if path.exists() and _zenity(["--question", f"--title={t('Save the bar layout')}", f"--text={t('Layout %s already exists. Overwrite?', name)}"]) is None:
        return
    os.makedirs(state.USER_LAYOUTS, exist_ok=True)
    bar = jsonio.read_object(paths.SHELL_JSON).get("bar") or {}
    write(path, {"note": t("Saved %s", _now("%F")), "position": bar.get("position"),
                 "centerAnchor": bar.get("centerAnchor"), "layout": bar.get("layout")})
    notify("-t", "3000", "Bar Layout", t("Saved: %s", name))


# ── Обои: Recolor и Dotify ──

def recolor(src):
    theme_dir = P / "themes" / state.theme_name()
    if not theme_dir.is_dir():
        notify("Wallpaper", t("Cannot recolor a stock Omarchy theme. Use a custom theme."))
        raise Exit(1)
    files = fsutil.images_in(src, 1, fsutil.MEDIA_EXT)
    if not files:
        notify("Wallpaper", t("No images in %s", src))
        raise Exit(1)
    if any(fsutil.is_live(f) for f in files):
        notify("-t", "4000", "Wallpaper", t("GIF / video is recolored frame by frame (ffmpeg) — this takes a while"))
    if len(files) == 1:
        notify("-t", "3000", "Wallpaper", t("Recoloring %s with lutgen…", os.path.basename(files[0])))
    else:
        notify("-t", "3000", "Wallpaper", t("Recoloring %s images from %s with lutgen…", len(files), os.path.basename(src)))
    if sh([str(RECOLOR), str(theme_dir), src], quiet=False)[0] != 0:
        notify("-u", "critical", "Wallpaper", t("lutgen failed"))
        raise Exit(1)
    if len(files) == 1:
        # Видео (кроме GIF) скрипт пишет в mp4 — имя результата может отличаться расширением.
        name = os.path.basename(files[0])
        if fsutil.is_live(name) and not name.lower().endswith(".gif"):
            name = os.path.splitext(name)[0] + ".mp4"
        sh(["omarchy", "theme", "bg", "set", f"{theme_dir}/backgrounds/{name}"], quiet=False)
        notify("-t", "3000", "Wallpaper", t("Applied %s", name))
    else:
        notify("-t", "5000", "Wallpaper", t("Added %s recolored wallpapers to %s. Pick one in Wallpaper.", len(files), state.theme_name()))


def recolor_files(files):
    src = tempfile.mkdtemp(prefix="omarchy-lutgen-src.", dir=os.environ.get("TMPDIR") or "/tmp")
    for f in files:
        try:
            shutil.copy(f, src)
        except OSError:
            pass
    recolor(src)


def resolve_hex(spec, fallback):
    """Hex или роль темы (bar → background, urgent → red) → #rrggbb, как resolve_hex_color."""
    if re.match(r"^#[0-9A-Fa-f]{6}$", spec or ""):
        return spec
    key = {"bar": "background", "urgent": "red"}.get(spec, spec)
    if key and paths.THEME_COLORS.is_file():
        for line in open(paths.THEME_COLORS, encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split('"')
            if re.match("^" + key + " *=", parts[0]):   # awk -F'"' '$1 ~ "^" k " *=" { print $2; exit }'
                hexv = parts[1] if len(parts) > 1 else ""
                if re.match(r"^#[0-9A-Fa-f]{6}$", hexv):
                    return hexv
                break
    return fallback


def _dotify_python():
    import importlib.util
    if os.path.exists("/usr/bin/python3") and fsutil.run(["/usr/bin/python3", "-I", "-c", "import numpy, PIL; print(1)"]) == "1":
        return "/usr/bin/python3"
    py = shutil.which("python3")
    if py and fsutil.run([py, "-I", "-c", "import numpy, PIL; print(1)"]) == "1":
        return "python3"
    return None


def _dotify_opts():
    v = tweak_ops
    path = DOTIFY_CFG
    return ["--pitch", v.value_of(path, "dotPitch", "9"), "--gamma", v.value_of(path, "dotGamma", "1.25"),
            "--off", v.value_of(path, "dotOff", "0.07"),
            "--tint", resolve_hex(v.value_of(path, "dotTint", "foreground"), "#f2f2f2"),
            "--background", resolve_hex(v.value_of(path, "dotBackground", "background"), "#000000")]


def _dest_dir():
    d = P / "backgrounds" / state.theme_name()
    os.makedirs(d, exist_ok=True)
    return str(d)


def dotify_files(files):
    py = _dotify_python()
    if not py:
        notify("-u", "critical", "Dotify", t("Dotify needs python3 with numpy and Pillow"))
        raise Exit(1)
    dest = _dest_dir()
    opts = _dotify_opts()
    if not files:
        notify("Dotify", t("No images selected"))
        raise Exit(1)
    if len(files) == 1:
        notify("-t", "3000", "Dotify", t("Rendering LED dot-matrix for %s…", os.path.basename(files[0])))
    else:
        notify("-t", "3000", "Dotify", t("Rendering %s LED dot-matrix wallpapers…", len(files)))
    count, last = 0, ""
    for src in files:
        if not os.path.isfile(src):
            continue
        base = os.path.basename(src)
        stem = base.rsplit(".", 1)[0] if "." in base else base
        stem = stem if stem.startswith("dot-") else "dot-" + stem
        out = f"{dest}/{stem}.png"
        if sh([py, "-I", str(DOTIFY), src, out, *opts])[0] != 0:
            notify("-u", "critical", "Dotify", t("Dotify failed on %s", base))
            raise Exit(1)
        last, count = out, count + 1
    if count == 1 and last:
        sh(["omarchy", "theme", "bg", "set", last], quiet=False)
        notify("-t", "3000", "Dotify", t("Applied %s", os.path.basename(last)))
    elif count > 1:
        notify("-t", "5000", "Dotify", t("Added %s dot-matrix wallpapers to %s. Pick one in Wallpaper.", count, state.theme_name()))


def dotify_glyph(glyph="󰣇", slug="arch"):
    py = _dotify_python()
    if not py:
        notify("-u", "critical", "Dotify", t("Dotify needs python3 with numpy and Pillow"))
        raise Exit(1)
    out = f"{_dest_dir()}/dot-{slug}.png"
    opts = _dotify_opts()
    notify("-t", "3000", "Dotify", t("Rendering Arch Linux LED dot-matrix wallpaper…"))
    if sh([py, "-I", str(DOTIFY), "--glyph", glyph, out, *opts])[0] != 0:
        notify("-u", "critical", "Dotify", t("Dotify failed"))
        raise Exit(1)
    sh(["omarchy", "theme", "bg", "set", out], quiet=False)
    notify("-t", "3000", "Dotify", t("Applied %s", os.path.basename(out)))


def _pick_images(title):
    picked = _zenity(["--file-selection", "--multiple", "--separator=\n", f"--title={title}",
                      f"--filename={lists_more.walls_dir()}/",
                      "--file-filter=Images | *.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP",
                      "--file-filter=Live (GIF / video) | *.gif *.mp4 *.webm *.mkv *.mov *.m4v *.GIF *.MP4 *.WEBM *.MKV *.MOV"])
    if picked is None:
        raise Exit(0)
    return picked.split("\n")


def _pick_dir(title):
    picked = _zenity(["--file-selection", "--directory", f"--title={title}", f"--filename={lists_more.walls_dir()}/"])
    if picked is None:
        raise Exit(0)
    return picked


# ── Фоновые: миниатюры, кэш пикера, снимки экранов блокировки ──

def thumbs(category, extra=""):
    from . import lists
    os.makedirs(THUMB_DIR, exist_ok=True)
    rows = lists.list_category(category, extra) or []
    srcs = []
    for line in rows:
        f = line.split("\t")
        if len(f) > 2 and not re.match(r"^(tweak:|section:)", f[1]) and f[2]:
            srcs.append(f[2])

    def one(src):
        dst = THUMB_DIR / (hashlib.md5(src.encode()).hexdigest() + ".jpg")
        try:
            if dst.is_file() and os.path.getmtime(src) <= os.path.getmtime(dst):
                return
        except OSError:
            pass
        sh(["vipsthumbnail", src, "--size", "320x200", "-o", f"{dst}[Q=82]"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        list(ex.map(one, srcs))


def picker_cache():
    cache = lists_more.PICKER_CACHE
    start = time.time()
    count = lambda: len([n for n in os.listdir(cache) if n.endswith(".jpg")]) if cache.is_dir() else 0  # noqa: E731
    before = count()
    notify("-t", "3000", "Theme Switcher", t("Caching thumbnails…"))
    sh(["omarchy-theme-switcher", "--print-rows"])
    sh(["omarchy-menu-images", "--cache-only", str(paths.CACHE / "omarchy/theme-selector/previews")])
    theme = state.theme_name()
    sh(["omarchy-menu-images", "--cache-only", str(paths.HOME / ".local/state/omarchy/current/theme/backgrounds"),
        str(P / "backgrounds" / theme)])
    notify("-t", "4000", "Theme Switcher", t("Done in %s s: %s new thumbnails", int(time.time() - start), count() - before))


def picker_prune(dry):
    """Удалить миниатюры исчезнувших/изменённых картинок (строго внутри кэша пикера)."""
    if dry:
        return lists_more.picker_prune_summary()
    try:
        return _prune()
    except OSError:
        return ""   # как bash: нет кэша — питон-скрипт падает, уведомление пустое


def _prune():
    cache = os.path.realpath(lists_more.PICKER_CACHE)
    index = os.path.join(cache, "index.tsv")
    keep, lines = set(), []
    try:
        for line in open(index, encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            p, sig, h = parts
            try:
                st = os.stat(p)
            except OSError:
                continue
            if f"{st.st_size}:{int(st.st_mtime)}" == sig:
                keep.add(h + ".jpg")
                lines.append(line if line.endswith("\n") else line + "\n")
    except FileNotFoundError:
        pass
    names = os.listdir(cache)
    for name in names:
        if name.endswith(".rows"):
            for row in open(os.path.join(cache, name), encoding="utf-8", errors="replace"):
                cols = row.rstrip("\n").split("\t")
                if len(cols) == 2:
                    keep.add(os.path.basename(cols[1]))
    count = size = 0
    for name in names:
        if not name.endswith(".jpg") or name in keep:
            continue
        full = os.path.join(cache, name)
        if not os.path.realpath(full).startswith(cache + os.sep) or not os.path.isfile(full):
            continue
        count += 1
        size += os.path.getsize(full)
        os.remove(full)  # только внутри кэша пикера (realpath-проверка выше), как в bash-версии
    tmp = index + ".prune.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(dict.fromkeys(lines))
    os.replace(tmp, index)
    return t("Deleted: %s thumbnails, %s GB; %s stay", count, f"{size / 1024 ** 3:.1f}", len(keep))


def lock_thumbs(only_missing=False):
    os.makedirs(LOCK_THUMBS, exist_ok=True)
    notify("-t", "3000", "Lock", t("Capturing design previews…"))
    designs = jsonio.read(state.LOCK_PLUGIN / "designs/designs.json")
    ids = [jq_str(d.get("id")) for d in designs if isinstance(d, dict)] if isinstance(designs, list) else []
    ids += ["my:" + os.path.basename(f) for f in fsutil.glob_sorted(lists_more.LOCK_USER_DIR, ".qml")]
    if only_missing:
        ids = [i for i in ids if not (LOCK_THUMBS / f"{state.lock_thumb_name(i)}.jpg").is_file()]
    for i in ids:
        sh(["omarchy-shell", "lock", "previewDesign", i])
        time.sleep(float(os.environ.get("CUSTOMIZER_LOCK_DELAY", "1.5")))
        sh(["grim", "-s", "1", "-t", "jpeg", "-q", "90", str(LOCK_THUMBS / f"{state.lock_thumb_name(i)}.jpg")])
    sh(["omarchy-shell", "lock", "hidePreview"])
    notify("-t", "3000", "Lock", t("Previews updated"))


# ── apply ──

def tweak_pick(value):
    tweak_ops.tweak(value.split(":", 1)[1] if value.startswith("tweak:") else value, "pick")


def dock_apply(value):
    """Вкладка «Док»: omarchy dock … и вкл / выкл плагина omarchy.dock."""
    if value == "toggle":
        on = lists_more.dock_enabled()
        sh(["omarchy", "plugin", "disable" if on else "enable", "omarchy.dock"])
        notify("-t", "2000", "Dock", t("Dock off") if on else t("Dock on"))
    elif value.startswith("pos:"):
        sh(["omarchy", "dock", "position", value[4:]])
    elif value == "autohide":
        sh(["omarchy", "dock", "autohide", "toggle"])
    elif value.startswith("unpin:"):
        sh(["omarchy", "dock", "unpin", value[6:]])
    elif value == "pin-pick":
        names = lists_more._desktop_names()
        rows = []
        for pid, name in sorted(names.items(), key=lambda kv: kv[1].lower()):
            rows += [name, pid]
        pick = _zenity(["--list", f"--title={t('Pin an app')}", "--width=560", "--height=640",
                        f"--column={t('App')}", "--column=id", "--print-column=2", *rows])
        if pick:
            sh(["omarchy", "dock", "pin", pick.strip().split("|")[0]])
    return ""


def apply(category, value):
    out = ""
    if category == "presets":
        if value == "save":
            save_user_preset()
        elif value.startswith("tweak:window"):
            tweak_pick(value)
            sh(["hyprctl", "reload"])
        elif value.startswith("tweak:"):
            tweak_pick(value)
        elif value == "geometry-reset":
            out = geometry_reset()
        else:
            apply_preset(value)
    elif category == "fonts":
        if not value.startswith("section:"):
            sh(["omarchy-font-profile", value])
    elif category == "windows":
        if value.startswith("tweak:"):
            tweak_pick(value)
            tweak_ops.window_after()
        elif value == "geometry-reset":
            out = geometry_reset()
    elif category == "sounds":
        if value.startswith("pack:"):
            d = read_or_empty(state.SOUND_CFG)
            d = dict(d) if isinstance(d, dict) else {}
            d["soundPack"] = value[5:]
            write(state.SOUND_CFG, d)
            out = sh([str(PLAY_SOUND), "notify", "--force"], quiet=False)[1]
        elif value.startswith("test:"):
            out = sh([str(PLAY_SOUND), value[5:], "--force"], quiet=False)[1]
        elif value.startswith("tweak:"):
            tweak_pick(value)
    elif category == "styles":
        if value == "save":
            save_user_style()
        elif value.startswith("tweak:"):
            tweak_pick(value)
        else:
            apply_style(value)
    elif category == "dotify":
        if value.startswith("tweak:"):
            tweak_pick(value)
        elif value == "current":
            picked = state.current_bg()
            if not os.path.isfile(picked):
                notify("-u", "critical", "Dotify", t("No active wallpaper found"))
                raise Exit(1)
            dotify_files([picked])
        elif value == "arch":
            dotify_glyph()
        elif value == "pick-dir":
            dotify_files(fsutil.images_in(_pick_dir(t("Folder to dotify")), 1))
        elif value == "pick-files":
            dotify_files(_pick_images(t("Image(s) to dotify")))
        else:
            dotify_files([value])
    elif category == "glyph":
        if value.startswith("tweak:"):
            tweak_pick(value)
        elif value in ("test:normal", "test:critical"):
            sh(["omarchy-shell", "-q", "glyph", "test", "true" if value == "test:critical" else "false"])
        elif value == "test:charge":
            sh(["omarchy-shell", "-q", "glyph", "charge"])
    elif category == "launcher":
        if value.startswith("tweak:"):
            tweak_pick(value)
        elif value == "open":
            preview_ops.launcher_open("", "open")
        elif value.startswith("skin:"):
            os.makedirs(os.path.dirname(str(state.MENU_CFG)), exist_ok=True)
            tweak_ops.set_key(state.MENU_CFG, "skin", value[5:])
            notify("-t", "2000", "Launcher", t("Skin: %s", value[5:]))
    elif category == "anims":
        shutil.copyfile(value, state.ANIM_ACTIVE)
        shutil.copyfile(value, ANIM_BACKUP)
        sh(["hyprctl", "reload"])
        base = os.path.basename(value)
        notify("-t", "2000", "Animations", t("Loaded: %s", base[:-4] if base.endswith(".lua") else base))
    elif category == "bar-layouts":
        if value == "save":
            save_user_layout()
            raise Exit(0)
        shell_apply_layout(jsonio.read(value))
        base = os.path.basename(value)
        notify("-t", "2000", "Bar Layout", t("Applied %s", base[:-5] if base.endswith(".json") else base))
    elif category == "bar-skins":
        if value == "save":
            save_user_skin()
            raise Exit(0)
        preview_ops.bar_skin_preview(value)
        shutil.copyfile(paths.BAR_SKIN, SKIN_BACKUP)
        base = os.path.basename(value)
        notify("-t", "2000", "Bar Skin", t("Applied %s", base[:-5] if base.endswith(".json") else base))
    elif category in ("bar-tweaks", "lock-tweaks", "widgets", "dashboard", "osd", "notifications"):
        tweak_ops.tweak(value, "pick")
    elif category == "wallpaper-fx":
        if value.startswith("tweak:"):
            tweak_pick(value)
            if value.startswith("tweak:owe"):
                tweak_ops.owe_after()
            raise Exit(0)
        if value == "owe-toggle":
            st = sh(["owe", "status"], quiet=False)[1]
            paused = '"manual_pause":true' in st.replace(" ", "")
            sh(["owe", "resume" if paused else "pause"])
            notify("-t", "2000", "Wallpaper", t("Live wallpaper resumed") if paused else t("Live wallpaper paused"))
            raise Exit(0)
        if value == "enable-plugin":
            code = sh(["omarchy", "plugin", "enable", "kamradsmeshnyavy.background"])[0]
            notify("-t", "3000", "Wallpaper FX", t("Enabled") if code == 0 else t("Could not enable the plugin"))
            raise Exit(code)
        if value in ("outline-install", "outline-warm", "outline-status"):
            script = str(state.PLUGINS / "kamradsmeshnyavy.background/scripts/wallpaper-fx-outline")
            if value == "outline-install":
                spawn(["omarchy-launch-floating-terminal-with-presentation",
                       f"{shlex.quote(script)} install && {shlex.quote(script)} warm"])
            elif value == "outline-warm":
                # warm только ставит обои в очередь; режет один фоновый воркер (flock) — сколько
                # ни нажимай, процесс один
                spawn([script, "warm"])
                notify("-t", "2500", "Wallpaper FX", t("Theme wallpapers queued for cut-out (one background process)"))
            raise Exit(0)
        tweak_ops.set_key(state.FX_CFG, "type", value)
        notify("-t", "2000", "Wallpaper FX", t("Transition: %s", value))
    elif category == "theme-switcher":
        if value.startswith("tweak:"):
            tweak_pick(value)
        elif value == "cache":
            picker_cache()
        elif value == "prune":
            info = picker_prune(True)
            if _zenity(["--question", f"--title={t('Thumbnail cache')}", f"--text={info}\\n\\n{t('Delete?')}"]) is None:
                raise Exit(0)
            notify("-t", "4000", "Theme Switcher", picker_prune(False))
        elif value.startswith("style:"):
            tweak_ops.set_key(state.PICKER_CFG, "style", value[6:])
            notify("-t", "2000", "Theme Switcher", t("Style: %s", value[6:]))
    elif category == "lock":
        if value == "regen-thumbs":
            lock_thumbs()
            raise Exit(0)
        if value == "missing-thumbs":
            lock_thumbs(True)
            raise Exit(0)
        tweak_ops.set_key(state.LOCK_CFG, "design", value)
        notify("-t", "2000", "Lock", t("Design: %s", value))
    elif category == "themes":
        if value.startswith("dynamic:"):
            opts = ["--mode", "light"] if value == "dynamic:light" else ["--scheme", value[8:]]
            notify("-t", "3000", "Theme", t("Building a theme from the wallpaper…"))
            if sh(["omarchy-wallpaper-theme", *opts], quiet=False)[0] != 0:
                notify("-u", "critical", "Theme", t("matugen failed"))
                raise Exit(1)
            notify("-t", "3000", "Theme", t("Applied %s", "dynamic"))
            raise Exit(0)
        notify("-t", "3000", "Theme", t("Applying %s…", value))
        out = sh(["omarchy", "theme", "set", value], quiet=False)[1]
        notify("-t", "3000", "Theme", t("Applied %s", value))
    elif category == "theme-walls":
        out = sh(["omarchy", "theme", "bg", "set", value], quiet=False)[1]
        notify("-t", "3000", "Wallpaper", t("Applied %s", os.path.basename(value)))
    elif category == "walls":
        if value == "pick-dir":
            recolor(_pick_dir(t("Folder to recolor")))
        elif value == "pick-files":
            recolor_files(_pick_images(t("Image(s) to recolor")))
        else:
            recolor_files([value])
    elif category == "dock":
        out = dock_apply(value)
    elif category == "shaders":
        if value.startswith("tweak:"):
            tweak_pick(value)
            tweak_ops.reading_after()
        elif value == "reading":
            out = sh([str(state.READING)], quiet=False)[1]
        elif not value.startswith("section:"):
            args = [] if value == "toggle" else ["next"] if value == "next" else ["on", value]
            out = sh([str(state.TOGGLE), *args], quiet=False)[1]
    elif category == "opacity":
        out = sh([str(state.OPACITY), "set", value], quiet=False)[1]
    elif category == "blur":
        out = sh([str(state.BLUR), "set", value], quiet=False)[1]
    return out


def run(args):
    cmd = args[0]
    try:
        if cmd == "apply":
            return 0, apply(args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "")
        if cmd == "thumbs":
            thumbs(args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "")
        elif cmd == "picker-cache":
            picker_cache()
        elif cmd == "lock-thumbs":
            lock_thumbs(len(args) > 1 and args[1] == "missing")
    except Exit as e:
        return e.code, ""
    return 0, ""


COMMANDS = {"apply", "thumbs", "picker-cache", "lock-thumbs"}
