"""Чтение JSON-конфигов и значения «как jq tostring»."""
import json


def read(path):
    """Объект из файла; нет файла, он пуст или битый — None."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def read_object(path) -> dict:
    data = read(path)
    return data if isinstance(data, dict) else {}


def tostring(value) -> str:
    """Как `tostring` в jq: строка — как есть, остальное — компактный JSON."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        return repr(value) if value != int(value) or "e" in repr(value) else repr(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
