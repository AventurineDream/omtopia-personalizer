"""Остальные категории `list` и команды status / available — перенос из customizer.sh.

Строки — байт в байт как у bash (проверяет tests/compare_readonly.py). Заметки пишутся с
литеральными \\n (два символа): overlay сам превращает их в переводы строк."""
import hashlib
import json
import os
import re
import shutil
import subprocess

from . import fsutil, jsonio, paths, state, tweaks
from .i18n import t

NL = "\\n"
CACHE_LOCK = paths.CACHE / "omarchy-customizer/lock"
PICKER_CACHE = paths.CACHE / "omarchy/image-selector"
LOCK_USER_DIR = paths.CONFIG / "lock-designs"
BAR_HIDDEN = paths.CONFIG / "customizer/bar-hidden.json"
FAV_THEMES = paths.CONFIG / "customizer/favorite-themes.json"
FAV_WALLS = paths.CONFIG / "customizer/favorite-wallpapers.json"
SOUND_EVENTS = ["open", "close", "switch", "menu", "notify", "critical", "lock", "power", "volume"]
OMARCHY_PATH = os.environ.get("OMARCHY_PATH", "")


def walls_dir() -> str:
    w = paths.HOME / "Wallpapers"
    return str(w if w.is_dir() else paths.HOME / "Pictures")


def _cur(flag) -> str:
    return "1" if flag else "0"


# ── Пресеты и стили ──

def presets():
    cur = state.current_preset_stem()
    out = [f"{t('💾 Save current setup as a preset…')}\tsave\t\t0\t"
           + t("Snapshot your active theme, wallpaper, bar, animations, opacity, blur, lock screen, launcher, widgets, OSD, notifications, sounds and Glyph into %s.", paths.tilde(state.USER_PRESETS))]
    last = state.LAST_PRESET
    if fsutil.nonempty(last):
        out.append(f"{t('↩ Restore previous setup')}\t{last}\t{last}\t0\t{state.meta(last)[1]}\t{state.preset_summary(last)}")
    for f in fsutil.glob_sorted(state.USER_PRESETS, ".json"):
        name, note = state.meta(f)
        stem = os.path.basename(f)[:-5]
        s = state.preset_summary(f)
        out.append(f"★ {name}\t{f}\t{f}\t{_cur(stem == cur)}\t{note}{NL}{NL}{s}{NL}{NL}{t('Your preset: %s', paths.tilde(f))}\t{s}")
    for f in fsutil.glob_sorted(state.PRESET_DIR, ".json"):
        name, note = state.meta(f)
        stem = os.path.basename(f)[:-5]
        s = state.preset_summary(f)
        out.append(f"{name}\t{f}\t{f}\t{_cur(stem == cur)}\t{note}{NL}{NL}{s}\t{s}")
    return out + tweaks.prefixed(tweaks.list_tweaks("PRESET_TWEAKS"))


def styles():
    cur = state.current_style_stem()
    out = [f"{t('💾 Save current look as a style…')}\tsave\t\t0\t"
           + t("Snapshot the form of your desktop without colours — window geometry, bar, lock screen, launcher, widgets, OSD, notifications, animations, opacity, blur, sounds, Glyph and fonts — into %s. It works on any theme.", paths.tilde(state.USER_STYLES))]
    for f in fsutil.glob_sorted(state.USER_STYLES, ".json"):
        name, note = state.meta(f)
        s = state.style_summary(f)
        out.append(f"★ {name}\t{f}\t{f}\t{_cur(os.path.basename(f)[:-5] == cur)}\t{note}{NL}{NL}{s}{NL}{NL}{t('Your style: %s', paths.tilde(f))}\t{s}")
    for f in fsutil.glob_sorted(state.STYLE_DIR, ".json"):
        name, note = state.meta(f)
        s = state.style_summary(f)
        out.append(f"{name}\t{f}\t{f}\t{_cur(os.path.basename(f)[:-5] == cur)}\t{note}{NL}{NL}{s}\t{s}")
    return out + tweaks.prefixed(tweaks.list_tweaks("STYLE_TWEAKS"))


def geometry_summary() -> str:
    f = paths.STATE.parent / "hypr/geometry"
    if not fsutil.nonempty(f):
        return t("Hyprland config")
    first = (fsutil.read_text(f) or "").split("\n", 1)[0]
    _n, gi, go, bs, r, shd = fsutil.read_ws(first, 6)
    return t("gaps %s/%s · border %s · rounding %s · shadow %s", gi, go, bs, r, "on" if (shd or "0") != "0" else "off")


def windows():
    out = tweaks.prefixed(tweaks.list_tweaks("WINDOW_LAYOUT_TWEAKS")) + tweaks.prefixed(tweaks.list_tweaks("WINDOW_TWEAKS"))
    out.append(f"{t('Reset')}\tsection:Reset\t\t0\t\theader")
    out.append(f"{t('↺ Reset window geometry')}\tgeometry-reset\t\t0\t"
               + t("Drop gaps, borders, rounding and shadow set by a style, a preset or this tab and return to your Hyprland config. Now: %s", geometry_summary()))
    return out


# ── Звуки и шрифты ──

_PACK_DESC = {
    "theme": "Sounds of the current Omarchy theme (apps/sounds), then the freedesktop theme",
    "dotmatrix": "DOT-MATRIX: tactile hardware clicks and LED blips", "classic": "Classic: soft neutral system sounds",
    "flat": "Flat: short clean sine ticks", "glass": "Glass: glassy inharmonic bells with a long ring",
    "fluent": "Fluent: soft marimba notes", "paper": "Paper: rustle of a sheet, pencil ticks and taps on the desk",
    "neumorph": "Neumorphism: muted soft thuds", "brutal": "Brutalism: hard clicks and low thumps",
    "retro": "Retro 9x: 8-bit square-wave chiptune motifs", "neon": "Neon: synth saw with a filter sweep",
}


