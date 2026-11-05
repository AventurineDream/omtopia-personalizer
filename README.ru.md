# Omarchy Customizer

[🇬🇧 English](README.md)

Один оверлей для всего оформления [Omarchy](https://omarchy.org): темы, обои, анимации Hyprland,
прозрачность, блюр и шейдеры экрана — с живым предпросмотром при листании. Если стоят плагины-компаньоны,
он же настраивает бар, экран блокировки, переходы обоев и стиль пикера.

![Рабочий стол](screenshots/desktop.webp)

| Группа | Что внутри |
|---|---|
| **Пресеты** | Полные снимки окружения (встроенный пресет **DOT-MATRIX** + свои пресеты в `~/.config/omarchy/customizer/presets/*.json` со ★, удаление по `D` и автоматический откат к предыдущим настройкам) и **Стиль** — форма окружения на любой теме: Flat, Стекло, Fluent, DOT-MATRIX или свой (геометрия окон, бар, локскрин, лаунчер, виджеты, OSD, уведомления, анимации, прозрачность, блюр, звуки, Glyph, шрифты; какие разделы применять — выбирается) |
| **Рабочий стол** | Тема (палитра + превью), Обои (категории как в переключателе обоев), Recolor (перекраска любой картинки в цвета темы через lutgen), Dotify (генератор матричных LED-обоев и логотипа Arch), Wallpaper FX*, Виджеты*, Дашборд* |
| **Бар*** | Bar Skin (и «💾 Сохранить текущий скин» в `~/.config/omarchy/bar-skins/`, со ★ в списке; `D` удаляет после подтверждения), Bar Layout (свои раскладки так же — в `~/.config/omarchy/bar-layouts/`), Bar Tweaks — 41 параметр, у каждого виден дефолт и живой предпросмотр |
| **Окна** | Анимации (18 пресетов), Прозрачность, Блюр, OSD*, Уведомления* (со звуковыми пакетами и озвучкой событий окон/воркспейсов Hyprland), Glyph (контурная подсветка экрана и лучи зарядки в духе Nothing), Шейдер (CRT / TFT) |
| **Блокировка*** | Дизайн экрана блокировки с превью в цветах темы, Lock Tweaks |
| **Пикеры*** | Стиль пикера тем / обоев, кэш миниатюр, скины Лаунчера* |

\* появляется, только если стоит соответствующий плагин-компаньон — см. ниже.

| Бар | Окна |
| :---: | :---: |
| ![Бар](screenshots/bar.webp) | ![Окна](screenshots/windows.webp) |
| **Блокировка** | **Пикеры** |
| ![Блокировка](screenshots/lock.webp) | ![Пикеры](screenshots/pickers.webp) |

## Установка

```sh
omarchy plugin add https://github.com/KamradSmeshnyavy/omarchy-customizer --enable
omarchy restart shell
```

Бинд в `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + T", "Omarchy Customizer", "omarchy-shell shell toggle kamradsmeshnyavy.customizer")
```

**Всё сразу** — `install.sh` ставит Customizer и спрашивает про каждый плагин-компаньон (всё через
`omarchy plugin add`), подключает шрифты DOT-MATRIX, добавляет бинд **Super+Shift+T** в
`~/.config/hypr/bindings.lua` и перезапускает шелл. Он идёт вместе с плагином — прочитайте и запустите:

```sh
less ~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/install.sh
bash ~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/install.sh            # --all — все компаньоны, --with bar,lock — только эти, --none — только Customizer
```

### Плагины-компаньоны

Каждый — отдельный плагин; Customizer находит их сам.

| Плагин | Что добавляет в Customizer |
|---|---|
| [omarchy-bar-skins](https://github.com/KamradSmeshnyavy/omarchy-bar-skins) | группа **Бар**: 20 скинов (вкл. `dotmatrix`), 10 раскладок, compact, LED и символьные стили workspaces |
| [omarchy-lock-designs](https://github.com/KamradSmeshnyavy/omarchy-lock-designs) | группа **Блокировка**: 22 дизайна (вкл. `dotmatrix`) |
| [omarchy-wallpaper-fx](https://github.com/KamradSmeshnyavy/omarchy-wallpaper-fx) | **Wallpaper FX**: 24 перехода с превью |
| [omarchy-image-picker-styles](https://github.com/KamradSmeshnyavy/omarchy-image-picker-styles) | группа **Пикеры**: шесть стилей |
| [omarchy-launcher-skins](https://github.com/KamradSmeshnyavy/omarchy-launcher-skins) | **Лаунчер** в Пикерах: полноэкранные скины и аппаратный выступ `dotmatrix` |
| [omarchy-desktop-widgets](https://github.com/KamradSmeshnyavy/omarchy-desktop-widgets) | **Виджеты** и **Дашборд** на Рабочем столе: карточки, LED-дашборд DOT-MATRIX и шторка быстрых настроек |
| [omarchy-edge-osd](https://github.com/KamradSmeshnyavy/omarchy-edge-osd) | **OSD** в Окнах: громкость и яркость у края экрана (вкл. LED-шкалу DOT-MATRIX) |
| [omarchy-drawer-notifications](https://github.com/KamradSmeshnyavy/omarchy-drawer-notifications) | **Уведомления** в Окнах: шторка или аппаратные карточки DOT-MATRIX + запуск подсветки Glyph |

### Необязательные программы

- `libvips` — быстрые миниатюры тем и обоев (пакет `libvips`)
- `zenity` — диалоги выбора цвета, текста и файла в твиках
- плагин `kamradsmeshnyavy.widgets` — категория **Виджеты** на Рабочем столе (часы, сейчас играет, визуализатор cava, кольца системы)
- `lutgen` — Recolor (виден, только когда есть и lutgen, и zenity)
- `omarchy-wallpaper-theme` в `PATH` + `matugen` — строки «🎨 Тема из обоев» в **Теме**: тема `dynamic` в стиле Material You из текущих обоев ([скрипт](https://github.com/KamradSmeshnyavy/dotfiles/blob/main/omarchy-themes/scripts/omarchy-wallpaper-theme))

## Требования

Omarchy 4 (Quattro) с его оболочкой. Проверено на Omarchy 4.0.6 и Quickshell 0.3.2.

- `jq` (есть в Omarchy).
- Необязательно: `libvips` (миниатюры), `zenity` (диалоги цвета, текста, файлов), `lutgen` (Recolor), `matugen` (тема из обоев), `ffmpeg` и `pipewire` (`pw-play`) — звуки, `uv` — сборка шрифтов Dotify. Функция без своей программы просто скрывается.
- Плагины-компаньоны — по желанию, см. таблицу выше.

## Удаление

```sh
omarchy plugin remove kamradsmeshnyavy.customizer
omarchy restart shell
```

Если ставили через `install.sh` — удалите и строку Super+Shift+T, которую он добавил в `~/.config/hypr/bindings.lua`, и ссылку `~/.local/share/fonts/dotmatrix`.

Настройки остаются в `~/.config/omarchy/customizer.json`, `~/.config/omarchy/customizer/`, `~/.config/omarchy/style.json`, `~/.local/state/omarchy-customizer/`, `~/.local/state/hypr/{opacity,blur,screen-shader}` — удалите их вручную, если не нужны.

## Клавиши

| Клавиши | |
|---|---|
| Tab / 1–6 | группы |
| j k · l ⏎ · h | вверх-вниз · открыть · назад |
| / | поиск |
| h l, − + | изменить твик · x — сбросить |
| p | проиграть / показать вживую (переходы, дизайны lock, пикер) |
| r | случайный выбор |
| ? · q / Esc | все клавиши · закрыть |

## Как выбор переживает перезагрузку

Пресет анимаций хранится в `~/.local/state/omarchy-customizer/animations.lua`; прозрачность, блюр и шейдер —
в `~/.local/state/hypr/{opacity,blur,screen-shader}`. Customizer применяет их при старте шелла и после
каждого `hyprctl reload`. Чтобы при перезагрузке конфига не мелькали даже на миг дефолты, подключи хук в
конфиге Hyprland (например, в конце `~/.config/hypr/looknfeel.lua`):

```lua
dofile(os.getenv("HOME") .. "/.config/omarchy/plugins/kamradsmeshnyavy.customizer/hypr/customizer.lua")
```

Скрипты работают и сами по себе — их можно повесить на клавиши:

```lua
o.bind("SUPER + ALT + O", "Next transparency preset", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/opacity.sh next")
o.bind("SUPER + ALT + U", "Next blur preset", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/blur.sh next")
o.bind("SUPER + ALT + C", "Toggle screen shader", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/crt-toggle.sh")
```

## Свои пресеты

- Пресеты окружения: `~/.config/omarchy/customizer/presets/*.json` (сохраняются прямо из вкладки **Пресеты**).
- Анимации: `~/.config/omarchy/customizer/animations/*.lua` (Lua Hyprland: `hl.curve`, `hl.animation`).
  Файл с тем же именем, что у встроенного, заменяет его.
- Шейдеры: `~/.config/omarchy/customizer/shaders/*.frag`. Шейдеру с `time` автоматически ставится
  `damage_tracking = 0`, искажающему — `1`.

## Окна и виджеты

**Окна → Окна**: отступы между окнами и от краёв экрана, толщина рамки, «без отступов» Omarchy, скругление всех окон,
тень и её размер, затемнение неактивных, раскладка (dwindle / master) и углы окон — `~/.config/omarchy/customizer/windows.json`,
применяет `hypr/customizer.lua` поверх геометрии стиля (стиль пишет туда и свою), с живым мини-экраном. **Рабочий
стол → Виджеты** показывает раскладку включённых виджетов на мини-столе и подсвечивает наложения красным. Открыть
оверлей сразу на вкладке: `omarchy-shell shell toggle kamradsmeshnyavy.customizer '{"category":"windows"}'`.

## Стили

Тема — цвета и обои, **стиль** — форма, пресет — тема + стиль + обои. Стиль — файл пресета без `theme` /
`wallpaper` плюс `fonts` (профиль `omarchy-font-profile`). Его разделы вливаются в текущие настройки: стиль меняет
вид, а не набор виджетов. Встроенные стили — в `styles/`, свои — в `~/.config/omarchy/customizer/styles/*.json`
(★, удаление по `D`; «Сохранить текущий вид как стиль» во вкладке **Стиль**). Переключатели под списком
(`~/.config/omarchy/customizer/style-apply.json`) задают, что применять. Пресет может сослаться на стиль
(`"style": "<id>"`): сначала применяется стиль, затем поля пресета поверх. Откат — та же строка «Восстановить
прежнюю настройку» во вкладке **Пресеты**.

Блок `look` стиля пишется в `~/.config/omarchy/style.json` с id стиля — это токены панелей (тени, скорость анимаций,
материал, углы, шрифт) для `BarStyle.qml` в omarchy-desktop-widgets, omarchy-edge-osd и omarchy-drawer-notifications.

**Неоморфизм, Брутализм, Ретро 9x, Неон** — панели своим материалом (мягкий рельеф, толстая рамка с жёсткой
тенью, объёмный кант, свечение акцента), свои скины бара (`soft`, `brutal`, `bevel`, `neon`), пары тем, звуковые пакеты,
вид GTK / Firefox; у Неона шейдер строк развёртки `neon`, у Ретро пиксельный профиль шрифтов `retro`.

**Бумага** — листы бумаги вместо панелей (рваный нижний край, зерно, полоска скотча цветом акцента), рукописный
[Caveat](https://github.com/googlefonts/caveat) (OFL, лежит в `fonts/`), скин бара `paper` и шейдер экрана `paper`
(статичное зерно на весь экран вместе с окнами; без `time`, самый дешёвый режим damage tracking). Цвета остаются от
темы: светлая даёт белую бумагу, тёмная — крафт / грифель. Тайл зерна генерирует `scripts/paper-texture.py`
(`textures/paper.png` для светлых панелей, `paper-dark.png` для тёмных).

`python3 scripts/check-styles.py` проверяет, что все стили задают одинаковый набор ручек.

Каждый стиль задаёт все ручки формы (у встроенных один набор ключей), поэтому переход между любыми двумя стилями
полный. `hyprGeometry.noGaps` управляет тогглом Omarchy «без отступов» (он же снимает рамки окон): DOT-MATRIX включает
его — окна вплотную к рамке-бортику, остальные стили и пресет с `"hyprGeometry": null` выключают, рамки возвращаются.

## Язык

Английский и русский. Язык берётся из `"lang"` в `~/.config/omarchy/customizer.json`, иначе из `$LANG`
(`ru*` → русский). Переводы — `i18n/<язык>.json`, ключ — английская строка: новый язык — ещё один файл.

## Лицензия

GPL-3.0 — см. [LICENSE](LICENSE) и [NOTICE](NOTICE). Пресеты анимаций — из
[HyDE](https://github.com/HyDE-Project/HyDE), [ML4W](https://github.com/mylinuxforwork/dotfiles),
[end-4](https://github.com/end-4/dots-hyprland) и [DOT-MATRIX](https://github.com/poligle/Nihil-Shell)
([авторы](animations/CREDITS.md)); Dotify, подсветка Glyph и звуковые пакеты DOT-MATRIX портированы из
[DOT-MATRIX](https://github.com/poligle/Nihil-Shell) (MIT, Pol Iglesias); оверлей сделан в стиле
собственных плагинов шелла [Omarchy](https://github.com/basecamp/omarchy) (MIT).

Часть [моих dotfiles](https://github.com/KamradSmeshnyavy/dotfiles).
