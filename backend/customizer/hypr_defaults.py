"""Windows-tab defaults as Hyprland actually applies them when windows.json has no key.

After «x» or «↺ Reset window geometry» the key is gone and Hyprland uses its own config, not
settings.json: Omarchy sets gaps_in 5, gaps_out 10, rounding 0, and so on. Layers, in the order
restore() (preview_ops) applies them: the geometry state of a preset/style (~/.local/state/hypr/
geometry), then the Hyprland Lua chain (hypr_chain.lua loads hyprland.lua and its requires the way
Hyprland does), then Hyprland's built-in value for options no file in the chain sets. When the
chain cannot be read, effective() returns None and callers keep the settings.json default.
"""
import functools
import os
import shutil
import subprocess
from pathlib import Path

from . import fsutil, paths

HYPR_STATE = paths.STATE.parent / "hypr"
NO_GAPS_FLAG = paths.STATE.parent / "omarchy/toggles/hypr/window-no-gaps.lua"
ENTRY = paths.HOME / ".config/hypr/hyprland.lua"
DRIVER = Path(__file__).with_name("hypr_chain.lua")
OMARCHY_PATH_DEFAULT = "/usr/share/omarchy"

# windows.json key -> Hyprland option that the tab overrides (preview_ops.window_overrides_lua).
OPTIONS = {
    "windowGapsIn": "general.gaps_in",
    "windowGapsOut": "general.gaps_out",
    "windowBorder": "general.border_size",
    "windowDecoRounding": "decoration.rounding",
    "windowShadow": "decoration.shadow.enabled",
    "windowShadowRange": "decoration.shadow.range",
    "windowDim": "decoration.dim_inactive",
    "windowDimStrength": "decoration.dim_strength",
    "windowLayout": "general.layout",
}

# Hyprland's built-in values, used only for options no file in the chain sets. Checked on Hyprland 0.56
# in an omabox box: decoration.shadow.range 4, dim_inactive false and dim_strength 0.5 are reported as
# "set: false" (stock). The rest are set by Omarchy's looknfeel in every real install (gaps_in 5,
# gaps_out 10, border 2, rounding 0, layout dwindle, shadow off), so their stock values are unverified.
# TODO(malachite): confirm stock gaps_in 5, gaps_out 20, border 2, rounding 0, layout dwindle and
# shadow.enabled true on a Hyprland with no looknfeel overrides — reason: these are not confirmed live.
BUILTIN = {
    "general.gaps_in": "5",
    "general.gaps_out": "20",
    "general.border_size": "2",
    "general.layout": "dwindle",
    "decoration.rounding": "0",
    "decoration.shadow.enabled": "true",
    "decoration.shadow.range": "4",
    "decoration.dim_inactive": "false",
    "decoration.dim_strength": "0.5",
}


def _geometry_layer() -> dict:
    """Keys the geometry state supplies, as restore() applies them; empty when restore() applies none."""
    if NO_GAPS_FLAG.is_file():
        return {}
    line = (fsutil.read_text(HYPR_STATE / "geometry") or "").split("\n", 1)[0]
    _gn, gi, go, bs, r, shd = fsutil.read_ws(line, 6)
    if not shd:
        return {}
    out = {"windowGapsIn": gi, "windowGapsOut": go, "windowBorder": bs, "windowDecoRounding": r}
    try:
        out["windowShadow"] = "true" if int(shd) > 0 else "false"
    except ValueError:
        pass
    return {k: v for k, v in out.items() if v}


@functools.cache
def _chain():
    """Option path -> value string set by the Hyprland config chain; None when the config cannot be read.

    Runs the Lua driver once per process. The driver is read-only (see hypr_chain.lua); a
    timeout or a missing Lua interpreter counts as unreadable."""
    lua = shutil.which("lua5.4") or shutil.which("lua")
    if lua is None or not ENTRY.is_file():
        return None
    env = dict(os.environ, OMARCHY_PATH=os.environ.get("OMARCHY_PATH") or OMARCHY_PATH_DEFAULT)
    try:
        p = subprocess.run([lua, str(DRIVER), str(ENTRY), *OPTIONS.values()], env=env, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    out = {}
    for line in p.stdout.splitlines():
        opt, _, value = line.partition("\t")
        out[opt] = value
    return out


def effective(key):
    """Hyprland's value for a Windows-tab key while windows.json does not set it, as a string.

    Returns None for keys outside the tab and when neither the geometry state nor the config
    chain can be read; the caller then uses the settings.json default. Strings look like
    "5", "0.1", "true" or "dwindle", matching the values the tab writes."""
    opt = OPTIONS.get(key)
    if opt is None:
        return None
    layer = _geometry_layer().get(key)
    if layer is not None:
        return layer
    chain = _chain()
    if chain is None:
        return None
    return chain.get(opt, BUILTIN[opt])
