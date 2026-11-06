#!/usr/bin/python3 -I
"""Сверка шагов настроек: `tweak <ключ> +|-|reset|set …` у Python-бэкенда и у customizer.sh.

  /usr/bin/python3 -I tests/compare_tweaks.py [ключ…]

Только в песочнице: две одинаковые копии конфигов в свежем каталоге (mktemp), HOME/XDG_* указывают
туда; omarchy-shell, hyprctl, omarchy-hyprland-toggle, omarchy-font-profile, zenity — заглушки,
которые пишут вызовы в лог. После каждого шага сравниваются все файлы песочниц и логи вызовов.
Живой стол не трогается. Каталоги песочниц не удаляются (лежат в $XDG_RUNTIME_DIR, это tmpfs)."""
import os
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, "backend"))
REAL_HOME = os.environ["HOME"]

from customizer import settings  # noqa: E402

CONFIGS = [
    ".config/omarchy/bar-skin.json", ".config/omarchy/shell.json", ".config/omarchy/lock-design.json",
    ".config/omarchy/widgets.json", ".config/omarchy/osd.json", ".config/omarchy/notify-style.json",
    ".config/omarchy/sounds.json", ".config/omarchy/glyph.json", ".config/omarchy/dotmatrix.json",
    ".config/omarchy/dotify.json", ".config/omarchy/wallpaper-transition.json", ".config/omarchy/image-picker.json",
    ".config/omarchy/extensions/menu-skin.json", ".config/omarchy/customizer.json",
    ".config/omarchy/customizer/windows.json", ".config/omarchy/customizer/preset-apply.json",
    ".config/omarchy/customizer/style-apply.json", ".config/omarchy/customizer/bar-hidden.json",
    ".local/state/omarchy/current/theme/colors.toml", ".local/state/omarchy/current/theme.name",
]

STUB = """#!/bin/bash
echo "$(basename "$0") $*" >>"$STUB_LOG"
case "$(basename "$0") $1" in
  "omarchy-font-profile ") echo stock ;;
  "omarchy-font-profile list") printf 'stock\\tStock\\tbase\\ta\\tb\\tc\\nnothing\\tNothing\\tbase\\ta\\tb\\tc\\ndot\\tDot\\tdotmatrix\\ta\\tb\\tc\\n' ;;
  "zenity "*) [[ -n ${ZENITY_ANSWER:-} ]] && { echo "$ZENITY_ANSWER"; exit 0; }; exit 1 ;;
esac
exit 0
"""


