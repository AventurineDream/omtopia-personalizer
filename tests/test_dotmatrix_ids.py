#!/usr/bin/python3 -I
"""DOT-MATRIX style: every bar widget it names is one that an installed plugin provides.

  /usr/bin/python3 -I tests/test_dotmatrix_ids.py

styles/dotmatrix.json applies its barLayoutData verbatim, so an id that no plugin provides replaces a real
widget with one nothing draws. Ids are checked against the bar-widget manifests of the stock shell
($OMARCHY_PATH/shell/plugins, default /usr/share/omarchy; a missing directory FAILS) and, when present, of the
bar plugin ($BAR_PLUGIN_DIR, default ~/.config/omarchy/plugins/kamradsmeshnyavy.bar). Entries of type "qml" are
not in any manifest; their source file must be in the bar plugin's modules/ directory, which is checked only
when the bar plugin is installed (otherwise a NOTE line says so). The tray entry may carry only the keys
that the bar plugin's Tray.qml reads.

Read-only: writes nothing and creates no temporary files.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE = os.path.join(REPO, "styles", "dotmatrix.json")
STOCK = os.path.join(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"), "shell", "plugins")
BAR_PLUGIN = os.environ.get("BAR_PLUGIN_DIR", os.path.expanduser("~/.config/omarchy/plugins/kamradsmeshnyavy.bar"))

# Settings that the bar plugin's Tray.qml reads from an omarchy.tray entry (pinned, hidden). Written out here
# on purpose: a change in Tray.qml must be mirrored in this set.
TRAY_KEYS = {"pinned", "hidden"}


def bar_widget_ids(root):
    """Return {id: manifest path} for each *manifest.json under root whose kinds include "bar-widget".

    Raises ValueError (from json) on a malformed manifest, so a broken plugin fails the test rather than
    silently dropping its ids.
    """
    found = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith("manifest.json"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, dict) and "bar-widget" in (m.get("kinds") or []) and isinstance(m.get("id"), str):
                found.setdefault(m["id"], path)
    return found


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
        if not ok:
            fails.append(name)

    check("stock shell plugins directory exists", os.path.isdir(STOCK), STOCK)
    if fails:
        print("\n1 failed")
        return 1

    provided = bar_widget_ids(STOCK)
    bar_present = os.path.isdir(BAR_PLUGIN)
    if bar_present:
        for wid, path in bar_widget_ids(BAR_PLUGIN).items():
            provided.setdefault(wid, path)
    modules_dir = os.path.join(BAR_PLUGIN, "modules")
    modules = set(os.listdir(modules_dir)) if bar_present and os.path.isdir(modules_dir) else None

    with open(STYLE, encoding="utf-8") as f:
        layout = json.load(f)["barLayoutData"]["layout"]
    entries = [e for section in layout.values() for e in section]
    check("style: every bar entry is an object with a string id",
          all(isinstance(e, dict) and isinstance(e.get("id"), str) for e in entries))

    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str):
            continue
        wid = e["id"]
        if e.get("type") == "qml":
            if modules is None:
                print(f"NOTE  {wid}: {BAR_PLUGIN} not installed, qml module not checked")
            else:
                module = os.path.basename(str(e.get("source", "")))
                check(f"{wid}: qml module {module} is in the bar plugin", module in modules, module)
        else:
            check(f"{wid}: a bar-widget manifest provides it", wid in provided)
        if wid == "omarchy.tray":
            extra = sorted(set(e) - {"id"} - TRAY_KEYS)
            check("omarchy.tray: only the settings Tray.qml reads", not extra, ", ".join(extra))

    check("omarchy.tray is on the bar", "omarchy.tray" in [e.get("id") for e in entries if isinstance(e, dict)])

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
