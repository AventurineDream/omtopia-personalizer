#!/usr/bin/python3 -I
"""The UI states the values that are true: live Hyprland values, no placeholder defaults, raw sentinels gone.

  /usr/bin/python3 -I tests/test_displayed_values.py

All cases run in order in one sandbox HOME under $XDG_RUNTIME_DIR; each case leaves the state the next one
expects. hyprctl, omarchy, notify-send and omarchy-hyprland-toggle are stubs that only log their calls, and
the stub hyprctl answers `getoption` from JSON files the test writes (a missing file or a `hyprctl-fail` marker
makes it fail). Gaps follow the no-gaps flag as Hyprland does: with the flag file present the stub reports
gaps 0. The live desktop is never touched.
  1. Windows tab: an absent key shows Hyprland's live value (int, bool, float, str, CSS gap of equal sides).
  2. A CSS gap with different sides, or a failing hyprctl, falls back to the settings.json default.
  3. A key the file sets: the default is named "Hyprland config" and a change is marked against the live value.
  4. windowNoGaps reads the flag file; after «Reset window geometry» the no-gaps row and the gaps rows agree.
  5. Transparency: a fresh system has no preset in use; a saved name that no longer exists restores live.
  6. Theme Switcher: sentinel values print the default's words, in rows and in the slider readout.
  7. Dock: pinned ids print the desktop file's Name=, from XDG_DATA_HOME and XDG_DATA_DIRS.
"""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
OPACITY = os.path.join(PLUGIN, "scripts/opacity.sh")


def write(path, text, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, mode)


