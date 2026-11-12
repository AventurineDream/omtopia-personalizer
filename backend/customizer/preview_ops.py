"""Превью и мелкие команды overlay — перенос из диспетчера customizer.sh:
*-preview / *-restore, anim-*, lock-preview, sound-preview, glyph-test, fx-replay, picker-open,
launcher-open, theme-fav, *-delete и restore. Вывод вызванных скриптов возвращается в out
(в режиме serve stdout занят протоколом)."""
import json
import os
import re
import shutil
import subprocess

from . import fsutil, jsonio, paths, state, tweak_ops
from .i18n import t

RUN = paths.RUN
SKIN_BACKUP = RUN / "bar-skin.json"
TRANSPARENT_BACKUP = RUN / "bar-transparent"
ANIM_BACKUP = RUN / "active_animations.lua"
PLAY_SOUND = paths.PLUGIN / "scripts/play-sound.sh"
FAV_THEMES = paths.CONFIG / "customizer/favorite-themes.json"
FAV_WALLS = paths.CONFIG / "customizer/favorite-wallpapers.json"
WINDOW_CFG = paths.CONFIG / "customizer/windows.json"
HYPR_STATE = paths.STATE.parent / "hypr"
NO_GAPS_FLAG = paths.STATE.parent / "omarchy/toggles/hypr/window-no-gaps.lua"


