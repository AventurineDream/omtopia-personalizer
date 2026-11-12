#!/usr/bin/python3 -I
"""Команды, которых нет у bash-эталона (сверять не с чем): wall-delete, launcher-open, Wallpaper FX выкл.

  /usr/bin/python3 -I tests/test_new_commands.py

Песочница: свой HOME в свежем каталоге под $XDG_RUNTIME_DIR, gio / omarchy-* / setsid — заглушки,
пишущие вызовы в лог (gio trash переносит файл в *.trashed). Живой стол не трогается."""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")


def sandbox():
    base = tempfile.mkdtemp(prefix="customizer-new.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs, log = (os.path.join(base, n) for n in ("home", "stubs", "calls.log"))
    os.makedirs(stubs)
    for name in ("gio", "omarchy-theme-bg-next", "notify-send", "setsid", "omarchy",
                 "omarchy-launch-floating-terminal-with-presentation"):
        extra = '[ "$1" = trash ] && mv "$2" "$2.trashed"\n' if name == "gio" else ""
        with open(os.path.join(stubs, name), "w") as f:
            f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\n{extra}')
        os.chmod(os.path.join(stubs, name), 0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"])
    env.pop("XDG_CONFIG_HOME", None)
    return base, home, log, env


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def calls(log):
    try:
        return open(log).read().splitlines()
    except FileNotFoundError:
        return []


def main():
    base, home, log, env = sandbox()
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    # ── wall-delete ──
    own_dir = os.path.join(home, ".config/omarchy/backgrounds/demo/sub")
    theme_dir = os.path.join(home, ".config/omarchy/themes/demo/backgrounds")
    stock_dir = os.path.join(home, ".local/state/omarchy/current/theme/backgrounds")
    for d in (own_dir, theme_dir, stock_dir):
        os.makedirs(d)
    f = {"own": os.path.join(own_dir, "own.png"), "theme": os.path.join(theme_dir, "theme.jpg"),
         "stock": os.path.join(stock_dir, "stock.png"), "cur": os.path.join(own_dir, "cur.webp"),
         "txt": os.path.join(own_dir, "notes.txt")}
    for p in f.values():
        open(p, "wb").write(b"x")
    os.symlink(f["cur"], os.path.join(home, ".local/state/omarchy/current/background"))
    fav = os.path.join(home, ".config/omarchy/customizer/favorite-wallpapers.json")
    os.makedirs(os.path.dirname(fav))
    json.dump([f["own"], f["stock"]], open(fav, "w"))

    check("own wallpaper → trash", run(env, "wall-delete", f["own"])[0] == 0 and os.path.exists(f["own"] + ".trashed"))
    check("favorite removed", json.load(open(fav)) == [f["stock"]])
    check("theme wallpaper → trash", run(env, "wall-delete", f["theme"])[0] == 0 and not os.path.exists(f["theme"]))
    check("stock copy refused", run(env, "wall-delete", f["stock"])[0] == 1 and os.path.exists(f["stock"]))
    check("non-image refused", run(env, "wall-delete", f["txt"])[0] == 1 and os.path.exists(f["txt"]))
    check("missing file refused", run(env, "wall-delete", f["own"])[0] == 1)
    n = len(calls(log))
    check("current wallpaper: next first, then trash",
          run(env, "wall-delete", f["cur"])[0] == 0 and calls(log)[n:] == ["omarchy-theme-bg-next ", f"gio trash {f['cur']}"])

    # ── launcher-open ──
    def last_payload():
        line = calls(log)[-1]
        prefix = "setsid -f omarchy-shell shell summon omarchy.menu "
        return json.loads(line[len(prefix):]) if line.startswith(prefix) else None

    run(env, "launcher-open")
    check("launcher-open: root, no return", last_payload() == {"menu": "root"})
    run(env, "launcher-open", "aurora", "skin:aurora")
    p = last_payload() or {}
    check("launcher-open skin + return to row",
          p.get("skin") == "aurora" and json.loads(p.get("returnTo", "{}")) == {"category": "launcher", "value": "skin:aurora"})
    run(env, "launcher-open", "", "home")
    p = last_payload() or {}
    check("launcher-open from home returns to {}", "skin" not in p and json.loads(p.get("returnTo", "null")) == {})
    run(env, "apply", "launcher", "open")
    p = last_payload() or {}
    check("apply launcher open returns to its row", json.loads(p.get("returnTo", "{}")).get("value") == "open")

    # ── Wallpaper FX выключен в shell.json → первая строка «включить», ⏎ — omarchy plugin enable ──
    first = run(env, "list", "wallpaper-fx")[1].split("\n")[0].split("\t")
    check("fx off: enable row first", len(first) > 1 and first[1] == "enable-plugin")
    run(env, "apply", "wallpaper-fx", "enable-plugin")
    check("fx off: enable-plugin calls omarchy plugin enable",
          "omarchy plugin enable kamradsmeshnyavy.background" in calls(log))
    shell = os.path.join(home, ".config/omarchy/shell.json")
    with open(shell, "w") as fh:
        json.dump({"plugins": [{"id": "kamradsmeshnyavy.background"}]}, fh)
    first = run(env, "list", "wallpaper-fx")[1].split("\n")[0].split("\t")
    check("fx on: no enable row", len(first) > 1 and first[1] != "enable-plugin")

    # ── outline: без venv — строка установки, с ним — вырезка; оба эффекта в списке ──
    rows = [r.split("\t") for r in run(env, "list", "wallpaper-fx")[1].split("\n")]
    values = [r[1] for r in rows if len(r) > 1]
    check("fx: contagion and outline listed", "contagion" in values and "outline" in values)
    check("fx: no venv → install row", "outline-install" in values and "outline-warm" not in values)
    venv_py = os.path.join(home, ".local/share/wallpaper-fx/venv/bin/python")
    os.makedirs(os.path.dirname(venv_py))
    open(venv_py, "w").close()
    values = [r.split("\t")[1] for r in run(env, "list", "wallpaper-fx")[1].split("\n") if "\t" in r]
    check("fx: venv → warm row", "outline-warm" in values and "outline-install" not in values)
    order = [r.split("\t")[1] for r in run(env, "list", "wallpaper-fx")[1].split("\n") if "\t" in r]
    check("fx: actions sit under their own header, after the transitions",
          "section:actions" in order and order.index("section:actions") < order.index("outline-warm")
          and order.index("section:transitions") < order.index("outline") < order.index("section:actions"))
    n = len(calls(log))
    run(env, "apply", "wallpaper-fx", "outline-install")
    check("fx: outline-install opens a terminal with install && warm",
          any("omarchy-launch-floating-terminal-with-presentation" in c and "install &&" in c for c in calls(log)[n:]))
    import time
    t0 = time.time()
    try:
        subprocess.run(["/usr/bin/python3", "-I", RUN, "apply", "wallpaper-fx", "outline-warm"], env=env,
                       capture_output=True, text=True, timeout=5)
        quick = time.time() - t0 < 5
    except subprocess.TimeoutExpired:
        quick = False
    check("fx: outline-warm returns at once (does not wait for the cut-out)", quick)
    cfg = os.path.join(home, ".config/omarchy/wallpaper-transition.json")
    check("fx: outline-install does not become the effect type",
          not os.path.exists(cfg) or json.load(open(cfg)).get("type") != "outline-install")

    # ── режим чтения: строка-действие и настройки во вкладке «Шейдер» ──
    renv = dict(env)
    renv.pop("XDG_STATE_HOME", None)   # состояние — только из песочницы
    _, out = run(renv, "list", "shaders")
    rows = [ln.split("\t") for ln in out.splitlines()]
    values = [r[1] for r in rows if len(r) > 1]
    check("reading: action row after toggle/next", values[:3] == ["toggle", "next", "reading"])
    check("reading: settings listed after the shaders",
          "tweak:readingPage" in values and values.index("tweak:readingPage") > values.index("reading", 3))
    run(renv, "tweak", "readingBrightness", "+")
    rcfg = os.path.join(home, ".config/omarchy/customizer/reading-mode.json")
    check("reading: tweak writes reading-mode.json", json.load(open(rcfg)).get("readingBrightness") == 45)

    print(f"{'OK' if not fails else 'FAIL'}; песочница: {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
