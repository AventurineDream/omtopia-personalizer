#!/usr/bin/python3 -I
"""Команды, которых нет у bash-эталона (сверять не с чем): wall-delete, launcher-open, Wallpaper FX выкл.

  /usr/bin/python3 -I tests/test_new_commands.py

Песочница: свой HOME в свежем каталоге под $XDG_RUNTIME_DIR, gio / omarchy-* / setsid / hyprctl — заглушки,
пишущие вызовы в лог (gio trash переносит файл в *.trashed; hyprctl отвечает на запрос текущего шейдера,
как при выключенном шейдере). Живой стол не трогается."""
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
    # hyprctl: без композитора crt-toggle.sh падает на стартовом запросе текущего шейдера —
    # заглушка отвечает, как при выключенном шейдере, а остальные вызовы (reload, eval) — no-op.
    with open(os.path.join(stubs, "hyprctl"), "w") as f:
        f.write(f'#!/bin/sh\nprintf "%s\\n" "hyprctl $*" >> "{log}"\n'
                'case "$*" in *"getoption decoration:screen_shader"*) printf \'{"str": "[[EMPTY]]"}\\n\';; esac\n')
    os.chmod(os.path.join(stubs, "hyprctl"), 0o755)
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
          "tweak:readingPage" in values and "reading" in values[3:]
          and values.index("tweak:readingPage") > values.index("reading", 3))
    run(renv, "tweak", "readingBrightness", "+")
    rcfg = os.path.join(home, ".config/omarchy/customizer/reading-mode.json")
    check("reading: tweak writes reading-mode.json", json.load(open(rcfg)).get("readingBrightness") == 45)

    # ── живые обои (owe): шаг настройки собирает ~/.config/owe/config.toml ──
    oenv = dict(renv, PATH=os.path.join(base, "stubs") + ":" + os.environ["PATH"])
    with open(os.path.join(base, "stubs", "owe"), "w") as f:
        f.write(f'#!/bin/sh\nprintf "%s\\n" "owe $*" >> "{log}"\n[ "$1" = status ] && echo \'{{"manual_pause":false}}\'\n')
    os.chmod(os.path.join(base, "stubs", "owe"), 0o755)
    run(oenv, "tweak", "oweBattery", "+")
    toml = open(os.path.join(home, ".config/owe/config.toml")).read()
    check("owe: tweak writes config.toml", 'battery_mode = "pause"' in toml and "fullscreen = true" in toml)
    check("owe: reload-config called", any(c == "owe reload-config" for c in calls(log)))
    _, out = run(oenv, "list", "wallpaper-fx")
    vals = [ln.split("\t")[1] for ln in out.splitlines() if "\t" in ln]
    check("owe: section listed before transitions", "owe-toggle" in vals and vals.index("owe-toggle") < vals.index("section:transitions"))

    # ── themes: частичная копия темы у пользователя не должна прятать системный превью ──
    sys_themes = os.path.join(base, "omarchy/themes")
    user_themes = os.path.join(home, ".config/omarchy/themes")
    os.makedirs(os.path.join(sys_themes, "tokyo-night"))
    os.makedirs(os.path.join(user_themes, "tokyo-night"))
    open(os.path.join(sys_themes, "tokyo-night/preview.png"), "w").write("PNG")
    open(os.path.join(sys_themes, "tokyo-night/colors.toml"), "w").write(
        'background = "#1a1b26"\nforeground = "#c0caf5"\n')
    open(os.path.join(user_themes, "tokyo-night/colors.toml"), "w").write('background = "#000000"\n')
    tenv = dict(env, OMARCHY_PATH=os.path.join(base, "omarchy"))
    _, out = run(tenv, "list", "themes")
    rows = [ln.split("\t") for ln in out.splitlines()]
    tn = [r for r in rows if len(r) > 1 and r[1] == "tokyo-night"]
    check("themes: system preview survives a partial user copy",
          bool(tn) and tn[0][2] == os.path.join(sys_themes, "tokyo-night/preview.png"))
    check("themes: user palette wins when present", bool(tn) and tn[0][4] == "#000000")

        # ── превью: повторный list во время превью не должен затирать backup (Finding #7) ──
    # RUN по умолчанию — живой каталог машины: песочница, иначе тест перезапишет
    # настоящие backup анимаций и скина бара.
    penv = dict(renv, XDG_RUNTIME_DIR=base)
    anim_active = os.path.join(home, ".local/state/omarchy-customizer/animations.lua")
    os.makedirs(os.path.dirname(anim_active), exist_ok=True)
    default_lua = open(os.path.join(PLUGIN, "animations/00-default.lua"), "rb").read()
    open(anim_active, "wb").write(default_lua)
    run(penv, "list", "anims")
    run(penv, "anim-preview", os.path.join(PLUGIN, "animations/01-default - v2.lua"))
    check("preview: anim preview changes the active file",
          open(anim_active, "rb").read() != default_lua)
    run(penv, "list", "anims")   # повторный list во время превью
    run(penv, "anim-restore")
    check("preview: anim restore returns the pre-preview file after a re-list",
          open(anim_active, "rb").read() == default_lua)
    # то же для скина бара
    bar_skin = os.path.join(home, ".config/omarchy/bar-skin.json")
    os.makedirs(os.path.dirname(bar_skin), exist_ok=True)
    open(bar_skin, "w").write('{"skin": "original"}\n')
    other_skin = os.path.join(base, "other-skin.json")
    open(other_skin, "w").write('{"skin": "previewed"}\n')
    run(penv, "list", "bar-skins")
    run(penv, "bar-skins-preview", other_skin)
    check("preview: bar-skin preview changes the active skin",
          json.load(open(bar_skin)).get("skin") == "previewed")
    run(penv, "list", "bar-skins")   # повторный list во время превью
    run(penv, "bar-skins-restore")
    check("preview: bar-skin restore returns the pre-preview skin after a re-list",
          json.load(open(bar_skin)).get("skin") == "original")
