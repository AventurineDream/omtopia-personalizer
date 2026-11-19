"""Windows-tab defaults: the value Hyprland uses now for a key that windows.json does not set.

customizer.lua applies only the keys windows.json has (preview_ops.window_overrides_lua), so for an absent
key the compositor runs whatever the Hyprland config and the restored geometry state set. `hyprctl -j
getoption <option>` reports exactly that value. A reading that is not one value (no hyprctl, a failed call,
CSS sides that differ) gives None, and callers keep the settings.json default.
"""
import json
import subprocess

from . import paths

# The no-gaps row is a toggle file, not a Hyprland option: the file's presence is the state.
NO_GAPS_FLAG = paths.STATE.parent / "omarchy/toggles/hypr/window-no-gaps.lua"

# windows.json key -> Hyprland option it overrides (preview_ops.window_overrides_lua).
OPTIONS = {
    "windowGapsIn": "general:gaps_in",
    "windowGapsOut": "general:gaps_out",
    "windowBorder": "general:border_size",
    "windowDecoRounding": "decoration:rounding",
    "windowShadow": "decoration:shadow:enabled",
    "windowShadowRange": "decoration:shadow:range",
    "windowDim": "decoration:dim_inactive",
    "windowDimStrength": "decoration:dim_strength",
    "windowLayout": "general:layout",
    "windowNoGaps": None,
}


def is_window_key(key: str) -> bool:
    """True for the keys of the Windows tab that this module reads."""
    return key in OPTIONS


# One hyprctl call waits at most TIMEOUT_S. A list asks once per row, so without a shared budget a hung
# compositor would stall the list for rows × TIMEOUT_S; after one timeout the list stops asking (begin_read).
TIMEOUT_S = 1
_unresponsive = False


def begin_read() -> None:
    """Start a new list or tweak: forget an earlier timeout, so each read gets its own budget."""
    global _unresponsive
    _unresponsive = False


def _getoption(option: str):
    """Parsed `hyprctl -j getoption <option>`; None when hyprctl is missing, fails, times out or prints no object.

    After a timeout, calls return None at once until begin_read(): the compositor is not answering, and each
    further call would wait TIMEOUT_S again. Not cached: the value changes whenever the config is reloaded.
    """
    global _unresponsive
    if _unresponsive:
        return None
    try:
        p = subprocess.run(["hyprctl", "-j", "getoption", option], capture_output=True, text=True,
                           timeout=TIMEOUT_S, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        _unresponsive = True
        return None
    except OSError:
        return None
    if p.returncode != 0:
        return None
    try:
        obj = json.loads(p.stdout)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def _value(obj: dict):
    """The option's single value as windows.json text, or None when it has none.

    A CSS gap prints one value only when all four sides are equal ("5 5 5 5" → "5"); "5 10" is two
    values and is not guessed at, so the caller falls back to settings.json.
    """
    if isinstance(obj.get("bool"), bool):
        return "true" if obj["bool"] else "false"
    if isinstance(obj.get("int"), int) and not isinstance(obj["int"], bool):
        return str(obj["int"])
    if isinstance(obj.get("float"), (int, float)) and not isinstance(obj["float"], bool):
        return repr(float(obj["float"]))
    if isinstance(obj.get("str"), str) and obj["str"]:
        return obj["str"]
    css = obj.get("css")
    if isinstance(css, str):
        sides = css.split()
        if sides and all(s == sides[0] for s in sides):
            return sides[0]
    return None


def live(key: str):
    """Hyprland's current value of a Windows-tab key as windows.json text ("5", "0.5", "true", "dwindle").

    windowNoGaps reads the toggle file. Returns None for keys outside the tab and when the value is not
    one value, so the caller shows the settings.json default instead.
    """
    if key not in OPTIONS:
        return None
    if key == "windowNoGaps":
        return "true" if NO_GAPS_FLAG.is_file() else "false"
    obj = _getoption(OPTIONS[key])
    return None if obj is None else _value(obj)
