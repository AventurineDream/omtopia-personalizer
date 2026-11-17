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
                 "omarchy-font-profile", "zenity", "omarchy", "setsid", "gio"):
        p = os.path.join(stubs, name)
        with open(p, "w") as f:
            f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\n')
        os.chmod(p, 0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"])
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, env


def write_shell(home, doc):
    p = os.path.join(home, ".config/omarchy/shell.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return p


def read_shell(home):
    with open(os.path.join(home, ".config/omarchy/shell.json"), encoding="utf-8") as f:
        return json.load(f)


def bar_ids(layout):
    out = {}
    for s in BAR_SECTIONS:
        entries = layout.get(s) or []
        out[s] = [e.get("id") if isinstance(e, dict) else e for e in entries]
    return out


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
    # a non-list section in the new layout is taken as-is; un-named widgets stay
    eq("non-list-section",
       merge_bar_layout(cur, {"left": [{"id": "a"}], "center": "weird"}),
       {"left": [{"id": "a"}, {"id": "b", "x": 1}], "center": "weird", "tray": [{"id": "t"}]})
    # new layout without a section the current one has -> kept as-is
    eq("current-only-section",
       merge_bar_layout(cur, {"left": [{"id": "a"}]}),
       {"left": [{"id": "a"}, {"id": "b", "x": 1}], "center": [], "tray": [{"id": "t"}]})
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
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
