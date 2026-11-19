#!/usr/bin/python3 -I
"""Сверка перенесённых команд только для чтения: вывод Python-бэкенда == вывод customizer.sh.

  /usr/bin/python3 -I tests/compare_readonly.py

Безопасно на живом столе: list/search-index/lang ничего не меняют. Пока перенос не закончен,
сравнивается с bash (CUSTOMIZER_LEGACY=1); каждая перенесённая команда добавляется сюда.

`list wallpaper-fx` зависит от состояния хоста (FX-плагин в shell.json, установлен ли owe), поэтому
идёт в песочнице (см. FX_CASES): свой HOME с фиксированным shell.json и заглушка owe первой в PATH.
Оба состояния плагина проверяются с обязательными маркерами, без необязательных строк."""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, "backend"))
sys.path.insert(0, os.path.join(PLUGIN, "tests"))

from customizer import commands, lists, state  # noqa: E402
import compare_tweaks as ct  # noqa: E402
import known_diffs  # noqa: E402

FX_ARGS = ["list", "wallpaper-fx"]
# (ключ allowlist, включён ли FX-плагин в shell.json). owe в PATH есть в обоих случаях.
FX_CASES = [("list wallpaper-fx", True), ("list wallpaper-fx (fx off)", False)]


def _walls_subdir():
    """Первая подпапка обоев темы — чтобы проверить и вход в категорию (list theme-walls <путь>)."""
    root = os.path.join(os.environ["HOME"], ".config/omarchy/backgrounds", state.theme_name())
    try:
        subs = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)) and not n.startswith("."))
    except OSError:
        subs = []
    return subs[:1]


CASES = ([["lang"], ["search-index"], ["status"], ["available"], ["list", "theme-walls"]]
         + [["list", "theme-walls", s] for s in _walls_subdir()]
         + [["list", c] for c in sorted(lists.LISTS)])


def fx_sandbox(base, name, fx_on):
    """Окружение песочницы для list wallpaper-fx: shell.json с FX-плагином (fx_on) или без него,
    заглушка owe первой в PATH — строки owe у обоих состояний одинаковы, живой owe не влияет."""
    root = os.path.join(base, name)
    home = os.path.join(root, "home")
    stubs = os.path.join(root, "stubs")
    os.makedirs(os.path.join(home, ".config/omarchy"))
    os.makedirs(stubs)
    with open(os.path.join(home, ".config/omarchy/shell.json"), "w") as f:
        json.dump({"plugins": [{"id": lists.FX_PLUGIN}] if fx_on else []}, f)
    owe = os.path.join(stubs, "owe")
    with open(owe, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(owe, 0o755)
    for d in ("state", "cache", "run"):
        os.makedirs(os.path.join(root, d))
    env = dict(os.environ, HOME=home, XDG_STATE_HOME=os.path.join(home, ".local/state"),
               XDG_CACHE_HOME=os.path.join(root, "cache"), XDG_RUNTIME_DIR=os.path.join(root, "run"),
               PATH=stubs + ":" + os.environ["PATH"])
    env.pop("XDG_CONFIG_HOME", None)
    return env


def bash(args, env=None):
    """stdout customizer.sh (bash-эталон) для аргументов; env — окружение песочницы или живое."""
    env = dict(env or os.environ, CUSTOMIZER_LEGACY="1")
    return subprocess.run(["bash", os.path.join(PLUGIN, "tests/legacy/customizer.sh"), *args],
                          capture_output=True, text=True, env=env).stdout


def python_sandboxed(args, env):
    """(код, stdout) backend/run.py в окружении песочницы — тот же вывод, что commands.run."""
    p = subprocess.run(["/usr/bin/python3", "-I", os.path.join(PLUGIN, "backend/run.py"), *args],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def main():
    entries = known_diffs.load()["compare_readonly"]
    favs = os.path.join(os.environ["HOME"], ".config/omarchy/customizer/favorite-wallpapers.json")
    try:
        has_favs = bool(json.load(open(favs)))
    except (OSError, ValueError):
        has_favs = False
    base = tempfile.mkdtemp(prefix="customizer-readonly.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    skipped = []
    results = []   # (ключ allowlist, ожидаемый bash-вывод, код python, вывод python)
    for args in CASES:
        if args == FX_ARGS:
            continue
        if has_favs and args[:2] == ["list", "theme-walls"]:
            skipped.append(" ".join(args))
            continue
        code, got, _ = commands.run(args)
        results.append((" ".join(args), bash(args), code, got))
    for n, (key, fx_on) in enumerate(FX_CASES):
        env = fx_sandbox(base, f"fx-{n}", fx_on)
        code, got = python_sandboxed(FX_ARGS, env)
        results.append((key, bash(FX_ARGS, env), code, got))
    for key in skipped:
        print("skip  " + key + "  (избранные обои — новое, у bash их нет)")

    bad = known = 0
    for key, want, code, got in results:
        if got == want and code == 0:
            print("ok    " + key)
            continue
        entry = known_diffs.lookup(entries, key)
        if entry is not None and known_diffs.matches_readonly(entry, want, got):
            known += 1
            print("KNOWN " + key + "  (" + entry["reason"] + ")")
        elif entry is not None:
            bad += 1
            print("KNOWN-CHANGED " + key
                  + "  (запись в allowlist больше не совпадает — обновить её или разобраться)")
        else:
            bad += 1
            print("DIFF  " + key)
        for a, b in zip(want.splitlines(), got.splitlines()):
            if a != b:
                print("  bash  :", a[:200])
                print("  python:", b[:200])
                break
    total = len(results)
    print(f"{total - bad - known}/{total} совпадают"
          + (f", {known} известных" if known else ""))
    if bad:
        print("песочницы сохранены: " + base)
    ct.discard_if_green(base, bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
