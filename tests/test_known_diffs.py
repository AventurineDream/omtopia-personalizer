#!/usr/bin/python3 -I
"""Контракт сверки allowlist (tests/known_diffs.py) — без запуска bash и бэкенда.

  /usr/bin/python3 -I tests/test_known_diffs.py

Сверка известных расхождений должна быть строгой: лишняя bash-строка, пропавший обязательный
маркер или чужая строка Python роняют запись (KNOWN-CHANGED), а маркер из "optional" может
отсутствовать (строка зависит от состояния хоста), но не извиняет чужую строку.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_tweaks as ct  # noqa: E402
import known_diffs  # noqa: E402

fails = []


def check(name, cond):
    print(("ok    " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


RO = {"expect": ["section:", "outline"], "optional": ["enable-plugin"]}
BASH = "Duration, ms: 420\ttweak:duration\nTransitions\tsection:transitions"
PY_FULL = "Settings\tsection:settings\n" + BASH + "\nenable-plugin row\tenable-plugin\noutline\toutline"


def main():
    check("readonly: matching output with optional row present",
          known_diffs.matches_readonly(RO, BASH, PY_FULL))
    check("readonly: optional marker may be absent",
          known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("enable-plugin row\tenable-plugin\n", "")))
    check("readonly: missing required marker fails",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("outline\toutline", "")))
    check("readonly: bash-only line fails",
          not known_diffs.matches_readonly(RO, BASH + "\nLost row\ttweak:lost", PY_FULL))
    check("readonly: extra python row without any marker fails",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL + "\nstray row"))
    check("readonly: a python line that changes a bash value is not covered",
          not known_diffs.matches_readonly(RO, BASH, PY_FULL.replace("Duration, ms: 420", "Duration, ms: 500")))

    apply_variant = {"code": [0, 0], "files": ["last-preset.json"], "expect": "\"windowsGeometry\"",
                     "expect_all": ["\"windowGapsIn\":", "\"windowsGeometry\""]}
    ok_lines = ['"windowGapsIn": 6,', '"windowsGeometry": {']
    check("apply: allowed py-only lines match",
          known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines, []))
    check("apply: structural lines are ignored",
          known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines + ["}", "  },"], []))
    check("apply: py-only key outside expect_all fails (stale signature)",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"],
                                        ok_lines + ['"windowBorder": 1,'], []))
    check("apply: bash-only line fails",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json"], ok_lines, ["x"]))
    check("apply: unexpected differing file fails",
          not known_diffs.matches_apply(apply_variant, 0, 0, ["last-preset.json", "calls.log"], ok_lines, []))
    check("readonly: extra row carrying only an optional marker is allowed",
          known_diffs.matches_readonly(dict(RO, optional=["enable-plugin", "owe-toggle"]), BASH,
                                       PY_FULL + "\nowe row\towe-toggle"))
    check("apply: exit code change fails",
          not known_diffs.matches_apply(apply_variant, 0, 1, ["last-preset.json"], ok_lines, []))
    variants = {"variants": [apply_variant, dict(apply_variant, files=["windows.json"])]}
    check("apply: any of several variants matches",
          known_diffs.matches_apply(variants, 0, 0, ["windows.json"], ok_lines, []))

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

    print("%d checks failed" % len(fails) if fails else "all known_diffs checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
