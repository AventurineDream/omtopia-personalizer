#!/usr/bin/python3 -I
"""Save and delete without zenity (see ui/InWindow.js): the overlay's in-window forms open no dialog, and
the zenity-only forms refuse with "zenity is not installed" instead of closing silently.

  /usr/bin/python3 -I tests/test_no_zenity.py

Sandbox: HOME, XDG_* and OMARCHY_PATH point into a fresh directory under XDG_RUNTIME_DIR. PATH is a
symlink farm of the real PATH without a zenity binary, so a zenity call fails as it does on a machine
without zenity. Desktop commands (omarchy*, hypr*, gio, notify-send, setsid, ...) are logging stubs, so
the live desktop is never touched. Exit 0 when every check passes; the sandbox is kept on failure."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")

# Commands that act on the desktop or send notifications: logging stubs, never the real binaries.
STUBBED = {"gio", "notify-send", "setsid", "hyprctl", "pkill", "killall", "systemctl", "makoctl", "owe", "xdg-open"}
STUB_PREFIXES = ("omarchy", "hypr")
# gio trash moves the file aside so the test can see it went; hyprctl answers the shader query the way a
# machine without a shader does (crt-toggle.sh stops at that query otherwise).
STUB_BODY = {
    "gio": '[ "$1" = trash ] && mv "$2" "$2.trashed"\n',
    "hyprctl": 'case "$*" in *"getoption decoration:screen_shader"*) printf \'{"str": "[[EMPTY]]"}\\n\';; esac\n',
}


def write_stub(path, name, log):
    with open(path, "w") as f:
        f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{log}"\n' + STUB_BODY.get(name, ""))
    os.chmod(path, 0o755)


def sandbox():
    base = tempfile.mkdtemp(prefix="customizer-nozenity.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs, farm, log = (os.path.join(base, n) for n in ("home", "stubs", "farm", "calls.log"))
    for d in (home, stubs, farm, os.path.join(base, "omarchy")):
        os.makedirs(d)
    seen = set()
    for name in STUBBED:
        write_stub(os.path.join(stubs, name), name, log)
        seen.add(name)
    for d in os.environ.get("PATH", "").split(":"):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            if name in seen or name == "zenity":
                continue
            seen.add(name)
            if name.startswith(STUB_PREFIXES):
                write_stub(os.path.join(stubs, name), name, log)
                continue
            try:
                os.symlink(os.path.join(d, name), os.path.join(farm, name))
            except OSError:
                pass
    env = {
        "PATH": stubs + ":" + farm,
        "HOME": home,
        "LC_ALL": "C",   # i18n.lang reads LC_ALL first: English messages for the assertions
        "XDG_STATE_HOME": os.path.join(home, ".local/state"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "XDG_RUNTIME_DIR": base,
        "OMARCHY_PATH": os.path.join(base, "omarchy"),
    }
    return base, home, env


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def touch_json(path, data="{}"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(data)
    return path


def main():
    base, home, env = sandbox()
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    cfg = os.path.join(home, ".config/omarchy")
    presets = os.path.join(cfg, "customizer/presets")
    styles = os.path.join(cfg, "customizer/styles")
    skins = os.path.join(cfg, "bar-skins")
    layouts = os.path.join(cfg, "bar-layouts")
    own = {
        "preset": touch_json(os.path.join(presets, "mine.json")),
        "style": touch_json(os.path.join(styles, "mine.json")),
        "skin": touch_json(os.path.join(skins, "mine.json")),
        "layout": touch_json(os.path.join(layouts, "mine.json")),
    }
    settings = touch_json(os.path.join(presets, "my-settings.json"))
    outside = touch_json(os.path.join(home, "Downloads/shared.json"))
    touch_json(os.path.join(cfg, "shell.json"),
               json.dumps({"bar": {"position": "top", "centerAnchor": "center", "layout": "default"}}))

    # ── deletes with --yes: the overlay has asked already, so no dialog and the trash is the only effect ──
    refusals = {"preset": "Only your own presets (★) can be deleted", "style": "Only your own styles (★) can be deleted",
                "skin": "Only your own skins (★) can be deleted", "layout": "Only your own layouts (★) can be deleted"}
    commands = {"preset": "preset-delete", "style": "style-delete", "skin": "skin-delete", "layout": "layout-delete"}
    for kind, cmd in commands.items():
        code, out, err = run(env, cmd, own[kind], "--yes")
        check(f"{cmd} --yes trashes an own {kind} without a dialog",
              code == 0 and not os.path.exists(own[kind]) and os.path.exists(own[kind] + ".trashed"))
        code, out, err = run(env, cmd, outside, "--yes")
        check(f"{cmd} --yes refuses a file outside the user folder",
              code == 1 and refusals[kind] in out + err and os.path.exists(outside))
    code, out, err = run(env, "preset-delete", settings, "--yes")
    check("preset-delete --yes refuses my-settings.json even inside the user folder",
          code == 1 and refusals["preset"] in out + err and os.path.exists(settings))

    # Without --yes (CLI form) the question is zenity's; with zenity missing the reason comes back and the file stays.
    keep = touch_json(os.path.join(skins, "keep.json"))
    code, out, err = run(env, "skin-delete", keep)
    check("skin-delete without --yes and without zenity fails with the reason and keeps the file",
          code == 1 and "zenity is not installed" in out + err and os.path.exists(keep))

    # ── in-window saves: apply <category> save --name <name> [--overwrite] ──
    code, out, err = run(env, "apply", "presets", "save", "--name", "My Test")
    check("apply presets save --name writes my-test.json and prints its path",
          code == 0 and out == os.path.join(presets, "my-test.json") and os.path.isfile(out))
    code, out, err = run(env, "apply", "presets", "save", "--name", "My Test")
    check("a taken preset name exits 3 with the reason", code == 3 and "Preset my-test already exists" in err)
    code, out, err = run(env, "apply", "presets", "save", "--name", "My Test", "--overwrite")
    check("--overwrite replaces the taken preset", code == 0 and os.path.isfile(os.path.join(presets, "my-test.json")))
    code, out, err = run(env, "apply", "presets", "save", "--name", "   ")
    check("an empty preset name exits 1 with the reason", code == 1 and "Enter a name" in err)

    code, out, err = run(env, "apply", "styles", "save", "--name", "Soft")
    check("apply styles save --name writes soft.json", code == 0 and out == os.path.join(styles, "soft.json"))

    code, out, err = run(env, "apply", "bar-skins", "save", "--name", "my skin")
    check("a skin name with a space is refused in the field", code == 1 and "Use latin letters, digits, - and _ only" in err)
    code, out, err = run(env, "apply", "bar-skins", "save", "--name", "Night_1")
    check("a skin name is lower-cased into the file name", code == 0 and out == os.path.join(skins, "night_1.json"))
    code, out, err = run(env, "apply", "bar-skins", "save", "--name", "night_1")
    check("a taken skin name exits 3", code == 3 and "Skin night_1 already exists" in err)

    code, out, err = run(env, "apply", "bar-layouts", "save", "--name", "left-bar")
    check("apply bar-layouts save --name writes left-bar.json",
          code == 0 and out == os.path.join(layouts, "left-bar.json") and os.path.isfile(out))
    code, out, err = run(env, "apply", "bar-layouts", "save", "--name", "bad/name")
    check("a layout name with a slash is refused", code == 1 and "Use latin letters, digits, - and _ only" in err)

    # ── names: latin letters, digits, spaces, - and _; the file name is the slug, and a refusal writes nothing ──
    code, out, err = run(env, "apply", "presets", "save", "--name", "../../escape")
    stray = [n for _, _, names in os.walk(home) for n in names if n.startswith("escape")]
    check("a preset name with ../ is refused and writes no file",
          code == 1 and "Use latin letters, digits, - and _ only" in err and not stray)
    code, out, err = run(env, "apply", "styles", "save", "--name", "Работа")
    timestamped = [n for n in os.listdir(styles) if n.startswith("style-")]
    check("a style name with no latin letters is refused, not saved under a timestamp",
          code == 1 and "Use latin letters, digits, - and _ only" in err and not timestamped)
    code, out, err = run(env, "apply", "styles", "save", "--name", "Soft Test")
    check("a style name with a space is saved as soft-test.json",
          code == 0 and out == os.path.join(styles, "soft-test.json"))

    # ── flags: each apply takes only the options its save or prune uses ──
    code, out, err = run(env, "apply", "presets", "save", "--name", "x", "--yes")
    check("a save takes no --yes: exit 2 with the option named", code == 2 and "Unknown option: --yes" in err)
    code, out, err = run(env, "apply", "walls", "pick-dir", "--name", "y")
    check("walls pick-dir takes no --name: exit 2 with the option named", code == 2 and "Unknown option: --name" in err)
    code, out, err = run(env, "apply", "theme-switcher", "prune", "--name", "y")
    check("prune takes --yes and --dry-run only: exit 2 with the option named", code == 2 and "Unknown option: --name" in err)

    # ── the Bar Layout 💾 row is a layout save row ──
    code, out, err = run(env, "list", "bar-layouts")
    check("the Bar Layout 💾 row says layout",
          out.split("\n")[0].split("\t")[:2] == ["💾 Save the current one as a layout…", "save"])

    # ── thumbnail prune: --dry-run only counts (the footer's question), --yes deletes ──
    picker_dir = os.path.join(home, ".cache/omarchy/image-selector")
    orphans = [touch_json(os.path.join(picker_dir, n), "jpg") for n in ("orphan-a.jpg", "orphan-b.jpg")]
    code, out, err = run(env, "apply", "theme-switcher", "prune", "--dry-run")
    check("prune --dry-run counts the thumbnails it would delete",
          code == 0 and out == "Can delete: 2 thumbnails, 0.0 GB; 0 stay")
    check("prune --dry-run deletes nothing", all(os.path.exists(p) for p in orphans))
    code, out, err = run(env, "apply", "theme-switcher", "prune", "--yes")
    check("prune --yes deletes the thumbnails", code == 0 and not any(os.path.exists(p) for p in orphans))

    # ── Bar Skin: listing the tab keeps no backup, so a colour set since survives the 💾 row and a save ──
    live = os.path.join(cfg, "bar-skin.json")
    touch_json(live, json.dumps({"background": "#112233"}))
    run(env, "list", "bar-skins")
    run(env, "tweak", "background", "set", "#c0ffee")
    run(env, "list", "bar-skins")
    run(env, "bar-skins-preview", "save")
    check("previewing the 💾 row after a colour change keeps the colour",
          json.load(open(live)).get("background") == "#c0ffee")
    code, out, err = run(env, "apply", "bar-skins", "save", "--name", "issue-b")
    saved = json.load(open(os.path.join(skins, "issue-b.json"))) if code == 0 else {}
    check("saving the bar skin keeps the colour in the saved skin", saved.get("background") == "#c0ffee")
    check("saving keeps the colour on the bar", json.load(open(live)).get("background") == "#c0ffee")
    # A skin preview the shell never restored (it restarted mid-preview) is undone by the overlay's restore.
    night = touch_json(os.path.join(skins, "night.json"), json.dumps({"background": "#445566"}))
    run(env, "bar-skins-preview", night)
    previewed = json.load(open(live)).get("background")
    run(env, "bar-skins-restore")
    check("a skin preview shows its colour, and the restore puts the bar back",
          previewed == "#445566" and json.load(open(live)).get("background") == "#c0ffee")
    # A save during a preview saves the bar as it was before the preview, and ends the preview.
    run(env, "bar-skins-preview", night)
    code, out, err = run(env, "apply", "bar-skins", "save", "--name", "issue-b2")
    saved2 = json.load(open(os.path.join(skins, "issue-b2.json"))) if code == 0 else {}
    check("saving during a preview saves the bar before it and leaves the bar as it was",
          saved2.get("background") == "#c0ffee" and json.load(open(live)).get("background") == "#c0ffee")
    run(env, "tweak", "background", "set", "#aaaaaa")
    run(env, "bar-skins-restore")
    check("after a save no backup is left to restore over a later change",
          json.load(open(live)).get("background") == "#aaaaaa")

    # ── thumbnail clean-up: the overlay asks in its footer and runs with --yes ──
    code, out, err = run(env, "apply", "theme-switcher", "prune", "--yes")
    check("theme-switcher prune --yes runs without a question", code == 0)
    code, out, err = run(env, "apply", "theme-switcher", "prune")
    check("bare prune without zenity fails with the reason", code == 1 and "zenity is not installed" in out + err)

    code, out, err = run(env, "apply", "presets", "save", "--bogus")
    check("an unknown option exits 2 with the option named", code == 2 and "Unknown option: --bogus" in err)

    # ── zenity-only forms: without zenity they fail with the reason, and create nothing ──
    before = sorted(os.listdir(presets)) + sorted(os.listdir(skins)) + sorted(os.listdir(layouts))
    zenity_only = [
        ("apply", "presets", "save"), ("apply", "styles", "save"), ("apply", "bar-skins", "save"),
        ("apply", "bar-layouts", "save"), ("apply", "walls", "pick-dir"), ("apply", "walls", "pick-files"),
        ("apply", "dock", "pin-pick"), ("apply", "lock", "sddm-fetch"),
        ("tweak", "background", "pick"), ("tweak", "photoDir", "pick"),
    ]
    for argv in zenity_only:
        code, out, err = run(env, *argv)
        check(f"{' '.join(argv)} without zenity exits 1 and says so",
              code == 1 and "zenity is not installed" in out + err)
    after = sorted(os.listdir(presets)) + sorted(os.listdir(skins)) + sorted(os.listdir(layouts))
    check("the zenity-only forms wrote no preset, skin or layout", before == after)

    print(f"{'OK' if not fails else 'FAIL'}; sandbox: {base}")
    if not fails:
        shutil.rmtree(base, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
