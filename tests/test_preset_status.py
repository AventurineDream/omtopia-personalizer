#!/usr/bin/python3 -I
"""«В использовании» пресета после apply и «Восстановить прежнюю настройку» (customizer.sh status / list presets).

  /usr/bin/python3 -I tests/test_preset_status.py

Регрессия: пресет DOT-MATRIX (тема не применяется, скина и блокировки нет) не сравнивается ни с чем,
поэтому прежде совпадал «по умолчанию» и оставался «в использовании» после отката. Каждый сценарий
идёт через Python-бэкенд и через bash-эталон в своей песочнице (свежий HOME под $XDG_RUNTIME_DIR;
omarchy / hyprctl / notify-send — заглушки), результат обоих должен совпасть. Живой стол не трогается.
"""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
LEGACY = os.path.join(PLUGIN, "tests/legacy/customizer.sh")
DOT = os.path.join(PLUGIN, "presets/DOT-MATRIX.json")
ENGINES = {"python": ["/usr/bin/python3", "-I", RUN], "bash": ["bash", LEGACY]}


class Box:
    """Песочница одного движка: свой HOME, заглушки внешних команд, журнал вызовов."""

    def __init__(self, engine):
        base = tempfile.mkdtemp(prefix=f"customizer-preset-{engine}.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
        self.engine = engine
        self.home = os.path.join(base, "home")
        stubs = os.path.join(base, "stubs")
        self.log = os.path.join(base, "calls.log")
        self.state = os.path.join(self.home, ".local/state/omarchy-customizer")
        self.cfg = os.path.join(self.home, ".config/omarchy")
        os.makedirs(stubs)
        os.makedirs(os.path.join(self.cfg, "customizer"))
        os.makedirs(self.state)
        # Тема «default» установлена: откат проверяет, что тема снимка стоит.
        os.makedirs(os.path.join(self.cfg, "themes/default"))
        for name in ("notify-send", "omarchy", "hyprctl", "setsid", "gio", "zenity", "omarchy-font-profile"):
            p = os.path.join(stubs, name)
            with open(p, "w") as f:
                f.write(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "{self.log}"\n')
            os.chmod(p, 0o755)
        self.env = dict(os.environ, HOME=self.home, PATH=stubs + ":" + os.environ["PATH"],
                        OMARCHY_PATH=os.path.join(base, "no-omarchy"), CUSTOMIZER_LEGACY="1")
        self.env.pop("XDG_CONFIG_HOME", None)
        self.env.pop("XDG_STATE_HOME", None)

    def set_theme(self, name):
        """Записать имя текущей темы, как это делает omarchy theme set."""
        path = os.path.join(self.home, ".local/state/omarchy/current/theme.name")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(name + "\n")

    def write_json(self, path, doc):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        return path

    def run(self, *args):
        r = subprocess.run(ENGINES[self.engine] + list(args), env=self.env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def preset_in_use(self):
        """Значение строки «preset» из status."""
        _rc, out = self.run("status")
        for line in out.splitlines():
            key, _, val = line.partition("\t")
            if key == "preset":
                return val
        raise AssertionError(f"{self.engine}: no preset line in status:\n{out}")

    def rows_in_use(self):
        """Имена строк списка пресетов, отмеченных как «В использовании» (флаг 4-го столбца)."""
        _rc, out = self.run("list", "presets")
        rows = [line.split("\t") for line in out.splitlines()]
        return sorted(r[0] for r in rows if len(r) > 3 and r[3] == "1")

    def apply(self, path):
        return self.run("apply", "presets", path)[0]

    def restore(self):
        return self.apply(os.path.join(self.state, "last-preset.json"))


def scenario_restore_and_glob(box):
    """Theme off: DOT-MATRIX (нечего сравнивать) и пользовательский пресет без полей не занимают «В использовании»."""
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
    """Откат возвращает пресет, который был в использовании при снимке (записан в снимке, не угадан)."""
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": False})
    # Пресет «Glyph» стоит из сохранённого состояния, резервной копии ещё нет.
    with open(os.path.join(box.state, "active-preset"), "w") as f:
        f.write("Glyph\n")
    obs = {"before": box.preset_in_use()}
    obs["apply_rc"] = box.apply(DOT)
    obs["just_applied"] = box.preset_in_use()
    snap = json.load(open(os.path.join(box.state, "last-preset.json")))
    obs["snapshot_preset"] = snap.get("preset")
    obs["restore_rc"] = box.restore()
    obs["after_restore"] = box.preset_in_use()
    return obs


def scenario_theme(box):
    """Apply theme on: сравнение темы работает и после применения, и после отката."""
    box.write_json(os.path.join(box.cfg, "customizer/preset-apply.json"), {"presetTheme": True})
    os.makedirs(os.path.join(box.cfg, "themes/dot-matrix"))
    obs = {"apply_rc": box.apply(DOT)}
    obs["theme_not_set"] = box.preset_in_use()          # omarchy theme set не сменил тему
    box.set_theme("dot-matrix")
    obs["theme_set"] = box.preset_in_use()
    obs["restore_rc"] = box.restore()
    box.set_theme("default")                             # omarchy theme set default (снимок)
    obs["after_restore"] = box.preset_in_use()
    return obs


SCENARIOS = {
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
        "apply_rc": 0, "theme_not_set": "custom", "theme_set": "DOT-MATRIX",
        "restore_rc": 0, "after_restore": "custom",
    }),
}


def main():
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

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

    if fails:
        print(f"\n{len(fails)} FAILED")
        return 1
    print("\nall preset status checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
