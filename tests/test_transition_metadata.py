#!/usr/bin/python3 -I
"""Контракт метаданных Wallpaper FX (issue #3): каталог → сгенерированный JS.

  /usr/bin/python3 -I tests/test_transition_metadata.py

Каталог backend/customizer/fx_catalog.py — единственный источник; ui/RandomCandidates.js
генерируется из него scripts/gen_random_candidates.py. Проверки: lists.py берёт строки из
каталога; JS свеж (без рассинхрона); каждый random-пригодный переход представлен в JS;
«none» и разовые действия вне случайного выбора; неизвестные значения не пригодны.
Новый переход в каталоге без перегенерации роняет этот тест.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, "backend"))
sys.path.insert(0, os.path.join(PLUGIN, "scripts"))

from customizer import lists  # noqa: E402
from customizer.fx_catalog import FX_EFFECTS, FX_RANDOM_EXCLUDED, FX_RANDOM_OK  # noqa: E402
import gen_random_candidates  # noqa: E402

JS = os.path.join(PLUGIN, "ui", "RandomCandidates.js")

ACTIONS = ("outline-install", "outline-warm", "owe-toggle", "enable-plugin",
           "toggle", "next", "save", "cache", "prune", "open", "current", "arch")


def js_transition_keys(text):
    """Ключи блока WALLPAPER_FX_TRANSITIONS из сгенерированного JS."""
    m = re.search(r"var WALLPAPER_FX_TRANSITIONS = \{(.*?)\n\};", text, re.S)
    assert m, "transition block missing from RandomCandidates.js"
    return set(re.findall(r'^\s*"?([A-Za-z0-9_-]+)"?: true,$', m.group(1), re.M))


def main():
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    text = open(JS, encoding="utf-8").read()
    keys = js_transition_keys(text)

    check("lists.py rows derive from the catalog",
          lists._FX_EFFECTS == [(v, d) for v, d, _ok in FX_EFFECTS])
    check("RandomCandidates.js is fresh (no drift)",
          gen_random_candidates.render() == text)
    check("every random-eligible catalog transition is in the JS map",
          keys == set(FX_RANDOM_OK))
    check("none is a catalog value but stays out of random selection",
          "none" in [v for v, _d, _ok in FX_EFFECTS]
          and "none" in FX_RANDOM_EXCLUDED and "none" not in keys)
    check("one-off actions are not transitions in the JS map",
          all(a not in keys for a in ACTIONS))
    check("unknown values are not in the JS map", "supernova" not in keys)

    # Backend metadata ↔ live list rows: every catalog value is emitted by `list wallpaper-fx`.
    home = tempfile.mkdtemp(prefix="fx-catalog.")
    env = dict(os.environ, HOME=home)
    r = subprocess.run(["/usr/bin/python3", "-I", os.path.join(PLUGIN, "backend/run.py"),
                        "list", "wallpaper-fx"], env=env, capture_output=True, text=True)
    values = [ln.split("\t")[1] for ln in r.stdout.splitlines() if "\t" in ln]
    check("list wallpaper-fx emits every catalog transition",
          r.returncode == 0 and all(v in values for v, _d, _ok in FX_EFFECTS))
    os.makedirs(os.path.join(home, ".config/omarchy"), exist_ok=True)
    with open(os.path.join(home, ".config/omarchy/wallpaper-transition.json"), "w") as fh:
        json.dump({"type": "outline-cut"}, fh)
    r = subprocess.run(["/usr/bin/python3", "-I", os.path.join(PLUGIN, "backend/run.py"),
                        "list", "wallpaper-fx"], env=env, capture_output=True, text=True)
    cur = [ln.split("\t")[1] for ln in r.stdout.splitlines()
           if "\t" in ln and ln.split("\t")[3:4] == ["1"]]
    check("current transition is flagged from wallpaper-transition.json", cur == ["outline-cut"])

    print("%d checks failed" % len(fails) if fails else "all metadata checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
