"""Команды бэкенда: разбор команды и вызов модуля. Результат: (код, stdout, stderr)."""
import os

from . import apply_ops, i18n, lists, lists_more, paths, preview_ops, settings, state, tweak_ops


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


USAGE = "usage: customizer.sh list|status|available|search-index|restore|lang|thumbs|anim-preview|anim-restore|opacity-preview|opacity-restore|blur-preview|blur-restore|bar-skins-preview|bar-skins-restore|tweak|apply|theme-fav|wall-fav ...\n"


def run(args):
    state.reset()   # «что стоит сейчас» считается заново для каждого запроса
    os.makedirs(paths.RUN, exist_ok=True)     # как mkdir -p "$RUN_DIR" "$STATE_DIR" в начале customizer.sh
    os.makedirs(paths.STATE, exist_ok=True)
    cmd = args[0] if args else ""
    if cmd in apply_ops.COMMANDS and len(args) >= 2 or cmd == "picker-cache":
        code, out = apply_ops.run(args)
        return code, out, ""
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
        return 0, _lines(rows or []), ""   # неизвестная категория — пусто и 0, как в bash
    return 1, "", USAGE
