#!/usr/bin/env python3
# Генератор встроенных стилей styles/*.json: одна таблица на все стили, проверка полноты (у каждого стиля —
# те же ручки, что у DOT-MATRIX) перед записью. DOT-MATRIX собирается из пресета-источника (свой пресет в духе Nothing).
#
#   python3 scripts/gen-styles.py <каталог плагина> <пресет-источник DOT-MATRIX.json>
#   python3 scripts/check-styles.py            # только проверить
import json, os, sys

plugin = sys.argv[1]
src = sys.argv[2]  # nothing-hacking.json
out = os.path.join(plugin, "styles")

# «Содержимое», а не форма: что видно и в каком формате — остаётся за пользователем.
CONTENT = {
    "widgets": ["clock", "media", "visualizer", "sysinfo", "edgeHover", "dashMedia", "dashCalendar", "dashWeather", "dashStats"],
    "lock": ["clock24", "showSeconds", "showDate"],
    "sounds": ["sounds", "soundVolume"],
    "imagePicker": ["autoCache"],
    "glyph": ["glyphCharger", "glyphCriticalRed"],
    "osd": ["osdShowValue"],
}

nh = json.load(open(src))
dotmatrix = {k: v for k, v in nh.items() if k not in ("theme", "wallpaper", "name", "name_ru", "note", "note_ru")}
for sec, keys in CONTENT.items():
    for k in keys:
        dotmatrix.get(sec, {}).pop(k, None)
dotmatrix["hyprGeometry"]["noGaps"] = True
dotmatrix["notifications"].setdefault("notifyAttach", "auto")
dotmatrix["fonts"] = "pixel"
# Nothing: плоское «железо» — без теней, сплошные поверхности, шрифт профиля.
dotmatrix["look"] = {"elevation": 0, "motion": 1, "material": "solid", "cornerScale": 1, "typeface": "profile", "texture": ""}
dotmatrix = {
    "name": "DOT-MATRIX", "name_ru": "DOT-MATRIX",
    "note": "Nothing-inspired hardware shell on any theme: bezel frame with windows flush against it, vertical LED bar, dot-matrix typography, signal colour strictly for alerts, perimeter Glyph lighting, LED dashboard/OSD/launcher/lock and a tactile sound pack.",
    "note_ru": "Аппаратная оболочка в духе Nothing на любой теме: рамка-бортик с окнами вплотную, вертикальный LED-бар, матричная типографика, сигнальный цвет строго для тревог, контурная подсветка Glyph, LED-дашборд/OSD/лаунчер/локскрин и тактильный звуковой пакет.",
    **dotmatrix,
}


def plain(name, name_ru, note, note_ru, *, geom, bar, opacity, blur, anims, lock, launcher, radius, alpha,
          cards, fx, picker, dash_anim, sound_pack, window_sounds, fonts, look, osd_side="right", attach="auto", shader="off"):
    return {
        "name": name, "name_ru": name_ru, "note": note, "note_ru": note_ru,
        "anims": anims, "opacity": opacity, "blur": blur, "shader": shader,
        "hyprGeometry": {**geom, "noGaps": False},
        "barSkin": bar, "barLayout": "omarchy-stock", "barTransparent": False,
        "lock": {"design": lock, "wallpaperBlur": 0.6 if lock == "style-glass" else 0, "wallpaperDim": 0.35},
        "launcher": {"skin": launcher, "backdrop": 0.6 if alpha < 0.9 else 0.75},
        "wallpaperFx": fx,
        "imagePicker": {"style": picker, "cardRadius": radius, "selectedBorder": 2 if cards == "flat" else 1, "dim": 0.5},
        "widgets": {
            "widgetStyle": "style", "clockStyle": "big" if cards != "flat" else "minimal",
            "dashStyle": "default", "dashFollowBar": True, "dashAttach": attach, "dashBackground": "background",
            "dashAlpha": alpha, "dashRadius": radius, "dashBorder": cards != "flat",
            "dashAnimation": dash_anim, "dashDuration": fx["duration"] // 2 + 100,
        },
        "osd": {
            "osdStyle": "edge", "osdFollowBar": True, "osdAttach": attach, "osdBackground": "background",
            "osdAlpha": alpha, "osdRadius": radius, "osdSide": osd_side, "osdAlign": "center",
        },
        "notifications": {
            "notifyStyle": "drawer", "notifyFollowBar": True, "notifyAttach": attach, "notifyBackground": "background", "notifyAlpha": alpha,
            "notifyRadius": radius, "notifyCards": cards, "notifyCorner": "top-right", "notifyWidth": 380,
        },
        "sounds": {"soundPack": sound_pack, "windowSounds": window_sounds},
        "glyph": {"glyphEnabled": False, "glyphColor": "foreground", "glyphCriticalColor": "urgent",
                  "glyphDuration": 1100, "glyphThickness": 2.5, "glyphInsetMode": "auto"},
        "fonts": fonts,
        "look": {"texture": "", **look},
    }


