#!/usr/bin/env python3
# Проверка полноты стилей: каждый стиль в styles/ задаёт те же ручки формы, что и остальные.
# Если у одного стиля раздела или ключа нет, переход на него оставит значение прежнего стиля
# (так было со звуком: NIHIL его задавал, Flat — нет).
#
#   python3 scripts/check-styles.py [styles-dir]
import json
import os
import sys

META = {"name", "name_ru", "note", "note_ru"}
# Взаимозаменяемые пары: скин / раскладка бара по имени или целиком.
ALT = {"barSkin": "barSkinData", "barSkinData": "barSkin", "barLayout": "barLayoutData", "barLayoutData": "barLayout"}


def keys(style):
    out = set()
    for k, v in style.items():
        if k in META:
            continue
        k = ALT.get(k, k) if k.endswith("Data") else k
        if isinstance(v, dict) and k not in ("barSkin", "barLayout"):
            out |= {f"{k}.{sub}" for sub in v}
        else:
            out.add(k)
    return out


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "styles")
    styles = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            with open(os.path.join(d, f)) as fh:
                styles[f[:-5]] = keys(json.load(fh))
    union = set().union(*styles.values())
    bad = False
    for name, ks in styles.items():
        missing = sorted(union - ks)
        if missing:
            bad = True
            print(f"{name}: нет {', '.join(missing)}")
    if not bad:
        print(f"ok: {len(styles)} стилей, {len(union)} ручек у каждого")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