def sh(args, env=None, quiet=True):
    """Команда; quiet — вывод в /dev/null (как >/dev/null), иначе stdout возвращается."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, env=env)
    except OSError:
        return 127, ""
    return p.returncode, "" if quiet else p.stdout


def _copy(src, dst):
    """cp: содержимое поверх, inode цели тот же."""
    os.makedirs(os.path.dirname(str(dst)), exist_ok=True)
    shutil.copyfile(src, dst)


# ── Скин бара ──

def bar_skin_preview(arg):
    src = SKIN_BACKUP if arg == "save" else arg
    if not os.path.isfile(src):
        return 0, ""
    _copy(src, paths.BAR_SKIN)
    d = jsonio.read(src)
    v = d.get("transparent") if isinstance(d, dict) else None
    tweak_ops.set_transparent(jsonio.tostring(v) if v not in (None, False) else "false")
    return 0, ""


def bar_skin_restore():
    if SKIN_BACKUP.is_file():
        _copy(SKIN_BACKUP, paths.BAR_SKIN)
    if TRANSPARENT_BACKUP.is_file():
        tweak_ops.set_transparent(fsutil.read_text(TRANSPARENT_BACKUP) or "")
    return 0, ""


# ── Анимации ──

def anim_preview(path):
    try:
        _copy(path, state.ANIM_ACTIVE)
    except OSError:
        pass
    return sh(["hyprctl", "reload"])[0], ""


def anim_restore():
    if ANIM_BACKUP.is_file():
        same = state.ANIM_ACTIVE.is_file() and ANIM_BACKUP.read_bytes() == state.ANIM_ACTIVE.read_bytes()
        if not same:
            _copy(ANIM_BACKUP, state.ANIM_ACTIVE)
            return sh(["hyprctl", "reload"])[0], ""
    return 0, ""


# ── Избранные темы ──

def theme_fav(slug):
    if not re.match(r"^[A-Za-z0-9._-]+$", slug or ""):
        return 1, ""
    cur = jsonio.read(FAV_THEMES)
    cur = cur if isinstance(cur, list) else []
    cur = [x for x in cur if x != slug] if slug in cur else cur + [slug]
    tweak_ops.write_inplace(FAV_THEMES, cur)
    return 0, ""


def wall_fav(path):
    """Избранные обои: абсолютный путь файла — добавить в конец / убрать."""
    path = os.path.abspath(os.path.expanduser(path or ""))
    if not os.path.isfile(path):
        return 1, ""
    cur = jsonio.read(FAV_WALLS)
    cur = [x for x in cur if isinstance(x, str)] if isinstance(cur, list) else []
    cur = [x for x in cur if x != path] if path in cur else cur + [path]
    tweak_ops.write_inplace(FAV_WALLS, cur)
    return 0, ""


WALL_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


def launcher_open(skin="", back=""):
    """Лаунчер (клон kamradsmeshnyavy.menu под id omarchy.menu): skin — показать этим скином без сохранения;
    back — строка Customizer, на которую вернуться после закрытия («home» — домашняя). Без back — как раньше."""
    payload = {"menu": "root"}
    if skin:
        payload["skin"] = skin
    if back:
        ret = {} if back == "home" else {"category": "launcher", "value": back}
        payload["returnTo"] = json.dumps(ret, ensure_ascii=False)
    return sh(["setsid", "-f", "omarchy-shell", "shell", "summon", "omarchy.menu",
               json.dumps(payload, ensure_ascii=False)])[0], ""


def wall_deletable(path) -> bool:
    """Свои обои: картинка в ~/.config/omarchy/backgrounds/… или ~/.config/omarchy/themes/<тема>/backgrounds/….
    Копии темы в ~/.local/state/omarchy/current/theme вернутся при следующей смене темы — их не трогаем."""
    path = str(path or "")
    if not (os.path.isfile(path) and path.lower().endswith(WALL_EXT)):
        return False
    real = os.path.realpath(path)
    walls = os.path.realpath(paths.CONFIG / "backgrounds") + os.sep
    if real.startswith(walls):
        return True
    themes = os.path.realpath(paths.CONFIG / "themes") + os.sep
    rest = real[len(themes):].split(os.sep) if real.startswith(themes) else []
    return len(rest) >= 3 and rest[1] == "backgrounds"


def wall_delete(path):
    """Обои — в корзину (подтверждение — в overlay). Текущие сначала сменяются следующими; путь
    убирается из избранного."""
    path = os.path.abspath(os.path.expanduser(path or ""))
    if not wall_deletable(path):
        return 1, t("Only your own wallpapers can be deleted (theme copies come back on theme change)")
    if os.path.realpath(path) == state.current_bg():
        sh(["omarchy-theme-bg-next"])
    if sh(["gio", "trash", path])[0] != 0:
        return 1, t("Could not move %s to the trash", os.path.basename(path))
    favs = jsonio.read(FAV_WALLS)
    if isinstance(favs, list) and path in favs:
        tweak_ops.write_inplace(FAV_WALLS, [x for x in favs if x != path])
    return 0, t("Deleted %s", os.path.basename(path))


# ── Удаление своих скинов, раскладок, пресетов, стилей (в корзину, с подтверждением) ──

def _delete(path, own_dir, title, ask, done, refuse, name, strict=True, extra_ok=True):
    path = str(path)
    ok = (os.path.isfile(path) and path.endswith(".json") and extra_ok
          and os.path.dirname(os.path.realpath(path)) == os.path.realpath(own_dir)
          and (os.path.isdir(own_dir) or not strict))
    if not ok:
        sh(["notify-send", "-u", "critical", title[0], refuse])
        return 1, ""
    if sh(["zenity", "--question", f"--title={title[1]}", f"--text={ask}"])[0] != 0:
        return 0, ""
    code = sh(["gio", "trash", path])[0]
    if code == 0:
        code = sh(["notify-send", "-t", "3000", title[0], done])[0]
    return code, ""


def skin_delete(path):
    name = os.path.basename(str(path))[:-5] if str(path).endswith(".json") else os.path.basename(str(path))
    return _delete(path, state.USER_SKINS, ("Bar Skin", t("Delete the bar skin")),
                   t("Delete your skin %s? The file goes to the trash.", name), t("Deleted %s", name),
                   t("Only your own skins (★) can be deleted"), name)


def layout_delete(path):
    name = os.path.basename(str(path))[:-5] if str(path).endswith(".json") else os.path.basename(str(path))
    return _delete(path, state.USER_LAYOUTS, ("Bar Layout", t("Delete the bar layout")),
                   t("Delete your layout %s? The file goes to the trash.", name), t("Deleted %s", name),
                   t("Only your own layouts (★) can be deleted"), name)


def preset_delete(path):
    ok_name = os.path.basename(str(path)) != "my-settings.json"
    valid = os.path.isfile(str(path)) and ok_name
    name = state.preset_name(path) if valid else ""
    return _delete(path, state.USER_PRESETS, ("Presets", t("Delete preset")),
                   t("Delete your preset %s? The file goes to the trash.", name), t("Deleted %s", name),
                   t("Only your own presets (★) can be deleted"), name, extra_ok=ok_name)


def style_delete(path):
    name = state.preset_name(path) if os.path.isfile(str(path)) else ""
    return _delete(path, state.USER_STYLES, ("Styles", t("Delete style")),
                   t("Delete your style %s? The file goes to the trash.", name), t("Deleted %s", name),
                   t("Only your own styles (★) can be deleted"), name, strict=False)


# ── restore: вернуть сохранённое после `hyprctl reload` ──

def window_overrides_lua():
    """Lua для hyprctl eval из windows.json — как jq-программа window_overrides_eval (байт в байт,
    включая её особенность: без windowLayout dwindle/master результат пустой)."""
    if not fsutil.nonempty(WINDOW_CFG):
        return None
    d = jsonio.read(WINDOW_CFG)
    if not isinstance(d, dict):
        return None
    ng = NO_GAPS_FLAG.is_file()

    def n(k):
        v = d.get(k)
        return jsonio.tostring(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def b(k):
        v = d.get(k)
        return jsonio.tostring(v) if isinstance(v, bool) else None

    items = []
    if not ng and d.get("windowLayout") in ("dwindle", "master"):
        g = ", ".join(x for x in (
            "gaps_in = " + n("windowGapsIn") if n("windowGapsIn") is not None else None,
            "gaps_out = " + n("windowGapsOut") if n("windowGapsOut") is not None else None,
            "border_size = " + n("windowBorder") if n("windowBorder") is not None else None) if x is not None)
        lay = 'layout = "' + d["windowLayout"] + '"'
        items.append("general = { " + ", ".join(x for x in (g, lay) if x) + " }")
        deco = []
        if n("windowDecoRounding") is not None:
            deco.append("rounding = " + n("windowDecoRounding"))
        if b("windowDim") is not None:
            deco.append("dim_inactive = " + b("windowDim"))
        if n("windowDimStrength") is not None:
            deco.append("dim_strength = " + n("windowDimStrength"))
        if b("windowShadow") is not None or n("windowShadowRange") is not None:
            sh_parts = []
            if b("windowShadow") is not None:
                sh_parts.append("enabled = " + b("windowShadow"))
            if n("windowShadowRange") is not None:
                sh_parts.append("range = " + n("windowShadowRange"))
            deco.append("shadow = { " + ", ".join(sh_parts) + " }")
        items.append("decoration = { " + ", ".join(deco) + " }")
    return "hl.config({ " + ", ".join(items) + " })"


def restore():
    out = []
    if fsutil.nonempty(state.ANIM_ACTIVE):
        sh(["hyprctl", "eval", fsutil.read_text(state.ANIM_ACTIVE) or ""])
    if fsutil.nonempty(HYPR_STATE / "opacity"):
        out.append(sh([str(state.OPACITY), "restore"], quiet=False)[1])
    if fsutil.nonempty(HYPR_STATE / "blur"):
        out.append(sh([str(state.BLUR), "restore"], quiet=False)[1])
    geo = HYPR_STATE / "geometry"
    if fsutil.nonempty(geo) and not NO_GAPS_FLAG.is_file():
        _gn, gi, go, bs, r, shd = fsutil.read_ws((fsutil.read_text(geo) or "").split("\n", 1)[0], 6)
        if shd:
            try:
                on = int(shd) > 0
            except ValueError:
                on = False
            sh(["hyprctl", "eval", f"hl.config({{ general = {{ gaps_in = {gi}, gaps_out = {go}, border_size = {bs} }}, "
                                   f"decoration = {{ rounding = {r}, shadow = {{ enabled = {'true' if on else 'false'} }} }} }})"])
    lua = window_overrides_lua()
    if lua:
        sh(["hyprctl", "eval", lua])
    out.append(sh([str(state.TOGGLE), "restore"], quiet=False)[1])
    if (state.STATE_HYPR / "reading-mode").is_file():
        sh([str(state.READING), "look"])   # режим чтения — поверх всего восстановленного
    sh(["hyprctl", "eval", 'hl.layer_rule({ match = { namespace = "omarchy-customizer" }, blur = true, ignore_alpha = 0.6 })'])
    import time
    os.makedirs(RUN, exist_ok=True)
    (RUN / "restored").write_text(f"{int(time.time())}\n")
    return 0, "".join(out)


# ── Диспетчер ──

def run(args):
    cmd, a = args[0], args[1:] + ["", ""]
    if cmd == "opacity-preview":
        return sh([str(state.OPACITY), "preview", a[0]], quiet=False)
    if cmd == "opacity-restore":
        return sh([str(state.OPACITY), "restore"], quiet=False)
    if cmd == "blur-preview":
        return sh([str(state.BLUR), "preview", a[0]], quiet=False)
    if cmd == "blur-restore":
        return sh([str(state.BLUR), "restore"], quiet=False)
    if cmd == "bar-skins-preview":
        return bar_skin_preview(a[0])
    if cmd == "bar-skins-restore":
        return bar_skin_restore()
    if cmd == "anim-preview":
        return anim_preview(a[0])
    if cmd == "anim-restore":
        return anim_restore()
    if cmd == "lock-preview":
        return sh(["omarchy-shell", "lock", "previewDesign", a[0]])[0], ""
    if cmd == "sound-preview":
        env = dict(os.environ, OMARCHY_SOUND_PACK=a[0] or "theme")
        return sh([str(PLAY_SOUND), a[1] or "notify", "--force"], env=env, quiet=False)
    if cmd == "fx-replay":
        return sh(["omarchy-shell", "background", "replay"])[0], ""
    if cmd == "picker-open":
        return sh(["setsid", "-f", "omarchy-menu", "toggle", "theme"])[0], ""
    if cmd == "launcher-open":
        return launcher_open(a[0], a[1])
    if cmd == "glyph-test":
        return sh(["omarchy-shell", "-q", "glyph", "test", a[0] or "false"])[0], ""
    if cmd == "theme-fav":
        return theme_fav(a[0])
    if cmd == "wall-fav":
        return wall_fav(a[0])
    if cmd == "wall-delete":
        return wall_delete(a[0])
    if cmd == "skin-delete":
        return skin_delete(a[0])
    if cmd == "layout-delete":
        return layout_delete(a[0])
    if cmd == "preset-delete":
        return preset_delete(a[0])
    if cmd == "style-delete":
        return style_delete(a[0])
    if cmd == "restore":
        return restore()
    return None


COMMANDS = {"opacity-preview", "opacity-restore", "blur-preview", "blur-restore", "bar-skins-preview",
            "bar-skins-restore", "anim-preview", "anim-restore", "lock-preview", "sound-preview", "fx-replay",
            "picker-open", "launcher-open", "glyph-test", "theme-fav", "wall-fav", "wall-delete", "skin-delete", "layout-delete",
            "preset-delete", "style-delete", "restore"}
