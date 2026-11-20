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


def _strip_markers(line, markers):
    """Строка с вырезанными маркерами записи (известными вставками бэкенда)."""
    for m in markers:
        line = line.replace(m, "")
    return line


def matches_readonly(entry, bash_output, python_output):
    """Строгая сверка: все маркеры в выводе Python, ни одной bash-only строки,
    и каждая лишняя строка Python содержит маркер из записи.

    Все маркеры записи обязательны. Строки, зависящие от состояния хоста (плагин FX, установленный
    owe), не делаются необязательными: их случай запускается в песочнице с фиксированным состоянием
    (compare_readonly), поэтому строки там всегда присутствуют.

    Строка bash считается покрытой, если она есть в выводе Python как есть,
    является префиксом строки Python (бэкенд дописал поле в конец строки,
    например палитру темы) или совпадает со строкой Python, из которой
    вырезаны маркеры (бэкенд вставил известное значение в поле, например
    системный путь превью темы). Строка Python считается лишней, только если
    она не покрыта ни одной строкой bash ни одним из этих способов, — тогда
    она обязана содержать маркер из записи. Иначе сломанный вывод (пропавшая
    строка, чужое значение) ушёл бы в зелёный цвет, лишь бы маркеры были
    на месте.
    """
    markers = entry["expect"]
    if not all(s in python_output for s in markers):
        return False
    bash_lines = bash_output.splitlines()
    python_lines = python_output.splitlines()

    def covered(bash_line):
        for p in python_lines:
            if p == bash_line or p.startswith(bash_line):
                return True
            stripped = _strip_markers(p, markers)
            if stripped == bash_line or stripped.startswith(bash_line):
                return True
        return False

    def is_extra(python_line):
        for b in bash_lines:
            if python_line == b or python_line.startswith(b):
                return False
            stripped = _strip_markers(python_line, markers)
            if stripped == b or stripped.startswith(b):
                return False
        return True

    # Ни одной bash-only строки: каждая строка bash покрыта Python.
    if any(not covered(b) for b in bash_lines):
        return False
    # Каждая лишняя строка Python содержит маркер.
    for p in python_lines:
        if is_extra(p) and not any(m in p for m in markers):
            return False
    return True


def _as_pairs(value):
    """Одна пара кодов [bash, py] или список таких пар -> список пар."""
    if value and isinstance(value[0], list):
        return [list(p) for p in value]
    return [list(value)]


def _as_file_sets(value):
    """Один набор файлов или список наборов -> список наборов."""
    if value and isinstance(value[0], list):
        return [set(s) for s in value]
    return [set(value)]


def matches_tweaks(entry, code_bash, code_py, err_bash, err_py, differing_files):
    """Коды выхода + stderr + точный набор различающихся файлов.
    code/files/stderr могут задавать несколько допустимых сигнатур: шаги
    одного сценария различаются по подкоманде ('set' даёт bash-код 2 вместо 1
    и печатает 'Unknown setting' в stderr, 'reset' может писать
    дополнительный файл), поэтому запись принимает одну пару/набор или
    список пар/наборов. Без поля stderr требуется, чтобы stderr совпадали."""
    if [code_bash, code_py] not in _as_pairs(entry["code"]):
        return False
    expected_err = entry.get("stderr")
    if expected_err is None:
        if err_bash != err_py:
            return False
    elif [err_bash, err_py] not in _as_pairs(expected_err):
        return False
    return set(differing_files) in _as_file_sets(entry["files"])


def _is_structural(line):
    """Строка — только структурный JSON (скобки/запятая), без содержимого."""
    return line.strip() in ("", "{", "}", "[", "]", ",", "},", "],")


def _matches_apply_variant(variant, code_bash, code_py, differing_files, py_only, bash_only):
    """Одна подпись расхождения: коды + файлы + маркеры + bash-only строки."""
    if [code_bash, code_py] != variant["code"]:
        return False
    if set(differing_files) not in _as_file_sets(variant["files"]):
        return False
    # bash-only строки: по умолчанию запрещены; подпись может перечислить
    # допустимые (например, '{}' — пустой windows.json у bash при restore).
    if sorted(bash_only) != sorted(variant.get("bash_only", [])):
        return False
    # Точный набор py-only строк: любое отличие значения или состава ключа — другая подпись.
    # Подписи без "py_only" (thumbs: набор системных тем зависит от машины) сверяются по маркерам.
    exact = variant.get("py_only")
    if exact is not None:
        return sorted(py_only) == sorted(exact)
    if variant.get("expect") not in "\n".join(py_only):
        return False
    allowed = variant.get("expect_all")
    if allowed is not None:
        for line in py_only:
            if _is_structural(line):
                continue
            if not any(a in line for a in allowed):
                return False
    return True


def matches_apply(entry, code_bash, code_py, differing_files, py_only, bash_only):
    """Коды + точный набор файлов; у Python — только строки из записи, у bash — ничего лишнего.
    Запись может задавать несколько допустимых подписей ("variants"): шаги
    одного сценария различаются (снапшот геометрии при apply пресета против
    её восстановления при повторном apply), поэтому каждая подпись — свой
    набор кодов/файлов/маркеров. Без "variants" — одна подпись из полей записи."""
    variants = entry.get("variants")
    if variants is None:
        return _matches_apply_variant(entry, code_bash, code_py, differing_files, py_only, bash_only)
    return any(_matches_apply_variant(v, code_bash, code_py, differing_files, py_only, bash_only)
               for v in variants)
