#!/usr/bin/python3 -I
"""Allowlist известных новых расхождений для compare-харнессов (issue #12).

`known_diffs.json` рядом фиксирует каждое известное расхождение: к какому
случаю оно относится, почему оно ожидаемо и какую точную подпись оно должно
иметь (коды выхода, различающиеся файлы, маркеры в выводе Python). Расхождение,
совпавшее с записью, печатается как KNOWN и не роняет прогон; расхождение в
allowlisted-случае, чья подпись ИЗМЕНИЛАСЬ, печатается как KNOWN-CHANGED и
по-прежнему роняет прогон — так регрессия, спрятавшаяся внутри известного
случая (или исправленное расхождение, которое никто не убрал из списка),
не уйдёт в зелёный цвет молча.
"""
import fnmatch
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(_HERE, "known_diffs.json")) as f:
        return json.load(f)


def lookup(entries, key):
    """Сначала точный ключ, потом fnmatch-шаблон (например, "preset-*.json")."""
    if key in entries:
        return entries[key]
    for pattern, entry in entries.items():
        if "*" in pattern and fnmatch.fnmatchcase(key, pattern):
            return entry
    return None


def matches_readonly(entry, python_output):
    """Все маркеры записи должны быть в выводе Python-бэкенда."""
    return all(s in python_output for s in entry["expect"])


def matches_tweaks(entry, code_bash, code_py, stderr_equal, differing_files):
    """Коды выхода + точный набор различающихся файлов + тот же stderr."""
    return ([code_bash, code_py] == entry["code"] and stderr_equal
            and set(differing_files) == set(entry["files"]))


def matches_apply(entry, code_bash, code_py, differing_files, py_only, bash_only):
    """Коды + точный набор файлов; у Python — только строки из записи, у bash — ничего лишнего."""
    if [code_bash, code_py] != entry["code"]:
        return False
    if set(differing_files) != set(entry["files"]):
        return False
    if bash_only:
        return False
    if entry.get("expect") not in "\n".join(py_only):
        return False
    allowed = entry.get("expect_all")
    if allowed is not None and any(not any(a in line for a in allowed) for line in py_only):
        return False
    return True