styles = {
    "dotmatrix": dotmatrix,
    "flat": plain(
        "Flat", "Плоский",
        "Flat / Metro: square corners, solid surfaces, no shadows or blur, quick motion, quiet. Typography and colour do all the work.",
        "Flat / Metro: прямые углы, сплошные поверхности, без теней и блюра, быстрые анимации, тихо. Всю работу делают шрифт и цвет.",
        geom={"gapsIn": 4, "gapsOut": 8, "borderSize": 2, "rounding": 0, "shadow": False},
        bar="solid-accent", opacity="solid", blur="off", anims="ML4W - fast", lock="style-flat", launcher="drawer-flat",
        radius=0, alpha=1, cards="flat", fx={"type": "fade", "duration": 300, "easing": "OutCubic"},
        picker="slices", dash_anim="fade", sound_pack="flat", window_sounds=True, fonts="stock",
        look={"elevation": 0, "motion": 0.7, "material": "solid", "cornerScale": 0, "typeface": "shell"}),
    "glass": plain(
        "Glass", "Стекло",
        "Glassmorphism: translucent windows over a frosted wallpaper, glass bar and panels, soft round corners, smooth motion and soft clicks.",
        "Глассморфизм: полупрозрачные окна над матовыми обоями, стеклянный бар и панели, мягкие скругления, плавные анимации и мягкие щелчки.",
        geom={"gapsIn": 6, "gapsOut": 14, "borderSize": 1, "rounding": 16, "shadow": True},
        bar="glass", opacity="frosted", blur="frosted", anims="HYDE - default", lock="style-glass", launcher="drawer-glass",
        radius=18, alpha=0.75, cards="bordered", fx={"type": "fade", "duration": 700, "easing": "OutCubic"},
        picker="cards", dash_anim="grow", sound_pack="glass", window_sounds=True, fonts="stock",
        look={"elevation": 1, "motion": 1.25, "material": "glass", "cornerScale": 1.2, "typeface": "shell"}),
    "fluent": plain(
        "Fluent", "Fluent",
        "Material / Fluent: layered surfaces with depth — gentle rounding, real shadows, a hint of translucency, island bar, card panels and the theme's own sounds.",
        "Material / Fluent: слои с глубиной — умеренные скругления, настоящие тени, лёгкая полупрозрачность, бар-острова, карточки и звуки самой темы.",
        geom={"gapsIn": 5, "gapsOut": 10, "borderSize": 1, "rounding": 8, "shadow": True},
        bar="islands", opacity="soft", blur="medium", anims="01-default - v2", lock="style-fluent", launcher="drawer-fluent",
        radius=10, alpha=0.9, cards="bordered", fx={"type": "fade", "duration": 450, "easing": "OutCubic"},
        picker="cards", dash_anim="slide", sound_pack="fluent", window_sounds=True, fonts="nothing",
        look={"elevation": 2, "motion": 1, "material": "auto", "cornerScale": 0.8, "typeface": "profile"}),    "neumorph": plain(
        "Neumorphism", "Неоморфизм",
        "Neumorphism: soft extruded plastic — no borders, panels in the background colour with a light and a dark shadow, generous round corners, muted soft sounds.",
        "Неоморфизм: мягкий выдавленный пластик — без рамок, панели цвета фона со светлой и тёмной тенью, крупные скругления, приглушённые мягкие звуки.",
        geom={"gapsIn": 10, "gapsOut": 22, "borderSize": 0, "rounding": 18, "shadow": True},
        bar="soft", opacity="solid", blur="off", anims="HYDE - minimal-1", lock="style-neumorph", launcher="drawer-neumorph",
        radius=20, alpha=1, cards="flat", fx={"type": "fade", "duration": 550, "easing": "OutCubic"},
        picker="cards", dash_anim="grow", sound_pack="neumorph", window_sounds=True, fonts="nothing",
        attach="floating",
        look={"elevation": 1, "motion": 1.0, "material": "soft", "cornerScale": 1.3, "typeface": "profile"}),
    "brutal": plain(
        "Brutalism", "Брутализм",
        "Brutalism: square everything, thick ink borders, hard offset shadows without blur, no transparency, fast motion and hard clicks.",
        "Брутализм: всё прямоугольное, толстые рамки цвета текста, жёсткие смещённые тени без размытия, никакой прозрачности, быстрые анимации и жёсткие клики.",
        geom={"gapsIn": 8, "gapsOut": 16, "borderSize": 3, "rounding": 0, "shadow": False},
        bar="brutal", opacity="solid", blur="off", anims="ML4W - fast", lock="style-brutal", launcher="drawer-brutal",
        radius=0, alpha=1, cards="bordered", fx={"type": "fade", "duration": 250, "easing": "OutCubic"},
        picker="slices", dash_anim="fade", sound_pack="brutal", window_sounds=True, fonts="stock",
        attach="floating",
        look={"elevation": 0, "motion": 0.6, "material": "brutal", "cornerScale": 0, "typeface": "shell"}),
    "retro": plain(
        "Retro 9x", "Ретро 9x",
        "Retro desktop of the nineties: grey panels with a 3D bevel, square windows, pixel interface font, no animations and chiptune sounds.",
        "Ретро-десктоп девяностых: серые панели с объёмным кантом, квадратные окна, пиксельный шрифт интерфейса, без анимаций и чиптюн-звуки.",
        geom={"gapsIn": 3, "gapsOut": 6, "borderSize": 2, "rounding": 0, "shadow": False},
        bar="bevel", opacity="solid", blur="off", anims="03- Disable Animation", lock="style-retro", launcher="drawer-retro",
        radius=0, alpha=1, cards="bordered", fx={"type": "fade", "duration": 200, "easing": "OutCubic"},
        picker="slices", dash_anim="fade", sound_pack="retro", window_sounds=True, fonts="retro",
        attach="floating",
        look={"elevation": 0, "motion": 0, "material": "bevel", "cornerScale": 0, "typeface": "profile"}),
    "neon": plain(
        "Neon / Cyber", "Неон",
        "Neon / cyber: dark glass, borders and panels glowing in the accent colour, a light scanline shader over the screen and synth sounds with a filter sweep.",
        "Неон / кибер: тёмное стекло, рамки и панели светятся цветом акцента, лёгкий шейдер строк развёртки на экране и синт-звуки с проходом фильтра.",
        geom={"gapsIn": 6, "gapsOut": 14, "borderSize": 2, "rounding": 8, "shadow": True},
        bar="neon", opacity="glass", blur="strong", anims="END-4", lock="style-neon", launcher="drawer-neon",
        radius=10, alpha=0.9, cards="bordered", fx={"type": "fade", "duration": 500, "easing": "OutCubic"},
        picker="cards", dash_anim="slide", sound_pack="neon", window_sounds=True, fonts="stock",
        attach="floating", shader="neon",
        look={"elevation": 1, "motion": 1.1, "material": "glow", "cornerScale": 0.8, "typeface": "shell"}),
    "paper": plain(
        "Paper", "Бумага",
        "Paper / sketchbook: panels are sheets of paper with a torn bottom edge, grain and a strip of tape, handwritten Caveat, a paper bar, a paper grain shader over the whole screen and calm motion. Colours stay the theme's: a light theme gives white paper, a dark one — kraft.",
        "Бумага / скетчбук: панели — листы с рваным нижним краем, зерном и полоской скотча, рукописный Caveat, бумажный бар, шейдер бумажного зерна на весь экран и спокойные анимации. Цвета остаются от темы: светлая даёт белую бумагу, тёмная — крафт.",
        geom={"gapsIn": 8, "gapsOut": 18, "borderSize": 2, "rounding": 6, "shadow": True},
        bar="paper", opacity="solid", blur="off", anims="ML4W - standard", lock="style-paper", launcher="drawer-paper",
        radius=8, alpha=1, cards="bordered", fx={"type": "fade", "duration": 600, "easing": "OutCubic"},
        picker="cards", dash_anim="fade", sound_pack="paper", window_sounds=True, fonts="paper-ui",
        attach="floating", shader="paper",
        look={"elevation": 2, "motion": 1.1, "material": "paper", "cornerScale": 0.5, "typeface": "hand",
              "texture": "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/textures/paper.png"}),

}

