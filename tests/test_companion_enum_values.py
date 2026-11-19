#!/usr/bin/python3 -I
"""Enum rows offer every style value the companion plugins accept.

  /usr/bin/python3 -I tests/test_companion_enum_values.py

The Customizer cycles (h/l) and draws chips only from a row's `values` in
settings.json, so a companion style missing there cannot be picked from the
Customizer at all. EXPECTED mirrors the values the companions branch on; the
comment above each key names the companion lines it was taken from. When a
companion gains or drops a style, update both sides in the same change.

Checks, per key: the row exists, its type is "enum", and its values are exactly
EXPECTED (same order, so chip order stays stable). Reads the repo's settings.json
only; no HOME, no shell, no plugin is touched.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

EXPECTED = {
    # omarchy-desktop-widgets/ClockWidget.qml:39-44 (clock.style branches);
    # Widgets.qml:26 comment lists the same set.
    "clockStyle": ["big", "stacked", "terminal", "minimal", "vitreus", "yami", "bruteon"],
    # omarchy-edge-osd/Osd.qml:26 (header lists stock) and :33-40 (edgeStyle branches).
    "osdStyle": ["edge", "dotmatrix", "stock", "space", "crt", "modern"],
    # omarchy-drawer-notifications/Service.qml:69 (header lists bordered) and :79-101 (cardStyle branches).
    "notifyCards": ["flat", "bordered", "dotmatrix", "rumda", "nier", "space", "crt", "modern"],
    # omarchy-desktop-widgets/Dashboard.qml:32-48 (dstyle branches).
    "dashStyle": [
        "default", "dotmatrix", "vitreus", "pencils", "rumda", "surface", "bruteon",
        "unit3", "yami", "cozytile", "glyph", "space", "crt", "modern",
    ],
}


def find_row(node, key):
    """Return the first settings row whose "key" equals `key`, or None.

    Walks dicts and lists recursively, because rows sit under category sections.
    """
    if isinstance(node, dict):
        if node.get("key") == key:
            return node
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return None
    for child in children:
        found = find_row(child, key)
        if found is not None:
            return found
    return None


def main():
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    failures = 0
    for key, expected in EXPECTED.items():
        row = find_row(settings, key)
        if row is None:
            print(f"FAIL  {key}: row missing from settings.json")
            failures += 1
            continue
        if row.get("type") != "enum":
            print(f"FAIL  {key}: type {row.get('type')!r}, want 'enum'")
            failures += 1
        values = row.get("values")
        if values != expected:
            print(f"FAIL  {key}: values {values} != {expected}")
            failures += 1
            continue
        print(f"ok    {key}: {len(values)} values")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
