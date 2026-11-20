#!/usr/bin/python3 -I
"""Regression test: "In use" for presets after apply and after "Restore previous setup".

  /usr/bin/python3 -I tests/test_preset_status.py

Covers customizer.sh status and list presets. The bug: DOT-MATRIX (theme only, no barSkin or lock)
compared nothing, so it matched by default and stayed "In use" after a restore. Each scenario runs
through the Python backend and the bash reference, each in its own sandbox (fresh HOME, own
XDG_RUNTIME_DIR and XDG_CACHE_HOME, stubbed omarchy / hyprctl / notify-send and other helpers).
Both engines must produce the same observations. The live desktop is never touched.

On success the sandboxes are removed. On failure they are kept and their paths are printed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
LEGACY = os.path.join(PLUGIN, "tests/legacy/customizer.sh")
DOT = os.path.join(PLUGIN, "presets/DOT-MATRIX.json")
ENGINES = {"python": ["/usr/bin/python3", "-I", RUN], "bash": ["bash", LEGACY]}
# Every external command a preset apply can reach. Stubs log their arguments to calls.log.
STUBS = ("notify-send", "omarchy", "hyprctl", "setsid", "gio", "zenity", "omarchy-font-profile",
         "omarchy-hyprland-toggle", "omarchy-app-themes", "omarchy-firefox-chrome")
SANDBOXES = []

# Stateful hyprctl for the blur scenarios: @LIVE@ holds "enabled size passes vibrancy noise", as Hyprland's
# decoration.blur does. getoption reads it; a `blur = {` eval rewrites it. Other calls are logged and ignored.
BLUR_HYPRCTL = r"""#!/bin/sh
printf '%s\n' "hyprctl $*" >> "@LOG@"
live="@LIVE@"
case "$1" in
  getoption)
    case "$2" in
      decoration:blur:enabled) f=1; k=bool ;;
      decoration:blur:size) f=2; k=int ;;
      decoration:blur:passes) f=3; k=int ;;
      decoration:blur:vibrancy) f=4; k=float ;;
      decoration:blur:noise) f=5; k=float ;;
      *) exit 0 ;;
    esac
    printf '{"option": "%s", "%s": %s}\n' "$2" "$k" "$(cut -d' ' -f$f "$live")"
    ;;
  eval)
    case "$2" in *"blur = {"*) ;; *) exit 0 ;; esac
    en=$(printf '%s\n' "$2" | sed -n -E 's/.*enabled = (true|false).*/\1/p')
    s=$(printf '%s\n' "$2" | sed -n -E 's/.*size = ([0-9]+).*/\1/p')
    p=$(printf '%s\n' "$2" | sed -n -E 's/.*passes = ([0-9]+).*/\1/p')
    v=$(printf '%s\n' "$2" | sed -n -E 's/.*vibrancy = ([0-9.]+).*/\1/p')
    n=$(printf '%s\n' "$2" | sed -n -E 's/.*noise = ([0-9.]+).*/\1/p')
    echo "$en $s $p $v $n" >"$live"
    ;;
