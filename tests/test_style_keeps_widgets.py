#!/usr/bin/python3 -I
"""A style keeps the user's bar widgets (README: a style "changes how things look, not which widgets are shown").

  /usr/bin/python3 -I tests/test_style_keeps_widgets.py

Before the fix, a style with an inline barLayoutData replaced the whole bar, including the
widget set and the tray drawer, with the style's own. Now a style apply (mode merge) carries
the user's widgets over (see merge_bar_layout): position and sections come from the style,
the widget set, their settings and the tray come from the user.

Every case runs through the Python backend and the legacy bash reference on a fresh sandbox
HOME; shell.json must be byte-identical after each step (parity, no allowlist):
  - style: a style with barLayoutData keeps the user's ids (tray included) and takes the
    style's arrangement and position;
  - preset-style: a preset with "style": id gets the same carry-over;
  - preset-own-layout: a preset's own barLayoutData (a snapshot) applies verbatim; when the
    preset also names a style, the style is applied first and the preset's layout on top;
  - restore: the rollback ("Restore previous setup", last-preset.json) after a style apply
    brings back the exact pre-style layout;
  - restore-stock-name: a rollback to a snapshot that named a stock layout applies that layout
    verbatim (no carry-over), so it returns exactly the saved widgets.

Only a sandbox (fresh HOME under $XDG_RUNTIME_DIR); the live shell.json is never touched and
the shell is never restarted. Sandbox, CUSTOM_SHELL and the invariant checks come from
test_layout_carryover.py.
"""
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_layout_carryover as tlc  # noqa: E402

STATE_DIR = ".local/state/omarchy-customizer"
STYLE_ID = "keeps-test"
USER_CUSTOM = tlc.CUSTOM_SHELL["bar"]["layout"]

# The style's own arrangement, position and anchor. It names widgets the user has (audio
# moves from right to left, network joins right, calendar and indicators go to center), one
# the user does not have (not.on.bar: must not be added) and a tray list of its own (must not
# replace the user's tray).
STYLE_LAYOUT = {
    "position": "bottom",
    "centerAnchor": "omarchy.indicators",
    "layout": {
        "left": [{"id": "omarchy.workspaces"}, {"id": "omarchy.audio"}],
        "center": [{"id": "tmn73.calendar"}, {"id": "omarchy.indicators"}],
        "right": [{"id": "omarchy.network"}, {"id": "not.on.bar"}, {"id": "omarchy.tray", "hidden": [], "pinned": []}],
        "tray": [{"id": "style.tray.only"}],
    },
}
# Hand-computed result of merging STYLE_LAYOUT into the user's bar. Widgets the style does not
# name stay in their section, after the ones it places.
EXPECTED_STYLE_SECTIONS = {
    "left": ["omarchy.workspaces", "omarchy.audio", "makehasteslowly.heliolune"],
    "center": ["tmn73.calendar", "omarchy.indicators", "bibek.focusd", "luotao.zen", "omarchy.system-update"],
    "right": ["omarchy.network", "omarchy.tray", "tristonarmstrong.dictionary", "tmn73.obsidian",
              "aven.omp-usage", "kamradsmeshnyavy.customizer", "aven.agentic-av", "omarchy.monitor",
              "omarchy.power"],
}


def own_layout():
    """A preset's own layout: the user's bar plus a widget that is only in the tray today."""
    layout = copy.deepcopy(USER_CUSTOM)
    layout["left"].append({"id": "omarchy.bluetooth"})
    return {"position": "bottom", "centerAnchor": "omarchy.workspaces", "layout": layout}


def write_user_files(home):
    """Style and presets under the sandbox's ~/.config/omarchy/customizer; the user's bar is CUSTOM_SHELL."""
    customizer = os.path.join(home, ".config/omarchy/customizer")
    styles = os.path.join(customizer, "styles")
    presets = os.path.join(customizer, "presets")
    os.makedirs(styles, exist_ok=True)
    os.makedirs(presets, exist_ok=True)
    tlc.write_json(os.path.join(styles, STYLE_ID + ".json"), {"name": "Keeps test", "barLayoutData": STYLE_LAYOUT})
    tlc.write_json(os.path.join(presets, "keeps-preset.json"), {"name": "Keeps preset", "style": STYLE_ID})
    tlc.write_json(os.path.join(presets, "own-layout.json"), {"name": "Own layout", "barLayoutData": own_layout()})
    tlc.write_json(os.path.join(presets, "style-own-layout.json"),
                   {"name": "Style and own layout", "style": STYLE_ID, "barLayoutData": own_layout()})
    tlc.write_shell(home, tlc.CUSTOM_SHELL)
    # A snapshot records theme "default" (no theme.name file here); the rollback refuses a
    # theme that is not installed, so the sandbox installs it (as tests/test_new_commands.py does).
    os.makedirs(os.path.join(home, ".config/omarchy/themes/default"), exist_ok=True)


