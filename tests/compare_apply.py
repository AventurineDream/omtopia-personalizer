#!/usr/bin/python3 -I
"""Сверка `apply` (пресеты, стили, бар, блокировка, лаунчер, темы, обои, Recolor, Dotify, анимации,
шейдеры, прозрачность, блюр, звуки, Glyph, пикер) и thumbs: Python-бэкенд против customizer.sh.

Только песочница (см. compare_tweaks.py). Плагины бара/блокировки/меню подключены симлинками на
настоящие — из них только читаются скины, раскладки, дизайны. Темы — пустые каталоги с нужными
именами и копией colors.toml (не ссылки: Recolor пишет в каталог темы). Порядок строк лога вызовов
не сравнивается (bash запускает часть команд параллельно); случайные имена временных каталогов и
время заменяются заглушками."""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_tweaks as ct  # noqa: E402

REAL = ct.REAL_HOME
PLUGINS = os.path.join(REAL, ".config/omarchy/plugins")
STUBS = ("pw-play", "paplay", "gio", "omarchy-menu", "setsid", "lutgen", "grim", "vipsthumbnail",
         "omarchy-theme-switcher", "omarchy-menu-images", "omarchy-wallpaper-theme", "omarchy-app-themes",
         "omarchy-firefox-chrome")


def theme_names():
    names = {open(os.path.join(REAL, ".local/state/omarchy/current/theme.name")).read().strip()}
    for d in ("presets", "styles"):
        for f in os.listdir(os.path.join(ct.PLUGIN, d)):
            try:
                doc = json.load(open(os.path.join(ct.PLUGIN, d, f)))
            except (OSError, ValueError):
                continue
            th = doc.get("theme")
            if isinstance(th, str):
                names.add(th)
            elif isinstance(th, dict):
                names.update(v for v in th.values() if isinstance(v, str))
    return sorted(n for n in names if n)


def sandbox(base, name):
    root, env = ct.sandbox(base, name)
    home = env["HOME"]
    for cmd in STUBS:
        p = os.path.join(root, "stubs", cmd)
        with open(p, "w") as f:
            f.write(ct.STUB)
        os.chmod(p, 0o755)
    pdir = os.path.join(home, ".config/omarchy/plugins")
    os.makedirs(pdir)
    for n in ("kamradsmeshnyavy.bar", "kamradsmeshnyavy.lock", "kamradsmeshnyavy.menu", "kamradsmeshnyavy.widgets",
              "kamradsmeshnyavy.osd", "kamradsmeshnyavy.notifications", "kamradsmeshnyavy.background",
              "kamradsmeshnyavy.image-picker"):
        if os.path.exists(os.path.join(PLUGINS, n)):
            os.symlink(os.path.realpath(os.path.join(PLUGINS, n)), os.path.join(pdir, n))
    colors = os.path.join(REAL, ".local/state/omarchy/current/theme/colors.toml")
    for n in theme_names():
        d = os.path.join(home, ".config/omarchy/themes", n)
        os.makedirs(os.path.join(d, "backgrounds"), exist_ok=True)
        if os.path.isfile(colors):
            open(os.path.join(d, "colors.toml"), "w").write(open(colors).read())
    for rel in (".config/omarchy/style.json",):
        src = os.path.join(REAL, rel)
        if os.path.isfile(src):
            open(os.path.join(home, rel), "w").write(open(src).read())
    return root, env


