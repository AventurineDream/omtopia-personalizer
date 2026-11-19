#!/usr/bin/python3 -I
"""Ключи настроек, объявленные в двух таблицах (clock24 — Lock Tweaks и Widgets): каждая строка пишет свой файл.

  /usr/bin/python3 -I tests/test_tweak_keys.py
  LC_ALL=ru_RU.UTF-8 /usr/bin/python3 -I tests/test_tweak_keys.py      # то же на русском

Не зависит от языка интерфейса: строки выбираются по полю value (индекс 1), а не по подписи (индекс 9),
которая переводится. Статическая проверка settings.json и динамическая в песочнице: свой HOME во временном
каталоге под $XDG_RUNTIME_DIR, который удаляется по выходу; внешние команды — заглушки. Живой стол не трогается.
Регресс: `tweak clock24 +` из Widgets писал lock-design.json, а строка не менялась."""
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
LOCK_KEY = "clock24"
VALUE, RAW = 1, 8   # поля вывода list: value (ключ команды) и сырое значение


def sandbox(base):
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
    os.makedirs(os.path.join(home, ".config/omarchy"))
    return home, env


def run(env, *args):
    r = subprocess.run(["/usr/bin/python3", "-I", RUN, *args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def rows(env, category):
    return [ln.split("\t") for ln in run(env, "list", category)[1].splitlines() if "\t" in ln]


def row(env, category, key):
    return next((r for r in rows(env, category) if len(r) > RAW and r[VALUE] == key), None)


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
    owners, within_table_dup = {}, []
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
    check("settings.json: clock24 is the duplicate under test",
          dups.get("clock24") == ["LOCK_TWEAKS", "WIDGET_TWEAKS"])
    tables = settings.tables()
    for key, ids in dups.items():
        cmd = {tid: settings.command_key(tables[tid], next(i for i in tables[tid].items if i.key == key)) for tid in ids}
        check(f"{key}: each table gets a distinct command key", len(set(cmd.values())) == len(ids))
        check(f"{key}: first table keeps the bare key", cmd[ids[0]] == key)
        for tid in ids[1:]:
            check(f"{key}: {tid} is qualified as {tid}:{key}", cmd[tid] == f"{tid}:{key}")
        for tid, ck in cmd.items():
            tbl, it = settings.find(ck)
            check(f"{ck}: resolves to its own table {tid}", tbl is not None and tbl.id == tid and it.key == key)
    check("find: empty bare key after a qualifier matches nothing", settings.find("WIDGET_TWEAKS:") == (None, None))

    # ── динамическая: песочница, удаляется по выходу ──
    with tempfile.TemporaryDirectory(prefix="customizer-keys.", dir=os.environ.get("XDG_RUNTIME_DIR") or None) as base:
        home, env = sandbox(base)
        cfg = os.path.join(home, ".config/omarchy")
        widgets_json = os.path.join(cfg, "widgets.json")
        lock_json = os.path.join(cfg, "lock-design.json")
        for path in (widgets_json, lock_json):
            with open(path, "w") as f:
                f.write('{\n  "clock24": false\n}\n')

        def snap():
            return open(widgets_json, "rb").read(), open(lock_json, "rb").read()

        wrow = row(env, "widgets", WIDGET_KEY)
        check("widgets list: Clock row is keyed WIDGET_TWEAKS:clock24", wrow is not None)
        check("widgets list: row points at widgets.json", wrow is not None and wrow[2] == widgets_json)
        lrow = row(env, "lock-tweaks", LOCK_KEY)
        check("lock list: Clock row keeps the bare key", lrow is not None)
        check("lock list: row points at lock-design.json", lrow is not None and lrow[2] == lock_json)

        w0, l0 = snap()
        code, _ = run(env, "tweak", WIDGET_KEY, "+")
        w1, l1 = snap()
        check("widgets step: exit 0", code == 0)
        check("widgets step: widgets.json flips to true", read_json(widgets_json).get("clock24") is True)
        check("widgets step: lock-design.json untouched", l1 == l0)
        check("widgets step: the Widgets row shows the new value",
              row(env, "widgets", WIDGET_KEY)[RAW] == "true")

        code, _ = run(env, "tweak", LOCK_KEY, "+")
        w2, l2 = snap()
        check("lock step (bare key): exit 0", code == 0)
        check("lock step: lock-design.json flips to true", read_json(lock_json).get("clock24") is True)
        check("lock step: widgets.json untouched", w2 == w1)
        check("lock step: the Lock row shows the new value", row(env, "lock-tweaks", LOCK_KEY)[RAW] == "true")

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

        before = snap()
        code, _ = run(env, "tweak", "WIDGET_TWEAKS:noSuchKey", "+")
        check("unknown qualified key: exit 1, nothing written", code == 1 and snap() == before)
        code, _ = run(env, "tweak", "WIDGET_TWEAKS:", "reset")
        check("empty bare key after qualifier: exit 1, nothing written", code == 1 and snap() == before)

        # Квалификатор только у дублей: точный набор, без лишних и без пропавших.
        for cat, expected in (("widgets", {WIDGET_KEY}), ("lock-tweaks", set())):
            qualified = {r[VALUE] for r in rows(env, cat)
                         if len(r) > VALUE and ":" in r[VALUE] and not r[VALUE].startswith(("section:", "tweak:"))}
            check(f"{cat}: qualified keys are exactly {sorted(expected)}", qualified == expected)

        hits = {(f[0], f[1]) for f in (ln.split("\t") for ln in run(env, "search-index")[1].splitlines())
                if len(f) > 1 and f[1].endswith("clock24")}
        check("search-index: widgets entry carries the Widgets row value", ("widgets", WIDGET_KEY) in hits)
        check("search-index: lock entry keeps the bare key", ("lock-tweaks", LOCK_KEY) in hits)

    print("OK" if not fails else f"FAILED: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
