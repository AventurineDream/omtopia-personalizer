#!/usr/bin/python3 -I
"""Bar Widgets «Add to bar» / «Remove»: a widget ends up on the bar exactly once, or off it entirely.

  /usr/bin/python3 -I tests/test_bar_widgets.py

Backend (list bar-widgets, tweak w:<id> toggle) in a sandbox HOME, with stubbed `omarchy` (plugin catalog)
and `omarchy-shell` (logged; the live shell is never touched). Cases:
  - a tray-drawer widget is listed under «In the tray drawer», never under «Not on the bar»;
  - adding a drawer widget moves its entry to the end of right, settings kept, with no putBarWidget call;
  - «Remove» drops every copy of the id (bar, tray drawer), stashes the visible copy, and re-add restores its slot;
  - the stash slot is honoured for a drawer-origin entry too, and ignored only when that section is not drawn;
  - odd layouts (tray-only widget, two tray copies, bare-string entries, non-list tray) still give one entry;
  - the drawer row's description says the bar does not draw the drawer when bar.id is kamradsmeshnyavy.bar;
  - the QML predicate that routes a widget row's ⏎ / «Add to bar» click to `tweak … toggle` (Customizer.qml).
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

KAMRAD_BAR = "kamradsmeshnyavy.bar"
STOCK_BAR = "omarchy.bar"
NOT_DRAWN = "does not draw the tray drawer"

CATALOG = [
    {"id": "omarchy.weather", "name": "Weather", "kinds": ["bar-widget"]},
    {"id": "omarchy.elsewhen", "name": "Elsewhen", "kinds": ["bar-widget"]},
    {"id": "omarchy.microphone", "name": "Microphone", "kinds": ["bar-widget"]},
    {"id": "omarchy.network", "name": "Network", "kinds": ["bar-widget"]},
    {"id": "omarchy.clock", "name": "Clock", "kinds": ["bar-widget"]},
]

ELSEWHEN = {"id": "omarchy.elsewhen", "cities": [{"name": "Tokyo", "zone": "Asia/Tokyo"}]}

BASE_LAYOUT = {
    "left": [{"id": "omarchy.workspaces"}],
    "center": [{"id": "omarchy.indicators"}],
    "centerBegin": [],
    "centerEnd": [],
    "right": [{"id": "omarchy.audio"}, {"id": "omarchy.network"}, {"id": "omarchy.power"},
              {"id": "omarchy.tray", "pinned": []}],
    "tray": [dict(ELSEWHEN), {"id": "omarchy.weather"}, {"id": "kamradsmeshnyavy.menu"}],
}


def base_layout():
    return json.loads(json.dumps(BASE_LAYOUT))


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
    return base, home, env, log


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip("\n"), r.stderr


def calls(log):
    try:
        with open(log) as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return []


def hidden_path(home):
    return os.path.join(home, ".config/omarchy/customizer/bar-hidden.json")


def write_shell(home, layout, bar_id=KAMRAD_BAR):
    """Write shell.json and clear bar-hidden.json, so every case starts without a stash."""
    path = os.path.join(home, ".config/omarchy/shell.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"bar": {"id": bar_id, "layout": layout}}, f, indent=2)
    if os.path.exists(hidden_path(home)):
        os.remove(hidden_path(home))


def write_hidden(home, data):
    os.makedirs(os.path.dirname(hidden_path(home)), exist_ok=True)
    with open(hidden_path(home), "w") as f:
        json.dump(data, f)


def read_shell(home):
    with open(os.path.join(home, ".config/omarchy/shell.json")) as f:
        return json.load(f)["bar"]["layout"]


def read_hidden(home):
    if not os.path.exists(hidden_path(home)):
        return {}
    with open(hidden_path(home)) as f:
        return json.load(f)


def entry_id(e):
    return e.get("id") if isinstance(e, dict) else e


def count_everywhere(layout, wid):
    return sum(1 for sec in layout.values() if isinstance(sec, list) for e in sec if entry_id(e) == wid)


def list_rows(env):
    """list bar-widgets → [(section, label, id, kind, description)] for each widget row."""
    _, out, _ = run(env, "list", "bar-widgets")
    rows, sec = [], ""
    for line in out.split("\n"):
        cols = line.split("\t")
        if len(cols) >= 4 and cols[1].startswith("section:") and cols[2] == "" and cols[3] == "0":
            sec = cols[1][len("section:"):]
            continue
        if len(cols) >= 7 and cols[1].startswith("tweak:w:"):
            rows.append((sec, cols[0], cols[1][len("tweak:w:"):], cols[6], cols[4]))
    return rows


def section_of(rows, wid):
    return [(sec, kind) for sec, _, value, kind, _ in rows if value == wid]


def desc_of(rows, wid):
    return [desc for _, _, value, _, desc in rows if value == wid]


def main():
    base, home, env, log = sandbox()
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    try:
        # ── list: drawer widgets get their own section, not «Not on the bar» ──
        write_shell(home, base_layout())
        rows = list_rows(env)
        check("list: tray widget listed under the drawer section",
              section_of(rows, "omarchy.weather") == [("tray", "add")])
        check("list: drawer settings widget listed under the drawer section",
              section_of(rows, "omarchy.elsewhen") == [("tray", "add")])
        check("list: no drawer widget under «Not on the bar»",
              not any(sec == "off" and value in ("omarchy.weather", "omarchy.elsewhen", "kamradsmeshnyavy.menu")
                      for sec, _, value, _, _ in rows))
        check("list: absent catalog widget still under «Not on the bar»",
              section_of(rows, "omarchy.microphone") == [("off", "add")])
        check("list: on-bar widget listed once, under right",
              section_of(rows, "omarchy.audio") == [("right", "move")])
        check("list: kamradsmeshnyavy.bar host: drawer row says the bar does not draw the drawer",
              all(NOT_DRAWN in d for d in desc_of(rows, "omarchy.weather")))
        write_shell(home, base_layout(), bar_id=STOCK_BAR)
        check("list: stock host: drawer row has no «not drawn» note",
              all(NOT_DRAWN not in d for d in desc_of(list_rows(env), "omarchy.weather")))
        write_shell(home, base_layout())

        # ── add a drawer widget: entry moves out of tray to the end of right, settings kept, no IPC ──
        n = len(calls(log))
        code, _, err = run(env, "tweak", "w:omarchy.elsewhen", "toggle")
        lay = read_shell(home)
        check("drawer add: exit 0", code == 0 and err == "")
        check("drawer add: entry is the last of right, inline settings verbatim", lay["right"][-1] == ELSEWHEN)
        check("drawer add: gone from tray", all(entry_id(e) != "omarchy.elsewhen" for e in lay["tray"]))
        check("drawer add: exactly one entry for the id", count_everywhere(lay, "omarchy.elsewhen") == 1)
        check("drawer add: no putBarWidget call to the live shell",
              not any("putBarWidget" in c for c in calls(log)[n:]))
        check("drawer add: now listed on the bar, not in the drawer",
              section_of(list_rows(env), "omarchy.elsewhen") == [("right", "move")])

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
        write_shell(home, base_layout())
        run(env, "tweak", "w:omarchy.network", "toggle")
        check("remove: entry gone from right", all(entry_id(e) != "omarchy.network" for e in read_shell(home)["right"]))
        check("remove: stashed with its section and index",
              read_hidden(home).get("omarchy.network") == {"entry": {"id": "omarchy.network"}, "section": "right", "index": 1})
        check("remove: listed under «Not on the bar»",
              section_of(list_rows(env), "omarchy.network") == [("off", "add")])
        run(env, "tweak", "w:omarchy.network", "toggle")
        lay = read_shell(home)
        check("re-add: back at its old index with one entry",
              lay["right"][1] == {"id": "omarchy.network"} and count_everywhere(lay, "omarchy.network") == 1)
        check("re-add: stash cleared", "omarchy.network" not in read_hidden(home))

        # ── un-anchored centerBegin (not drawn without centerAnchor): still moved to right, once ──
        layout = base_layout()
        layout["centerBegin"] = [{"id": "omarchy.clock", "format": "HH:mm"}]
        write_shell(home, layout)
        check("un-anchored centerBegin: listed under «Not on the bar»",
              section_of(list_rows(env), "omarchy.clock") == [("off", "add")])
        run(env, "tweak", "w:omarchy.clock", "toggle")
        lay = read_shell(home)
        check("un-anchored centerBegin: moved to right with its settings, once",
              lay["right"][-1] == {"id": "omarchy.clock", "format": "HH:mm"} and lay["centerBegin"] == []
              and count_everywhere(lay, "omarchy.clock") == 1)

        # ── «Remove» on a widget on the bar AND in the drawer: every copy goes, the bar copy is stashed ──
        layout = base_layout()
        layout["right"].insert(1, {"id": "omarchy.weather"})
        write_shell(home, layout)
        check("bar + drawer copy: listed once, as on the bar",
              section_of(list_rows(env), "omarchy.weather") == [("right", "move")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("remove with drawer copy: no copy left on the bar or in the tray",
              count_everywhere(lay, "omarchy.weather") == 0)
        check("remove with drawer copy: stash keeps the bar copy's slot",
              read_hidden(home).get("omarchy.weather") == {"entry": {"id": "omarchy.weather"}, "section": "right", "index": 1})
        check("remove with drawer copy: listed under «Not on the bar», not the drawer",
              section_of(list_rows(env), "omarchy.weather") == [("off", "add")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("re-add after remove with drawer copy: one entry at its old slot",
              lay["right"][1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1
              and "omarchy.weather" not in read_hidden(home))

        # ── stash + drawer copy: the drawer entry (settings kept) lands at the stashed slot ──
        write_shell(home, base_layout())
        write_hidden(home, {"omarchy.elsewhen": {"entry": {"id": "omarchy.elsewhen"}, "section": "right", "index": 2}})
        run(env, "tweak", "w:omarchy.elsewhen", "toggle")
        lay = read_shell(home)
        check("stash + drawer copy: lands at the stashed slot with the drawer copy's settings",
              lay["right"][2] == ELSEWHEN and count_everywhere(lay, "omarchy.elsewhen") == 1)
        check("stash + drawer copy: stash cleared", "omarchy.elsewhen" not in read_hidden(home))

        # ── stash in a section that is not drawn (centerBegin without anchor): falls back to the end of right ──
        write_shell(home, base_layout())
        write_hidden(home, {"omarchy.elsewhen": {"entry": {"id": "omarchy.elsewhen"}, "section": "centerBegin", "index": 0}})
        run(env, "tweak", "w:omarchy.elsewhen", "toggle")
        lay = read_shell(home)
        check("stash in an undrawn section: falls back to the end of right, once",
              lay["right"][-1] == ELSEWHEN and count_everywhere(lay, "omarchy.elsewhen") == 1)

        # ── tray-only widget, and the tray widget itself absent from the bar ──
        layout = base_layout()
        layout["right"] = [{"id": "omarchy.audio"}]
        write_shell(home, layout)
        check("tray-only: listed under the drawer section",
              section_of(list_rows(env), "omarchy.weather") == [("tray", "add")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("tray-only: moved to the end of right, out of the tray",
              lay["right"][-1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1)

        # ── two copies of one id in the tray: one drawer row; add keeps the first copy, drops both ──
        layout = base_layout()
        layout["tray"] = [{"id": "omarchy.weather"}, {"id": "omarchy.weather", "x": 1}]
        write_shell(home, layout)
        rows = list_rows(env)
        check("two tray copies: one drawer row", section_of(rows, "omarchy.weather") == [("tray", "add")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("two tray copies: one entry on the bar (first copy), none left in the tray",
              lay["right"][-1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1)

        # ── bare-string entries in right and tray ──
        layout = base_layout()
        layout["right"] = ["omarchy.audio", {"id": "omarchy.power"}]
        layout["tray"] = ["omarchy.weather"]
        write_shell(home, layout)
        rows = list_rows(env)
        check("bare strings: on-bar bare entry listed under right",
              section_of(rows, "omarchy.audio") == [("right", "move")])
        check("bare strings: tray bare entry listed under the drawer",
              section_of(rows, "omarchy.weather") == [("tray", "add")])
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("bare strings: drawer add writes one dict entry at the end of right",
              lay["right"][-1] == {"id": "omarchy.weather"} and count_everywhere(lay, "omarchy.weather") == 1
              and lay["tray"] == [])
        run(env, "tweak", "w:omarchy.audio", "toggle")
        check("bare strings: remove stashes the bare entry as it was",
              read_hidden(home).get("omarchy.audio") == {"entry": "omarchy.audio", "section": "right", "index": 0})
        run(env, "tweak", "w:omarchy.audio", "toggle")
        lay = read_shell(home)
        check("bare strings: re-add restores the bare entry at index 0, once",
              lay["right"][0] == "omarchy.audio" and count_everywhere(lay, "omarchy.audio") == 1)

        # ── non-list tray (malformed): not listed, and the add still yields one entry ──
        layout = base_layout()
        layout["tray"] = {"id": "omarchy.weather"}
        write_shell(home, layout)
        code, out, _ = run(env, "list", "bar-widgets")
        check("non-list tray: no drawer section", "section:tray" not in out)
        run(env, "tweak", "w:omarchy.weather", "toggle")
        lay = read_shell(home)
        check("non-list tray: add gives one entry at the end of right and leaves tray alone",
              lay["right"][-1] == {"id": "omarchy.weather"} and lay["tray"] == {"id": "omarchy.weather"})

        # ── QML: one helper decides what a widget row is; ⏎ and «Add to bar» route through it ──
        with open(QML, encoding="utf-8") as f:
            qml = f.read()
        m = re.search(r"function isWidgetKey\(key\) \{ return /(\^[^/]+)/\.test\(key\) \}", qml)
        pattern = m.group(1) if m else None
        check("QML: isWidgetKey helper defined", pattern is not None)
        check("QML: activate() toggles widget rows through isWidgetKey",
              'root.isWidgetKey(root.tweakKey(root.selectedRow))) root.tweak("toggle")' in qml)
        check("QML: predictStep uses isWidgetKey for widget rows",
              "root.isWidgetKey(key) ||" in qml)
        check("QML: matches w:<id> (drawer, absent and on-bar rows)",
              pattern is not None and bool(re.search(pattern, "w:omarchy.weather")))
        check("QML: wset:<id>:<key> rows are not widget rows (tray settings removed)",
              pattern is not None and not re.search(pattern, "wset:kamradsmeshnyavy.tray:collapse"))
        check("QML: other tweak rows are not widget rows",
              pattern is not None and not any(re.search(pattern, k) for k in ("fontProfile", "shape", "wallpaper")))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
