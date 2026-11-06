"""Перевод как в scripts/i18n.sh: строки в коде английские, i18n/<язык>.json — перевод.

Язык: "lang" в ~/.config/omarchy/customizer.json, иначе LC_ALL / LC_MESSAGES / LANG (ru* → ru).
Подстановка — только %s по порядку; остальные % и обратные слэши остаются как есть.
"""
import json
import os

from . import paths

_table = None
_lang = None


def lang() -> str:
    global _lang
    if _lang is None:
        value = ""
        try:
            value = json.loads(paths.CUSTOMIZER_JSON.read_text()).get("lang") or ""
        except (OSError, ValueError, AttributeError):
            value = ""
        if not value:
            value = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en"
        _lang = "ru" if str(value).startswith("ru") else "en"
    return _lang


def _load():
    global _table
    if _table is None:
        _table = {}
        if lang() != "en":
            try:
                _table = json.loads((paths.I18N_DIR / f"{lang()}.json").read_text())
            except (OSError, ValueError):
                _table = {}
    return _table


def t(text: str, *args) -> str:
    s = _load().get(text, text)
    if not args:
        return s
    parts = s.split("%s")
    out = [parts[0]]
    for i, part in enumerate(parts[1:]):
        out.append(str(args[i]) if i < len(args) else "")
        out.append(part)
    return "".join(out)
