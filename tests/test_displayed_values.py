#!/usr/bin/python3 -I
"""The UI states the values that are true: placeholder defaults and raw sentinels are gone.

  /usr/bin/python3 -I tests/test_displayed_values.py

Four cases, each in a fresh sandbox HOME under $XDG_RUNTIME_DIR with stub commands (hyprctl,
omarchy, notify-send) that only log their calls; the live desktop is never touched:
  1. Windows tab: a key windows.json does not set shows the value Hyprland uses. A fake Omarchy
     default config + a user file (with a commented line that must not apply) form the chain;
     the geometry state of a preset and the missing-config fallback are checked too.
  2. Transparency: with no state file no preset is "in use" (scripts/opacity.sh current is empty,
     no list marker, status opacity empty); the first next/prev still applies the anchor preset.
  3. Theme Switcher: a value equal to its sentinel (0 / -1, stored as 0.0 / -1.0) prints the
     default's words and is not marked as changed; other values still print as numbers.
  4. Dock: a pinned id prints its .desktop Name= (XDG_DATA_HOME, XDG_DATA_DIRS); an id without a
     desktop file prints the id.
"""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
OPACITY = os.path.join(PLUGIN, "scripts/opacity.sh")

FAKE_OMARCHY_LOOKNFEEL = """\
hl.config({
  general = { gaps_in = 7, gaps_out = 13, border_size = 3, layout = "master" },
  decoration = { rounding = 9, shadow = { enabled = true, range = 6 }, dim_inactive = true, dim_strength = 0.3 },
})
"""
# Real Omarchy user files are mostly commented out: the commented gaps_in must not count.
FAKE_USER_LOOKNFEEL = """\
-- hl.config({ general = { gaps_in = 99 } })
hl.config({ general = { gaps_out = 11 } })
"""
FAKE_ENTRY = """\
package.path = os.getenv("HOME") .. "/.config/?.lua;" .. os.getenv("OMARCHY_PATH") .. "/?.lua;" .. package.path
require("default.hypr.looknfeel")
require("hypr.looknfeel")
"""


