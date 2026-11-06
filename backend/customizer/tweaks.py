"""Строки настроек (list_tweaks в customizer.sh): вывод TSV байт в байт как у bash-версии.

Поля: подпись · value · файл · current(0) · заметка (литеральные \\n) · подпись под строкой ·
тип · аргументы · сырое значение · имя без значения.
"""
import os
import re

from . import jsonio, paths, settings
from .i18n import t


def file_values(path) -> dict:
    """Значения файла настроек строками (null — как будто ключа нет)."""
    return {k: jsonio.tostring(v) for k, v in jsonio.read_object(path).items() if v is not None}


def default_label(key: str, value: str) -> str:
    """Как показывать значение в подписи: особые значения — словами (default_label)."""
    special = {
        "height:0": "auto", "wsActiveColor:default": "as in the style (omarchy — text colour, otherwise accent)",
        "avatar:": "~/.face (or the first letter of the name)", "wallpaperBlur:1": "1 (stock)",
        "expandedWidth:0": "from the style", "expandedHeight:0": "from the style", "sliceWidth:0": "from the style",
        "sliceHeight:0": "from the style", "cardRadius:-1": "from the style", "scrimAlpha:-1": "from the theme",
        "duration:420": "420 (stock)", "compactHeight:0": "unchanged", "compactAlpha:-1": "as usual",
        "compact:off": "off", "compact:single": "one window on the workspace", "compact:fullscreen": "fullscreen window",
        "compact:always": "always",
        "compactModules:essentials": "essentials (menu, workspaces, clock, network, audio, power)",
        "compactModules:center": "center (center only)", "compactModules:minimal": "minimal (workspaces + clock)",
        "compactModules:all": "all (everything)", "compactShape:same": "same (as usual)",
        "compactReserve:keep": "keep (unchanged, windows don't jump)",
        "compactReserve:shrink": "shrink (windows take the space)", "padding:-1": "stock",
        "backgroundAlpha:-1": "from the theme", "gradient:none": "none", "font:": "system",
    }
    pair = f"{key}:{value}"
    if pair == "ownerMessage:":
        return t("Hello, %s", os.environ.get("USER", ""))
    if key.startswith("dotmatrix") and value == "default":
        return t("auto (theme or mono palette)")
    if pair in special:
        return t(special[pair])
    if value == "bar":
        return t("bar (theme colour)")
    return value


# Bar Tweaks: для каких форм бара параметр имеет смысл (bar_tweak_note).
_NEED = {
    "gap": "floating pill islands", "margin": "floating pill islands notch", "width": "floating pill notch",
    "radius": "floating islands notch hug frame", "frameWidth": "frame", "islandGap": "islands",
    "shadow": "floating pill islands notch underline", "glow": "floating pill islands notch underline",
}


def bar_tweak_note(key: str, shape: str, compact: str) -> str:
    if key == "compact":
        return ""
    if key.startswith("compact"):
        return t("only works when “Compact: when to shrink” is on") if compact == "off" else ""
    need = _NEED.get(key, "")
    if not need or shape in need.split():
        return ""
    return t("no effect for shape %s — needs: %s", shape, need)


_FOLLOW = re.compile(r"^(dash|osd|notify)(Background|Alpha|Radius|Border)$")

_HINTS = {
    "enum": None,  # с аргументом
    "color": "h/l — theme roles (bar = stock bar colour) · ⏎ — your own colour",
    "bool": "h/l or ⏎ — on/off",
    "font": "h/l — Nerd fonts from fc-list; empty = system",
    "text": "⏎ — enter text",
    "file": "⏎ — pick an image",
    "dir": "⏎ — pick a folder · h/l — back to default",
}


def _hint(item: settings.Item) -> str:
    if item.type == "num":
        lo, hi, st, _ = item.args.split()
        return t("h/l or −/+ — step %s, range %s", st, f"{lo} … {hi}")
    if item.type == "enum":
        return t("h/l — cycle: %s", item.args)
    return t(_HINTS.get(item.type) or "")


def list_tweaks(table_id: str) -> list:
    """Строки одной таблицы — как list_tweaks <ТАБЛИЦА> <файл>."""
    tbl = settings.table(table_id)
    path = paths.expand(tbl.file)
    values = file_values(path)
    shape = values.get("shape", "full")
    compact = values.get("compact", "off")
    out = []
    for it in tbl.items:
        if it.is_section:
            out.append(f"{t(it.section)}\tsection:{it.section}\t\t0\t\theader")
            continue
        default = it.default_value
        if it.key == "transparent":
            bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
            tr = bar.get("transparent") if isinstance(bar, dict) else None
            value = jsonio.tostring(tr) if tr not in (None, False) else "false"
        else:
            value = values.get(it.key, default)
        mark = "●  " if value != default else ""
        long = default_label(it.key, value)
        deflong = default_label(it.key, default)
        if it.type == "dir":
            if not value:
                long = t("default (current wallpaper)")
            deflong = t("default (current wallpaper)")
        sub = t("default: %s", deflong.split(" (", 1)[0])
        na = ""
        if table_id == "TWEAKS":
            na = bar_tweak_note(it.key, shape, compact)
        else:
            m = _FOLLOW.match(it.key)
            if m and values.get(m.group(1) + "FollowBar", "true") != "false":
                na = t("no effect while “Follow the bar style” is on")
        if na:
            sub = "○ " + na
        lab = t(it.label)
        note = (t("Now: %s", long) + "\\n" + t("Default: %s", deflong) + ("\\n" + na if na else "")
                + "\\n\\n" + _hint(it) + " · " + t("x — reset to default"))
        out.append("\t".join([f"{mark}{lab}:  {long.split(' (', 1)[0]}", it.key, str(path), "0", note, sub,
                              it.type, it.args, value, lab]))
    return out


def prefixed(lines: list, skip_key: str = "") -> list:
    """Как awk-обёртка в list: value строк-настроек получает префикс "tweak:"."""
    out = []
    for line in lines:
        f = line.split("\t")
        if skip_key and f[1] == skip_key:
            continue
        if not f[1].startswith("section:"):
            f[1] = "tweak:" + f[1]
        out.append("\t".join(f))
    return out