def scenarios():
    P = ct.PLUGIN
    presets = sorted(os.path.join(P, "presets", f) for f in os.listdir(os.path.join(P, "presets")) if f.endswith(".json"))
    styles = sorted(os.path.join(P, "styles", f) for f in os.listdir(os.path.join(P, "styles")) if f.endswith(".json"))
    bar = os.path.realpath(os.path.join(PLUGINS, "kamradsmeshnyavy.bar"))
    skins = sorted(os.listdir(os.path.join(bar, "skins")))
    layouts = sorted(os.listdir(os.path.join(bar, "layouts")))
    anims = sorted(os.listdir(os.path.join(P, "animations")))
    bg = os.path.realpath(os.path.join(REAL, ".local/state/omarchy/current/background"))
    out = []
    for f in presets:
        out.append(("preset-" + os.path.basename(f), [["apply", "presets", f],
                                                      ["apply", "presets", "{HOME}/.local/state/omarchy-customizer/last-preset.json"]]))
    user = os.path.join(REAL, ".config/omarchy/customizer/presets")
    for f in sorted(os.listdir(user)) if os.path.isdir(user) else []:
        if f.endswith(".json"):
            out.append(("user-preset-" + f, [["apply", "presets", os.path.join(user, f)]]))
    out.append(("lock-thumbs", [["lock-thumbs", "missing"]]))
    out.append(("preset-save", [["apply", "presets", "save", "Test Preset"], ["apply", "presets", "geometry-reset"]]))
    for f in styles:
        out.append(("style-" + os.path.basename(f), [["apply", "styles", f]]))
    out.append(("style-save", [["apply", "styles", "save", "Test Style"]]))
    out.append(("bar", [["list", "bar-skins"], ["apply", "bar-skins", os.path.join(bar, "skins", skins[0])],
                        ["apply", "bar-skins", "save", "my-test"], ["apply", "bar-layouts", os.path.join(bar, "layouts", layouts[0])],
                        ["apply", "bar-layouts", "save", "my-layout"]]))
    # «apply launcher open» не сверяется: теперь summon с возвратом в Customizer (tests/test_new_commands.py).
    out.append(("small", [["apply", "lock", "classic"], ["apply", "launcher", "skin:board"],
                          ["apply", "wallpaper-fx", "fade"], ["apply", "theme-switcher", "style:cards"],
                          ["apply", "theme-switcher", "cache"], ["apply", "theme-switcher", "prune", "y"],
                          ["apply", "fonts", "stock"], ["apply", "sounds", "pack:glass"], ["apply", "sounds", "test:notify"],
                          ["apply", "glyph", "test:normal"], ["apply", "glyph", "test:critical"], ["apply", "glyph", "test:charge"]]))
    out.append(("hypr", [["apply", "anims", os.path.join(P, "animations", anims[1])], ["apply", "shaders", "toggle"],
                         ["apply", "shaders", "next"], ["apply", "opacity", "solid"], ["apply", "blur", "off"],
                         ["apply", "windows", "geometry-reset"]]))
    out.append(("themes", [["apply", "themes", "nord"], ["apply", "themes", "dynamic:vibrant"], ["apply", "themes", "dynamic:light"],
                           ["apply", "theme-walls", bg]]))
    out.append(("recolor", [["apply", "walls", bg]]))
    out.append(("dotify", [["apply", "dotify", "current"], ["apply", "dotify", "arch"]]))
    out.append(("thumbs", [["thumbs", "themes"], ["thumbs", "lock"]]))
    return out


def norm(snap, root):
    out = {}
    for k, v in snap.items():
        if k.endswith(".tmp"):
            continue   # bash оставляет временные файлы (snapshot: $out.tmp), Python — нет
        v = v.replace(root.encode(), b"<ROOT>")
        v = re.sub(rb"omarchy-lutgen-src\.\w+", b"omarchy-lutgen-src.X", v)
        v = re.sub(rb"lutgen-out-\w+", b"lutgen-out-X", v)          # случайный каталог recolor-wallpapers
        v = re.sub(rb"thumbs/[0-9a-f]{32}", b"thumbs/H", v)           # md5 пути — пути песочниц разные
        v = re.sub(rb"\d{4}-\d\d-\d\d( \d\d:\d\d)?", b"<DATE>", v)
        v = re.sub(rb"\d+ (s|\xd1\x81):", b"N s:", v)
        if k == "calls.log":
            v = b"\n".join(sorted(v.split(b"\n")))
        out[k] = v
    return out


def main():
    base = tempfile.mkdtemp(prefix="customizer-apply.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    only = sys.argv[1:]
    bad = total = 0
    for n, (name, steps) in enumerate(scenarios()):
        if only and not any(o in name for o in only):
            continue
        rb, eb = sandbox(base, f"{n:02}-{name}.bash")
        rp, ep = sandbox(base, f"{n:02}-{name}.py")
        for step in steps:
            zen = ""
            if step[:3] in (["apply", "presets", "save"], ["apply", "styles", "save"], ["apply", "bar-skins", "save"],
                            ["apply", "bar-layouts", "save"], ["apply", "theme-switcher", "prune"]):
                step, zen = step[:3], step[3]
            total += 1
            cb, _ = ct.run(eb, "bash", [s.replace("{HOME}", eb["HOME"]) for s in step], zen)
            cp, _ = ct.run(ep, "py", [s.replace("{HOME}", ep["HOME"]) for s in step], zen)
            sb, sp = norm(ct.snapshot(rb), rb), norm(ct.snapshot(rp), rp)
            if cb != cp or sb != sp:
                bad += 1
                print("DIFF ", name, " ".join(step)[:120], f"code {cb}/{cp}")
                for k in sorted(set(sb) | set(sp)):
                    if sb.get(k) != sp.get(k):
                        a = (sb.get(k) or b"").decode(errors="replace").splitlines()
                        b = (sp.get(k) or b"").decode(errors="replace").splitlines()
                        print("   file:", k, len(a), len(b))
                        for x in sorted(set(a) ^ set(b))[:6]:
                            print("     ", "bash" if x in a else "py  ", x[:160])
                break
        else:
            print("ok   ", name)
    print(f"{total - bad}/{total} шагов совпадают; песочницы: {base}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
