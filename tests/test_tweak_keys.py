#!/usr/bin/python3 -I
"""Ключи настроек, объявленные в двух таблицах (clock24 — Lock Tweaks и Widgets): каждая строка пишет свой файл.

  /usr/bin/python3 -I tests/test_tweak_keys.py

Статическая проверка settings.json (ключ в нескольких таблицах получает однозначный ключ команды) и
динамическая в песочнице: свой HOME в каталоге под $XDG_RUNTIME_DIR, внешние команды — заглушки.
Живой стол не трогается. Регресс: `tweak clock24 +` из Widgets писал lock-design.json, а строка не менялась."""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(PLUGIN, "backend/run.py")
sys.path.insert(0, os.path.join(PLUGIN, "backend"))

from customizer import settings  # noqa: E402

WIDGET_KEY = "WIDGET_TWEAKS:clock24"


def sandbox():
    base = tempfile.mkdtemp(prefix="customizer-keys.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stubs = os.path.join(base, "home"), os.path.join(base, "stubs")
    os.makedirs(stubs)
    for name in ("omarchy-shell", "hyprctl", "notify-send", "omarchy-hyprland-toggle", "omarchy-font-profile"):
        with open(os.path.join(stubs, name), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(stubs, name), 0o755)
    env = dict(os.environ, HOME=home, PATH=stubs + ":" + os.environ["PATH"],
               XDG_STATE_HOME=os.path.join(base, "state"), XDG_CACHE_HOME=os.path.join(base, "cache"),
               XDG_RUNTIME_DIR=os.path.join(base, "run"))
    env.pop("XDG_CONFIG_HOME", None)
    return home, env


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def rows(env, category):
    return [ln.split("\t") for ln in run(env, "list", category)[1].splitlines() if "\t" in ln]


def read_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    fails = []

    def check(name, cond):
        print(("ok    " if cond else "FAIL  ") + name)
        if not cond:
            fails.append(name)

    # ── статическая: settings.json без неоднозначных ключей ──
    with open(settings.paths.SETTINGS_JSON) as f:
        doc = json.load(f)
    owners = {}
    within_table_dup = []
    for t in doc["tables"]:
        seen = set()
        for it in t["items"]:
            if "key" not in it:
                continue
            if it["key"] in seen:
                within_table_dup.append((t["id"], it["key"]))
            seen.add(it["key"])
            owners.setdefault(it["key"], []).append(t["id"])
    check("settings.json: no key repeated inside one table", not within_table_dup)
    dups = {k: v for k, v in owners.items() if len(v) > 1}
    check("settings.json: clock24 is the duplicate under test", "clock24" in dups and dups["clock24"] == ["LOCK_TWEAKS", "WIDGET_TWEAKS"])
    tables = settings.tables()
    for key, ids in dups.items():
        cmd = {tid: settings.command_key(tables[tid], next(i for i in tables[tid].items if i.key == key)) for tid in ids}
        check(f"{key}: each table gets a distinct command key", len(set(cmd.values())) == len(ids))
        check(f"{key}: first table keeps the bare key {cmd[ids[0]]!r}", cmd[ids[0]] == key)
        for tid in ids[1:]:
            check(f"{key}: {tid} is qualified as {cmd[tid]!r}", cmd[tid] == f"{tid}:{key}")
        for tid, ck in cmd.items():
            tbl, it = settings.find(ck)
            check(f"{ck}: resolves to its own table {tid}", tbl is not None and tbl.id == tid and it.key == key)

    # ── динамическая: песочница ──
    home, env = sandbox()
    cfg = os.path.join(home, ".config/omarchy")
    os.makedirs(cfg)
    widgets_json = os.path.join(cfg, "widgets.json")
    lock_json = os.path.join(cfg, "lock-design.json")
    with open(widgets_json, "w") as f:
        f.write('{\n  "clock24": false\n}\n')
    with open(lock_json, "w") as f:
        f.write('{\n  "clock24": false\n}\n')

    def snap():
        return open(widgets_json, "rb").read(), open(lock_json, "rb").read()

    wrow = next((r for r in rows(env, "widgets") if len(r) > 9 and r[9] == "Clock: 24-hour"), None)
    check("widgets list: Clock: 24-hour row has the qualified key", wrow is not None and wrow[1] == WIDGET_KEY)
    check("widgets list: row points at widgets.json", wrow is not None and wrow[2] == widgets_json)
    lrow = next((r for r in rows(env, "lock-tweaks") if len(r) > 9 and r[9] == "Clock: 24-hour"), None)
    check("lock list: Clock: 24-hour row keeps the bare key", lrow is not None and lrow[1] == "clock24")
    check("lock list: row points at lock-design.json", lrow is not None and lrow[2] == lock_json)

    w0, l0 = snap()
    code, _ = run(env, "tweak", WIDGET_KEY, "+")
    w1, l1 = snap()
    check("widgets step: exit 0", code == 0)
    check("widgets step: widgets.json flips to true", read_json(widgets_json).get("clock24") is True)
    check("widgets step: lock-design.json untouched", l1 == l0)
    wrow = next(r for r in rows(env, "widgets") if len(r) > 9 and r[9] == "Clock: 24-hour")
    check("widgets step: the Widgets row shows the new value (raw field)", wrow[8] == "true")

    code, _ = run(env, "tweak", "clock24", "+")
    w2, l2 = snap()
    check("lock step (bare key): exit 0", code == 0)
    check("lock step: lock-design.json flips to true", read_json(lock_json).get("clock24") is True)
    check("lock step: widgets.json untouched", w2 == w1)
    lrow = next(r for r in rows(env, "lock-tweaks") if len(r) > 9 and r[9] == "Clock: 24-hour")
    check("lock step: the Lock row shows the new value (raw field)", lrow[8] == "true")

    run(env, "tweak", WIDGET_KEY, "+")
    check("widgets step again: widgets.json back to false, lock stays true",
          read_json(widgets_json).get("clock24") is False and read_json(lock_json).get("clock24") is True)

    run(env, "tweak", "LOCK_TWEAKS:clock24", "+")
    check("explicit LOCK_TWEAKS:clock24 writes lock-design.json only",
          read_json(lock_json).get("clock24") is False and read_json(widgets_json).get("clock24") is False)

    run(env, "tweak", WIDGET_KEY, "set", "true")
    check("widgets set: value written to widgets.json only",
          read_json(widgets_json).get("clock24") is True and read_json(lock_json).get("clock24") is False)

    run(env, "tweak", WIDGET_KEY, "reset")
    check("widgets reset: key removed from widgets.json only",
          "clock24" not in read_json(widgets_json) and read_json(lock_json).get("clock24") is False)

    code, _ = run(env, "tweak", "WIDGET_TWEAKS:noSuchKey", "+")
    check("unknown qualified key: exit 1, nothing written", code == 1 and read_json(lock_json) == {"clock24": False})

    # Уникальные ключи не меняются: квалификатор только у дублей (section: и tweak: — свои префиксы).
    for cat in ("widgets", "lock-tweaks"):
        bad = [r[1] for r in rows(env, cat) if len(r) > 1 and ":" in r[1] and not r[1].startswith(("section:", "tweak:"))
               and r[1].split(":", 1)[1] not in dups]
        check(f"{cat}: only duplicate keys are qualified", not bad)

    index = [ln.split("\t") for ln in run(env, "search-index")[1].splitlines()]
    hits = {(f[0], f[1]) for f in index if len(f) > 1 and f[1].endswith("clock24")}
    check("search-index: widgets entry carries the Widgets row value", ("widgets", WIDGET_KEY) in hits)
    check("search-index: lock entry keeps the bare key", ("lock-tweaks", "clock24") in hits)
    check("search-index: result value matches the list row (jump lands on the row)",
          wrow is not None and wrow[1] == WIDGET_KEY and ("widgets", wrow[1]) in hits)

    print("OK" if not fails else f"FAILED: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
