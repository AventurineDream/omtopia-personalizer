#!/usr/bin/python3 -I
"""Сверка превью и мелких команд (opacity/blur/bar-skins/anim preview и restore, lock-preview,
sound-preview, glyph-test, fx-replay, picker-open, launcher-open, theme-fav, *-delete, restore):
Python-бэкенд против customizer.sh, в песочнице (см. compare_tweaks.py). Пути песочниц в логах
вызовов заменяются на <ROOT> — сравнивается сам вызов."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_tweaks as ct  # noqa: E402

EXTRA_STUBS = ("pw-play", "paplay", "gio", "omarchy-menu", "setsid")


def sandbox(base, name):
    root, env = ct.sandbox(base, name)
    for cmd in EXTRA_STUBS:
        p = os.path.join(root, "stubs", cmd)
        with open(p, "w") as f:
            f.write(ct.STUB)
        os.chmod(p, 0o755)
    home = env["HOME"]
    # Свои скин, раскладка, пресет и стиль — чтобы было что удалять.
    for rel, body in ((".config/omarchy/bar-skins/mine.json", '{"note": "my skin", "shape": "pill"}\n'),
                      (".config/omarchy/bar-layouts/mine.json", '{"position": "top", "layout": {}}\n'),
                      (".config/omarchy/customizer/presets/mine.json", '{"name": "Mine", "theme": "x"}\n'),
                      (".config/omarchy/customizer/styles/mine.json", '{"name": "My style"}\n')):
        p = os.path.join(home, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(body)
    return root, env


def scenarios(home):
    skins = os.path.join(ct.REAL_HOME, ".config/omarchy/plugins/kamradsmeshnyavy.bar/skins")
    skin = sorted(os.listdir(skins))[0] if os.path.isdir(skins) else ""
    anims = os.path.join(ct.PLUGIN, "animations")
    anim = os.path.join(anims, sorted(os.listdir(anims))[0])
    return [
        ("opacity", [["opacity-preview", "solid"], ["opacity-restore"]]),
        ("blur", [["blur-preview", "off"], ["blur-restore"]]),
        ("bar-skins", [["list", "bar-skins"], ["bar-skins-preview", os.path.join(skins, skin)],
                       ["bar-skins-preview", "save"], ["bar-skins-restore"]]),
        ("anims", [["list", "anims"], ["anim-preview", anim], ["anim-restore"], ["anim-restore"]]),
        ("misc", [["lock-preview", "classic"], ["sound-preview", "glass", "notify"], ["glyph-test", "true"],
                  ["fx-replay"], ["picker-open"], ["launcher-open"]]),
        ("fav", [["theme-fav", "nord"], ["theme-fav", "nord"], ["theme-fav", "bad slug!"], ["theme-fav", "tokyo-night"]]),
        ("delete-yes", [["skin-delete", "{HOME}/.config/omarchy/bar-skins/mine.json", "y"],
                        ["layout-delete", "{HOME}/.config/omarchy/bar-layouts/mine.json", "y"],
                        ["preset-delete", "{HOME}/.config/omarchy/customizer/presets/mine.json", "y"],
                        ["style-delete", "{HOME}/.config/omarchy/customizer/styles/mine.json", "y"]]),
        ("delete-no", [["skin-delete", "{HOME}/.config/omarchy/bar-skins/mine.json", ""],
                       ["skin-delete", "{HOME}/.config/omarchy/shell.json", "y"],
                       ["preset-delete", "{HOME}/.config/omarchy/customizer/presets/my-settings.json", "y"]]),
        ("restore", [["restore"], ["restore"]]),
    ]


def norm(snap, root):
    return {k: v.replace(root.encode(), b"<ROOT>") for k, v in snap.items()}


def main():
    base = tempfile.mkdtemp(prefix="customizer-commands.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    bad = total = 0
    for n, (name, steps) in enumerate(scenarios(ct.REAL_HOME)):
        rb, eb = sandbox(base, f"{n:02}-{name}.bash")
        rp, ep = sandbox(base, f"{n:02}-{name}.py")
        for step in steps:
            zen = ""
            if step[0].endswith("-delete"):
                step, zen = step[:2], step[2]
            total += 1
            sb_step = [s.replace("{HOME}", eb["HOME"]) for s in step]
            sp_step = [s.replace("{HOME}", ep["HOME"]) for s in step]
            cb, errb = ct.run(eb, "bash", sb_step, zen)
            cp, errp = ct.run(ep, "py", sp_step, zen)
            sb, sp = norm(ct.snapshot(rb), rb), norm(ct.snapshot(rp), rp)
            if cb != cp or sb != sp:
                bad += 1
                print("DIFF ", " ".join(step), f"code {cb}/{cp}")
                for k in sorted(set(sb) | set(sp)):
                    if sb.get(k) != sp.get(k):
                        print("   file:", k)
                        print("     bash:", (sb.get(k) or b"")[-300:].decode(errors="replace"))
                        print("     py  :", (sp.get(k) or b"")[-300:].decode(errors="replace"))
                break
            print("ok   ", " ".join(step))
    print(f"{total - bad}/{total} команд совпадают; песочницы: {base}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