def sandbox():
    base = tempfile.mkdtemp(prefix="displayed-values.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs = os.path.join(base, "home"), os.path.join(base, "stubs")
    state = os.path.join(base, "state")
    flag = os.path.join(state, "omarchy/toggles/hypr/window-no-gaps.lua")
    log = os.path.join(base, "calls.log")
    os.makedirs(os.path.join(home, ".config"))
    write(os.path.join(stubs, "hyprctl"), f"""#!/bin/sh
printf '%s\\n' "hyprctl $*" >> "{log}"
[ -f "{base}/hyprctl-fail" ] && exit 1
if [ "$1" = "-j" ] && [ "$2" = "getoption" ]; then
  case "$3" in
  general:gaps_in|general:gaps_out)
    [ -f "{flag}" ] && {{ printf '%s' '{{"option": "'"$3"'", "css": "0 0 0 0", "set": true}}'; exit 0; }} ;;
  esac
  [ -f "{base}/opts/$3.json" ] && exec cat "{base}/opts/$3.json"
  exit 1
fi
exit 0
""", mode=0o755)
    write(os.path.join(stubs, "omarchy-hyprland-toggle"), f"""#!/bin/sh
printf '%s\\n' "toggle $*" >> "{log}"
case "$2" in on) mkdir -p "{os.path.dirname(flag)}"; : > "{flag}" ;; off) rm -f "{flag}" ;; esac
exit 0
""", mode=0o755)
    for name in ("omarchy", "notify-send"):
        write(os.path.join(stubs, name), f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\nexit 0\n', mode=0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"], OMARCHY_PATH="/usr/share/omarchy",
               XDG_RUNTIME_DIR=base, XDG_STATE_HOME=state, XDG_DATA_HOME=os.path.join(home, ".local/share"),
               XDG_DATA_DIRS=os.path.join(base, "xdg-share"))
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, state, env


def set_opt(base, option, obj):
    write(os.path.join(base, "opts", option + ".json"), json.dumps(obj))


def backend(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def rows(env, category):
    """List rows as TSV fields: [label, key, file, current, note, sub, kind, args, raw, name]."""
    _, out = backend(env, "list", category)
    return [line.split("\t") for line in out.splitlines() if line]


def row(env, category, key):
    for f in rows(env, category):
        if len(f) > 1 and f[1] == key:
            return f
    return None


LIVE = {
    "general:gaps_in": {"css": "5 5 5 5", "set": True},
    "general:gaps_out": {"css": "10 10 10 10", "set": True},
    "general:border_size": {"int": 2, "set": True},
    "decoration:rounding": {"int": 0, "set": True},
    "decoration:shadow:enabled": {"bool": False, "set": True},
    "decoration:shadow:range": {"int": 4, "set": False},
    "decoration:dim_inactive": {"bool": False, "set": False},
    "decoration:dim_strength": {"float": 0.5, "set": False},
    "general:layout": {"str": "master", "set": True},
}


def main():
    base, home, state, env = sandbox()
    flag = os.path.join(state, "omarchy/toggles/hypr/window-no-gaps.lua")
    win_json = os.path.join(home, ".config/omarchy/customizer/windows.json")
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    for option, obj in LIVE.items():
        set_opt(base, option, obj)

    # ── 1. Absent keys show Hyprland's live values ──
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("1 gaps in: CSS gap of equal sides → live 5, not settings' 2",
          gin is not None and gin[8] == "5" and gin[5] == "default: 5" and not gin[0].startswith("●"))
    check("1 gaps out: live 10", row(env, "windows", "tweak:windowGapsOut")[8] == "10")
    check("1 border: int option → live 2", row(env, "windows", "tweak:windowBorder")[8] == "2")
    check("1 rounding, shadow, dim strength: live values",
          row(env, "windows", "tweak:windowDecoRounding")[8] == "0"
          and row(env, "windows", "tweak:windowShadow")[8] == "false"
          and row(env, "windows", "tweak:windowDimStrength")[8] == "0.5")
    check("1 layout: string option → live master", row(env, "windows", "tweak:windowLayout")[8] == "master")
    check("1 no-gaps: no flag file → false", row(env, "windows", "tweak:windowNoGaps")[8] == "false")

    # A step from an absent key starts from the live value: 5 → 6, and the enum from master → dwindle.
    backend(env, "tweak", "windowGapsIn", "+")
    check("1 step from an absent key starts from the live value (5 → 6)",
          json.load(open(win_json)).get("windowGapsIn") == 6)
    backend(env, "tweak", "windowGapsIn", "reset")
    check("1 reset drops the key; the row shows the live value again",
          "windowGapsIn" not in json.load(open(win_json)) and row(env, "windows", "tweak:windowGapsIn")[8] == "5")
    backend(env, "tweak", "windowLayout", "+")
    check("1 enum step from an absent key starts from the live layout (master → dwindle)",
          json.load(open(win_json)).get("windowLayout") == "dwindle")
    os.unlink(win_json)

    # ── 2. Not one value → settings.json default; hyprctl failing → settings.json default ──
    set_opt(base, "general:gaps_in", {"css": "5 10 5 10", "set": True})
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("2 CSS gap with different sides → settings default 2, row still listed",
          gin is not None and gin[8] == "2" and gin[5] == "default: 2")
    check("2 the other rows still list after a multi-value gap",
          row(env, "windows", "tweak:windowBorder") is not None and len(rows(env, "windows")) > 10)
    set_opt(base, "general:gaps_in", LIVE["general:gaps_in"])
    write(os.path.join(base, "hyprctl-fail"), "")
    check("2 hyprctl failing → settings default 10 for rounding",
          row(env, "windows", "tweak:windowDecoRounding")[8] == "10")
    os.unlink(os.path.join(base, "hyprctl-fail"))

    # ── 3. A key the file sets: default named as the Hyprland config; change marked against live ──
    write(win_json, json.dumps({"windowGapsIn": 4}))
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set to 4 (live 5): default is the Hyprland config, and it is marked",
          gin[5] == "default: Hyprland config" and gin[0].startswith("●") and gin[8] == "4")
    write(win_json, json.dumps({"windowGapsIn": 5}))
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set equal to live 5: no change mark, label still names the config",
          gin[5] == "default: Hyprland config" and not gin[0].startswith("●"))
    write(os.path.join(base, "hyprctl-fail"), "")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set and live unknown: marked as changed (nothing to compare with)",
          gin[0].startswith("●") and gin[5] == "default: Hyprland config")
    os.unlink(os.path.join(base, "hyprctl-fail"))
    os.unlink(win_json)

    # ── 4. windowNoGaps reads the flag; after reset the no-gaps row and the gaps rows agree ──
    write(win_json, json.dumps({"windowNoGaps": True}))
    write(flag, "")
    ng = row(env, "windows", "tweak:windowNoGaps")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("4 flag file present, key set true: no-gaps row true, gaps row shows 0 (live)",
          ng[8] == "true" and gin[8] == "0")
    backend(env, "apply", "windows", "geometry-reset")
    ng = row(env, "windows", "tweak:windowNoGaps")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("4 after reset: flag file gone and no-gaps row false", not os.path.exists(flag) and ng[8] == "false")
    check("4 after reset: gaps row shows the live value 5 — agrees with no-gaps off",
          gin[8] == "5" and "windowNoGaps" not in json.load(open(win_json)))

    # ── 5. Transparency: fresh system has no preset in use; a stale saved name restores live ──
    def opacity(*args):
        r = subprocess.run(["bash", OPACITY, *args], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    check("5 fresh system: current is empty, not subtle", opacity("current") == (0, ""))
    check("5 fresh system: no list row is marked in use",
          all(f[3] == "0" for f in rows(env, "opacity")) and len(rows(env, "opacity")) == 6)
    opacity("next")
    check("5 next from a fresh system applies the anchor preset (subtle) and marks it",
          opacity("current") == (0, "subtle")
          and [f[1] for f in rows(env, "opacity") if f[3] == "1"] == ["subtle"])
    write(os.path.join(state, "hypr/opacity"), "frosty 0.5 0.5\n")
    calls_before = len(open(os.path.join(base, "calls.log")).read().splitlines())
    rc, _ = opacity("restore")
    check("5 stale saved name: restore exits 0 (keeps the live values)", rc == 0)
    check("5 stale saved name: restore applies no preset",
          not any("active_opacity = 1" in c for c in open(os.path.join(base, "calls.log")).read().splitlines()[calls_before:]))

    # ── 6. Theme Switcher: sentinel values print the default's words ──
    write(os.path.join(home, ".config/omarchy/image-picker.json"),
          json.dumps({"scrimAlpha": -1.0, "expandedWidth": 0.0, "animMs": 200}))
    scrim = row(env, "theme-switcher", "tweak:scrimAlpha")
    width = row(env, "theme-switcher", "tweak:expandedWidth")
    check("6 scrimAlpha -1.0 (sentinel) → «Background dim:  from the theme», not −1.00",
          scrim is not None and scrim[0] == "Background dim:  from the theme" and scrim[8] == "-1")
    check("6 sentinel is not marked as changed", not scrim[0].startswith("●"))
    check("6 expandedWidth 0.0 (sentinel) → «from the style»",
          width is not None and width[0] == "Selected width:  from the style" and not width[0].startswith("●"))
    anim = row(env, "theme-switcher", "tweak:animMs")
    check("6 a real value still prints as a number and is marked", anim[0] == "●  Scroll animation, ms:  200")

    # ── 7. Dock: pinned ids print the desktop file's Name= ──
    apps = os.path.join(home, ".local/share/applications")
    write(os.path.join(apps, "chrome-abc123-Default.desktop"), "[Desktop Entry]\nName=Google Drive\nExec=x\n")
    write(os.path.join(env["XDG_DATA_DIRS"], "applications/tool-x.desktop"), "[Desktop Entry]\nName=Tool X\n")
    write(os.path.join(home, ".config/omarchy/shell.json"),
          json.dumps({"dock": {"pinned": ["chrome-abc123-Default", "tool-x", "chrome-gone-Default"]}}))
    dock = {f[1]: f[0] for f in rows(env, "dock") if f[1].startswith("unpin:")}
    check("7 pinned PWA id → its Name= from ~/.local/share/applications",
          dock.get("unpin:chrome-abc123-Default") == "★ Google Drive")
    check("7 pinned id from an XDG data dir → its Name=", dock.get("unpin:tool-x") == "★ Tool X")
    check("7 pinned id without a desktop file → the id itself",
          dock.get("unpin:chrome-gone-Default") == "★ chrome-gone-Default")

    print(f"{'OK' if not fails else 'FAIL'}; sandbox: {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
