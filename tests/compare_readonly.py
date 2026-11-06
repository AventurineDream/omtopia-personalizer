#!/usr/bin/python3 -I
"""Сверка перенесённых команд только для чтения: вывод Python-бэкенда == вывод customizer.sh.

  /usr/bin/python3 -I tests/compare_readonly.py

Безопасно на живом столе: list/search-index/lang ничего не меняют. Пока перенос не закончен,
сравнивается с bash (CUSTOMIZER_LEGACY=1); каждая перенесённая команда добавляется сюда."""
import os
import subprocess
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, "backend"))

from customizer import commands, lists  # noqa: E402

def _walls_subdir():
    """Первая подпапка обоев темы — чтобы проверить и вход в категорию (list theme-walls <путь>)."""
    from customizer import state
    root = os.path.join(os.environ["HOME"], ".config/omarchy/backgrounds", state.theme_name())
    try:
        subs = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)) and not n.startswith("."))
    except OSError:
        subs = []
    return subs[:1]


CASES = ([["lang"], ["search-index"], ["status"], ["available"], ["list", "theme-walls"]]
         + [["list", "theme-walls", s] for s in _walls_subdir()]
         + [["list", c] for c in sorted(lists.LISTS)])


def bash(args):
    env = dict(os.environ, CUSTOMIZER_LEGACY="1")
    return subprocess.run(["bash", os.path.join(PLUGIN, "customizer.sh"), *args],
                          capture_output=True, text=True, env=env).stdout


def main():
    bad = 0
    for args in CASES:
        want = bash(args)
        code, got, err = commands.run(args)
        ok = got == want and code == 0
        bad += not ok
        print(("ok    " if ok else "DIFF  ") + " ".join(args))
        if not ok:
            for a, b in zip(want.splitlines(), got.splitlines()):
                if a != b:
                    print("  bash  :", a[:200])
                    print("  python:", b[:200])
                    break
    print(f"{len(CASES) - bad}/{len(CASES)} совпадают")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