def sandbox(base, name):
    root = os.path.join(base, name)
    home = os.path.join(root, "home")
    for rel in CONFIGS:
        src = os.path.join(REAL_HOME, rel)
        if os.path.isfile(src):
            dst = os.path.join(home, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    stubs = os.path.join(root, "stubs")
    os.makedirs(stubs)
    for cmd in ("omarchy-shell", "hyprctl", "omarchy-hyprland-toggle", "omarchy-font-profile", "zenity", "notify-send", "omarchy"):
        p = os.path.join(stubs, cmd)
        with open(p, "w") as f:
            f.write(STUB)
        os.chmod(p, 0o755)
    for d in ("state", "cache", "run"):
        os.makedirs(os.path.join(root, d))
    env = dict(os.environ, HOME=home, XDG_STATE_HOME=os.path.join(home, ".local/state"),
               XDG_CACHE_HOME=os.path.join(root, "cache"), XDG_RUNTIME_DIR=os.path.join(root, "run"),
               PATH=stubs + ":" + os.environ["PATH"], STUB_LOG=os.path.join(root, "calls.log"))
    open(env["STUB_LOG"], "w").close()
    return root, env


def snapshot(root):
    out = {}
    for d, _, files in os.walk(os.path.join(root, "home")):
        for f in files:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = open(p, "rb").read()
    out["calls.log"] = open(os.path.join(root, "calls.log"), "rb").read()
    return out


def run(env, impl, args, zenity=""):
    e = dict(env, ZENITY_ANSWER=zenity)
    if impl == "bash":
        e["CUSTOMIZER_LEGACY"] = "1"
        cmd = ["bash", os.path.join(PLUGIN, "customizer.sh"), *args]
    else:
        cmd = ["/usr/bin/python3", "-I", os.path.join(PLUGIN, "backend/run.py"), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, env=e)
    return p.returncode, p.stderr.strip()


def scenarios(keys):
    out = []
    for tbl in settings.tables().values():
        for it in tbl.items:
            if it.is_section or (keys and it.key not in keys) or keys == ["widgets"]:
                continue
            steps = [["tweak", it.key, "+"], ["tweak", it.key, "+"], ["tweak", it.key, "-"], ["tweak", it.key, "reset"]]
            if it.type == "num":
                mid = it.min + (it.max - it.min) / 2
                steps += [["tweak", it.key, "set", f"{mid:g}"], ["tweak", it.key, "set", "abc"],
                          ["tweak", it.key, "set", str(it.max + 1)]]
            elif it.type == "enum":
                steps += [["tweak", it.key, "set", it.values[-1]], ["tweak", it.key, "set", "nope"]]
            elif it.type == "bool":
                steps += [["tweak", it.key, "set", "on"], ["tweak", it.key, "set", "maybe"]]
            elif it.type == "color":
                steps += [["tweak", it.key, "set", "#123456"], ["tweak", it.key, "set", "accent"],
                          ["tweak", it.key, "set", "bogus"], ["tweak", it.key, "pick", "rgb(10,20,30)"]]
            elif it.type in ("text", "dir"):
                steps += [["tweak", it.key, "set", "hello" if it.type == "text" else "~"], ["tweak", it.key, "set", ""]]
            out.append((it.key, steps))
    if not keys or keys == ["widgets"]:
        import json
        lay = (json.load(open(os.path.join(REAL_HOME, ".config/omarchy/shell.json"))).get("bar") or {}).get("layout") or {}
        ids = [e["id"] if isinstance(e, dict) else e for s in ("left", "center", "right") for e in (lay.get(s) or [])]
        for wid in ids[:1] + ids[-1:]:
            out.append(("w-" + wid, [["tweak", "w:" + wid, "+"], ["tweak", "w:" + wid, "-"], ["tweak", "w:" + wid, "toggle"],
                                     ["tweak", "w:" + wid, "toggle"], ["tweak", "w:" + wid, "set"]]))
        if keys:
            return out
    if not keys:
        out.append(("fontProfile", [["tweak", "fontProfile", "+"], ["tweak", "fontProfile", "reset"]]))
        out.append(("wset", [["tweak", "wset:kamradsmeshnyavy.tray:collapse", "+"]]))
        out.append(("unknown", [["tweak", "noSuchKey", "+"], ["tweak", "noSuchKey", "set", "1"]]))
    return out


def main():
    keys = sys.argv[1:]
    base = tempfile.mkdtemp(prefix="customizer-tweaks.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    bad = total = 0
    for n, (name, steps) in enumerate(scenarios(keys)):
        rb, eb = sandbox(base, f"{n:03}-{name}.bash")
        rp, ep = sandbox(base, f"{n:03}-{name}.py")
        for step in steps:
            zen = ""
            if step[2] == "pick":
                zen, step = step[3], step[:3]
            total += 1
            cb, errb = run(eb, "bash", step, zen)
            cp, errp = run(ep, "py", step, zen)
            sb, sp = snapshot(rb), snapshot(rp)
            if (cb, errb) != (cp, errp) or sb != sp:
                bad += 1
                print("DIFF ", " ".join(step), f"code {cb}/{cp}")
                if errb != errp:
                    print("   stderr bash:", errb[:150], "| py:", errp[:150])
                for k in sorted(set(sb) | set(sp)):
                    if sb.get(k) != sp.get(k):
                        print("   file:", k)
                        a, b = (sb.get(k) or b"").decode(errors="replace"), (sp.get(k) or b"").decode(errors="replace")
                        for la, lb in zip(a.splitlines(), b.splitlines()):
                            if la != lb:
                                print("     bash:", la[:120])
                                print("     py  :", lb[:120])
                                break
                        else:
                            print("     длина", len(a), len(b))
                break
    print(f"{total - bad}/{total} шагов совпадают; песочницы: {base}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