def run_apply(legacy, home, env, args):
    """One `apply` through Python or bash; returns the shell.json bytes it leaves behind."""
    if legacy:
        cmd, run_env = ["bash", tlc.LEGACY, "apply", *args], dict(env, CUSTOMIZER_LEGACY="1")
    else:
        cmd, run_env = ["/usr/bin/python3", "-I", tlc.RUN, "apply", *args], env
    r = subprocess.run(cmd, env=run_env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{'bash' if legacy else 'python'} apply {' '.join(args)} exited {r.returncode}: "
                           f"{r.stderr.strip()[:300]}")
    with open(os.path.join(home, ".config/omarchy/shell.json"), "rb") as f:
        return f.read()


def play(legacy, steps, setup=None):
    """Fresh sandbox, then setup (optional) and each step's apply; returns shell.json bytes after every step.
    A step is an argument list; "{HOME}" in it stands for the sandbox HOME."""
    _base, home, env = tlc.sandbox()
    write_user_files(home)
    if setup:
        setup(home)
    out = []
    for args in steps:
        args = [a.replace("{HOME}", home) for a in args]
        out.append(run_apply(legacy, home, env, args))
    return out


def sections(doc):
    """Bar section ids of a shell.json document, for readable failure messages."""
    return tlc.bar_ids(doc["bar"]["layout"])


def style_fails(name, doc):
    """A style applied with carry-over: the user's ids (tray too) kept, the style's arrangement and position."""
    fails = [f"{name}: {f}" for f in tlc.check_invariants(name, tlc.CUSTOM_SHELL, doc, STYLE_LAYOUT)]
    got = {s: sections(doc)[s] for s in EXPECTED_STYLE_SECTIONS}
    if got != EXPECTED_STYLE_SECTIONS:
        fails.append(f"{name}: sections {got} != {EXPECTED_STYLE_SECTIONS}")
    return fails


def verbatim_fails(name, doc, layout, position):
    """The bar layout and position are exactly the given ones (nothing carried over, nothing dropped)."""
    fails = []
    if doc["bar"]["layout"] != layout:
        fails.append(f"{name}: layout is not verbatim: {sections(doc)}")
    if doc["bar"].get("position") != position:
        fails.append(f"{name}: position {doc['bar'].get('position')} != {position}")
    return fails


def case(name, steps, check, setup=None):
    """Run the steps through Python and bash, require byte-identical shell.json after every step, then
    run check(docs) on the parsed Python results; returns the failed case names."""
    try:
        py = play(False, steps, setup)
        bash = play(True, steps, setup)
    except RuntimeError as e:
        print(f"FAIL  {name}: {e}")
        return [name]
    if py != bash:
        for i, (p, b) in enumerate(zip(py, bash)):
            if p != b:
                print(f"FAIL  {name}: step {i + 1}: bash/python shell.json differ ({len(b)} vs {len(p)} bytes)")
        return [name]
    fails = check([json.loads(b) for b in py])
    for f in fails:
        print("FAIL  " + f)
    if fails:
        return [name]
    print(f"ok    {name}")
    return []


def main():
    if not os.path.isdir(tlc.BAR_LAYOUTS):
        print(f"SKIP: no bar layouts at {tlc.BAR_LAYOUTS}")
        return 0

    def style_check(docs):
        return style_fails("style", docs[0])

    def preset_style_check(docs):
        return style_fails("preset-style", docs[0])

    def own_layout_check(docs):
        return verbatim_fails("preset-own-layout", docs[0], own_layout()["layout"], "bottom")

    def style_then_own_check(docs):
        return verbatim_fails("preset-style-own-layout", docs[0], own_layout()["layout"], "bottom")

    def restore_check(docs):
        return style_fails("restore: style", docs[0]) + verbatim_fails(
            "restore: back to pre-style", docs[1], USER_CUSTOM, "top")

    def restore_stock_check(docs):
        stock = json.load(open(os.path.join(tlc.BAR_LAYOUTS, "omarchy-stock.json"), encoding="utf-8"))
        return verbatim_fails("restore-stock-name", docs[0], stock["layout"], stock.get("position"))

    def write_stock_snapshot(home):
        tlc.write_json(os.path.join(home, STATE_DIR, "last-preset.json"),
                       {"name": "Previous setup", "barLayout": "omarchy-stock"})

    style_file = "{HOME}/.config/omarchy/customizer/styles/" + STYLE_ID + ".json"
    presets = "{HOME}/.config/omarchy/customizer/presets/"
    last_preset = "{HOME}/" + STATE_DIR + "/last-preset.json"

    failed = []
    failed += case("style", [["styles", style_file]], style_check)
    failed += case("preset-style", [["presets", presets + "keeps-preset.json"]], preset_style_check)
    failed += case("preset-own-layout", [["presets", presets + "own-layout.json"]], own_layout_check)
    failed += case("preset-style-own-layout", [["presets", presets + "style-own-layout.json"]], style_then_own_check)
    failed += case("restore", [["styles", style_file], ["presets", last_preset]], restore_check)
    failed += case("restore-stock-name", [["presets", last_preset]], restore_stock_check, setup=write_stock_snapshot)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