def sound_pack_desc(pack: str) -> str:
    return t(_PACK_DESC[pack]) if pack in _PACK_DESC else t("Sound pack: %s", pack)


def sound_packs():
    return ["theme"] + [os.path.basename(d) for d in fsutil.glob_sorted(paths.PLUGIN / "sounds", "", dirs=True)]


def sounds():
    data = jsonio.read(state.SOUND_CFG)
    cur = jsonio.tostring(state.alt(data.get("soundPack"), "theme")) if isinstance(data, dict) else "theme"
    out = [f"{t('Sound packs')}\tsection:Sound packs\t\t0\t\theader"]
    for pack in sound_packs():
        d = sound_pack_desc(pack)
        out.append(f"{pack}\tpack:{pack}\t\t{_cur(pack == cur)}\t{d}{NL}{NL}{t('⏎ — use this pack · p — listen without switching')}\t{d}")
    out += tweaks.prefixed(tweaks.list_tweaks("SOUND_TWEAKS"), skip_key="soundPack")
    out.append(f"{t('Test events')}\tsection:Test events\t\t0\t\theader")
    for ev in SOUND_EVENTS:
        out.append(f"▶ {ev}\ttest:{ev}\t\t0\t{t('⏎ or p — play «%s» with the current pack', ev)}")
    return out


_FONT_GROUP = {"base": "Without a style", "dotmatrix": "DOT-MATRIX", "paper": "Paper", "retro": "Retro"}


def fonts():
    if not fsutil.which("omarchy-font-profile"):
        return []
    cur = fsutil.run(["omarchy-font-profile"])
    out, last = [], ""
    for line in fsutil.run(["omarchy-font-profile", "list"]).split("\n"):
        if not line:
            continue
        name, desc, group, sans, mono, title = fsutil.read_fields(line, 6)
        if group != last:
            out.append(f"{t(_FONT_GROUP.get(group, group))}\tsection:{group}\t\t0\t\theader")
            last = group
        out.append(f"{name}\t{name}\t\t{_cur(name == cur)}\t{t(desc)}\t{sans} · {mono} · {title or sans}")
    return out


# ── Рабочий стол ──

def dotify():
    d = walls_dir()
    cur_bg = state.current_bg()
    out = [
        f"{t('⚡ Dotify current wallpaper')}\tcurrent\t{cur_bg}\t0\t"
        + t("Convert the active wallpaper into an LED dot-matrix wallpaper at your monitor's native resolution and apply it."),
        f"{t('󰣇 Generate Arch Linux LED wallpaper')}\tarch\t\t0\t"
        + t("Render the Arch Linux glyph on an LED dot-matrix grid for your monitor resolution and apply it."),
        f"{t('📂 Dotify a whole folder…  (O)')}\tpick-dir\t\t0\t"
        + t("Pick a folder; every image directly in it is converted into an LED dot-matrix wallpaper for the current theme."),
        f"{t('🖼 Dotify image(s) from anywhere…  (o)')}\tpick-files\t\t0\t"
        + t("Pick one or more images (Ctrl/Shift-click) from any folder to convert into LED dot-matrix wallpapers."),
    ]
    out += tweaks.prefixed(tweaks.list_tweaks("DOTIFY_TWEAKS"))
    out.append(f"{t('Source images')}\tsection:Source images\t\t0\t\theader")
    for f in fsutil.images_in(d, 10):
        out.append(f"{f[len(d) + 1:] if f.startswith(d + '/') else f}\t{f}\t{f}\t0")
    return out


LIVE_THUMBS = paths.HOME / ".cache/omarchy-customizer/live-thumbs"


def live_thumb(f):
    """Превью живых обоев: у видео — кадр на 1-й секунде (ffmpeg, кэш по пути и mtime), GIF Qt покажет сам."""
    if not fsutil.is_live(f) or f.lower().endswith(".gif"):
        return f
    try:
        key = hashlib.md5(f"{f}\t{os.path.getmtime(f)}".encode()).hexdigest()
    except OSError:
        return ""
    dst = LIVE_THUMBS / f"{key}.jpg"
    if not dst.is_file() and shutil.which("ffmpeg"):
        os.makedirs(LIVE_THUMBS, exist_ok=True)
        for seek in (["-ss", "1"], []):
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *seek, "-i", f, "-frames:v", "1",
                            "-vf", "scale=640:-2", str(dst)], capture_output=True)
            if dst.is_file():
                break
    return str(dst) if dst.is_file() else ""


def _wall_row(f, cur_bg, star=""):
    """Строка обоев: живые — со ▶, превью-кадром и словом live в заметке (его находит поиск /)."""
    live = fsutil.is_live(f)
    note = f"{t('Live wallpaper (owe) · live')}" if live else ""
    return f"{star}{'▶ ' if live else ''}{os.path.basename(f)}\t{f}\t{live_thumb(f)}\t{_cur(os.path.realpath(f) == cur_bg)}\t{note}"


def walls():
    d = walls_dir()
    out = [
        f"{t('📂 Recolor a whole folder…  (O)')}\tpick-dir\t\t0\t"
        + t("Pick a folder; every image directly in it is recolored into the theme's backgrounds."),
        f"{t('🖼 Recolor image(s) from anywhere…  (o)')}\tpick-files\t\t0\t" + t("Pick one or more images (Ctrl/Shift-click) from any folder."),
    ]
    for f in fsutil.images_in(d, 10, fsutil.MEDIA_EXT):
        live = fsutil.is_live(f)
        out.append(f"{'▶ ' if live else ''}{f[len(d) + 1:] if f.startswith(d + '/') else f}\t{f}\t{live_thumb(f)}\t0"
                   + (f"\t{t('Live wallpaper (owe) · live')}{NL}{NL}{t('Recolored frame by frame with ffmpeg (slow); a video becomes mp4.')}" if live else ""))
    return out


