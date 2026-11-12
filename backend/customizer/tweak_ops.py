"""`tweak <ключ> <+|-|reset|pick|toggle>` и `tweak <ключ> set <значение>` — перенос tweak / tweak_set
из customizer.sh. Файлы пишутся как jq (отступ 2, порядок ключей сохраняется, новый — в конец) и
на месте (тот же inode): бар и шелл следят за ними через FileView.

Результат — (код, stdout, stderr), как у bash: у set неверное значение — код 2 и причина в stderr."""
import json
import os
import re
import subprocess

from . import fsutil, jsonio, paths, settings
from .i18n import t

WINDOW_CFG = paths.CONFIG / "customizer/windows.json"
PICKER_CFG = paths.CONFIG / "image-picker.json"
BAR_HIDDEN = paths.CONFIG / "customizer/bar-hidden.json"
NO_GAPS_FLAG = paths.STATE.parent / "omarchy/toggles/hypr/window-no-gaps.lua"


class Fail(Exception):
    """Отказ set: код 2, сообщение — в stderr."""


# ── JSON как jq ──

def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def write_inplace(path, obj):
    """cp поверх файла: содержимое меняется, inode тот же."""
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(obj))


def edit(path, fn) -> bool:
    """skin_edit: jq-правка файла настроек; нет файла / пустой — начинаем с {}. Битый JSON — не трогаем."""
    if fsutil.nonempty(path):
        data = jsonio.read(path)
        if data is None:
            return False
    else:
        data = {}
    write_inplace(path, fn(data))
    return True


def set_key(path, key, value):
    def fn(d):
        d = dict(d) if isinstance(d, dict) else d
        d[key] = value
        return d
    return edit(path, fn)


def del_key(path, key):
    def fn(d):
        if isinstance(d, dict):
            d = {k: v for k, v in d.items() if k != key}
        return d
    return edit(path, fn)


def json_number(text: str):
    """Строка числа → число JSON, как --argjson (2 → 2, 0.60 → 0.6)."""
    v = json.loads(text)
    return v


# ── Значения ──

def value_of(path, key, default) -> str:
    """tweak_value: значение строкой, null/нет ключа — default."""
    if key == "transparent":
        bar = jsonio.read_object(paths.SHELL_JSON).get("bar")
        v = bar.get("transparent") if isinstance(bar, dict) else None
        return jsonio.tostring(v) if v not in (None, False) else "false"
    d = jsonio.read(path) if fsutil.nonempty(path) else {}
    if not isinstance(d, dict):
        return default
    v = d.get(key)
    return default if v is None else jsonio.tostring(v)


def cycle(cur, direction, items):
    """Следующий по кругу; не нашли (задано руками) — вперёд первый, назад последний."""
    n = len(items)
    if n == 0:
        return ""
    i = items.index(cur) if cur in items else n
    if i == n:
        i = n - 1 if direction > 0 else 0
    return items[(i + direction + n) % n]


def color_roles():
    out = ["bar", "background", "foreground", "accent", "muted", "urgent",
           "dotmatrix.bg", "dotmatrix.fg", "dotmatrix.dim", "dotmatrix.line", "dotmatrix.surface",
           "dotmatrix.signal", "dotmatrix.danger"]
    try:
        with open(paths.THEME_COLORS, encoding="utf-8", errors="replace") as f:
            for line in f:
                if re.match(r'^[a-z_]+ *= *"#', line):
                    k = line.split("=", 1)[0].replace(" ", "")
                    if k not in ("background", "foreground", "accent", "muted"):
                        out.append(k)
    except OSError:
        pass
    return out


def font_list():
    names = set()
    for line in fsutil.run(["fc-list", ":", "family"]).split("\n"):
        for n in line.split(","):
            if re.search(r"nerd font$|( |^)NF$", n, re.I):
                names.add(n)
    return [""] + fsutil.lsort(list(names))


def num_step(cur: str, direction: int, lo: str, hi: str, step: str) -> str:
    """Шаг числа — как awk в tweak(): округление к шагу, -1 = «как в стоке», пределы."""
    c, lo_f, hi_f, s = _awk_num(cur), float(lo), float(hi), float(step)
    if lo_f == -1 and c < 0:
        v = 0.0 if direction > 0 else -1.0
    else:
        v = c + direction * s
        v = int(v / s + (0.5 if v >= 0 else -0.5)) * s
        if lo_f == -1 and v < 0:
            v = -1.0
    v = max(lo_f, min(hi_f, v))
    if s == int(s):
        return str(int(v))
    out = f"{v:.2f}".rstrip("0")
    return out[:-1] if out.endswith(".") else out


