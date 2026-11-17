#!/usr/bin/python3 -I
"""Layout apply carries the user's widgets over (issue: stock layout clobbered the bar).

  /usr/bin/python3 -I tests/test_layout_carryover.py

Applies every stock bar layout over a custom bar (Aven's shape: third-party widgets
with inline settings, a tray drawer, empty centerBegin/centerEnd) and asserts:
  - no widget is lost and none is added (same id set, bar sections only);
  - every widget entry survives verbatim (inline settings untouched);
  - position / centerAnchor come from the new layout;
  - the tray drawer list is untouched;
  - the bar's other top-level keys (id, background, transparent) are untouched;
  - no widget id is duplicated across bar sections.
The same apply is then run through the legacy bash reference and the resulting
shell.json must be byte-identical to the Python one (parity, no allowlist).

Carryover applies ONLY to stock layouts (BAR_DIR/layouts). Saved layouts,
presets, snapshots and backups apply verbatim, so a restore can bring back
widgets that are not currently on the bar:
  - snapshot restore: last-preset.json (is_backup) with a barLayoutData that
    holds a widget missing from the current bar -> the widget comes back, the
    layout is exactly the saved one, Python == bash byte-identical;
  - user layout: a file under USER_LAYOUTS (bar-layouts/) applied through the
    bar-layouts command -> same verbatim behaviour, Python == bash.
Unit cases cover the merge edges: duplicate instances of one id, folding
un-anchored centerBegin/centerEnd into center, and object-valued sections
(Python and bash must agree: skipped, not iterated).

Only a sandbox (fresh HOME under $XDG_RUNTIME_DIR); the live shell.json is never
touched and the shell is never restarted.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
LEGACY = os.path.join(PLUGIN, "tests/legacy/customizer.sh")
BAR_LAYOUTS = os.path.join(os.environ["HOME"], ".config/omarchy/plugins/kamradsmeshnyavy.bar/layouts")

# Aven-like custom bar: third-party widgets with inline settings, tray drawer.
CUSTOM_SHELL = {
    "bar": {
        "background": "glassy",
        "centerAnchor": "omarchy.workspaces",
        "id": "kamradsmeshnyavy.bar",
        "layout": {
            "center": [
                {"id": "bibek.focusd"},
                {"id": "luotao.zen", "minutes": 5, "pattern": "box"},
                {"format": "ddd d MMM HH:mm", "formatAlt": "d MMMM 'W'ww yyyy",
                 "id": "tmn73.calendar", "showLunarDates": False, "showYearProgress": True,
                 "verticalFormat": "HH\n—\nmm"},
                {"id": "omarchy.system-update"},
                {"id": "omarchy.indicators"},
            ],
            "centerBegin": [],
            "centerEnd": [],
            "left": [
                {"id": "omarchy.workspaces"},
                {"colorMode": "theme", "id": "makehasteslowly.heliolune", "moonStyle": "nouveau",
                 "notifyBlue": "on", "notifyMornings": "on", "skyLight": "on",
                 "timeFormat": "24", "weather": "f", "windUnit": "mph"},
            ],
            "right": [
                {"id": "tristonarmstrong.dictionary"},
                {"chipItems": False, "id": "tmn73.obsidian",
                 "lists": [{"badge": True, "id": "root-todo", "name": "TODO", "path": "TODO.md", "type": "tasks"}],
                 "obsidianSync": True, "tweetPreviews": True, "vaultPath": "/home/aven/Projects/Obsidian/Home "},
                {"id": "aven.omp-usage"},
                {"id": "kamradsmeshnyavy.customizer"},
                {"id": "omarchy.audio"},
                {"id": "aven.agentic-av"},
                {"id": "omarchy.network"},
                {"id": "omarchy.monitor"},
                {"id": "omarchy.power"},
                {"hidden": ["artcraft-launcher"], "id": "omarchy.tray", "pinned": []},
            ],
            "tray": [
                {"cities": [{"name": "Los Angeles", "zone": "America/Los_Angeles"}],
                 "id": "omarchy.elsewhen"},
                {"id": "omarchy.weather"},
                {"id": "kamradsmeshnyavy.menu"},
                {"id": "omarchy.keyboard-layout"},
                {"id": "omarchy.bluetooth"},
                {"id": "omarchy.agents"},
            ],
        },
        "position": "top",
        "transparent": False,
    },
    "cloneSourceRestores": ["kamradsmeshnyavy.menu"],
    "disabledPlugins": [],
    "dock": {"pinned": [], "position": "left"},
    "idle": {"lock": 4800, "screensaver": 1200},
    "plugins": [{"id": "kamradsmeshnyavy.customizer"}],
    "version": 1,
}

BAR_SECTIONS = ("left", "centerBegin", "center", "centerEnd", "right")


def sandbox():
    base = tempfile.mkdtemp(prefix="customizer-layout.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs, log = (os.path.join(base, n) for n in ("home", "stubs", "calls.log"))
    os.makedirs(os.path.join(home, ".config/omarchy"))
    os.makedirs(stubs)
    for name in ("notify-send", "omarchy-shell", "hyprctl", "omarchy-hyprland-toggle",
                 "omarchy-font-profile", "zenity", "omarchy", "setsid", "gio",
                 "omarchy-app-themes", "omarchy-firefox-chrome"):
        p = os.path.join(stubs, name)
        with open(p, "w") as f:
            f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\n')
        os.chmod(p, 0o755)
    # The real bar plugin, so stock-layout detection sees the same files the
    # test passes in: Python realpaths the symlink, bash -ef compares inodes.
    real_bar = os.path.dirname(BAR_LAYOUTS)
    if os.path.isdir(real_bar):
        plugins = os.path.join(home, ".config/omarchy/plugins")
        os.makedirs(plugins, exist_ok=True)
        os.symlink(real_bar, os.path.join(plugins, "kamradsmeshnyavy.bar"))
    # State dir (ACTIVE_PRESET / ACTIVE_STYLE writes) and user layouts dir.
    os.makedirs(os.path.join(home, ".local/state/omarchy-customizer"), exist_ok=True)
    os.makedirs(os.path.join(home, ".config/omarchy/bar-layouts"), exist_ok=True)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"])
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, env


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return path


def write_shell(home, doc):
    return write_json(os.path.join(home, ".config/omarchy/shell.json"), doc)


def read_shell(home):
    with open(os.path.join(home, ".config/omarchy/shell.json"), encoding="utf-8") as f:
        return json.load(f)


def bar_ids(layout):
    out = {}
    for s in BAR_SECTIONS:
        entries = layout.get(s) or []
        out[s] = [e.get("id") if isinstance(e, dict) else e for e in entries]
    return out


def run_both(home, env, args):
    """Run the same apply through Python and the legacy bash; return (py, bash) shell.json bytes."""
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, "apply", *args],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"python apply {' '.join(args)} exited {r.returncode}: {r.stderr.strip()[:300]}")
    py_bytes = open(os.path.join(home, ".config/omarchy/shell.json"), "rb").read()
    write_shell(home, CUSTOM_SHELL)
    benv = dict(env, CUSTOMIZER_LEGACY="1")
    r = subprocess.run(["bash", LEGACY, "apply", *args],
                       env=benv, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"bash apply {' '.join(args)} exited {r.returncode}: {r.stderr.strip()[:300]}")
    bash_bytes = open(os.path.join(home, ".config/omarchy/shell.json"), "rb").read()
    return py_bytes, bash_bytes


def check_invariants(name, before, after, layout):
    fails = []
    bl, al = before["bar"]["layout"], after["bar"]["layout"]
    before_by_id, after_by_id = {}, {}
    for s in BAR_SECTIONS:
        for e in bl.get(s) or []:
            before_by_id[e.get("id") if isinstance(e, dict) else e] = e
        for e in al.get(s) or []:
            wid = e.get("id") if isinstance(e, dict) else e
            if wid in after_by_id:
                fails.append(f"{name}: duplicate {wid} in bar sections")
            after_by_id[wid] = e
    if set(before_by_id) != set(after_by_id):
        fails.append(f"{name}: widget set changed: lost={sorted(set(before_by_id) - set(after_by_id))} "
                     f"added={sorted(set(after_by_id) - set(before_by_id))}")
    for wid, entry in before_by_id.items():
        if after_by_id.get(wid) != entry:
            fails.append(f"{name}: entry for {wid} changed: {entry} -> {after_by_id.get(wid)}")
    if after["bar"].get("position") != layout.get("position"):
        fails.append(f"{name}: position {after['bar'].get('position')} != {layout.get('position')}")
    if "centerAnchor" in layout and after["bar"].get("centerAnchor") != layout.get("centerAnchor"):
        fails.append(f"{name}: centerAnchor {after['bar'].get('centerAnchor')} != {layout.get('centerAnchor')}")
    if al.get("tray") != bl.get("tray"):
        fails.append(f"{name}: tray drawer changed")
    for k in ("id", "background", "transparent"):
        if after["bar"].get(k) != before["bar"].get(k):
            fails.append(f"{name}: bar.{k} changed")
    return fails


def test_merge_unit():
    """Edge cases for merge_bar_layout, straight against the Python function."""
    sys.path.insert(0, os.path.join(PLUGIN, "backend"))
    from customizer.apply_ops import merge_bar_layout
    fails = []

    def eq(name, got, want):
        if got != want:
            fails.append(f"unit/{name}: got {got!r}, want {want!r}")
        else:
            print(f"ok    unit/{name}")

    cur = {"left": [{"id": "a"}, {"id": "b", "x": 1}], "center": [], "tray": [{"id": "t"}]}
    # empty current layout -> new layout as-is, current-only sections kept
    eq("empty-current", merge_bar_layout({}, {"left": [{"id": "a"}], "center": [{"id": "c"}]}),
       {"left": [{"id": "a"}], "center": [{"id": "c"}]})
    # widgets only in the tray -> nothing to carry over, new layout as-is + tray kept
    eq("tray-only", merge_bar_layout({"tray": [{"id": "t"}]},
                                      {"left": [{"id": "a"}], "center": []}),
       {"left": [{"id": "a"}], "center": [], "tray": [{"id": "t"}]})
    # string entries (non-dict) are carried by their value
    eq("string-entries",
       merge_bar_layout({"left": ["a", "b"], "center": []}, {"left": ["b"], "center": ["a"]}),
       {"left": ["b"], "center": ["a"]})
    # an id named twice in the new layout is placed once (first section wins)
    eq("duplicate-in-new",
       merge_bar_layout(cur, {"left": [{"id": "b"}], "center": [{"id": "b"}, {"id": "a"}]}),
       {"left": [{"id": "b", "x": 1}], "center": [{"id": "a"}], "tray": [{"id": "t"}]})
    # the same id twice in one new section is placed once
    eq("duplicate-in-new-same-section",
       merge_bar_layout(cur, {"left": [{"id": "b"}, {"id": "b"}, {"id": "a"}], "center": []}),
       {"left": [{"id": "b", "x": 1}, {"id": "a"}], "center": [], "tray": [{"id": "t"}]})
    # a non-list section in the new layout is taken as-is; un-named widgets stay
    eq("non-list-section",
       merge_bar_layout(cur, {"left": [{"id": "a"}], "center": "weird"}),
       {"left": [{"id": "a"}, {"id": "b", "x": 1}], "center": "weird", "tray": [{"id": "t"}]})
    # new layout without a section the current one has -> kept as-is
    eq("current-only-section",
       merge_bar_layout(cur, {"left": [{"id": "a"}]}),
       {"left": [{"id": "a"}, {"id": "b", "x": 1}], "center": [], "tray": [{"id": "t"}]})
    # (3) extra instances of a named id are carried after the placed one
    eq("duplicate-instances",
       merge_bar_layout({"left": [{"id": "a"}, {"id": "x", "v": 1}], "center": [{"id": "x", "v": 2}], "tray": []},
                        {"left": [{"id": "a"}], "right": [{"id": "x"}], "center": []}, anchor="a"),
       {"left": [{"id": "a"}], "right": [{"id": "x", "v": 1}, {"id": "x", "v": 2}], "center": [], "tray": []})
    # (2) fold: no centerAnchor -> centerBegin/centerEnd move into center
    anchored = {"left": [{"id": "a"}], "center": [{"id": "c"}],
                "centerBegin": [{"id": "b1"}], "centerEnd": [{"id": "e1"}], "tray": []}
    new = {"left": [{"id": "a"}], "center": [{"id": "c"}], "right": []}
    eq("fold-no-anchor", merge_bar_layout(anchored, new, anchor=None),
       {"left": [{"id": "a"}], "center": [{"id": "b1"}, {"id": "c"}, {"id": "e1"}],
        "right": [], "centerBegin": [], "centerEnd": [], "tray": []})
    # anchor present in center -> begin/end stay where they are
    eq("fold-anchored", merge_bar_layout(anchored, new, anchor="c"),
       {"left": [{"id": "a"}], "center": [{"id": "c"}], "right": [],
        "centerBegin": [{"id": "b1"}], "centerEnd": [{"id": "e1"}], "tray": []})
    # anchor named but not in center -> no anchor holds them, fold
    eq("fold-anchor-missing", merge_bar_layout(anchored, new, anchor="zz"),
       {"left": [{"id": "a"}], "center": [{"id": "b1"}, {"id": "c"}, {"id": "e1"}],
        "right": [], "centerBegin": [], "centerEnd": [], "tray": []})
    # empty-string anchor (right-heavy stock layout) -> fold
    eq("fold-anchor-empty", merge_bar_layout(anchored, new, anchor=""),
       {"left": [{"id": "a"}], "center": [{"id": "b1"}, {"id": "c"}, {"id": "e1"}],
        "right": [], "centerBegin": [], "centerEnd": [], "tray": []})
    # fold creates center when the new layout has none
    eq("fold-no-center-key",
       merge_bar_layout({"left": [{"id": "a"}], "centerBegin": [{"id": "b1"}],
                         "centerEnd": [{"id": "e1"}], "tray": []},
                        {"left": [{"id": "a"}], "right": []}, anchor=None),
       {"left": [{"id": "a"}], "right": [], "center": [{"id": "b1"}, {"id": "e1"}],
        "centerBegin": [], "centerEnd": [], "tray": []})
    # non-list center -> no fold (nothing safe to fold into)
    eq("fold-center-nonlist",
       merge_bar_layout({"left": [{"id": "a"}], "center": "weird", "centerBegin": [{"id": "b1"}], "tray": []},
                        {"left": [{"id": "a"}], "center": "weird", "right": []}, anchor=None),
       {"left": [{"id": "a"}], "center": "weird", "right": [],
        "centerBegin": [{"id": "b1"}], "tray": []})
    # a widget in a section the new layout omits, named in a destination
    # section, is placed once (not duplicated into the omitted section)
    eq("no-dup-omitted",
       merge_bar_layout({"left": [{"id": "a"}], "center": [{"id": "c"}],
                         "centerBegin": [{"id": "omarchy.audio"}], "tray": []},
                        {"left": [{"id": "a"}], "center": [{"id": "c"}],
                         "right": [{"id": "omarchy.audio"}]}, anchor="c"),
       {"left": [{"id": "a"}], "center": [{"id": "c"}],
        "right": [{"id": "omarchy.audio"}], "centerBegin": [], "tray": []})
    # object-valued sections are skipped by both implementations (parity):
    # current side: "c" is never in by_id, so the new layout's "c" is not
    # added (merge adds nothing) and center ends up empty, not the object.
    eq("obj-section-current",
       merge_bar_layout({"left": [{"id": "a"}], "center": {"id": "c", "x": 1}, "tray": []},
                        {"left": [{"id": "a"}], "center": [{"id": "c"}], "right": []}, anchor="c"),
       {"left": [{"id": "a"}], "center": [], "right": [], "tray": []})
    # new side: passed through as-is
    eq("obj-section-new",
       merge_bar_layout({"left": [{"id": "a"}], "center": [{"id": "c"}], "tray": []},
                        {"left": [{"id": "a"}], "center": {"id": "c"}, "right": []}, anchor="c"),
       {"left": [{"id": "a"}], "center": {"id": "c"}, "right": [], "tray": []})
    return fails


def test_snapshot_restore(home, env):
    """A snapshot (last-preset.json, is_backup) restores verbatim: a widget
    present in the saved layout but absent from the current bar comes back."""
    fails = []
    saved = {
        "note": "Previous setup",
        "position": "bottom",
        "centerAnchor": "omarchy.workspaces",
        "layout": json.loads(json.dumps(CUSTOM_SHELL["bar"]["layout"])),
    }
    # omarchy.weather lives only in the tray of the current bar; the saved
    # layout has it on the bar -> restore must bring it back.
    saved["layout"]["right"].append({"id": "omarchy.weather"})
    preset_path = write_json(
        os.path.join(home, ".local/state/omarchy-customizer/last-preset.json"),
        {"name": "Previous setup", "barLayoutData": saved})
    write_shell(home, CUSTOM_SHELL)
    try:
        py_bytes, bash_bytes = run_both(home, env, ["presets", preset_path])
    except RuntimeError as e:
        print("FAIL  snapshot-restore: " + str(e))
        return ["snapshot-restore"]
    if py_bytes != bash_bytes:
        print(f"FAIL  snapshot-restore: bash/python shell.json differ ({len(bash_bytes)} vs {len(py_bytes)} bytes)")
        return ["snapshot-restore"]
    doc = json.loads(py_bytes)
    if doc["bar"]["layout"] != saved["layout"]:
        print(f"FAIL  snapshot-restore: layout is not the saved one verbatim: {bar_ids(doc['bar']['layout'])}")
        fails.append("snapshot-restore")
    if doc["bar"].get("position") != "bottom":
        print(f"FAIL  snapshot-restore: position {doc['bar'].get('position')} != bottom")
        fails.append("snapshot-restore")
    if "omarchy.weather" not in bar_ids(doc["bar"]["layout"]).get("right", []):
        print("FAIL  snapshot-restore: omarchy.weather did not come back")
        fails.append("snapshot-restore")
    if not fails:
        print("ok    snapshot-restore (verbatim, weather back, python == bash)")
    return fails


def test_user_layout_verbatim(home, env):
    """A user-saved layout (USER_LAYOUTS) applied through bar-layouts applies
    verbatim: a widget in the saved file but not on the bar comes back."""
    fails = []
    saved = {
        "note": "Saved 2026-11-16",
        "position": "top",
        "centerAnchor": "omarchy.workspaces",
        "layout": json.loads(json.dumps(CUSTOM_SHELL["bar"]["layout"])),
    }
    # omarchy.bluetooth lives only in the tray of the current bar; the saved
    # layout has it on the bar -> apply must bring it back, verbatim.
    saved["layout"]["left"].append({"id": "omarchy.bluetooth"})
    layout_path = write_json(
        os.path.join(home, ".config/omarchy/bar-layouts/my-layout.json"), saved)
    write_shell(home, CUSTOM_SHELL)
    try:
        py_bytes, bash_bytes = run_both(home, env, ["bar-layouts", layout_path])
    except RuntimeError as e:
        print("FAIL  user-layout-verbatim: " + str(e))
        return ["user-layout-verbatim"]
    if py_bytes != bash_bytes:
        print(f"FAIL  user-layout-verbatim: bash/python shell.json differ ({len(bash_bytes)} vs {len(py_bytes)} bytes)")
        return ["user-layout-verbatim"]
    doc = json.loads(py_bytes)
    if doc["bar"]["layout"] != saved["layout"]:
        print(f"FAIL  user-layout-verbatim: layout is not the saved one verbatim: {bar_ids(doc['bar']['layout'])}")
        fails.append("user-layout-verbatim")
    if "omarchy.bluetooth" not in bar_ids(doc["bar"]["layout"]).get("left", []):
        print("FAIL  user-layout-verbatim: omarchy.bluetooth did not come back")
        fails.append("user-layout-verbatim")
    if not fails:
        print("ok    user-layout-verbatim (verbatim, bluetooth back, python == bash)")
    return fails


def main():
    if not os.path.isdir(BAR_LAYOUTS):
        print(f"SKIP: no bar layouts at {BAR_LAYOUTS}")
        return 0
    fails = test_merge_unit()
    base, home, env = sandbox()
    layouts = sorted(f for f in os.listdir(BAR_LAYOUTS) if f.endswith(".json"))
    layout_fails = 0
    for name in layouts:
        path = os.path.join(BAR_LAYOUTS, name)
        layout = json.load(open(path, encoding="utf-8"))
        write_shell(home, CUSTOM_SHELL)
        r = subprocess.run(["/usr/bin/python3", "-I", RUN, "apply", "bar-layouts", path],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL  {name}: python apply exited {r.returncode}: {r.stderr.strip()[:200]}")
            fails.append(name)
            layout_fails += 1
            continue
        py_bytes = open(os.path.join(home, ".config/omarchy/shell.json"), "rb").read()
        py_doc = json.loads(py_bytes)
        inv = check_invariants(name, CUSTOM_SHELL, py_doc, layout)
        if inv:
            for f in inv:
                print("FAIL  " + f)
            fails.append(name)
            layout_fails += 1
            continue
        # bash reference on the same starting shell.json: byte-identical result?
        write_shell(home, CUSTOM_SHELL)
        benv = dict(env, CUSTOMIZER_LEGACY="1")
        r = subprocess.run(["bash", LEGACY, "apply", "bar-layouts", path],
                           env=benv, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL  {name}: bash apply exited {r.returncode}: {r.stderr.strip()[:200]}")
            fails.append(name)
            layout_fails += 1
            continue
        bash_bytes = open(os.path.join(home, ".config/omarchy/shell.json"), "rb").read()
        if bash_bytes != py_bytes:
            print(f"FAIL  {name}: bash/python shell.json differ ({len(bash_bytes)} vs {len(py_bytes)} bytes)")
            a, b = py_bytes.decode().splitlines(), bash_bytes.decode().splitlines()
            for x in sorted(set(a) ^ set(b))[:6]:
                print("     ", "py  " if x in a else "bash", x[:150])
            fails.append(name)
            layout_fails += 1
            continue
        print(f"ok    {name}")
    print(f"{len(layouts) - layout_fails}/{len(layouts)} layouts carry over; sandbox: {base}")
    fails += test_snapshot_restore(home, env)
    fails += test_user_layout_verbatim(home, env)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
