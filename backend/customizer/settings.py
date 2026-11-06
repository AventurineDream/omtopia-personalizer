"""settings.json: таблицы настроек (категория, файл, пункты с типом, пределами и подписью)."""
import json
from dataclasses import dataclass, field

from . import paths


@dataclass
class Item:
    key: str = ""
    type: str = ""
    label: str = ""
    section: str = ""             # не пусто — это заголовок раздела
    values: list = field(default_factory=list)
    min: float = 0
    max: float = 0
    step: float = 0
    default: object = None

    @property
    def is_section(self) -> bool:
        return bool(self.section)

    @property
    def args(self) -> str:
        """Аргументы в прежнем виде «ключ|тип|аргументы|подпись» (поле 8 вывода list)."""
        if self.type == "num":
            return f"{_num(self.min)} {_num(self.max)} {_num(self.step)} {_num(self.default)}"
        if self.type == "enum":
            return " ".join(self.values)
        if self.type == "bool":
            return "true" if self.default else "false"
        if self.type == "color":
            return str(self.default)
        return ""

    @property
    def default_value(self) -> str:
        """Значение по умолчанию строкой — как def в list_tweaks."""
        if self.type == "num":
            return _num(self.default)
        if self.type == "enum":
            return self.values[0] if self.values else ""
        if self.type in ("bool", "color"):
            return self.args
        return ""


@dataclass
class Table:
    id: str
    category: str
    value_prefix: str
    file: str
    items: list


def _num(x) -> str:
    """Число как в settings.json (как вывел бы jq): 2 → "2", 0.05 → "0.05"."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    return repr(x)


_tables = None


def tables() -> dict:
    global _tables
    if _tables is None:
        doc = json.loads(paths.SETTINGS_JSON.read_text())
        _tables = {}
        for t in doc["tables"]:
            items = []
            for it in t["items"]:
                if "section" in it:
                    items.append(Item(section=it["section"]))
                else:
                    items.append(Item(key=it["key"], type=it["type"], label=it["label"], values=it.get("values", []),
                                      min=it.get("min", 0), max=it.get("max", 0), step=it.get("step", 0),
                                      default=it.get("default")))
            _tables[t["id"]] = Table(t["id"], t["category"], t["valuePrefix"], t["file"], items)
    return _tables


def table(table_id: str) -> Table:
    return tables()[table_id]


def find(key: str):
    """(Table, Item) по ключу настройки, как tweak_spec + tweak_file."""
    for tbl in tables().values():
        for it in tbl.items:
            if it.key == key:
                return tbl, it
    return None, None
