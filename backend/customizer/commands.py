"""Команды бэкенда. Перенесённые выполняются здесь; остальные — старым bash (customizer.sh c
CUSTOMIZER_LEGACY=1), пока перенос не закончен. Результат: (код, stdout, stderr)."""
import os
import subprocess

from . import i18n, lists, lists_more, paths, preview_ops, settings, state, tweak_ops


def _search_index():
    out = []
    for tbl in settings.tables().values():
        section = ""
        for it in tbl.items:
            if it.is_section:
                section = it.section
                continue
            if tbl.category == "sounds" and it.key == "soundPack":
                continue
            out.append(f"{tbl.category}\t{tbl.value_prefix}{it.key}\t{i18n.t(it.label)}\t{i18n.t(section) if section else ''}")
    return out


def _lines(rows) -> str:
    return "".join(r + "\n" for r in rows)


def legacy(args, stdin=None):
    """Не перенесённая команда — старый bash."""
    env = dict(os.environ, CUSTOMIZER_LEGACY="1")
    p = subprocess.run(["bash", str(paths.LEGACY), *args], capture_output=True, text=True, env=env, input=stdin)
    return p.returncode, p.stdout, p.stderr


def run(args):
    state.reset()   # «что стоит сейчас» считается заново для каждого запроса
    os.makedirs(paths.RUN, exist_ok=True)     # как mkdir -p "$RUN_DIR" "$STATE_DIR" в начале customizer.sh
    os.makedirs(paths.STATE, exist_ok=True)
    cmd = args[0] if args else ""
    if cmd in preview_ops.COMMANDS:
        code, out = preview_ops.run(args)
        return code, out, ""
    if cmd == "tweak" and len(args) >= 2:
        return tweak_ops.run(args)
    if cmd == "status":
        return 0, _lines(lists_more.status()), ""
    if cmd == "available":
        return 0, _lines(lists_more.available()), ""
    if cmd == "lang":
        return 0, i18n.lang() + "\n", ""
    if cmd == "search-index":
        return 0, _lines(_search_index()), ""
    if cmd == "list" and len(args) >= 2:
        rows = lists.list_category(args[1], args[2] if len(args) > 2 else "")
        if rows is not None:
            return 0, _lines(rows), ""
    return legacy(args)


def handled_here(args) -> bool:
    """Выполнит ли команду сам Python (для CLI: иначе — сразу exec в bash, без лишнего круга)."""
    cmd = args[0] if args else ""
    if cmd in ("lang", "search-index", "status", "available") or cmd in preview_ops.COMMANDS or (cmd == "tweak" and len(args) >= 2):
        return True
    return cmd == "list" and len(args) >= 2 and (args[1] in lists.LISTS or args[1] == "theme-walls")
