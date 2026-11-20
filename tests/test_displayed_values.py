#!/usr/bin/python3 -I
"""The UI states the values that are true: live Hyprland values, no placeholder defaults, raw sentinels gone.

  /usr/bin/python3 -I tests/test_displayed_values.py

All cases run in order in one sandbox HOME under $XDG_RUNTIME_DIR; each case leaves the state the next one
expects. hyprctl, omarchy, notify-send and omarchy-hyprland-toggle are stubs that only log their calls. The stub
hyprctl answers `getoption` from JSON files the test writes; marker files switch it to failing (exit 1), printing
non-JSON with exit 0, or hanging. With the no-gaps flag file present the stub reports gaps 0, as Hyprland does.
The live desktop is never touched.
  1. Windows tab: an absent key shows Hyprland's live value (int, bool, float, str, CSS gap of equal sides).
  2. A CSS gap with different sides, a failing hyprctl, or non-JSON output falls back to the settings.json default.
  3. A key windows.json sets is always marked; its default is named "Hyprland config".
  4. windowNoGaps reads the flag file; «Reset window geometry» keeps the toggle, and the rows agree.
  5. Transparency and Blur: a fresh system has no preset in use (the first next applies the default); a saved name
     that no longer exists restores live; a preset saved on a fresh system stores neither opacity nor blur.
  6. Theme Switcher: sentinel values print the default's words, in rows and in the slider readout.
  7. Dock: pinned ids print the desktop file's Name=, from XDG_DATA_HOME and XDG_DATA_DIRS.
  8. Bash mirror (tests/legacy/customizer.sh): the same rows as the backend; enum step from the live layout;
     one hyprctl timeout per list.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
LEGACY = os.path.join(PLUGIN, "tests/legacy/customizer.sh")
OPACITY = os.path.join(PLUGIN, "scripts/opacity.sh")
BLUR = os.path.join(PLUGIN, "scripts/blur.sh")


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
[ -f "{base}/hyprctl-garbage" ] && {{ echo "not json"; exit 0; }}
[ -f "{base}/hyprctl-hang" ] && exec sleep 30
case "$1" in
  getoption) opt="$2" ;;
  -j) [ "$2" = getoption ] || exit 0; opt="$3" ;;
  *) exit 0 ;;
esac
# blur.sh reads `getoption OPT -j`; the Windows tab reads `-j getoption OPT`. Both answer from opts/.
case "$opt" in
  general:gaps_in|general:gaps_out)
    [ -f "{flag}" ] && {{ printf '%s' '{{"option": "'"$opt"'", "css": "0 0 0 0", "set": true}}'; exit 0; }} ;;
esac
[ -f "{base}/opts/$opt.json" ] && exec cat "{base}/opts/$opt.json"
exit 1
exit 0
""", mode=0o755)
    write(os.path.join(stubs, "omarchy-hyprland-toggle"), f"""#!/bin/sh
printf '%s\\n' "toggle $*" >> "{log}"
case "$2" in on) mkdir -p "{os.path.dirname(flag)}"; : > "{flag}" ;; off) rm -f "{flag}" ;; esac
exit 0
""", mode=0o755)
    write(os.path.join(stubs, "zenity"), f"""#!/bin/sh
printf '%s\\n' "zenity $*" >> "{log}"
case "$*" in *--question*) exit 1 ;; *Description*) echo ;; *--entry*) echo freshblur ;; esac
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


def set_marker(base, name, on):
    path = os.path.join(base, name)
    if on:
        write(path, "")
    elif os.path.exists(path):
        os.unlink(path)


def backend(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def legacy(env, *args):
    r = subprocess.run(["bash", LEGACY, *args], env=env, capture_output=True, text=True)
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


def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else {}


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
    "decoration:rounding_power": {"float": 2.0, "set": False},
}


def main():
    base, home, state, env = sandbox()
    flag = os.path.join(state, "omarchy/toggles/hypr/window-no-gaps.lua")
    win_json = os.path.join(home, ".config/omarchy/customizer/windows.json")
    calls = os.path.join(base, "calls.log")
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    def call_count():
        return len(open(calls).read().splitlines()) if os.path.exists(calls) else 0

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
    rp = row(env, "windows", "tweak:windowRoundingPower")
    check("1 corner power: absent key shows the live rounding_power 2, not settings' 2.5",
          rp is not None and rp[8] == "2" and rp[5] == "default: 2")
    rad = row(env, "windows", "tweak:windowRadius")
    check("1 corner radius: absent key shows the global rounding it falls back to (live 0), not settings' 16",
          rad is not None and rad[8] == "0" and rad[5] == "default: 0")

    # A step from an absent key starts from the live value: 5 → 6, and the enum from master → dwindle.
    backend(env, "tweak", "windowGapsIn", "+")
    check("1 step from an absent key starts from the live value (5 → 6)",
          load_json(win_json).get("windowGapsIn") == 6)
    backend(env, "tweak", "windowGapsIn", "reset")
    check("1 reset drops the key; the row shows the live value again",
          "windowGapsIn" not in load_json(win_json) and row(env, "windows", "tweak:windowGapsIn")[8] == "5")
    backend(env, "tweak", "windowLayout", "+")
    check("1 enum step from an absent key starts from the live layout (master → dwindle)",
          load_json(win_json).get("windowLayout") == "dwindle")
    os.unlink(win_json)

    # ── 2. Not one value, a failing hyprctl, or non-JSON output → settings.json default ──
    set_opt(base, "general:gaps_in", {"css": "5 10 5 10", "set": True})
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("2 CSS gap with different sides → settings default 2, row still listed",
          gin is not None and gin[8] == "2" and gin[5] == "default: 2")
    check("2 the other rows still list after a multi-value gap",
          row(env, "windows", "tweak:windowBorder") is not None and len(rows(env, "windows")) > 10)
    set_opt(base, "general:gaps_in", LIVE["general:gaps_in"])
    set_marker(base, "hyprctl-fail", True)
    check("2 hyprctl failing → settings default 10 for rounding",
          row(env, "windows", "tweak:windowDecoRounding")[8] == "10")
    set_marker(base, "hyprctl-fail", False)
    set_marker(base, "hyprctl-garbage", True)
    check("2 hyprctl exit 0 with non-JSON stdout → settings defaults (rounding 10, gaps 2)",
          row(env, "windows", "tweak:windowDecoRounding")[8] == "10"
          and row(env, "windows", "tweak:windowGapsIn")[8] == "2")
    set_marker(base, "hyprctl-garbage", False)

    # ── 3. A key windows.json sets is always marked; its default is named as the Hyprland config ──
    write(win_json, json.dumps({"windowGapsIn": 4}))
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set to 4 (live 5): marked, default named as the Hyprland config",
          gin[0].startswith("●  ") and gin[5] == "default: Hyprland config" and gin[8] == "4")
    write(win_json, json.dumps({"windowGapsIn": 5}))
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set equal to live 5: still marked (the user chose it)",
          gin[0].startswith("●  ") and gin[5] == "default: Hyprland config" and gin[8] == "5")
    set_marker(base, "hyprctl-fail", True)
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key set and live unknown: marked", gin[0].startswith("●  ") and gin[5] == "default: Hyprland config")
    set_marker(base, "hyprctl-fail", False)
    os.unlink(win_json)
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("3 key absent: not marked, default is the live value", not gin[0].startswith("●") and gin[5] == "default: 5")
    write(win_json, json.dumps({"windowRoundingPower": 3}))
    rp = row(env, "windows", "tweak:windowRoundingPower")
    check("3 corner power set to 3 (live 2): marked, default named as the Hyprland config, shows 3",
          rp[0].startswith("●  ") and rp[5] == "default: Hyprland config" and rp[8] == "3")
    os.unlink(win_json)
    # An explicit float mode with no radius gives the rule its settings default 16 (not the global rounding), so the row shows it.
    write(win_json, json.dumps({"windowRounding": "float"}))
    rad = row(env, "windows", "tweak:windowRadius")
    check("3 float mode, radius absent: not marked, default 16 (the rule's radius), not live rounding",
          not rad[0].startswith("●") and rad[8] == "16" and rad[5] == "default: 16")
    os.unlink(win_json)

    # ── 4. windowNoGaps reads the flag; «Reset window geometry» keeps the toggle and the rows agree ──
    write(win_json, json.dumps({"windowNoGaps": True, "windowGapsOut": 12}))
    write(flag, "")  # the toggle is on
    ng = row(env, "windows", "tweak:windowNoGaps")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("4 no-gaps on, key set true: no-gaps row true, gaps row 0 (live)",
          ng[8] == "true" and gin[8] == "0" and ng[0].startswith("●  "))
    before = call_count()
    backend(env, "apply", "windows", "geometry-reset")
    ng = row(env, "windows", "tweak:windowNoGaps")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("4 reset keeps the toggle: flag file still there", os.path.exists(flag))
    check("4 reset drops the geometry keys from windows.json (windowNoGaps and windowGapsOut)",
          "windowNoGaps" not in load_json(win_json) and "windowGapsOut" not in load_json(win_json))
    check("4 reset does not turn the toggle off (no toggle call after reset)",
          not any("window-no-gaps off" in c for c in open(calls).read().splitlines()[before:]))
    check("4 after reset the rows agree: no-gaps row true and gaps row 0",
          ng[8] == "true" and gin[8] == "0")
    os.unlink(flag)
    backend(env, "apply", "windows", "geometry-reset")
    ng = row(env, "windows", "tweak:windowNoGaps")
    gin = row(env, "windows", "tweak:windowGapsIn")
    check("4 toggle off, reset: no-gaps row false and gaps row shows the live 5",
          ng[8] == "false" and gin[8] == "5")

    # ── 5. Transparency and Blur: fresh system has no preset in use; a stale saved name restores live ──
    def opacity(*args):
        r = subprocess.run(["bash", OPACITY, *args], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    check("5 fresh system: current is empty, not subtle", opacity("current") == (0, ""))
    check("5 fresh system: no list row is marked in use",
          all(f[3] == "0" for f in rows(env, "opacity")) and len(rows(env, "opacity")) == 6)

    # Blur follows the same rules as Transparency. Status (the Home card) and both bash and Python snapshots must agree.
    def blur(*args):
        r = subprocess.run(["bash", BLUR, *args], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    def status_fields(text):
        return {k: v for k, _, v in (ln.partition("\t") for ln in text.splitlines())}

    check("5 fresh system: blur current is empty, not medium", blur("current") == (0, ""))
    check("5 fresh system: no blur row is marked in use",
          all(f[3] == "0" for f in rows(env, "blur")) and len(rows(env, "blur")) == 7)
    fresh = status_fields(backend(env, "status")[1])
    check("5 fresh system: status names no transparency or blur preset",
          fresh.get("opacity") == "" and fresh.get("blur") == "")
    fresh_sh = status_fields(legacy(env, "status")[1])
    check("5 fresh system: bash status names no transparency or blur preset",
          fresh_sh.get("opacity") == "" and fresh_sh.get("blur") == "")
    # The Transparency preview stage draws status blur-values; with no preset in use it must be
    # the blur Hyprland runs, not empty (which drew no blur at all). Hyprland's stock 4 × 2 here, then off.
    for opt, obj in (("decoration:blur:enabled", {"bool": True, "set": True}),
                     ("decoration:blur:size", {"int": 4, "set": True}),
                     ("decoration:blur:passes", {"int": 2, "set": True}),
                     ("decoration:blur:vibrancy", {"float": 0.1696, "set": True}),
                     ("decoration:blur:noise", {"float": 0.0117, "set": True})):
        set_opt(base, opt, obj)
    for engine, run in (("Python", backend), ("bash", legacy)):
        check(f"5 fresh system ({engine}): status blur-values are the live blur",
              status_fields(run(env, "status")[1]).get("blur-values") == "4 2 0.1696 0.0117")
    set_opt(base, "decoration:blur:enabled", {"bool": False, "set": True})
    for engine, run in (("Python", backend), ("bash", legacy)):
        check(f"5 fresh system ({engine}): live blur off gives size 0, so the stage draws none",
              status_fields(run(env, "status")[1]).get("blur-values") == "0 0 0 0")
    set_opt(base, "decoration:blur:enabled", {"bool": True, "set": True})
    saved_path = os.path.join(home, ".config/omarchy/customizer/presets/freshblur.json")
    backend(env, "apply", "presets", "save", "--name", "freshblur")
    saved = load_json(saved_path)
    check("5 fresh snapshot (Python): stores neither opacity nor blur",
          bool(saved) and "opacity" not in saved and "blur" not in saved)
    os.unlink(saved_path)  # a taken name stops the save (EXISTS / zenity question), so the file is removed first
    legacy(env, "apply", "presets", "save")  # the bash mirror still asks zenity for the name (the stub answers freshblur)
    saved_sh = load_json(saved_path)
    check("5 fresh snapshot (bash): stores neither opacity nor blur",
          bool(saved_sh) and "opacity" not in saved_sh and "blur" not in saved_sh)
    os.unlink(saved_path)
    opacity("next")
    check("5 next from a fresh system applies the anchor preset (subtle) and marks it",
          opacity("current") == (0, "subtle")
          and [f[1] for f in rows(env, "opacity") if f[3] == "1"] == ["subtle"])
    write(os.path.join(state, "hypr/opacity"), "frosty 0.5 0.5\n")
    before = call_count()
    rc, _ = opacity("restore")
    check("5 stale saved name: restore exits 0 (keeps the live values)", rc == 0)
    check("5 stale saved name: restore applies no preset",
          not any("active_opacity = 1" in c for c in open(calls).read().splitlines()[before:]))
    blur("next")
    check("5 blur next from a fresh system applies the default (medium) and marks it",
          blur("current") == (0, "medium") and [f[1] for f in rows(env, "blur") if f[3] == "1"] == ["medium"])
    for opt, obj in (("decoration:blur:enabled", {"bool": True, "set": True}),
                     ("decoration:blur:size", {"int": 5, "set": True}),
                     ("decoration:blur:passes", {"int": 2, "set": True}),
                     ("decoration:blur:vibrancy", {"float": 0.13, "set": True}),
                     ("decoration:blur:noise", {"float": 0.007, "set": True})):
        set_opt(base, opt, obj)
    write(os.path.join(state, "hypr/blur"), "frosty 1 1 0.00 0.000\n")
    before = call_count()
    rc, _ = blur("restore")
    check("5 stale saved blur name: restore exits 0", rc == 0)
    # Restore keeps the live values verbatim: any blur eval it sends carries them, never a preset's.
    blur_evals = [c for c in open(calls).read().splitlines()[before:] if "blur = {" in c]
    check("5 stale saved blur name: any blur eval re-sends the live values, no preset",
          all("size = 5, passes = 2, vibrancy = 0.13, noise = 0.007" in c for c in blur_evals))
    check("5 stale saved blur name: live blur values unchanged", blur("live") == (0, "true 5 2 0.13 0.007"))

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

    # ── 8. Bash mirror: same rows as the backend, enum from the live layout, one timeout per list ──
    def same_rows(category):
        py = backend(env, "list", category)[1].splitlines()
        rc, sh = legacy(env, "list", category)
        return rc == 0 and py == sh.splitlines()

    write(win_json, json.dumps({"windowGapsIn": 4}))
    check("8 bash list windows = backend list windows (a present key, live values)", same_rows("windows"))
    os.unlink(win_json)
    check("8 bash list windows = backend list windows (all keys absent)", same_rows("windows"))
    set_opt(base, "general:gaps_in", {"css": "5 10 5 10", "set": True})
    check("8 bash list windows = backend list windows (multi-value gap → settings default)", same_rows("windows"))
    set_opt(base, "general:gaps_in", LIVE["general:gaps_in"])
    rc, _ = legacy(env, "tweak", "windowLayout", "+")
    check("8 bash enum step starts from the live layout (master → dwindle)",
          rc == 0 and load_json(win_json).get("windowLayout") == "dwindle")
    os.unlink(win_json)
    set_marker(base, "hyprctl-hang", True)
    t0 = time.monotonic()
    backend(env, "list", "windows")
    py_s = time.monotonic() - t0
    t0 = time.monotonic()
    legacy(env, "list", "windows")
    sh_s = time.monotonic() - t0
    check(f"8 hung hyprctl: one 1 s budget per list, not one per row (backend {py_s:.1f} s, bash {sh_s:.1f} s)",
          py_s < 4 and sh_s < 4)
    set_marker(base, "hyprctl-hang", False)

    print(f"{'OK' if not fails else 'FAIL'}; sandbox: {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
