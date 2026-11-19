#!/usr/bin/python3 -I
"""Every English string the overlay translates has a key in i18n/ru.json.

  /usr/bin/python3 -I tests/test_i18n_keys.py

The overlay passes strings through tr() / localized() from these places; each is
extracted from the QML source:
  - tr("…") and tr(cond ? "…" : "…") calls in Customizer.qml, ui/, previews/, dotmatrix/;
  - title / hint of allCategories, allGroups and allStatusChips (localized());
  - the label (second item) of [keys, label] pairs in keyHints() and the Keys dialog;
  - widget box titles (defs) and font roles, which reach tr(modelData.…).
Missing keys are listed and the test exits 1. Known strings from every source must be
found, so a refactor that silently empties one source fails too.
This is a small string- and comment-aware bracket scanner, not a QML parser: keep the
literal forms above, or extend the source list here.
"""
import glob
import json
import os
import re
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOMIZER = os.path.join(PLUGIN, "Customizer.qml")
RU_JSON = os.path.join(PLUGIN, "i18n", "ru.json")

STRING = r'"((?:[^"\\\n]|\\.)*)"'
OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}


def decode(raw):
    """Body of a JS string literal (as matched by STRING) -> its value."""
    return json.loads('"' + raw + '"')


def literals(text):
    """Values of all string literals in a code fragment."""
    return [decode(m) for m in re.findall(STRING, text)]


def skip_string(src, i):
    """Index just past the string literal that starts at src[i]."""
    quote = src[i]
    i += 1
    while i < len(src) and src[i] != quote:
        i += 2 if src[i] == "\\" else 1
    return i + 1


def code_chars(src, start=0):
    """Yield (index, char) for every character outside string literals and // comments."""
    i = start
    while i < len(src):
        c = src[i]
        if c in "\"'":
            i = skip_string(src, i)
            continue
        if src.startswith("//", i):
            nl = src.find("\n", i)
            if nl == -1:
                return
            i = nl
            continue
        yield i, c
        i += 1


def close_index(src, open_at):
    """Index of the bracket that closes the one at src[open_at]."""
    depth = 0
    for i, c in code_chars(src, open_at):
        if c in OPEN_TO_CLOSE:
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"unbalanced bracket at offset {open_at}")


def top_level_items(body):
    """Split a bracket body on commas that sit outside nested brackets."""
    items, depth, last = [], 0, 0
    for i, c in code_chars(body):
        if c in OPEN_TO_CLOSE:
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            items.append(body[last:i].strip())
            last = i + 1
    items.append(body[last:].strip())
    return items


def pair_labels(region):
    """Labels of [keys, label] pairs in region: the string literals of each label expression.

    Matches any two-item bracket group whose first item is not itself a bracket group,
    so key/label pairs are found at any nesting depth. Comparison operands
    (`x === "presets" ? "delete preset" : …`) are not labels and are dropped first.
    """
    labels = []
    for i, c in code_chars(region):
        if c != "[":
            continue
        items = top_level_items(region[i + 1:close_index(region, i)])
        if len(items) == 2 and not items[0].startswith("["):
            labels += literals(re.sub(r"[!=]==?\s*" + STRING, "", items[1]))
    return labels


def block_after(src, marker, opener):
    """Text of the bracket group that follows the first occurrence of marker."""
    open_at = src.index(opener, src.index(marker))
    return src[open_at:close_index(src, open_at) + 1]


def field_values(region, field):
    """Values of `field: "…"` pairs in region."""
    return [decode(m) for m in re.findall(r"\b" + field + r"\s*:\s*" + STRING, region)]


def tr_args(src):
    """Argument text of every tr( call, without the call's own parentheses."""
    out = []
    for m in re.finditer(r"\btr\(", src):
        open_at = m.end() - 1
        out.append(src[open_at + 1:close_index(src, open_at)])
    return out


def extract():
    """Return {english string: set of sources} for everything the overlay translates."""
    with open(CUSTOMIZER, encoding="utf-8") as f:
        customizer = f.read()
    found = {}

    def add(strings, source):
        for s in strings:
            found.setdefault(s, set()).add(source)

    qml_files = [CUSTOMIZER] + sorted(glob.glob(os.path.join(PLUGIN, "ui", "*.qml"))
                                      + glob.glob(os.path.join(PLUGIN, "previews", "*.qml"))
                                      + glob.glob(os.path.join(PLUGIN, "dotmatrix", "*.qml")))
    for path in qml_files:
        if path == CUSTOMIZER:
            src = customizer
        else:
            with open(path, encoding="utf-8") as f:
                src = f.read()
        for args in tr_args(src):
            add(literals(args), "tr() in " + os.path.relpath(path, PLUGIN))

    for name in ("allCategories", "allGroups", "allStatusChips"):
        block = block_after(customizer, "readonly property var " + name, "[")
        add(field_values(block, "title") + field_values(block, "hint"), name)

    add(pair_labels(block_after(customizer, "function keyHints()", "{")), "keyHints()")

    # The Keys dialog's model is the array that holds the first ["j k  ↑ ↓", …] pair.
    pair_at = customizer.index('["j k  ↑ ↓"')
    model_at = customizer.rindex("model: [", 0, pair_at) + len("model: ")
    keys_dialog = customizer[model_at:close_index(customizer, model_at) + 1]
    add(pair_labels(keys_dialog), "Keys dialog")

    add(field_values(block_after(customizer, "readonly property var defs", "["), "title"), "widget defs")
    add(field_values(customizer, "role"), "font roles")
    return found


# Known strings per source. If the extractor stops finding one, the source was refactored.
EXPECTED_SOURCES = {
    "Bar Layout": "allCategories",
    "Skin": "allStatusChips",
    "Pickers": "allGroups",
    "Good night": "tr() in Customizer.qml",
    "go there": "keyHints()",
    "jump": "keyHints()",
    "settings: type a value": "Keys dialog",
    "Now playing": "widget defs",
    "Titles": "font roles",
}


def main():
    found = extract()
    lost = [f"{s!r} not found from {src}" for s, src in EXPECTED_SOURCES.items() if src not in found.get(s, ())]
    if lost:
        print("FAIL  extractor lost known strings:")
        for line in lost:
            print("     ", line)
        return 1
    with open(RU_JSON, encoding="utf-8") as f:
        ru = json.load(f)
    missing = sorted((s, ", ".join(sorted(srcs))) for s, srcs in found.items() if s not in ru)
    for s, src in missing:
        print(f"MISSING  {s!r}  ({src})")
    if missing:
        print(f"FAIL  {len(missing)} of {len(found)} overlay strings have no key in i18n/ru.json")
        return 1
    print(f"ok    all {len(found)} overlay strings have a key in i18n/ru.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
