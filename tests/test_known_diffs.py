#!/usr/bin/python3 -I
"""Контракт сверки allowlist (tests/known_diffs.py) и проверки снимка геометрии (compare_apply) —
без запуска bash и бэкенда.

  /usr/bin/python3 -I tests/test_known_diffs.py

Сверка известных расхождений строгая: лишняя bash-строка, пропавший обязательный маркер или чужая
строка Python роняют запись (KNOWN-CHANGED). Для apply-записей с "py_only" набор py-строк
сверяется точно: любое другое значение или лишний/пропавший ключ — другая подпись.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_apply as ca  # noqa: E402
import compare_tweaks as ct  # noqa: E402
import known_diffs  # noqa: E402
from customizer import apply_ops  # noqa: E402

fails = []


def check(name, cond):
    print(("ok    " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


RO = {"expect": ["section:", "outline", "enable-plugin"]}
BASH = "Duration, ms: 420\ttweak:duration\nTransitions\tsection:transitions"
PY_FULL = "Settings\tsection:settings\n" + BASH + "\nenable-plugin row\tenable-plugin\noutline\toutline"

SNAP = ['"windowGapsIn": 6,', '"windowGapsOut": 9,', '"windowBorder": 3,', '"windowDecoRounding": 10,',
        '"windowShadow": true,', '"windowNoGaps": true', '"windowsGeometry": {']
EXACT = {"code": [0, 0], "files": ["last-preset.json"], "py_only": SNAP, "bash_only": []}


def readonly_checks():
    check("readonly: matching output with every marker present",
          known_diffs.matches_readonly(RO, BASH, PY_FULL))
    check("readonly: a missing marker fails (no optional escape hatch)",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("enable-plugin row\tenable-plugin\n", "")))
    check("readonly: missing required marker fails",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("outline\toutline", "")))
    check("readonly: bash-only line fails",
          not known_diffs.matches_readonly(RO, BASH + "\nLost row\ttweak:lost", PY_FULL))
    check("readonly: extra python row without any marker fails",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL + "\nstray row"))
    check("readonly: a python line that changes a bash value is not covered",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("Duration, ms: 420", "Duration, ms: 500")))
    check("readonly: extra row carrying a marker is allowed",
          known_diffs.matches_readonly(RO, BASH, PY_FULL + "\nowe row\toutline"))


def apply_checks():
    apply_variant = {"code": [0, 0], "files": ["last-preset.json"], "expect": "\"windowsGeometry\"",
                     "expect_all": ["\"windowGapsIn\":", "\"windowsGeometry\""]}
    ok_lines = ['"windowGapsIn": 6,', '"windowsGeometry": {']
    check("apply substring mode: allowed py-only lines match",
          known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines, []))
    check("apply substring mode: structural lines are ignored",
          known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines + ["}", "  },"], []))
    check("apply substring mode: py-only key outside expect_all fails",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"],
                                        ok_lines + ['"windowBorder": 1,'], []))
    check("apply: bash-only line fails",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines, ["x"]))
    check("apply: unexpected differing file fails",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json", "calls.log"], ok_lines, []))
    check("apply: exit code change fails",
          not known_diffs.matches_apply(apply_variant, 0, 1, ["last-preset.json"], ok_lines, []))
    variants = {"variants": [apply_variant, dict(apply_variant, files=["windows.json"])]}
    check("apply: any of several variants matches",
          known_diffs.matches_apply(variants, 0, 0, ["windows.json"], ok_lines, []))

    check("apply exact: the exact py-only set matches",
          known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"], list(SNAP), []))
    check("apply exact: order of py-only lines does not matter",
          known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"], list(reversed(SNAP)), []))
    check("apply exact: a swapped value (gaps 8 instead of 9) fails",
          not known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"],
                                        [s.replace("9", "8") if "GapsOut" in s else s for s in SNAP], []))
    check("apply exact: a dropped key fails",
          not known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"],
                                        [s for s in SNAP if "Shadow" not in s], []))
    check("apply exact: an extra key fails",
          not known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"], SNAP + ['"windowFoo": 1,'], []))
    check("apply exact: a missing structural line fails",
          not known_diffs.matches_apply(EXACT, 0, 0, ["last-preset.json"], SNAP[:-1], []))


def geometry_checks():
    check("fixture pins exactly the apply geometry keys",
          set(ca.WINDOWS_FIXTURE) == set(apply_ops.WINDOW_GEOM_KEYS))
    check("fixture values differ from apply defaults (4/8/1/12, no shadow, no gaps)",
          ca.WINDOWS_FIXTURE["windowGapsIn"] != 4 and ca.WINDOWS_FIXTURE["windowGapsOut"] != 8
          and ca.WINDOWS_FIXTURE["windowBorder"] != 1 and ca.WINDOWS_FIXTURE["windowDecoRounding"] != 12
          and ca.WINDOWS_FIXTURE["windowShadow"] is True and ca.WINDOWS_FIXTURE["windowNoGaps"] is True)
    check("save file name: title lower-cased, spaces to hyphens",
          ca.expected_geometry_files(["apply", "presets", "save", "Test Preset"])
          == [".config/omarchy/customizer/presets/test-preset.json"])
    check("style save writes under styles/",
          ca.expected_geometry_files(["apply", "styles", "save", "Test Style"])
          == [".config/omarchy/customizer/styles/test-style.json"])
    check("geometry-reset writes no snapshot file",
          ca.expected_geometry_files(["apply", "presets", "geometry-reset"]) == [])

    base = tempfile.mkdtemp(prefix="known-diffs-geom.")
    home = os.path.join(base, "home")
    last = os.path.join(home, ca.LAST_PRESET)
    cfg = os.path.join(home, ca.WINDOWS_CFG)
    os.makedirs(os.path.dirname(last))
    os.makedirs(os.path.dirname(cfg))
    orig = ["apply", "presets", "{HOME}/" + ca.LAST_PRESET]
    with open(last, "w") as f:
        json.dump({"windowsGeometry": dict(ca.WINDOWS_FIXTURE)}, f)
    with open(cfg, "w") as f:
        json.dump(ca.WINDOWS_FIXTURE, f)
    check("geometry: exact snapshot and restored windows.json pass",
          ca.geometry_problems(base, orig) == [])
    with open(last, "w") as f:
        json.dump({"windowsGeometry": dict(ca.WINDOWS_FIXTURE, windowGapsOut=8)}, f)
    check("geometry: a default-valued gap in the snapshot is a problem",
          len(ca.geometry_problems(base, orig)) == 1)
    with open(last, "w") as f:
        json.dump({"windowsGeometry": {k: v for k, v in ca.WINDOWS_FIXTURE.items() if k != "windowShadow"}}, f)
    check("geometry: a dropped key in the snapshot is a problem",
          len(ca.geometry_problems(base, orig)) == 1)
    with open(last, "w") as f:
        json.dump({"windowsGeometry": dict(ca.WINDOWS_FIXTURE)}, f)
    with open(cfg, "w") as f:
        json.dump({}, f)
    check("geometry: windows.json not restored after re-apply is a problem",
          len(ca.geometry_problems(base, orig)) == 1)
    os.remove(last)
    check("geometry: a missing snapshot file is a problem",
          any("не читается" in p for p in ca.geometry_problems(base, orig)))
    ct.discard_if_green(base, False)


def lookup_and_discard_checks():
    entries = {"preset-*.json": {"reason": "glob"}, "preset-save": {"reason": "exact"}}
    check("lookup: exact key wins over glob", known_diffs.lookup(entries, "preset-save")["reason"] == "exact")
    check("lookup: glob matches", known_diffs.lookup(entries, "preset-Glyph.json")["reason"] == "glob")
    check("lookup: unknown key is None", known_diffs.lookup(entries, "style-x") is None)

    base = tempfile.mkdtemp(prefix="known-diffs-test.")
    open(os.path.join(base, "calls.log"), "w").close()
    ct.discard_if_green(base, True)
    check("discard: a failed run keeps its sandbox", os.path.isdir(base))
    ct.discard_if_green(base, False)
    check("discard: a green run removes its sandbox", not os.path.exists(base))


def main():
    readonly_checks()
    apply_checks()
    geometry_checks()
    lookup_and_discard_checks()
    print("%d checks failed" % len(fails) if fails else "all known_diffs checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
