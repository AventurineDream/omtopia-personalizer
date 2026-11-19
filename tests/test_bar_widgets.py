#!/usr/bin/python3 -I
"""Bar Widgets «Add to bar»: every add path leaves the widget on the bar exactly once.

  /usr/bin/python3 -I tests/test_bar_widgets.py

Covers the backend (list bar-widgets, tweak w:<id> toggle) in a sandbox HOME with stubbed
`omarchy` (plugin catalog) and `omarchy-shell` (logged, never reached the live session):
  - a tray-drawer widget is listed under «In the tray drawer», never under «Not on the bar»;
  - adding a drawer widget moves its existing entry to the end of right, settings kept, no copy left behind;
  - adding an absent widget (catalog plugin, kamradsmeshnyavy.bar QML module) gives one entry;
  - remove then add restores the same entry at the same index, and clears bar-hidden.json;
  - an un-anchored centerBegin entry is still moved to right, once;
  - a layout that already holds a duplicate (drawer copy + visible copy, left by the old bug) heals to one entry;
  - the QML dispatch that sends a w: row's ⏎ / «Add to bar» click to `tweak … toggle` matches w: keys (Customizer.qml).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
QML = os.path.join(PLUGIN, "Customizer.qml")

CATALOG = [
    {"id": "omarchy.weather", "name": "Weather", "kinds": ["bar-widget"]},
    {"id": "omarchy.elsewhen", "name": "Elsewhen", "kinds": ["bar-widget"]},
    {"id": "omarchy.microphone", "name": "Microphone", "kinds": ["bar-widget"]},
    {"id": "omarchy.network", "name": "Network", "kinds": ["bar-widget"]},
    {"id": "omarchy.clock", "name": "Clock", "kinds": ["bar-widget"]},
]

ELSEWHEN = {"id": "omarchy.elsewhen", "cities": [{"name": "Tokyo", "zone": "Asia/Tokyo"}]}


def sandbox():
    base = tempfile.mkdtemp(prefix="customizer-barw.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs, log = (os.path.join(base, n) for n in ("home", "stubs", "calls.log"))
    os.makedirs(home)
    os.makedirs(stubs)
    catalog = os.path.join(base, "catalog.json")
    with open(catalog, "w") as f:
        json.dump(CATALOG, f)
    scripts = {
        "omarchy": f'case "$*" in "plugin list --json") cat "{catalog}";; '
                   f'*) printf "%s\\n" "omarchy $*" >> "{log}";; esac\n',
        "omarchy-shell": f'printf "%s\\n" "omarchy-shell $*" >> "{log}"\n',
    }
    for name, body in scripts.items():
        with open(os.path.join(stubs, name), "w") as f:
            f.write("#!/bin/sh\n" + body)
        os.chmod(os.path.join(stubs, name), 0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"])
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, env


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip("\n"), r.stderr


def write_shell(home, layout, **bar):
    path = os.path.join(home, ".config/omarchy/shell.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"bar": dict(bar, id="kamradsmeshnyavy.bar", layout=layout)}, f, indent=2)


def read_shell(home):
    with open(os.path.join(home, ".config/omarchy/shell.json")) as f:
        return json.load(f)["bar"]["layout"]


def read_hidden(home):
    path = os.path.join(home, ".config/omarchy/customizer/bar-hidden.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def entry_id(e):
    return e.get("id") if isinstance(e, dict) else e


def count_everywhere(layout, wid):
    return sum(1 for sec in layout.values() if isinstance(sec, list) for e in sec if entry_id(e) == wid)


def list_rows(env):
    """list bar-widgets → [(section, label, value, kind)] with the section of each row."""
    code, out, _ = run(env, "list", "bar-widgets")
    rows, sec = [], ""
    for line in out.split("\n"):
        cols = line.split("\t")
        if len(cols) >= 2 and cols[1].startswith("section:") and len(cols) >= 4 and cols[3] == "0" and cols[2] == "":
            sec = cols[1][len("section:"):]
            continue
        if len(cols) >= 7 and cols[1].startswith("tweak:w:"):
            rows.append((sec, cols[0], cols[1][len("tweak:w:"):], cols[6]))
    return rows


def section_of(rows, wid):
    return [(sec, kind) for sec, _, value, kind in rows if value == wid]


def main():
    base, home, env = sandbox()
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    try:
        base_layout = {
            "left": [{"id": "omarchy.workspaces"}],
            "center": [{"id": "omarchy.indicators"}],
            "centerBegin": [],
            "centerEnd": [],
            "right": [{"id": "omarchy.audio"}, {"id": "omarchy.network"}, {"id": "omarchy.power"},
                      {"id": "omarchy.tray", "pinned": []}],
            "tray": [dict(ELSEWHEN), {"id": "omarchy.weather"}, {"id": "kamradsmeshnyavy.menu"}],
        }

        # ── list: drawer widgets get their own section, not «Not on the bar» ──
        write_shell(home, json.loads(json.dumps(base_layout)))
        rows = list_rows(env)
        check("list: tray widget listed under the drawer section",
              section_of(rows, "omarchy.weather") == [("tray", "add")])
        check("list: drawer settings widget listed under the drawer section",
              section_of(rows, "omarchy.elsewhen") == [("tray", "add")])
        check("list: no drawer widget under «Not on the bar»",
              not any(sec == "off" and value in ("omarchy.weather", "omarchy.elsewhen", "kamradsmeshnyavy.menu")
                      for sec, _, value, _ in rows))
        check("list: absent catalog widget still under «Not on the bar»",
              section_of(rows, "omarchy.microphone") == [("off", "add")])
        check("list: on-bar widget listed once, under right",
              section_of(rows, "omarchy.audio") == [("right", "move")])

        # ── add a drawer widget: entry moves out of tray to the end of right, settings kept ──
        code, _, err = run(env, "tweak", "w:omarchy.elsewhen", "toggle")
        lay = read_shell(home)
        check("drawer add: exit 0", code == 0 and err == "")
        check("drawer add: entry is the last of right, inline settings verbatim",
              lay["right"][-1] == ELSEWHEN)
        check("drawer add: gone from tray", all(entry_id(e) != "omarchy.elsewhen" for e in lay["tray"]))
        check("drawer add: exactly one entry for the id", count_everywhere(lay, "omarchy.elsewhen") == 1)
        rows = list_rows(env)
        check("drawer add: now listed on the bar, not in the drawer",
              section_of(rows, "omarchy.elsewhen") == [("right", "move")])

        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("drawer add (plain): one entry at the end of right",
              lay["right"][-1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1)

        # ── add an absent widget: one entry, rendered in right ──
        run(env, "tweak", "w:omarchy.microphone", "toggle")
        lay = read_shell(home)
        check("absent add: one entry at the end of right",
              lay["right"][-1] == {"id": "omarchy.microphone"} and count_everywhere(lay, "omarchy.microphone") == 1)
        run(env, "tweak", "w:dot-clock", "toggle")
        lay = read_shell(home)
        check("absent add: QML bar module gets its {id,type:qml,source} entry once",
              lay["right"][-1] == {"id": "dot-clock", "type": "qml",
                                   "source": "~/.config/omarchy/plugins/kamradsmeshnyavy.bar/modules/DotClock.qml"}
              and count_everywhere(lay, "dot-clock") == 1)

        # ── remove then add: same entry, same index, stash cleared ──
        write_shell(home, json.loads(json.dumps(base_layout)))
        run(env, "tweak", "w:omarchy.network", "toggle")
        check("remove: entry gone from right", all(entry_id(e) != "omarchy.network" for e in read_shell(home)["right"]))
        check("remove: stashed with its section and index",
              read_hidden(home).get("omarchy.network") == {"entry": {"id": "omarchy.network"}, "section": "right", "index": 1})
        check("remove: listed under «Not on the bar»",
              section_of(list_rows(env), "omarchy.network") == [("off", "add")])
        run(env, "tweak", "w:omarchy.network", "toggle")
        lay = read_shell(home)
        check("re-add: back at its old index with one entry", lay["right"][1] == {"id": "omarchy.network"}
              and count_everywhere(lay, "omarchy.network") == 1)
        check("re-add: stash cleared", "omarchy.network" not in read_hidden(home))

        # ── un-anchored centerBegin (not drawn without centerAnchor): still moved to right, once ──
        layout = json.loads(json.dumps(base_layout))
        layout["centerBegin"] = [{"id": "omarchy.clock", "format": "HH:mm"}]
        write_shell(home, layout)
        check("un-anchored centerBegin: listed under «Not on the bar»",
              section_of(list_rows(env), "omarchy.clock") == [("off", "add")])
        run(env, "tweak", "w:omarchy.clock", "toggle")
        lay = read_shell(home)
        check("un-anchored centerBegin: moved to right with its settings, once",
              lay["right"][-1] == {"id": "omarchy.clock", "format": "HH:mm"} and lay["centerBegin"] == []
              and count_everywhere(lay, "omarchy.clock") == 1)

        # ── heal: the old bug left weather in right AND in the drawer ──
        layout = json.loads(json.dumps(base_layout))
        layout["right"].insert(0, {"id": "omarchy.weather"})
        write_shell(home, layout)
        rows = list_rows(env)
        check("heal: duplicate is listed once, as on the bar",
              section_of(rows, "omarchy.weather") == [("right", "move")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("heal: hiding the bar copy leaves the drawer copy as the only one",
              count_everywhere(lay, "omarchy.weather") == 1 and "omarchy.weather" in
              [entry_id(e) for e in lay["tray"]])
        check("heal: then offered in the drawer", section_of(list_rows(env), "omarchy.weather") == [("tray", "add")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("heal: add leaves exactly one entry on the bar",
              lay["right"][-1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1)

        # ── QML dispatch: a w: row's ⏎ / «Add to bar» click calls tweak … toggle ──
        with open(QML, encoding="utf-8") as f:
            qml = f.read()
        line = next((ln for ln in qml.split("\n") if 'root.tweak("toggle")' in ln and "tweakKey" in ln), "")
        m = re.search(r"/(\^[^/]+)/\.test\(root\.tweakKey", line)
        pattern = m.group(1) if m else None
        check("QML dispatch: the toggle branch has a key regex", pattern is not None)
        check("QML dispatch: matches w:<id> (drawer, absent and on-bar rows)",
              pattern is not None and bool(re.search(pattern, "w:omarchy.weather")))
        check("QML dispatch: still matches wset:<id>:<key> rows",
              pattern is not None and bool(re.search(pattern, "wset:kamradsmeshnyavy.tray:collapse")))
        check("QML dispatch: other tweak rows are not toggled",
              pattern is not None and not re.search(pattern, "fontProfile") and not re.search(pattern, "shape"))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
