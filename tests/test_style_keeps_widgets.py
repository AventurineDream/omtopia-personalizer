#!/usr/bin/python3 -I
"""A style's bar layout merges into the user's bar: the user keeps their widgets, settings and tray.

  /usr/bin/python3 -I tests/test_style_keeps_widgets.py

A style's bar layout (inline barLayoutData, or a barLayout name resolved from bar-layouts/ or
the stock layouts) is merged into the user's bar by merge_bar_layout: position, centerAnchor and
the arrangement of the sections come from the style; the widget set, each widget's settings and
the tray drawer come from the user. Widgets the style does not name keep their section, widgets
it names that the user does not have are not added, and the style never sets the tray.
A preset's own layout (a saved snapshot), a restore and a rollback apply verbatim; a stock layout
named by a preset carries widgets as a style does.

Each case runs through the Python backend and the legacy bash reference, each on a fresh sandbox
HOME; shell.json must be byte-identical after every step. Cases that read the stock layouts of
the bar plugin print SKIP when the plugin is not installed; every other case always runs.

Sandbox, CUSTOM_SHELL and the widget invariants come from test_layout_carryover.py.
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
CUSTOM_LAYOUT = tlc.CUSTOM_SHELL["bar"]["layout"]
CUSTOM_TRAY = CUSTOM_LAYOUT["tray"]


def without_tray(doc):
    """A copy of a layout document whose layout has no tray key."""
    doc = copy.deepcopy(doc)
    doc["layout"].pop("tray", None)
    return doc


def shell_with(layout_edit):
    """A copy of CUSTOM_SHELL whose bar layout is changed by layout_edit(layout)."""
    shell = copy.deepcopy(tlc.CUSTOM_SHELL)
    layout_edit(shell["bar"]["layout"])
    return shell


# The style's own arrangement, position and anchor. It names widgets the user has (audio
# moves from right to left, network joins right, calendar and indicators go to center), one
# the user does not have (not.on.bar: must not be added) and a tray list (must not be applied).
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
STYLE_NO_TRAY = without_tray(STYLE_LAYOUT)
# No centerAnchor, and begin/end sections: the anchor is dropped and begin/end fold into center.
STYLE_NO_ANCHOR = {
    "position": "bottom",
    "layout": {
        "left": [{"id": "omarchy.workspaces"}],
        "centerBegin": [{"id": "tmn73.calendar"}],
        "center": [{"id": "bibek.focusd"}],
        "centerEnd": [{"id": "omarchy.indicators"}],
        "right": [{"id": "omarchy.audio"}],
        "tray": [{"id": "style.tray.only"}],
    },
}
# A saved user layout (bar-layouts/my-layout.json) that a style names; its tray is not applied either.
USER_LAYOUT = {
    "position": "bottom",
    "centerAnchor": "omarchy.indicators",
    "layout": {
        "left": [{"id": "omarchy.workspaces"}],
        "center": [{"id": "omarchy.indicators"}, {"id": "tmn73.calendar"}],
        "right": [{"id": "omarchy.network"}, {"id": "omarchy.audio"}],
        "tray": [{"id": "style.tray.only"}],
    },
}

# Hand-computed sections for each merge (the widgets the style does not name keep their section,
# after the ones it places). Only sections the layout names are compared.
EXPECTED_STYLE = {
    "left": ["omarchy.workspaces", "omarchy.audio", "makehasteslowly.heliolune"],
    "center": ["tmn73.calendar", "omarchy.indicators", "bibek.focusd", "luotao.zen", "omarchy.system-update"],
    "right": ["omarchy.network", "omarchy.tray", "tristonarmstrong.dictionary", "tmn73.obsidian",
              "aven.omp-usage", "kamradsmeshnyavy.customizer", "aven.agentic-av", "omarchy.monitor",
              "omarchy.power"],
}
EXPECTED_NO_ANCHOR = {
    "left": ["omarchy.workspaces", "makehasteslowly.heliolune"],
    "centerBegin": [],
    "center": ["tmn73.calendar", "bibek.focusd", "luotao.zen", "omarchy.system-update", "omarchy.indicators"],
    "centerEnd": [],
    "right": ["omarchy.audio", "tristonarmstrong.dictionary", "tmn73.obsidian", "aven.omp-usage",
              "kamradsmeshnyavy.customizer", "aven.agentic-av", "omarchy.network", "omarchy.monitor",
              "omarchy.power", "omarchy.tray"],
}
EXPECTED_USER_LAYOUT = {
    "left": ["omarchy.workspaces", "makehasteslowly.heliolune"],
    "center": ["omarchy.indicators", "tmn73.calendar", "bibek.focusd", "luotao.zen", "omarchy.system-update"],
    "right": ["omarchy.network", "omarchy.audio", "tristonarmstrong.dictionary", "tmn73.obsidian",
              "aven.omp-usage", "kamradsmeshnyavy.customizer", "aven.agentic-av", "omarchy.monitor",
              "omarchy.power", "omarchy.tray"],
}
# A bar with no widget in any section takes the style's sections as they are (merge_bar_layout's
# empty-bar branch); the tray is still the user's.
EXPECTED_EMPTY_BAR = {
    "left": ["omarchy.workspaces", "omarchy.audio"],
    "center": ["tmn73.calendar", "omarchy.indicators"],
    "right": ["omarchy.network", "not.on.bar", "omarchy.tray"],
}

# The user's bar with no widget in any section, and with one tray entry.
EMPTY_SHELL = shell_with(lambda layout: layout.update(
    left=[], center=[], right=[], tray=[{"id": "omarchy.weather"}]))
# The user's bar with no tray key at all.
NO_TRAY_SHELL = shell_with(lambda layout: layout.pop("tray"))
# The user's tray holds an id that is also on the bar (duplicated id).
DUP_TRAY = CUSTOM_TRAY + [{"id": "omarchy.audio"}]
DUP_SHELL = shell_with(lambda layout: layout.update(tray=DUP_TRAY))


def own_layout():
    """A preset's own layout: the user's bar plus a widget that is only in the tray today."""
    layout = copy.deepcopy(CUSTOM_LAYOUT)
    layout["left"].append({"id": "omarchy.bluetooth"})
    return {"position": "bottom", "centerAnchor": "omarchy.workspaces", "layout": layout}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_user_files(home, shell):
    """The user's styles, presets and bar layouts under the sandbox's ~/.config/omarchy; bar = shell."""
    customizer = os.path.join(home, ".config/omarchy/customizer")
    styles = os.path.join(customizer, "styles")
    presets = os.path.join(customizer, "presets")
    os.makedirs(styles, exist_ok=True)
    os.makedirs(presets, exist_ok=True)
    tlc.write_json(os.path.join(styles, STYLE_ID + ".json"), {"name": "Keeps test", "barLayoutData": STYLE_LAYOUT})
    tlc.write_json(os.path.join(styles, "keeps-no-tray.json"), {"name": "No tray", "barLayoutData": STYLE_NO_TRAY})
    tlc.write_json(os.path.join(styles, "keeps-no-anchor.json"),
                   {"name": "No anchor", "barLayoutData": STYLE_NO_ANCHOR})
    tlc.write_json(os.path.join(styles, "keeps-user-layout.json"),
                   {"name": "User layout", "barLayout": "my-layout"})
    tlc.write_json(os.path.join(home, ".config/omarchy/bar-layouts/my-layout.json"), USER_LAYOUT)
    tlc.write_json(os.path.join(presets, "keeps-preset.json"), {"name": "Keeps preset", "style": STYLE_ID})
    tlc.write_json(os.path.join(presets, "keeps-stock-preset.json"),
                   {"name": "Keeps stock preset", "style": STYLE_ID, "barLayout": "omarchy-stock"})
    tlc.write_json(os.path.join(presets, "own-layout.json"), {"name": "Own layout", "barLayoutData": own_layout()})
    tlc.write_json(os.path.join(presets, "style-own-layout.json"),
                   {"name": "Style and own layout", "style": STYLE_ID, "barLayoutData": own_layout()})
    tlc.write_shell(home, shell)
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


def play(legacy, steps, shell, setup=None):
    """Fresh sandbox with the user's files and bar = shell, then setup (optional) and each step's apply;
    returns shell.json bytes after every step. A step is an argument list; "{HOME}" stands for the sandbox HOME."""
    _base, home, env = tlc.sandbox()
    write_user_files(home, shell)
    if setup:
        setup(home)
    out = []
    for args in steps:
        args = [a.replace("{HOME}", home) for a in args]
        out.append(run_apply(legacy, home, env, args))
    return out


def sections(doc):
    """Bar section ids of a shell.json document (the bar's centerBegin/centerEnd included)."""
    return tlc.bar_ids(doc["bar"]["layout"])


def layout_fails(name, doc, want_sections, want_tray, want_position, want_anchor):
    """The named sections, the tray, the position and the centerAnchor (None = key absent) are as given."""
    bar = doc["bar"]
    fails = []
    got = sections(doc)
    for section, want in want_sections.items():
        if got.get(section) != want:
            fails.append(f"{name}: {section} {got.get(section)} != {want}")
    if bar["layout"].get("tray") != want_tray:
        fails.append(f"{name}: tray {bar['layout'].get('tray')} != {want_tray}")
    if bar.get("position") != want_position:
        fails.append(f"{name}: position {bar.get('position')} != {want_position}")
    if bar.get("centerAnchor") != want_anchor:
        fails.append(f"{name}: centerAnchor {bar.get('centerAnchor')} != {want_anchor}")
    return fails


def verbatim_fails(name, doc, layout, position, anchor):
    """The bar layout, position and centerAnchor are exactly the given ones."""
    fails = []
    if doc["bar"]["layout"] != layout:
        fails.append(f"{name}: layout is not verbatim: {sections(doc)}")
    if doc["bar"].get("position") != position:
        fails.append(f"{name}: position {doc['bar'].get('position')} != {position}")
    if doc["bar"].get("centerAnchor") != anchor:
        fails.append(f"{name}: centerAnchor {doc['bar'].get('centerAnchor')} != {anchor}")
    return fails


def case(name, steps, shell, check, setup=None):
    """Run the steps through Python and bash, require byte-identical shell.json after every step, then
    run check(docs) on the parsed Python results. Returns "ok", "fail" or "skip"."""
    try:
        py = play(False, steps, shell, setup)
        bash = play(True, steps, shell, setup)
    except RuntimeError as e:
        print(f"FAIL  {name}: {e}")
        return "fail"
    if py != bash:
        for i, (p, b) in enumerate(zip(py, bash)):
            if p != b:
                print(f"FAIL  {name}: step {i + 1}: bash/python shell.json differ ({len(b)} vs {len(p)} bytes)")
        return "fail"
    fails = check([json.loads(b) for b in py])
    for f in fails:
        print("FAIL  " + f)
    if fails:
        return "fail"
    print(f"ok    {name}")
    return "ok"


def style_file(stem):
    return "{HOME}/.config/omarchy/customizer/styles/" + stem + ".json"


def preset_file(stem):
    return "{HOME}/.config/omarchy/customizer/presets/" + stem + ".json"


def main():
    have_plugin = os.path.isdir(tlc.BAR_LAYOUTS)
    stock = read_json(os.path.join(tlc.BAR_LAYOUTS, "omarchy-stock.json")) if have_plugin else None
    last_preset = "{HOME}/" + STATE_DIR + "/last-preset.json"

    def expect_style(name, doc, shell, layout, sections_want):
        """A style merged into the user's bar: widgets/tray/settings kept, the style's arrangement and position."""
        return (tlc.check_invariants(name, shell, doc, layout)
                + layout_fails(name, doc, sections_want, shell["bar"]["layout"].get("tray"),
                               layout["position"], layout.get("centerAnchor")))

    def expect_stock_preset(name, doc):
        return tlc.check_invariants(name, tlc.CUSTOM_SHELL, doc, stock)

    def write_stock_snapshot(home):
        """last-preset.json naming the stock layout; the user's bar has widgets the stock layout does not."""
        tlc.write_json(os.path.join(home, STATE_DIR, "last-preset.json"),
                       {"name": "Previous setup", "barLayout": "omarchy-stock"})

    # (name, bar of the user, steps, check on the parsed docs, needs the bar plugin, setup)
    cases = [
        ("style", tlc.CUSTOM_SHELL, [["styles", style_file(STYLE_ID)]],
         lambda d: expect_style("style", d[0], tlc.CUSTOM_SHELL, STYLE_LAYOUT, EXPECTED_STYLE), False, None),
        ("style-no-anchor", tlc.CUSTOM_SHELL, [["styles", style_file("keeps-no-anchor")]],
         lambda d: expect_style("style-no-anchor", d[0], tlc.CUSTOM_SHELL, STYLE_NO_ANCHOR, EXPECTED_NO_ANCHOR),
         False, None),
        ("style-user-layout", tlc.CUSTOM_SHELL, [["styles", style_file("keeps-user-layout")]],
         lambda d: expect_style("style-user-layout", d[0], tlc.CUSTOM_SHELL, USER_LAYOUT, EXPECTED_USER_LAYOUT),
         False, None),
        ("style-no-tray-bar", NO_TRAY_SHELL, [["styles", style_file(STYLE_ID)]],
         lambda d: expect_style("style-no-tray-bar", d[0], NO_TRAY_SHELL, STYLE_LAYOUT, EXPECTED_STYLE), False, None),
        ("style-empty-bar", EMPTY_SHELL, [["styles", style_file(STYLE_ID)]],
         lambda d: layout_fails("style-empty-bar", d[0], EXPECTED_EMPTY_BAR, EMPTY_SHELL["bar"]["layout"]["tray"],
                                "bottom", "omarchy.indicators"), False, None),
        ("style-dup-tray-id", DUP_SHELL, [["styles", style_file("keeps-no-tray")]],
         lambda d: expect_style("style-dup-tray-id", d[0], DUP_SHELL, STYLE_NO_TRAY, EXPECTED_STYLE), False, None),
        ("preset-style", tlc.CUSTOM_SHELL, [["presets", preset_file("keeps-preset")]],
         lambda d: expect_style("preset-style", d[0], tlc.CUSTOM_SHELL, STYLE_LAYOUT, EXPECTED_STYLE), False, None),
        ("preset-stock-style", tlc.CUSTOM_SHELL, [["presets", preset_file("keeps-stock-preset")]],
         lambda d: expect_stock_preset("preset-stock-style", d[0]), True, None),
        ("preset-own-layout", tlc.CUSTOM_SHELL, [["presets", preset_file("own-layout")]],
         lambda d: verbatim_fails("preset-own-layout", d[0], own_layout()["layout"], "bottom", "omarchy.workspaces"),
         False, None),
        ("preset-style-own-layout", tlc.CUSTOM_SHELL, [["presets", preset_file("style-own-layout")]],
         lambda d: verbatim_fails("preset-style-own-layout", d[0], own_layout()["layout"], "bottom",
                                  "omarchy.workspaces"), False, None),
        ("restore", tlc.CUSTOM_SHELL, [["styles", style_file(STYLE_ID)], ["presets", last_preset]],
         lambda d: expect_style("restore: style", d[0], tlc.CUSTOM_SHELL, STYLE_LAYOUT, EXPECTED_STYLE)
         + verbatim_fails("restore: back to pre-style", d[1], CUSTOM_LAYOUT, "top", "omarchy.workspaces"),
         False, None),
        ("restore-stock-name", tlc.CUSTOM_SHELL, [["presets", last_preset]],
         lambda d: verbatim_fails("restore-stock-name", d[0], stock["layout"], stock.get("position"),
                                  stock.get("centerAnchor")) if have_plugin else [], True, write_stock_snapshot),
    ]

    counts = {"ok": 0, "fail": 0, "skip": 0}
    for name, shell, steps, check, needs_plugin, setup in cases:
        if needs_plugin and not have_plugin:
            print(f"SKIP  {name}: needs the bar plugin's stock layouts ({tlc.BAR_LAYOUTS})")
            counts["skip"] += 1
            continue
        counts[case(name, steps, shell, check, setup)] += 1
    print(f"{counts['ok']} ok, {counts['fail']} failed, {counts['skip']} skipped")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