_PAL_KEYS = ["background", "foreground", "accent", "red", "yellow", "green", "blue", "magenta"]
_PAL_RE = re.compile(r"^(background|foreground|accent|red|yellow|green|blue|magenta) *=")


def _palette(colors_toml) -> str:
    c = {}
    try:
        with open(colors_toml, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if _PAL_RE.match(line):
                    fields = line.split('"')
                    c[fields[0].split(" ", 1)[0]] = fields[1] if len(fields) > 1 else ""
    except OSError:
        return None
    return " ".join(c[k] for k in _PAL_KEYS if c.get(k))


def _theme_label(slug: str) -> str:
    out, prev = [], "-"
    for ch in slug:
        if ch == "-":
            out.append(" ")
        elif prev == "-" and "a" <= ch <= "z":
            out.append(ch.upper())
        else:
            out.append(ch)
        prev = ch
    return "".join(out)


def themes():
    current = state.theme_name()
    out = []
    if fsutil.which("omarchy-wallpaper-theme"):
        for scheme in ("tonal-spot", "vibrant", "expressive", "fruit-salad", "monochrome", "light"):
            out.append(f"{t('🎨 Theme from wallpaper: %s', scheme)}\tdynamic:{scheme}\t\t0\t"
                       + t("Build the “dynamic” theme from the current wallpaper with matugen (Material You) and apply it."))
    user_root = str(paths.CONFIG / "themes")
    sys_root = OMARCHY_PATH + "/themes"
    names = set()
    for root in (user_root, sys_root):
        for p in fsutil.glob_sorted(root, "", dirs=True) if os.path.isdir(root) else []:
            names.add(os.path.basename(p))
        # find -mindepth 1 -maxdepth 1 -type d видит и скрытые каталоги
        try:
            for n in os.listdir(root):
                if n.startswith(".") and os.path.isdir(os.path.join(root, n)):
                    names.add(n)
        except OSError:
            pass
    allnames = fsutil.lsort(list(names))
    favs = [x for x in (jsonio.read(FAV_THEMES) or []) if isinstance(x, str)] if isinstance(jsonio.read(FAV_THEMES), list) else []
    pal = {}
    for root in (user_root, sys_root):
        for d in fsutil.glob_sorted(root, "", dirs=True) if os.path.isdir(root) else []:
            p = _palette(os.path.join(d, "colors.toml"))
            if p is not None:
                pal[d] = p

    def row(slug, star):
        d = f"{user_root}/{slug}"
        if not os.path.isdir(d):
            d = f"{sys_root}/{slug}"
        if not os.path.isdir(d):
            return
        prev = ""
        cands = [f"{d}/preview.{e}" for e in ("png", "jpg", "jpeg", "webp")]
        cands += [p for e in ("jpg", "jpeg", "png", "webp") for p in _glob_ci(f"{d}/backgrounds", e)]
        for p in cands:
            if os.path.isfile(p):
                prev = p
                break
        out.append(f"{star}{_theme_label(slug)}\t{slug}\t{prev}\t{_cur(slug == current)}\t{pal.get(d, '')}")

    if favs:
        out.append(f"{t('Favorites')}\tsection:Favorites\t\t0\t\theader")
        for slug in favs:
            row(slug, "★ ")
        out.append(f"{t('All themes')}\tsection:All themes\t\t0\t\theader")
    favset = set(favs)
    for slug in allnames:
        if slug and slug not in favset:
            row(slug, "")
    return out


def _glob_ci(directory, ext):
    """"$d"/backgrounds/*.<ext> c nocaseglob: файлы с расширением без учёта регистра, по алфавиту."""
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return fsutil.lsort([os.path.join(directory, n) for n in names
                         if not n.startswith(".") and n.lower().endswith("." + ext)])


def theme_walls(rel: str):
    if ".." in rel or rel.startswith("/"):
        rel = ""
    root = paths.CONFIG / "backgrounds" / state.theme_name()
    d = str(root) + (f"/{rel}" if rel else "")
    cur_bg = state.current_bg()
    out = []
    if rel:
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
        out.append(f"󰁝  ..\tdir:{parent}\t\t0\t{t('Back: %s', parent or t('all categories'))}\t{rel}")
    exts = fsutil.MEDIA_EXT
    # Избранные (f): в корне — разделом наверху, из любых папок; в списках файлов — со ★.
    favs = jsonio.read(FAV_WALLS)
    favs = [f for f in favs if isinstance(f, str) and os.path.isfile(f)] if isinstance(favs, list) else []
    favset = set(favs)
    star = lambda f: "★ " if f in favset else ""  # noqa: E731
    hdr = lambda title: f"{t(title)}\tsection:{title}\t\t0\t\theader"  # noqa: E731
    if not rel and favs:
        out.append(hdr("Favorites"))
        for f in favs:
            out.append(_wall_row(f, cur_bg, "★ "))
    # Файлы этого уровня: обои папки + (в корне) обои самой темы.
    files = []
    if os.path.isdir(d):
        files += fsutil.images_in(d, 1, exts)
    if not rel:
        bg = paths.CONFIG / "themes" / state.theme_name() / "backgrounds"
        if not bg.is_dir():
            bg = paths.HOME / ".local/state/omarchy/current/theme/backgrounds"
        files += fsutil.images_in(bg, 1, exts)
    static = [f for f in files if not fsutil.is_live(f)]
    # Живые — в корне отдельным разделом, со всех подпапок (их обычно мало); в подпапке — среди своих.
    live = [f for f in files if fsutil.is_live(f)]
    if not rel and os.path.isdir(d):
        live += [p for p in fsutil.walk_files(d, 10) if fsutil.is_live(p) and os.path.dirname(p) != d
                 and not os.path.basename(p).startswith(".")]
    if not rel:
        out.append(hdr("Static wallpapers"))
    if os.path.isdir(d):
        subs = fsutil.lsort([os.path.join(d, n) for n in os.listdir(d)
                             if not n.startswith(".") and os.path.isdir(os.path.join(d, n))])
        for sub in subs:
            n = sum(1 for p in fsutil.walk_files(sub, 10 ** 6)
                    if p.lower().endswith(exts) and not os.path.basename(p).startswith("."))
            if n <= 0:
                continue
            name = os.path.basename(sub)
            imgs = fsutil.images_in(sub, 10)
            first = imgs[0] if imgs else live_thumb(next((p for p in fsutil.images_in(sub, 10, exts)), ""))
            cur = cur_bg.startswith(os.path.realpath(sub) + "/")
            out.append(f"󰉋  {name}\tdir:{rel + '/' if rel else ''}{name}\t{first}\t{_cur(cur)}\t"
                       f"{t('Category — wallpapers: %s', n)}{NL}{NL}{t('⏎ — open · h — back')}\t{t('wallpapers: %s', n)}")
    for f in static:
        out.append(_wall_row(f, cur_bg, star(f)))
    if rel:
        for f in live:
            out.append(_wall_row(f, cur_bg, star(f)))
    elif live:
        out.append(hdr("Live wallpapers"))
        for f in fsutil.lsort(live):
            out.append(_wall_row(f, cur_bg, star(f)))
    return out


# ── Окна: анимации, прозрачность, блюр, шейдеры ──

def anims():
    # Снимок того, что стоит сейчас (пустой — ничего не выбрано), — его вернёт anim-restore.
    backup = paths.RUN / "active_animations.lua"
    os.makedirs(paths.RUN, exist_ok=True)
    active = state.ANIM_ACTIVE
    data = b""
    if active.is_file():
        data = active.read_bytes()
    backup.write_bytes(data)
    out = []
    for f in state.anim_files():
        cur = active.is_file() and open(f, "rb").read() == data
        out.append(f"{os.path.basename(f)[:-4]}\t{f}\t{f}\t{_cur(cur)}")
    return out


def opacity():
    out = []
    for line in fsutil.run([str(state.OPACITY), "list"]).split("\n"):
        if not line:
            continue
        n, a, i, cur = fsutil.read_ws(line, 4)
        out.append(f"{n}  ({a} / {i})\t{n}\t\t{cur}\tactive_opacity = {a} · inactive_opacity = {i}")
    return out


def blur():
    out = []
    for line in fsutil.run([str(state.BLUR), "list"]).split("\n"):
        if not line:
            continue
        n, sz, ps, v, no, cur = fsutil.read_ws(line, 6)
        if sz == "0" or (sz.lstrip("-").isdigit() and int(sz) == 0):
            out.append(f"{n}  ({t('no blur')})\t{n}\t\t{cur}\tsize 0 passes 0 vibrancy 0 noise 0")
        else:
            out.append(f"{n}  ({sz} × {ps})\t{n}\t\t{cur}\tsize {sz} passes {ps} vibrancy {v} noise {no}")
    return out


def shaders():
    cur = state.current_shader()
    out = [f"{t('⏻ Toggle shader (now: %s)', cur)}\ttoggle\t\t0", f"{t('⏭ Next shader')}\tnext\t\t0"]
    on = (state.STATE_HYPR / "reading-mode").is_file()
    out.append(f"{t('📖 Reading mode (now: %s)', t('on') if on else t('off'))}\treading\t\t0\t"
               + t("The screen as a printed page: ink on paper, flat windows, no animations. Super+Alt+R. Settings are below the shader list."))
    for f in fsutil.run([str(state.TOGGLE), "list"]).split("\n"):
        if not f:
            continue
        n = os.path.basename(f)
        n = n[:-5] if n.endswith(".frag") else n
        out.append(f"{n}\t{n}\t{f}\t{_cur(n == cur)}")
    return out + tweaks.prefixed(tweaks.list_tweaks("READING_TWEAKS"))


# ── Бар ──

def bar_layouts():
    cur = state.current_layout()
    out = [f"{t('💾 Save the current one as a preset…')}\tsave\t\t0\t"
           + t("Save the layout from shell.json as your own in %s — it shows up here with a ★.", paths.tilde(state.USER_LAYOUTS))]
    for f in fsutil.glob_sorted(state.USER_LAYOUTS, ".json"):
        stem = os.path.basename(f)[:-5]
        out.append(f"★ {stem}\t{f}\t{f}\t{_cur(stem == cur)}\t{state.meta(f)[1]}  ·  {state.layout_summary(f)}{NL}{NL}{t('Your layout: %s', paths.tilde(f))}")
    for f in fsutil.glob_sorted(state.BAR_DIR / "layouts", ".json"):
        stem = os.path.basename(f)[:-5]
        out.append(f"{stem}\t{f}\t{f}\t{_cur(stem == cur)}\t{state.meta(f)[1]}  ·  {state.layout_summary(f)}")
    return out


def bar_skins():
    # Снимок того, что на баре сейчас: превью перезаписывают его до bar-skins-restore.
    os.makedirs(paths.RUN, exist_ok=True)
    backup = paths.RUN / "bar-skin.json"
    if fsutil.nonempty(paths.BAR_SKIN):
        shutil.copyfile(paths.BAR_SKIN, backup)
    else:
        backup.write_text("{}\n")
    bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
    tr = bar.get("transparent") if isinstance(bar, dict) else None
    (paths.RUN / "bar-transparent").write_text((jsonio.tostring(tr) if tr not in (None, False) else "false") + "\n")
    cur = state.current_skin()
    out = [f"{t('💾 Save the current skin…')}\tsave\t{backup}\t0\t"
           + t("Save what is on the bar now as your own skin in %s — it shows up here with a ★.", paths.tilde(state.USER_SKINS))]
    for f in fsutil.glob_sorted(state.USER_SKINS, ".json"):
        stem = os.path.basename(f)[:-5]
        out.append(f"★ {stem}\t{f}\t{f}\t{_cur(stem == cur)}\t{state.meta(f)[1]}{NL}{NL}{t('Your skin: %s', paths.tilde(f))}")
    for f in fsutil.glob_sorted(state.BAR_DIR / "skins", ".json"):
        stem = os.path.basename(f)[:-5]
        out.append(f"{stem}\t{f}\t{f}\t{_cur(stem == cur)}\t{state.meta(f)[1]}")
    return out


_WIDGET_LABEL = {"dotmatrix-mark": "DOT-MATRIX logo", "active-app": "Active app", "battery-gauge": "Battery (LED)",
                 "dot-clock": "Clock (Doto)", "privacy-led": "Microphone LED", "runcat": "RunCat (runs faster with CPU load)",
                 "cpu-ram": "CPU / RAM rings", "cava-dots": "Cava dots (while music plays)", "focus-timer": "Focus timer (pomodoro)", "taskbar": "Taskbar / dock (windows; pinned apps on an empty workspace)"}
# QML-модули бара (kamradsmeshnyavy.bar/modules): ставятся в «Не на баре» даже если их никогда не было на баре.
BAR_MODULES = {"dotmatrix-mark": "DotMatrixMark.qml", "active-app": "ActiveAppIcon.qml", "battery-gauge": "BatteryGauge.qml",
               "dot-clock": "DotClock.qml", "privacy-led": "PrivacyLed.qml", "runcat": "RunCat.qml",
               "cpu-ram": "CpuRamRings.qml", "cava-dots": "CavaDots.qml", "focus-timer": "FocusTimer.qml", "taskbar": "Taskbar.qml"}
WIDGET_SETTINGS = [
    ("kamradsmeshnyavy.tray", "collapse", "false", "Tray: collapse into a drawer (opens on hover)"),
    ("kamradsmeshnyavy.tray", "monochrome", "true", "Tray: monochrome icons (colour on hover)"),
]


def _entry_id(e):
    return e.get("id") if isinstance(e, dict) else e


def bar_widgets():
    try:
        catalog = json.loads(fsutil.run(["omarchy", "plugin", "list", "--json"]) or "[]")
    except ValueError:
        catalog = []
    catalog = catalog if isinstance(catalog, list) else []

    def label(wid):
        if wid in _WIDGET_LABEL:
            return t(_WIDGET_LABEL[wid])
        for p in catalog:
            if isinstance(p, dict) and p.get("id") == wid:
                bw = p.get("barWidget")
                return jsonio.tostring(state.alt(bw.get("displayName") if isinstance(bw, dict) else None, p.get("name"), wid))
        return wid

    shell = jsonio.read_object(paths.SHELL_JSON)
    bar = shell.get("bar") if isinstance(shell.get("bar"), dict) else {}
    layout = bar.get("layout") if isinstance(bar.get("layout"), dict) else {}
    out, seen = [], set()
    # centerBegin / centerEnd бар рисует только при якоре центра — без него их записи считаются «не на баре».
    anchored = bool(bar.get("centerAnchor")) and bar.get("centerAnchor") in [_entry_id(e) for e in (layout.get("center") or [])]
    groups = (("left", "Left / top", ["left"]),
              ("center", "Center", ["centerBegin", "center", "centerEnd"] if anchored else ["center"]),
              ("right", "Right / bottom", ["right"]))
    for sec, title, secs in groups:
        out.append(f"{t(title)}\tsection:{sec}\t\t0\t\theader")
        for e in [x for s_ in secs for x in (layout.get(s_) or [])]:
            wid = jsonio.tostring(_entry_id(e)) if _entry_id(e) is not None else "null"
            if not wid:
                continue
            seen.add(wid)
            out.append(f"● {label(wid)}\ttweak:w:{wid}\t\t0\t{t('On the bar · %s', wid)}{NL}{NL}"
                       f"{t('h/l — move earlier / later (across sections at the edge) · ⏎ — remove from the bar')}\t{wid}\tmove\t\t\t{label(wid)}")
    out.append(f"{t('Not on the bar')}\tsection:off\t\t0\t\theader")
    hidden = jsonio.read(BAR_HIDDEN)
    cand = sorted(hidden.keys()) if isinstance(hidden, dict) else []
    cloned = []
    for m in fsutil.glob_sorted(paths.CONFIG / "plugins", "", dirs=True):
        mf = jsonio.read(os.path.join(m, "manifest.json"))
        if isinstance(mf, dict):
            cf = (mf.get("omarchy") or {}).get("clonedFrom") if isinstance(mf.get("omarchy"), dict) else None
            if cf not in (None, False):
                cloned.append(cf)
    for p in catalog:
        if isinstance(p, dict) and "bar-widget" in (p.get("kinds") or []) and p.get("id") not in cloned:
            cand.append(jsonio.tostring(p.get("id")))
    if (state.BAR_DIR / "modules").is_dir():
        cand += [m for m, f in BAR_MODULES.items() if (state.BAR_DIR / "modules" / f).is_file()]
    done = set()
    for wid in cand:
        if wid in done:
            continue
        done.add(wid)
        if not wid or wid in seen:
            continue
        out.append(f"○ {label(wid)}\ttweak:w:{wid}\t\t0\t{t('Not on the bar · %s', wid)}{NL}{NL}"
                   f"{t('⏎ — put on the bar (back to its old place if it was removed here)')}\t{wid}\tadd\t\t\t{label(wid)}")
    out.append(f"{t('Widget settings')}\tsection:settings\t\t0\t\theader")
    for tid, key, default, lab in WIDGET_SETTINGS:
        v = default
        for sec in layout.values():
            hit = next((e for e in (sec or []) if isinstance(e, dict) and e.get("id") == tid), None)
            if hit is not None:
                v = jsonio.tostring(hit[key]) if hit.get(key) is not None else default
                break
        out.append(f"{t(lab)}:  {v}\ttweak:wset:{tid}:{key}\t\t0\t{t('Now: %s', v)}{NL}{t('Default: %s', default)}{NL}{NL}"
                   f"{t('h/l or ⏎ — on/off')}\t{t('default: %s', default)}\tbool\t{default}\t{v}\t{t(lab)}")
    return out


# ── Док Omarchy (omarchy.dock: shell.json → dock; omarchy dock …) ──

def dock():
    shell = jsonio.read_object(paths.SHELL_JSON)
    cfg = shell.get("dock") if isinstance(shell.get("dock"), dict) else {}
    pos = str(cfg.get("position") or "bottom")
    auto = cfg.get("autohide") is True
    pinned = cfg.get("pinned") if isinstance(cfg.get("pinned"), list) else []
    on = dock_enabled()
    hdr = lambda title, sid: f"{t(title)}\tsection:{sid}\t\t0\t\theader"  # noqa: E731
    out = [f"{t('Dock: on') if on else t('Dock: off')}\ttoggle\t\t{1 if on else 0}\t"
           + t("The Omarchy dock (plugin omarchy.dock). ⏎ — turn it on / off. The Taskbar bar module uses the same pinned apps."),
           hdr("Edge", "edge")]
    for p, icon in (("bottom", "󰁅"), ("top", "󰁝"), ("left", "󰁍"), ("right", "󰁔")):
        out.append(f"{icon}  {t(p)}\tpos:{p}\t\t{1 if p == pos else 0}\t{t('Dock at the %s edge (omarchy dock position %s)', t(p), p)}")
    out.append(hdr("Behaviour", "behaviour"))
    out.append(f"{t('Auto-hide: %s', t('on') if auto else t('off'))}\tautohide\t\t{1 if auto else 0}\t"
               + t("Hide the dock until the pointer reaches its edge (omarchy dock autohide). ⏎ — toggle."))
    out.append(hdr("Pinned apps", "pinned"))
    out.append(f"{t('＋ Pin an app…')}\tpin-pick\t\t0\t" + t("Pick an installed app from the list (zenity) and keep it in the dock."))
    names = _desktop_names()
    for i, pid in enumerate(pinned):
        out.append(f"★ {names.get(pid, pid)}\tunpin:{pid}\t\t0\t{t('Pinned · %s', pid)}{NL}{NL}"
                   + t("⏎ — unpin") + f"\t{pid}")
    return out


def dock_enabled():
    """omarchy.dock — стоковый, включён по умолчанию и в shell.json не перечислен: спрашиваем omarchy plugin list."""
    try:
        cat = json.loads(fsutil.run(["omarchy", "plugin", "list", "--json"]) or "[]")
    except ValueError:
        return False
    return any(isinstance(p, dict) and p.get("id") == "omarchy.dock" and p.get("enabled") is True for p in cat)


def _desktop_names():
    """id .desktop → Name, из стандартных каталогов приложений."""
    out = {}
    dirs = [paths.HOME / ".local/share/applications", "/usr/share/applications", "/var/lib/flatpak/exports/share/applications"]
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            if not n.endswith(".desktop"):
                continue
            pid = n[:-8]
            if pid in out:
                continue
            try:
                with open(os.path.join(d, n), encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("Name="):
                            out[pid] = line[5:].strip()
                            break
                        if line.startswith("[") and line.strip() != "[Desktop Entry]":
                            break
            except OSError:
                pass
    return out


# ── Блокировка, лаунчер, пикер ──

def lock():
    cur = state.lock_current()
    designs = jsonio.read(state.LOCK_PLUGIN / "designs/designs.json")
    designs = designs if isinstance(designs, list) else []
    ids = [jsonio.tostring(d.get("id")) for d in designs if isinstance(d, dict)]
    ids += ["my:" + os.path.basename(f) for f in fsutil.glob_sorted(LOCK_USER_DIR, ".qml")]
    missing = sum(1 for i in ids if not (CACHE_LOCK / f"{state.lock_thumb_name(i)}.jpg").is_file())
    out = []
    if missing > 0:
        out.append(f"{t('📸 Capture missing previews (%s)  (T)', missing)}\tmissing-thumbs\t\t0\t"
                   + t("Only designs without a preview show on screen in turn (≈1.5 s each) and are captured."))
    out.append(f"{t('🔄 Refresh previews of all designs')}\tregen-thumbs\t\t0\t"
               + t("Each design shows on screen in turn (≈1.5 s each) and is captured in the current theme's colours."))
    lang = state.i18n.lang()
    for d in designs:
        if not isinstance(d, dict):
            continue
        fields = [fsutil.tsv_escape(jsonio.tostring(x)) for x in (
            d.get("id"), d.get("name"), state.alt(d.get("description_" + lang), d.get("description")),
            " · ".join(d.get("tags") or []))]
        did, name, desc, tags = fsutil.read_fields("\t".join(fields), 4)
        out.append(f"{name}\t{did}\t{CACHE_LOCK}/{state.lock_thumb_name(did)}.jpg\t{_cur(did == cur)}\t"
                   f"{desc}{NL}{NL}{t('p — show it live · ⏎ — select')}\t{tags}")
    for f in fsutil.glob_sorted(LOCK_USER_DIR, ".qml"):
        name = os.path.basename(f)
        did = "my:" + name
        out.append(f"{name[:-4]}\t{did}\t{CACHE_LOCK}/{state.lock_thumb_name(did)}.jpg\t{_cur(did == cur)}\t"
                   f"{t('Your design: %s', f)}{NL}{NL}{t('p — show it live · ⏎ — select')}\tcustom")
    return out


def _skin_desc(sk: str) -> str:
    fixed = {"dotmatrix": "DOT-MATRIX hardware bump with concave fillets, monochrome app grid, > actions and = LED calculator",
             "sketchbook": "Sketchbook page: polaroid cards on a ruled sheet, pencil circle, tape and a sticky note"}
    if sk in fixed:
        return t(fixed[sk])
    if sk.startswith("drawer-"):
        return t("DOT-MATRIX drawer layout in the %s style finish: search, 7-column grid, > actions, = calculator", sk[7:])
    more = {"list": "Stock Omarchy compact list card", "board": "Tactile keycap board grid",
            "constellation": "Starfield constellation launcher", "terminal": "Minimalist terminal prompt launcher"}
    if sk in more:
        return t(more[sk])
    if sk.endswith("-hack"):
        return t("Minimalist terminal-style hack variant of %s", sk[:-5])
    if sk.endswith("-term"):
        return t("Terminal-palette variant of %s", sk[:-5])
    return t("Launcher skin: %s", sk)


def launcher():
    cur = state.launcher_current()
    out = [f"{t('🚀 Open launcher  (p)')}\topen\t\t0\t" + t("Open the application launcher with the active skin.")]
    out += tweaks.prefixed(tweaks.list_tweaks("LAUNCHER_TWEAKS"))
    out.append(f"{t('Skins')}\tsection:Skins\t\t0\t\theader")
    skins = []
    conf = state.MENU_PLUGIN / "SkinConfig.qml"
    if conf.is_file():
        skins.append("list")
        for line in conf.read_text(errors="replace").split("\n"):
            if re.match(r'^    "[a-z0-9-]+":', line):
                skins.append(line.split('"')[1])
    done = set()
    for sk in skins:
        if sk in done or not sk:
            continue
        done.add(sk)
        out.append(f"{sk}\tskin:{sk}\t\t{_cur(sk == cur)}\t{_skin_desc(sk)}{NL}{NL}{t('⏎ — select · p — open launcher')}")
    return out


def picker_prune_summary() -> str:
    """Сколько миниатюр пикера можно удалить (picker_prune --dry-run)."""
    cache = os.path.realpath(PICKER_CACHE)
    keep = set()
    try:
        with open(os.path.join(cache, "index.tsv"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 3:
                    continue
                path, sig, h = parts
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if f"{st.st_size}:{int(st.st_mtime)}" == sig:
                    keep.add(h + ".jpg")
    except FileNotFoundError:
        pass
    try:
        names = os.listdir(cache)
    except OSError:
        return ""
    for name in names:
        if name.endswith(".rows"):
            with open(os.path.join(cache, name), encoding="utf-8", errors="replace") as fh:
                for row in fh:
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
    return t("Can delete: %s thumbnails, %s GB; %s stay", count, f"{size / 1024 ** 3:.1f}", len(keep))


def theme_switcher():
    du = fsutil.run(["du", "-sh", str(PICKER_CACHE)]).split("\t", 1)[0]
    out = [
        f"{t('⚡ Cache thumbnails')}\tcache\t\t0\t"
        + t("Make thumbnails for the theme switcher (all themes) and for the current theme's wallpapers ahead of time, so the pickers open instantly.")
        + NL + NL + t("Cache: %s", f"{PICKER_CACHE} ({du})"),
        f"{t('🧹 Clean up unused thumbnails')}\tprune\t\t0\t"
        + t("Delete thumbnails of images that are gone or have changed. Thumbnails of existing images stay.")
        + NL + NL + picker_prune_summary(),
    ]
    out += tweaks.prefixed(tweaks.list_tweaks("PICKER_TWEAKS"))
    data = jsonio.read(state.PICKER_CFG)
    cur = jsonio.tostring(state.alt(data.get("style"), "slices")) if isinstance(data, dict) else "slices"
    for st, desc in (("slices", "Slanted slices — stock Omarchy"), ("cards", "Even rounded cards"),
                     ("coverflow", "Neighbours turned in 3D, like iTunes"),
                     ("strip", "A strip of equal cards, the selected one bigger"),
                     ("wide", "A huge preview and thin slices"), ("polaroid", "Cards in a white frame with a caption"),
                     ("honeycomb", "Honeycomb: a big hexagon in the middle, neighbours in rings of hexagons around it (after Vitreus)"),
                     ("dots", "Round thumbnails; the preview assembles from dots in a wave (after glyph-rice)")):
        out.append(f"{st}\tstyle:{st}\t\t{_cur(st == cur)}\t{t(desc)}{NL}{NL}{t('⏎ — select · p — open the theme switcher')}")
    return out


# ── status / available ──

def status():
    olist = fsutil.run([str(state.OPACITY), "list"])
    blist = fsutil.run([str(state.BLUR), "list"])
    ocur = next((f[0] for f in (fsutil.read_ws(ln, 5) for ln in olist.split("\n") if ln) if f[3] == "1"), "")
    bcur = next((f[0] for f in (fsutil.read_ws(ln, 7) for ln in blist.split("\n") if ln) if f[5] == "1"), "")
    if not ocur:
        ocur = state.opacity_current()
    if not bcur:
        bcur = fsutil.run([str(state.BLUR), "current"])
    state._memo["opacity"] = ocur
    anim = "custom" if fsutil.nonempty(state.ANIM_ACTIVE) else "default"
    try:
        active = state.ANIM_ACTIVE.read_bytes()
        for f in state.anim_files():
            if open(f, "rb").read() == active:
                anim = os.path.basename(f)[:-4]
                break
    except OSError:
        pass
    stem = state.current_preset_stem()
    preset = "custom"
    if stem != "custom":
        preset = stem
        for f in (state.USER_PRESETS / f"{stem}.json", state.PRESET_DIR / f"{stem}.json"):
            if f.is_file():
                preset = state.preset_name(f)
                break
    sstem = state.current_style_stem()
    sf = state.style_file_of(sstem) if sstem != "custom" else None
    style = state.preset_name(sf) if sf else "custom"
    out = [f"preset\t{preset}", f"style\t{style}"]
    if fsutil.which("omarchy-font-profile"):
        out.append(f"fonts\t{fsutil.run(['omarchy-font-profile'])}")
    snd = jsonio.read(state.SOUND_CFG)
    if isinstance(snd, dict):
        sound = "off" if snd.get("sounds") is False else jsonio.tostring(state.alt(snd.get("soundPack"), "theme"))
    else:
        sound = "theme"
    cur_bg = state.current_bg()
    out += [f"sound\t{sound}", f"theme\t{state.theme_name()}", f"wallpaper\t{cur_bg}", f"anims\t{anim}",
            f"shader\t{state.current_shader()}", f"opacity\t{ocur}", f"blur\t{bcur}", f"glyph\t{state.glyph_status()}",
            f"bar-skin\t{state.current_skin()}", f"bar-layout\t{state.current_layout()}", f"lock\t{state.lock_current()}"]
    fx = jsonio.read(state.FX_CFG)
    out.append("fx\t" + (jsonio.tostring(state.alt(fx.get("type"), "slant")) if isinstance(fx, dict) else "slant"))
    pk = jsonio.read(state.PICKER_CFG)
    out.append("picker\t" + (jsonio.tostring(state.alt(pk.get("style"), "slices")) if isinstance(pk, dict) else "slices"))
    out.append(f"launcher\t{state.launcher_current()}")
    nxt = next((f for f in fsutil.images_in(os.path.dirname(cur_bg) if cur_bg else ".", 1) if f != cur_bg), "") if cur_bg else ""
    out.append(f"wallpaper-next\t{nxt}")
    prev_dir = paths.CACHE / "omarchy/theme-selector/previews"
    files = fsutil.lsort(fsutil.walk_files(prev_dir, 1))
    cur_theme = state.theme_name()
    c = 0
    for i, f in enumerate(files, 1):
        n = re.sub(r"\.[^.]+$", "", os.path.basename(f))
        if n == cur_theme:
            c = i
    c = c or 4
    s = max(1, c - 3)
    e = min(len(files), s + 6)
    out.append("picker-previews\t" + "|".join(files[s - 1:e]))
    ov = next((f"{f[1]} {f[2]}" for f in (fsutil.read_ws(ln, 5) for ln in olist.split("\n") if ln) if f[3] == "1"), "")
    bv = next((f"{f[1]} {f[2]} {f[3]} {f[4]}" for f in (fsutil.read_ws(ln, 7) for ln in blist.split("\n") if ln) if f[5] == "1"), "")
    out += [f"opacity-values\t{ov}", f"blur-values\t{bv}"]
    return out


def _dotify_python() -> bool:
    import importlib.util
    if importlib.util.find_spec("numpy") and importlib.util.find_spec("PIL"):
        return True
    py = shutil.which("python3")
    return bool(py) and fsutil.run([py, "-I", "-c", "import numpy, PIL; print(1)"]) == "1"


def available():
    plugins = paths.CONFIG / "plugins"
    out = ["presets", "styles", "windows"]
    if fsutil.which("omarchy-font-profile"):
        out.append("fonts")
    if fsutil.which("pw-play"):
        out.append("sounds")
    out += ["themes", "theme-walls"]
    if fsutil.which("lutgen") and fsutil.which("zenity"):
        out.append("walls")
    if _dotify_python():
        out.append("dotify")
    out += ["anims", "opacity", "blur", "glyph", "shaders"]
    if (state.BAR_DIR / "manifest.json").is_file():
        out += ["bar-skins", "bar-layouts", "bar-tweaks"]
    out.append("bar-widgets")
    if fsutil.which("omarchy-dock"):
        out.append("dock")
    if (state.LOCK_PLUGIN / "manifest.json").is_file():
        out += ["lock", "lock-tweaks"]
    for plugin, cats in (("background", ["wallpaper-fx"]), ("widgets", ["widgets", "dashboard"]), ("osd", ["osd"]),
                         ("notifications", ["notifications"]), ("image-picker", ["theme-switcher"])):
        if (plugins / f"kamradsmeshnyavy.{plugin}/manifest.json").is_file():
            out += cats
    if (state.MENU_PLUGIN / "manifest.json").is_file():
        out.append("launcher")
    if fsutil.which("zenity"):
        out.append("has:zenity")
    return out
