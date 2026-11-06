"""Файлы и процессы так же, как их видел bash: find -L, sort по правилам локали, $(…) без хвостовых \\n."""
import locale
import os
import re
import shutil
import subprocess

try:
    locale.setlocale(locale.LC_COLLATE, "")
except locale.Error:
    pass

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def lsort(items, key=None):
    """Как `sort`: по правилам локали (strcoll), а не по кодам символов."""
    k = key or (lambda s: s)
    return sorted(items, key=lambda x: (locale.strxfrm(k(x)), k(x)))


def walk_files(root, maxdepth):
    """Файлы как `find -L root -maxdepth N -type f` (корень — глубина 0)."""
    root = str(root)
    if not os.path.isdir(root):
        return []
    out = []
    base = root.rstrip("/").count("/")
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        depth = dirpath.rstrip("/").count("/") - base
        if depth >= maxdepth - 1:
            dirnames[:] = []
        for name in filenames:
            p = os.path.join(dirpath, name)
            if os.path.isfile(p):
                out.append(p)
        if depth + 1 > maxdepth:
            break
    return out


def images_in(root, maxdepth, exts=IMAGE_EXT):
    """images_in: картинки в каталоге до глубины maxdepth, отсортированные как `sort`."""
    return lsort([p for p in walk_files(root, maxdepth) if p.lower().endswith(exts)])


def glob_sorted(pattern_dir, suffix, dirs=False):
    """Как bash-глоб "$dir"/*<suffix> (без скрытых, по правилам локали)."""
    d = str(pattern_dir)
    try:
        names = os.listdir(d)
    except OSError:
        return []
    out = []
    for n in names:
        if n.startswith(".") or not n.endswith(suffix):
            continue
        p = os.path.join(d, n)
        if (os.path.isdir(p) if dirs else os.path.isfile(p)):
            out.append(p)
    return lsort(out)


def read_text(path) -> str:
    """Как $(cat файл): содержимое без хвостовых переводов строк; нет файла — None."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().rstrip("\n")
    except OSError:
        return None


def nonempty(path) -> bool:
    """[[ -s файл ]]"""
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False


def run(args, stdin=None) -> str:
    """$(команда): stdout без хвостовых \\n; ошибка запуска — пусто."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, input=stdin)
    except OSError:
        return ""
    return p.stdout.rstrip("\n")


def which(name) -> bool:
    return shutil.which(name) is not None


def tsv_escape(s: str) -> str:
    """Экранирование @tsv из jq."""
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def read_fields(line: str, n: int):
    """Как `IFS=$'\\t' read -r a b c …`: табы — пробельный разделитель (подряд — один),
    последнее поле забирает остаток."""
    parts = re.split(r"\t+", line.strip("\t"), maxsplit=n - 1) if line.strip("\t") else []
    return parts + [""] * (n - len(parts))


def read_ws(line: str, n: int):
    """Как `read -r a b c …` с обычным IFS (пробелы и табы)."""
    parts = line.split(None, n - 1)
    return parts + [""] * (n - len(parts))