def _awk_num(s: str) -> float:
    """Число из строки, как awk: ведущее число, иначе 0."""
    m = re.match(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", s or "")
    return float(m.group(0)) if m else 0.0


# ── Побочные действия ──

def set_transparent(value: str):
    """Стоковый флаг bar.transparent в shell.json — только если меняется."""
    shell = jsonio.read(paths.SHELL_JSON)
    if not isinstance(shell, dict):
        return
    bar = shell.get("bar") if isinstance(shell.get("bar"), dict) else None
    cur = bar.get("transparent") if bar else None
    cur_s = jsonio.tostring(cur) if cur not in (None, False) else "false"
    if cur_s == value:
        return
    shell = dict(shell)
    shell["bar"] = dict(bar or {})
    shell["bar"]["transparent"] = value == "true"
    write_inplace(paths.SHELL_JSON, shell)


def _quiet(args):
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def window_after():
    """После шага по ключам window*: тоггл «без отступов», reload Hyprland и restore (как в bash)."""
    d = jsonio.read(WINDOW_CFG)
    if isinstance(d, dict) and "windowNoGaps" in d:
        want = jsonio.tostring(d["windowNoGaps"])
        if want == "true" and not NO_GAPS_FLAG.is_file():
            _quiet(["omarchy-hyprland-toggle", "window-no-gaps", "on"])
        elif want != "true" and NO_GAPS_FLAG.is_file():
            _quiet(["omarchy-hyprland-toggle", "window-no-gaps", "off"])
    _quiet(["hyprctl", "reload"])
    from . import preview_ops
    preview_ops.restore()


def reading_after():
    """После шага по ключам reading*: если режим чтения включён — перепечь шейдер и перезагрузить Hyprland."""
    from . import state
    if (state.STATE_HYPR / "reading-mode").is_file():
        _quiet([str(state.READING), "restore"])


# ── Виджеты бара и профиль шрифтов ──

def _layout():
    shell = jsonio.read_object(paths.SHELL_JSON)
    bar = shell.get("bar") if isinstance(shell.get("bar"), dict) else {}
    return shell, bar.get("layout") if isinstance(bar.get("layout"), dict) else {}


def _loc(wid):
    _, lay = _layout()
    for s in ("left", "center", "right"):
        ids = [e.get("id") if isinstance(e, dict) else e for e in (lay.get(s) or [])]
        if wid in ids:
            return s, ids.index(wid)
    return None


def widget_step(wid, how):
    loc = _loc(wid)
    if how == "set":
        return
    if how not in ("-", "+"):
        if loc:
            _widget_hide(wid, *loc)
        else:
            _widget_show(wid)
        return
    if not loc:
        return
    secs = ["left", "center", "right"]
    sec, idx = loc
    _, lay = _layout()
    n = len(lay.get(sec) or [])
    si = secs.index(sec)
    if how == "-":
        if idx > 0:
            place = {"section": sec, "index": idx - 1}
        elif si > 0:
            place = {"section": secs[si - 1], "index": len(lay.get(secs[si - 1]) or [])}
        else:
            return
    else:
        if idx < n - 1:
            place = {"section": sec, "index": idx + 1}
        elif si < 2:
            place = {"section": secs[si + 1], "index": 0}
        else:
            return
    _quiet(["omarchy-shell", "shell", "moveBarWidget", wid, json.dumps(place, separators=(",", ":"))])


def _widget_hide(wid, sec, idx):
    shell, lay = _layout()
    entry = (lay.get(sec) or [])[idx]
    hidden = jsonio.read(BAR_HIDDEN) if fsutil.nonempty(BAR_HIDDEN) else {}
    hidden = dict(hidden) if isinstance(hidden, dict) else {}
    hidden[wid] = {"entry": entry, "section": sec, "index": idx}
    write_inplace(BAR_HIDDEN, hidden)
    shell = dict(shell)
    shell["bar"] = dict(shell["bar"])
    shell["bar"]["layout"] = dict(lay)
    items = list(lay.get(sec) or [])
    shell["bar"]["layout"][sec] = items[:idx] + items[idx + 1:]
    write_inplace(paths.SHELL_JSON, shell)


def _widget_show(wid):
    hidden = jsonio.read(BAR_HIDDEN)
    stash = hidden.get(wid) if isinstance(hidden, dict) else None
    if stash:
        shell, lay = _layout()
        sec = stash["section"]
        items = list(lay.get(sec) or [])
        i = min(stash["index"], len(items))
        shell = dict(shell)
        shell["bar"] = dict(shell.get("bar") or {})
        shell["bar"]["layout"] = dict(lay)
        shell["bar"]["layout"][sec] = items[:i] + [stash["entry"]] + items[i:]
        write_inplace(paths.SHELL_JSON, shell)
        write_inplace(BAR_HIDDEN, {k: v for k, v in hidden.items() if k != wid})
    else:
        _quiet(["omarchy-shell", "shell", "putBarWidget", wid, "{}"])


def widget_setting(spec):
    from .lists_more import WIDGET_SETTINGS
    wid, key = spec.rsplit(":", 1)
    default = "false"
    for tid, tkey, d, _ in WIDGET_SETTINGS:
        default = d
        if tid == wid and tkey == key:
            break
    _, lay = _layout()
    cur = default
    for sec in lay.values():
        hit = next((e for e in (sec or []) if isinstance(e, dict) and e.get("id") == wid), None)
        if hit is not None:
            cur = jsonio.tostring(hit[key]) if hit.get(key) is not None else default
            break
    _quiet(["omarchy-shell", "shell", "setBarWidget", wid, key, "false" if cur == "true" else "true", "{}"])


def font_profile_step(how):
    if not fsutil.which("omarchy-font-profile"):
        return
    items = [ln.split("\t", 1)[0] for ln in fsutil.run(["omarchy-font-profile", "list"]).split("\n") if ln]
    cur = fsutil.run(["omarchy-font-profile"])
    nxt = "stock" if how == "reset" else cycle(cur, -1 if how == "-" else 1, items)
    _quiet(["omarchy-font-profile", nxt])


# ── tweak / tweak set ──

def _zenity(args) -> str:
    """Ответ zenity; отмена — None."""
    try:
        p = subprocess.run(["zenity", *args], capture_output=True, text=True)
    except OSError:
        return None
    return p.stdout.rstrip("\n") if p.returncode == 0 else None


def tweak(key, how):
    if key.startswith("w:"):
        return widget_step(key[2:], how)
    if key == "fontProfile":
        return font_profile_step(how)
    if key.startswith("wset:"):
        return widget_setting(key[5:])
    tbl, it = settings.find(key)
    if it is None:
        raise SystemExit(1)
    path = paths.expand(tbl.file)
    direction = -1 if how == "-" else 1
    if how == "reset":
        if key == "transparent":
            set_transparent("false")
        del_key(path, key)
        return
    kind = it.type
    if kind == "enum":
        nxt = cycle(value_of(path, key, it.values[0] if it.values else ""), direction, it.values)
        set_key(path, key, nxt)
    elif kind == "font":
        nxt = cycle(value_of(path, key, ""), direction, font_list())
        set_key(path, key, nxt)
    elif kind == "bool":
        nxt = "false" if value_of(path, key, it.args) == "true" else "true"
        if key == "transparent":
            set_transparent(nxt)
            set_key(path, "transparent", nxt == "true")
        else:
            set_key(path, key, nxt == "true")
    elif kind == "num":
        lo, hi, step, default = it.args.split()
        nxt = num_step(value_of(path, key, default), direction, lo, hi, step)
        if path == PICKER_CFG and nxt == default and default in ("0", "-1"):
            del_key(path, key)
        else:
            set_key(path, key, json_number(nxt))
    elif kind == "text":
        if how != "pick":
            return
        nxt = _zenity(["--entry", f"--title={key}", f"--text={t('Text (empty — default):')}",
                       f"--entry-text={value_of(path, key, '')}"])
        if nxt is None:
            return
        del_key(path, key) if not nxt else set_key(path, key, nxt)
    elif kind == "dir":
        if how != "pick":
            del_key(path, key)
            return
        start = value_of(path, key, "")
        start = str(paths.HOME) + start[1:] if start.startswith("~") else start
        if not os.path.isdir(start):
            start = str(paths.HOME / "Pictures")
        if not os.path.isdir(start):
            start = str(paths.HOME)
        nxt = _zenity(["--file-selection", "--directory", f"--title={t('Pick a folder')}", f"--filename={start}/"])
        if nxt:
            set_key(path, key, paths.tilde(nxt))
    elif kind == "file":
        if how != "pick":
            return
        nxt = _zenity(["--file-selection", f"--title={t('Avatar')}", f"--filename={paths.HOME}/",
                       "--file-filter=Images | *.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP"])
        if nxt is None:
            return
        set_key(path, key, nxt)
    elif kind == "color":
        if how == "pick":
            picked = _zenity(["--color-selection", f"--title={key}"])
            if picked is None:
                return
            m = re.match(r"rgba?\((\d+),(\d+),(\d+)", picked)
            nxt = "#%02x%02x%02x" % tuple(int(x) for x in m.groups()) if m else picked
        else:
            items = (["none"] if key == "gradient" else []) + (["default"] if key == "wsActiveColor" or key.startswith("dotmatrix") else [])
            items += ([it.args] if it.args.startswith("#") else []) + color_roles()
            nxt = cycle(value_of(path, key, it.args), direction, items)
        if nxt in ("none", "default"):
            del_key(path, key)
        else:
            set_key(path, key, nxt)


def tweak_set(key, value):
    tbl, it = settings.find(key)
    if it is None:
        raise Fail(t("Unknown setting: %s", key))
    path = paths.expand(tbl.file)
    value = value.strip()
    kind = it.type
    if kind == "num":
        lo, hi = it.args.split()[:2]
        if not re.match(r"^-?[0-9]+([.][0-9]+)?$", value):
            raise Fail(t("%s is not a number", value))
        if not float(lo) <= float(value) <= float(hi):
            raise Fail(t("%s is out of range %s … %s — not applied", value, lo, hi))
        set_key(path, key, json_number(_printf_g(float(value))))
    elif kind == "enum":
        if value not in it.values:
            raise Fail(t("%s is not one of: %s", value, it.args))
        set_key(path, key, value)
    elif kind == "bool":
        low = value.lower()
        if low in ("true", "on", "yes", "1", "вкл", "да"):
            value = "true"
        elif low in ("false", "off", "no", "0", "выкл", "нет"):
            value = "false"
        else:
            raise Fail(t("%s is not on/off", value))
        if key == "transparent":
            set_transparent(value)
        set_key(path, key, value == "true")
    elif kind == "color":
        if (key == "gradient" and value == "none") or ((key == "wsActiveColor" or key.startswith("dotmatrix")) and value == "default"):
            del_key(path, key)
        elif re.match(r"^#[0-9A-Fa-f]{6}$", value) or value in color_roles():
            set_key(path, key, value)
        else:
            raise Fail(t("%s is not #rrggbb or a theme colour role", value))
    elif kind == "font":
        if value and value not in font_list():
            raise Fail(t("Font not found: %s", value))
        del_key(path, key) if not value else set_key(path, key, value)
    elif kind == "text":
        del_key(path, key) if not value else set_key(path, key, value)
    elif kind == "file":
        if not value:
            del_key(path, key)
        else:
            full = str(paths.HOME) + value[1:] if value.startswith("~") else value
            if not os.path.isfile(full):
                raise Fail(t("File not found: %s", value))
            set_key(path, key, value)
    elif kind == "dir":
        deflabel = t("default (current wallpaper)")
        if (not value or value == deflabel or value == deflabel.split(" (", 1)[0] or value.lower() == "default"
                or value.startswith("по умолчанию")):
            del_key(path, key)
        else:
            full = str(paths.HOME) + value[1:] if value.startswith("~") else value
            if not os.path.isdir(full):
                raise Fail(t("Folder not found: %s", value))
            set_key(path, key, paths.tilde(full))
    else:
        raise Fail(t("This setting cannot be typed in — use h/l or ⏎"))


def _printf_g(v: float) -> str:
    """awk printf "%g": до 6 значащих цифр, без хвостовых нулей."""
    return "%g" % v


def run(args):
    """Команда tweak целиком (как ветка tweak) в диспетчере customizer.sh)."""
    key = args[1] if len(args) > 1 else ""
    code, err = 0, ""
    try:
        if len(args) > 2 and args[2] == "set":
            tweak_set(key, args[3] if len(args) > 3 else "")
        else:
            tweak(key, args[2] if len(args) > 2 else "+")
    except Fail as e:
        return 2, "", str(e) + "\n"
    except SystemExit as e:
        return int(e.code or 0), "", ""   # как exit в bash: хвост для окон не выполняется
    if key.startswith("window"):
        window_after()
    elif key.startswith("reading"):
        reading_after()
    return code, "", err