# Полнота: каждый стиль задаёт те же ручки, что и DOT-MATRIX, иначе переход между стилями будет неполным.
def shape(d):
    return {k: (sorted(v) if isinstance(v, dict) else None) for k, v in d.items()
            if k not in ("name", "name_ru", "note", "note_ru", "barSkin", "barSkinData", "barLayout", "barLayoutData")}

ref = shape(styles["dotmatrix"])
bad = False
for name, st in styles.items():
    sh = shape(st)
    for k in ref:
        if k not in sh:
            print(f"{name}: missing {k}"); bad = True
        elif ref[k] and set(ref[k]) - set(sh[k] or []):
            print(f"{name}.{k}: missing {sorted(set(ref[k]) - set(sh[k] or []))}"); bad = True
if bad:
    sys.exit(1)
# Тема стиля (переключатель styleTheme): пара тёмная / светлая.
THEMES = {"dotmatrix": ("nothing-steel", "nothing-ashlight"), "flat": ("matte-black", "white"),
          "glass": ("catppuccin", "catppuccin-latte"), "fluent": ("tokyo-night", "rose-pine"),
          "paper": ("kanagawa", "kanagawa-lotus"), "neumorph": ("nord", "bliss"),
          "brutal": ("gruvbox-material", "flexoki-light"), "retro": ("ibm", "bliss"), "neon": ("cyber-aura", "")}
for name, st in styles.items():
    dark, light = THEMES[name]
    st["theme"] = {"dark": dark, "light": light or dark}
for name, st in styles.items():
    with open(os.path.join(out, name + ".json"), "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
        f.write("\n")
print("ok:", ", ".join(styles))
