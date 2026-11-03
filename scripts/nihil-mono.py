#!/usr/bin/env python3
"""Nihil Mono — Geist Mono с включёнными лигатурами.

В официальном Geist Mono (OFL 1.1, Vercel) лигатуры (-> => != === :: …) уже нарисованы, но
включаются только набором ss11 — терминалы и редакторы без настройки их не показывают. Здесь те же
цепочки подстановок дополнительно подключаются к функции calt, которую приложения включают сами.
Кириллица — Geist Mono как есть. Значки Nerd Font терминалы берут из Symbols Nerd Font
(пакет ttf-nerd-fonts-symbols) — встраивать их не нужно.

Изменённую версию нельзя называть так же — семейство переименовано в «Nihil Mono».

    uv run --with fonttools scripts/nihil-mono.py <каталог GeistMono/ttf> <каталог вывода>
"""
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

FAMILY = "Nihil Mono"
STYLES = {"Regular": "Regular", "Bold": "Bold", "Italic": "Italic", "BoldItalic": "Bold Italic"}


def add_calt(font):
    """Функция calt со списком lookup набора ss11 — во всех системах письма и языках."""
    gsub = font["GSUB"].table
    ss11 = [fr for fr in gsub.FeatureList.FeatureRecord if fr.FeatureTag == "ss11"]
    if not ss11:
        raise SystemExit("в шрифте нет ss11 с лигатурами")
    lookups = sorted(ss11[0].Feature.LookupListIndex)
    rec = otTables.FeatureRecord()
    rec.FeatureTag = "calt"
    rec.Feature = otTables.Feature()
    rec.Feature.FeatureParams = None
    rec.Feature.LookupListIndex = lookups
    rec.Feature.LookupCount = len(lookups)
    feats = gsub.FeatureList.FeatureRecord
    feats.append(rec)
    # FeatureList должен быть отсортирован по тегу; индексы в LangSys пересчитываются.
    order = sorted(range(len(feats)), key=lambda i: feats[i].FeatureTag)
    remap = {old: new for new, old in enumerate(order)}
    gsub.FeatureList.FeatureRecord = [feats[i] for i in order]
    gsub.FeatureList.FeatureCount = len(feats)
    calt_index = remap[len(feats) - 1]
    for script in gsub.ScriptList.ScriptRecord:
        systems = [script.Script.DefaultLangSys] + [r.LangSys for r in script.Script.LangSysRecord]
        for ls in systems:
            if ls is None:
                continue
            ls.FeatureIndex = sorted(remap[i] for i in ls.FeatureIndex) + [calt_index]
            ls.FeatureIndex.sort()
            ls.FeatureCount = len(ls.FeatureIndex)


def rename(font, style):
    names = font["name"]
    full = f"{FAMILY} {style}" if style != "Regular" else FAMILY
    ps = f"{FAMILY.replace(' ', '')}-{style.replace(' ', '')}"
    for rec in list(names.names):
        if rec.nameID in (16, 17, 21, 22, 25):
            names.removeNames(nameID=rec.nameID)
    legacy_style = style if style in ("Regular", "Bold", "Italic", "Bold Italic") else "Regular"
    for nid, text in ((1, FAMILY), (2, legacy_style), (3, f"{ps};nihil"), (4, full), (6, ps)):
        names.setName(text, nid, 3, 1, 0x409)
        names.setName(text, nid, 1, 0, 0)
    names.setName("Nihil Mono is a modified version of Geist Mono (OFL 1.1) with ligatures enabled through "
                  "calt, for the Nihil Omarchy style.", 10, 3, 1, 0x409)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for file_style, style in STYLES.items():
        font = TTFont(os.path.join(src, f"GeistMono-{file_style}.ttf"))
        add_calt(font)
        rename(font, style)
        out = os.path.join(dst, f"NihilMono-{file_style}.ttf")
        font.save(out)
        print(out)


if __name__ == "__main__":
    main()