def sandbox():
    base = tempfile.mkdtemp(prefix="displayed-values.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs, omarchy = (os.path.join(base, n) for n in ("home", "stubs", "omarchy"))
    os.makedirs(stubs)
    os.makedirs(os.path.join(omarchy, "default/hypr"))
    os.makedirs(os.path.join(home, ".config/hypr"))
    write(os.path.join(omarchy, "default/hypr/looknfeel.lua"), FAKE_OMARCHY_LOOKNFEEL)
    write(os.path.join(home, ".config/hypr/looknfeel.lua"), FAKE_USER_LOOKNFEEL)
    write(os.path.join(home, ".config/hypr/hyprland.lua"), FAKE_ENTRY)
    log = os.path.join(base, "calls.log")
    for name in ("hyprctl", "omarchy", "notify-send"):
        write(os.path.join(stubs, name), f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\nexit 0\n', mode=0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"], OMARCHY_PATH=omarchy,
               XDG_RUNTIME_DIR=base, XDG_STATE_HOME=os.path.join(base, "state"),
               XDG_DATA_HOME=os.path.join(home, ".local/share"), XDG_DATA_DIRS=os.path.join(base, "xdg-share"))
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, env


def write(path, text, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, mode)


def backend(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def rows(env, category):
    """List rows as TSV fields: [label, value, file, current, note, sub, kind, args, raw, name]."""
    _, out = backend(env, "list", category)
    return [line.split("\t") for line in out.splitlines() if line]


def row(env, category, value):
    for f in rows(env, category):
        if len(f) > 1 and f[1] == value:
            return f
    return None


def main():
    base, home, env = sandbox()
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    win_json = os.path.join(home, ".config/omarchy/customizer/windows.json")
    geometry = os.path.join(env["XDG_STATE_HOME"], "hypr/geometry")

    # ── 1. Windows: the default is what Hyprland applies without the key ──
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("1 gaps in: no key → raw is Omarchy's looknfeel value (7), not settings' 2",
          gin is not None and gin[8] == "7" and gin[5] == "default: 7")
    check("1 gaps out: user file overrides the default config (11), commented line ignored",
          row(env, "windows", "tweak:windowGapsOut")[8] == "11")
    check("1 rounding / shadow / dim / layout come from the chain",
          row(env, "windows", "tweak:windowDecoRounding")[8] == "9"
          and row(env, "windows", "tweak:windowShadow")[8] == "true"
          and row(env, "windows", "tweak:windowShadowRange")[8] == "6"
          and row(env, "windows", "tweak:windowDimStrength")[8] == "0.3"
          and row(env, "windows", "tweak:windowLayout")[8] == "master")
    check("1 no key is not marked as changed", not gin[0].startswith("●"))

    write(win_json, json.dumps({"windowGapsIn": 3}))
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("1 an explicit key wins and is marked", gin[8] == "3" and gin[0].startswith("●"))

    # The step starts from what is shown: 7 → 8 (not 2 → 3 as before).
    os.unlink(win_json)
    backend(env, "tweak", "windowGapsIn", "+")
    check("1 step from an absent key starts from the Hyprland value", json.load(open(win_json)).get("windowGapsIn") == 8)
    # The chain sets layout = "master": the first step from it goes to the next value (dwindle), not master.
    os.unlink(win_json)
    backend(env, "tweak", "windowLayout", "+")
    check("1 enum step from an absent key starts from the Hyprland layout (master → dwindle)",
          json.load(open(win_json)).get("windowLayout") == "dwindle")
    backend(env, "tweak", "windowGapsIn", "reset")
    check("1 reset drops the key; the row falls back to the Hyprland value",
          "windowGapsIn" not in json.load(open(win_json)) and row(env, "windows", "tweak:windowGapsIn")[8] == "7")

    # Preset geometry state is applied by restore() before windows.json: it is the value without the key.
    write(geometry, "preset 4 8 1 12 1\n")
    check("1 geometry state supplies gaps when the key is absent",
          row(env, "windows", "tweak:windowGapsIn")[8] == "4"
          and row(env, "windows", "tweak:windowDecoRounding")[8] == "12"
          and row(env, "windows", "tweak:windowShadow")[8] == "true")
    check("1 geometry state does not touch keys it does not carry",
          row(env, "windows", "tweak:windowDim")[8] == "true")
    os.unlink(geometry)

    # Without a readable config the settings.json default is the honest fallback.
    os.unlink(os.path.join(home, ".config/hypr/hyprland.lua"))
    check("1 unreadable chain → settings.json default",
          row(env, "windows", "tweak:windowGapsIn")[8] == "2" and row(env, "windows", "tweak:windowDecoRounding")[8] == "10")
    write(os.path.join(home, ".config/hypr/hyprland.lua"), 'error("broken config")\n')
    check("1 a config that fails to load → settings.json default",
          row(env, "windows", "tweak:windowGapsIn")[8] == "2")

    # ── 2. Transparency: no state file → no preset in use ──
    def opacity(*args):
        return subprocess.run(["bash", OPACITY, *args], env=env, capture_output=True, text=True).stdout.strip()

    check("2 fresh system: current is empty, not subtle", opacity("current") == "")
    check("2 fresh system: no list row is marked in use",
          all(f[3] == "0" for f in rows(env, "opacity")) and len(rows(env, "opacity")) == 6)
    status = backend(env, "status")[1].splitlines()
    check("2 status reports no opacity in use", "opacity\t" in status)
    opacity("next")
    check("2 next from a fresh system applies the anchor preset (subtle) and marks it",
          opacity("current") == "subtle" and [f[1] for f in rows(env, "opacity") if f[3] == "1"] == ["subtle"])

    # ── 3. Theme Switcher: sentinel values print the default's words ──
    write(os.path.join(home, ".config/omarchy/image-picker.json"),
          json.dumps({"scrimAlpha": -1.0, "expandedWidth": 0.0, "animMs": 200}))
    scrim = row(env, "theme-switcher", "tweak:scrimAlpha")
    width = row(env, "theme-switcher", "tweak:expandedWidth")
    check("3 scrimAlpha -1.0 (sentinel) → «Background dim:  from the theme», not −1.00",
          scrim is not None and scrim[0] == "Background dim:  from the theme" and scrim[8] == "-1")
    check("3 sentinel is not marked as changed", not scrim[0].startswith("●"))
    check("3 expandedWidth 0.0 (sentinel) → «from the style»",
          width is not None and width[0] == "Selected width:  from the style" and not width[0].startswith("●"))
    anim = row(env, "theme-switcher", "tweak:animMs")
    check("3 a real value still prints as a number and is marked", anim[0] == "●  Scroll animation, ms:  200")

    # ── 4. Dock: pinned ids print the desktop file's Name= ──
    apps = os.path.join(home, ".local/share/applications")
    write(os.path.join(apps, "chrome-abc123-Default.desktop"), "[Desktop Entry]\nName=Google Drive\nExec=x\n")
    write(os.path.join(env["XDG_DATA_DIRS"], "applications/tool-x.desktop"), "[Desktop Entry]\nName=Tool X\n")
    write(os.path.join(home, ".config/omarchy/shell.json"),
          json.dumps({"dock": {"pinned": ["chrome-abc123-Default", "tool-x", "chrome-gone-Default"]}}))
    dock = {f[1]: f[0] for f in rows(env, "dock") if f[1].startswith("unpin:")}
    check("4 pinned PWA id → its Name= from ~/.local/share/applications",
          dock.get("unpin:chrome-abc123-Default") == "★ Google Drive")
    check("4 pinned id from an XDG data dir → its Name=", dock.get("unpin:tool-x") == "★ Tool X")
    check("4 pinned id without a desktop file → the id itself",
          dock.get("unpin:chrome-gone-Default") == "★ chrome-gone-Default")

    print(f"{'OK' if not fails else 'FAIL'}; sandbox: {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