# ── rollback: snapshot preserves windows.json geometry (Finding #4) ──
    # Direct import: snapshot() reads paths from os.environ at import time,
    # so this goes last, after the subprocess-based sections.
    win_cfg = os.path.join(home, ".config/omarchy/customizer/windows.json")
    os.makedirs(os.path.dirname(win_cfg), exist_ok=True)
    with open(win_cfg, "w") as f:
        json.dump({"windowGapsIn": 6}, f)
    # the snapshot records theme "default" (no theme.name file): the rollback
    # refuses a backup whose theme is not installed, so make it exist
    os.makedirs(os.path.join(home, ".config/omarchy/themes/default"), exist_ok=True)
    os.environ["HOME"] = home
    sys.path.insert(0, os.path.join(PLUGIN, "backend"))
    from customizer import apply_ops
    backup = os.path.join(home, ".local/state/omarchy-customizer/last-preset.json")
    apply_ops.snapshot(backup, "Previous setup", "test")
    doc = json.load(open(backup))
    check("rollback: snapshot captures windows.json geometry",
          doc.get("windowsGeometry") == {"windowGapsIn": 6} and doc.get("hyprGeometry") is None)
    # simulate a preset apply that changed the geometry, then roll back
    with open(win_cfg, "w") as f:
        json.dump({"windowGapsIn": 2, "windowGapsOut": 8}, f)
    run(env, "apply", "presets", backup)
    check("rollback: windows.json geometry restored verbatim",
          json.load(open(win_cfg)).get("windowGapsIn") == 6)

    # ── регрессия (Iolite, PR #11): restore после внешней смены скина/анимации
    # не должен возвращать устаревший backup ──
    # Скин: A → превью B → restore (A) → внешняя смена на C → превью D → restore (C, не A).
    open(bar_skin, "w").write('{"skin": "A"}\n')
    b_skin = os.path.join(base, "b-skin.json")
    d_skin = os.path.join(base, "d-skin.json")
    open(b_skin, "w").write('{"skin": "B"}\n')
    open(d_skin, "w").write('{"skin": "D"}\n')
    run(penv, "list", "bar-skins")
    run(penv, "bar-skins-preview", b_skin)
    run(penv, "bar-skins-restore")
    check("regression: skin restore after first preview returns A",
          json.load(open(bar_skin)).get("skin") == "A")
    open(bar_skin, "w").write('{"skin": "C"}\n')   # внешняя смена (пресет/тема)
    run(penv, "list", "bar-skins")
    run(penv, "bar-skins-preview", d_skin)
    run(penv, "bar-skins-restore")
    check("regression: skin restore after outside change returns C, not the stale A",
          json.load(open(bar_skin)).get("skin") == "C")
    # Анимации: то же.
    open(anim_active, "wb").write(default_lua)   # A
    b_lua = os.path.join(PLUGIN, "animations/01-default - v2.lua")
    d_lua = os.path.join(base, "d.lua")
    open(d_lua, "wb").write(b"-- d preview\n")
    run(penv, "list", "anims")
    run(penv, "anim-preview", b_lua)
    run(penv, "anim-restore")
    check("regression: anim restore after first preview returns A",
          open(anim_active, "rb").read() == default_lua)
    open(anim_active, "wb").write(b"-- C applied outside\n")   # внешняя смена
    run(penv, "list", "anims")
    run(penv, "anim-preview", d_lua)
    run(penv, "anim-restore")
    check("regression: anim restore after outside change returns C, not the stale A",
          open(anim_active, "rb").read() == b"-- C applied outside\n")

    print(f"{'OK' if not fails else 'FAIL'}; песочница: {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