esac
exit 0
"""


class Box:
    """One engine's sandbox: its own HOME, runtime and cache dirs, stubs, and a call log."""

    def __init__(self, engine):
        base = tempfile.mkdtemp(prefix=f"customizer-preset-{engine}.")
        SANDBOXES.append(base)
        self.engine = engine
        self.base = base
        self.home = os.path.join(base, "home")
        stubs = os.path.join(base, "stubs")
        self.log = os.path.join(base, "calls.log")
        self.state = os.path.join(self.home, ".local/state/omarchy-customizer")
        self.cfg = os.path.join(self.home, ".config/omarchy")
        os.makedirs(stubs)
        os.makedirs(os.path.join(self.cfg, "customizer"))
        os.makedirs(self.state)
        # The installed "default" theme: a restore checks that the snapshot's theme exists.
        os.makedirs(os.path.join(self.cfg, "themes/default"))
        for name in STUBS:
            p = os.path.join(stubs, name)
            with open(p, "w") as f:
                f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{self.log}"\n')
                if name == "omarchy":
                    # `omarchy theme set X` switches the current theme, as the real command does.
                    f.write('[ "$1" = theme ] && [ "$2" = set ] && {\n'
                            '  mkdir -p "$HOME/.local/state/omarchy/current"\n'
                            '  printf "%s\\n" "$3" > "$HOME/.local/state/omarchy/current/theme.name"\n'
                            '}\n')
            os.chmod(p, 0o755)
        self.env = dict(os.environ, HOME=self.home, PATH=stubs + ":" + os.environ["PATH"],
                        XDG_RUNTIME_DIR=os.path.join(base, "run"), XDG_CACHE_HOME=os.path.join(base, "cache"),
                        OMARCHY_PATH=os.path.join(base, "no-omarchy"))
        os.makedirs(self.env["XDG_RUNTIME_DIR"])
        self.env.pop("XDG_CONFIG_HOME", None)
        self.env.pop("XDG_STATE_HOME", None)

    def set_theme(self, name):
        """Set the current theme name directly, as if the user switched themes outside the Customizer."""
        path = os.path.join(self.home, ".local/state/omarchy/current/theme.name")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(name + "\n")

    def write_json(self, path, doc):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f)

    def theme_calls(self):
        """Lines of `omarchy theme ...` calls recorded so far."""
        try:
            with open(self.log) as f:
                return [line for line in f.read().splitlines() if line.startswith("omarchy theme ")]
        except FileNotFoundError:
            return []

    def use_blur_stub(self, live):
        """Replace the hyprctl stub with the stateful blur one, holding `live` ("enabled size passes vibrancy noise")."""
        self.live_path = os.path.join(self.base, "blur-live")
        with open(self.live_path, "w") as f:
            f.write(live + "\n")
        with open(os.path.join(self.base, "stubs", "hyprctl"), "w") as f:
            f.write(BLUR_HYPRCTL.replace("@LOG@", self.log).replace("@LIVE@", self.live_path))

    def live_blur(self):
        """The live blur values as the stateful stub holds them."""
        with open(self.live_path) as f:
            return f.read().strip()

    def write_text(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def blur_in_use(self):
        """Value of the `blur` line in status ("" when no blur preset is in use)."""
        _rc, out = self.run("status")
        for line in out.splitlines():
            key, _, val = line.partition("\t")
            if key == "blur":
                return val
        raise AssertionError(f"{self.engine}: no blur line in status:\n{out}")

    def run(self, *args):
        r = subprocess.run(ENGINES[self.engine] + list(args), env=self.env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def preset_in_use(self):
        """Value of the `preset` line in status."""
        _rc, out = self.run("status")
        for line in out.splitlines():
            key, _, val = line.partition("\t")
            if key == "preset":
                return val
        raise AssertionError(f"{self.engine}: no preset line in status:\n{out}")

    def rows_in_use(self):
        """Names of the presets-list rows flagged as in use (column 4 equals 1)."""
        _rc, out = self.run("list", "presets")
        rows = [line.split("\t") for line in out.splitlines()]
        return sorted(r[0] for r in rows if len(r) > 3 and r[3] == "1")

    def apply(self, path):
        return self.run("apply", "presets", path)[0]

    def restore(self):
        return self.apply(os.path.join(self.state, "last-preset.json"))


def scenario_blur_rollback_fresh(box):
    """Fresh system, no blur preset in use: a preset with blur strong, then Restore previous setup.

    The restore must put back the live 4x2 blur the desktop had, and name no blur preset: the snapshot
    stores the live values, because a preset name would mark that preset in use after the restore.
    """
    box.use_blur_stub("true 4 2 0.00 0.000")
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": False})
    strong = os.path.join(box.cfg, "customizer/presets/strong-blur.json")
    box.write_json(strong, {"name": "Strong blur", "blur": "strong"})
    obs = {"fresh_blur": box.blur_in_use()}
    obs["apply_rc"] = box.apply(strong)
    obs["just_applied_live"] = box.live_blur()
    obs["just_applied_blur"] = box.blur_in_use()
    with open(os.path.join(box.state, "last-preset.json"), encoding="utf-8") as f:
        snap = json.load(f)
    obs["snapshot_blur"] = snap.get("blur")
    obs["snapshot_blur_live"] = snap.get("blurLive")
    obs["restore_rc"] = box.restore()
    obs["after_restore_live"] = box.live_blur()
    obs["after_restore_blur"] = box.blur_in_use()
    return obs


def scenario_blur_rollback_named(box):
    """Blur light in use by name, then a preset with blur strong: Restore previous setup names light again."""
    box.use_blur_stub("true 3 2 0.10 0.010")
    box.write_text(os.path.join(box.home, ".local/state/hypr/blur"), "light 3 2 0.10 0.010\n")
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": False})
    strong = os.path.join(box.cfg, "customizer/presets/strong-blur.json")
    box.write_json(strong, {"name": "Strong blur", "blur": "strong"})
    obs = {"before_blur": box.blur_in_use()}
    obs["apply_rc"] = box.apply(strong)
    obs["just_applied_live"] = box.live_blur()
    with open(os.path.join(box.state, "last-preset.json"), encoding="utf-8") as f:
        snap = json.load(f)
    obs["snapshot_blur"] = snap.get("blur")
    obs["restore_rc"] = box.restore()
    obs["after_restore_live"] = box.live_blur()
    obs["after_restore_blur"] = box.blur_in_use()
    return obs


def scenario_restore_and_glob(box):
    """Apply theme off: DOT-MATRIX and an empty user preset must not be "In use" by default."""
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": False})
    box.write_json(os.path.join(box.cfg, "customizer/presets/empty.json"), {"name": "Empty"})
    obs = {"fresh": box.preset_in_use(), "fresh_rows": box.rows_in_use()}
    obs["apply_rc"] = box.apply(DOT)
    obs["just_applied"] = box.preset_in_use()
    obs["just_applied_rows"] = box.rows_in_use()
    obs["restore_rc"] = box.restore()
    obs["after_restore"] = box.preset_in_use()
    obs["after_restore_rows"] = box.rows_in_use()
    return obs


def scenario_origin(box):
    """The rollback restores the preset that was in use when the snapshot was taken."""
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": False})
    # "Glyph" is in use from saved state, with no rollback snapshot yet.
    with open(os.path.join(box.state, "active-preset"), "w") as f:
        f.write("Glyph\n")
    obs = {"before": box.preset_in_use()}
    obs["apply_rc"] = box.apply(DOT)
    obs["just_applied"] = box.preset_in_use()
    with open(os.path.join(box.state, "last-preset.json"), encoding="utf-8") as f:
        obs["snapshot_preset"] = json.load(f).get("preset")
    obs["restore_rc"] = box.restore()
    obs["after_restore"] = box.preset_in_use()
    return obs


def scenario_theme(box):
    """Apply theme on: the theme comparison decides "In use" after apply, outside switch, and restore."""
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": True})
    os.makedirs(os.path.join(box.cfg, "themes/dot-matrix"))
    obs = {"apply_rc": box.apply(DOT)}
    # The apply runs `omarchy theme set dot-matrix`, so the theme now matches the preset.
    obs["just_applied"] = box.preset_in_use()
    # The user switches the theme outside the Customizer: the recorded preset no longer matches.
    box.set_theme("some-other-theme")
    obs["theme_switched"] = box.preset_in_use()
    obs["restore_rc"] = box.restore()
    # The restore runs `omarchy theme set default` for the snapshot's theme.
    obs["theme_calls"] = box.theme_calls()
    obs["after_restore"] = box.preset_in_use()
    return obs


SCENARIOS = {
    "blur_rollback_fresh": (scenario_blur_rollback_fresh, {
        "fresh_blur": "", "apply_rc": 0, "just_applied_live": "true 10 4 0.20 0.015", "just_applied_blur": "strong",
        "snapshot_blur": None, "snapshot_blur_live": "true 4 2 0.00 0.000",
        "restore_rc": 0, "after_restore_live": "true 4 2 0.00 0.000", "after_restore_blur": "",
    }),
    "blur_rollback_named": (scenario_blur_rollback_named, {
        "before_blur": "light", "apply_rc": 0, "just_applied_live": "true 10 4 0.20 0.015",
        "snapshot_blur": "light", "restore_rc": 0,
        "after_restore_live": "true 3 2 0.10 0.010", "after_restore_blur": "light",
    }),
    "restore_and_glob": (scenario_restore_and_glob, {
        "fresh": "custom", "fresh_rows": [],
        "apply_rc": 0, "just_applied": "DOT-MATRIX", "just_applied_rows": ["DOT-MATRIX"],
        "restore_rc": 0, "after_restore": "custom", "after_restore_rows": [],
    }),
    "origin": (scenario_origin, {
        "before": "Glyph", "apply_rc": 0, "just_applied": "DOT-MATRIX",
        "snapshot_preset": "Glyph", "restore_rc": 0, "after_restore": "Glyph",
    }),
    "theme": (scenario_theme, {
        "apply_rc": 0, "just_applied": "DOT-MATRIX", "theme_switched": "custom",
        "restore_rc": 0, "theme_calls": ["omarchy theme set dot-matrix", "omarchy theme set default"],
        "after_restore": "custom",
    }),
}


def main():
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    try:
        for sname, (fn, expect) in SCENARIOS.items():
            results = {}
            for engine in ENGINES:
                box = Box(engine)
                results[engine] = fn(box)
                print(f"      {sname} [{engine}] {json.dumps(results[engine], ensure_ascii=False)}")
            check(f"{sname}: python and bash agree", results["python"] == results["bash"])
            for key, want in expect.items():
                for engine in ENGINES:
                    got = results[engine].get(key)
                    check(f"{sname} [{engine}] {key} == {want!r}", got == want)
    finally:
        if fails:
            print("\nsandboxes kept for inspection:")
            for b in SANDBOXES:
                print("  " + b)
        else:
            for b in SANDBOXES:
                shutil.rmtree(b, ignore_errors=True)

    if fails:
        print(f"\n{len(fails)} FAILED")
        return 1
    print("\nall preset status checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
