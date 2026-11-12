# Omarchy Customizer

[🇬🇧 English](README.md)

Один оверлей для всего оформления [Omarchy](https://omarchy.org): темы, обои, анимации Hyprland,
прозрачность, блюр и шейдеры экрана — с живым предпросмотром при листании. Если стоят плагины-компаньоны,
он же настраивает бар, экран блокировки, переходы обоев и стиль пикера.

Окно устроено как настройки в Material 3: рейл навигации (Главная и группы ниже), страница с хлебными крошками,
заголовком, поиском по всем настройкам и вкладками группы, сверху — карточка живого превью, под ней карточки
настроек (переключатели, сегменты, ползунки, образцы цвета) или галерея плиток. На Главной — что стоит сейчас и
быстрые действия. Окно следует теме, материалу (стекло / сплошной) и стилю DOT-MATRIX.

![Customizer](screenshots/home.webp)

<!-- Demo video: repo-videos/omarchy-customizer.mp4 — drag it here when editing this file on GitHub -->

| Группа | Что внутри |
|---|---|
| **Пресеты** | Полные снимки окружения (встроенный пресет **DOT-MATRIX** + свои пресеты в `~/.config/omarchy/customizer/presets/*.json` со ★, удаление по `D` и автоматический откат к предыдущим настройкам) и **Стиль** — форма окружения на любой теме: Flat, Стекло, Жидкое стекло, Fluent, DOT-MATRIX или свой (геометрия окон, бар, локскрин, лаунчер, виджеты, OSD, уведомления, анимации, прозрачность, блюр, звуки, Glyph, шрифты; какие разделы применять — выбирается) |
| **Рабочий стол** | Тема (палитра + превью), Обои (категории как в переключателе обоев), Recolor (перекраска любой картинки в цвета темы через lutgen), Dotify (генератор матричных LED-обоев и логотипа Arch), Wallpaper FX*, Виджеты*, Дашборд* |
| **Бар*** | Bar Skin (и «💾 Сохранить текущий скин» в `~/.config/omarchy/bar-skins/`, со ★ в списке; `D` удаляет после подтверждения), Bar Layout (свои раскладки так же — в `~/.config/omarchy/bar-layouts/`), Bar Tweaks — 41 параметр, у каждого виден дефолт и живой предпросмотр |
| **Окна** | Анимации (18 пресетов), Прозрачность, Блюр, OSD*, Уведомления* (со звуковыми пакетами и озвучкой событий окон/воркспейсов Hyprland), Glyph (контурная подсветка экрана и лучи зарядки в духе Nothing), Шейдер (CRT / TFT / чтение / плёнка / Game Boy) |
| **Блокировка*** | Дизайн экрана блокировки с превью в цветах темы, Lock Tweaks |
| **Пикеры*** | Стиль пикера тем / обоев, кэш миниатюр, скины Лаунчера* (в карточке — живое превью настоящего скина) |

\* появляется, только если стоит соответствующий плагин-компаньон — см. ниже.

| Тема | Обои (избранное, `D` — в корзину) |
| :---: | :---: |
| ![Тема](screenshots/themes.webp) | ![Обои](screenshots/wallpaper.webp) |
| **Стиль — живая сцена, `z` на весь размер** | **Скин бара** |
| ![Стиль](screenshots/styles-full.webp) | ![Скин бара](screenshots/bar-skins.webp) |
| **Анимации — кривые проигрываются в карточке** | **Шейдеры экрана** |
| ![Анимации](screenshots/anims.webp) | ![Шейдеры](screenshots/shaders.webp) |
| **Лаунчер — настоящий скин вживую** | **Шрифты** |
| ![Лаунчер](screenshots/launcher-full.webp) | ![Шрифты](screenshots/fonts.webp) |
| **Поиск по всем настройкам** | **Dotify в DOT-MATRIX** |
| ![Поиск](screenshots/search.webp) | ![Dotify](screenshots/dotmatrix-dotify.webp) |

Окно следует стилю: Стекло, Бумага и DOT-MATRIX —

![Стили](screenshots/styles.webp)

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

- `python3` и `jq` (оба есть в Omarchy).
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
| j k · h l | движение · рейл ⇄ страница (в галерее h l — по плиткам) |
| Tab / ⇧Tab · 0 · 1–6 | следующая / предыдущая вкладка · Главная · раздел рейла |
| ⏎ | применить · переключить · открыть |
| h l, − + | изменить настройку · x — сбросить · i — ввести значение |
| / | поиск по всем настройкам (↑↓ — результат из другого раздела, ⏎ — перейти) |
| v · z · n · J K | скрыть превью · превью на весь размер · описание поверх · прокрутить описание |
| f | избранная тема / обои (Тема, Обои) |
| D | удалить свой пресет / стиль / скин / раскладку бара; в Обоях — свои обои в корзину (спросит в окне) |
| p | проиграть / показать вживую (переходы, дизайны блокировки, пикер); в Лаунчере — открыть его скином под курсором, после закрытия — назад в Customizer |
| r | удиви меня |
| ? · q / Esc | все клавиши · закрыть |

Всё работает и мышью: ползунки тянутся, переключатели, сегменты и плитки нажимаются. Клавиши работают в любой раскладке (по физической клавише, как в US); ввод в поиске остаётся как напечатан.

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
o.bind("SUPER + ALT + R", "Toggle reading mode", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/reading-mode.sh")
```

## Режим чтения

`scripts/reading-mode.sh` (Super+Alt+R; toggle / on / off / status) превращает рабочий стол в печатную страницу для
долгого чтения: экранный шейдер `reading` (кривая e-ink, монохромные чернила на тёплой бумаге; зерно, волокна по
направлению и упорядоченный дизеринг 4×4 только на бумаге — края текста остаются чистыми; лёгкая виньетка; статичный,
самый дешёвый damage tracking), плоские окна (без отступов, чёрная рамка 1 px, прямые углы, без блюра, тени и
затемнения), без анимаций, яркость экрана 40%. Тёмной теме не нужна медленная смена темы: в режиме `auto` шейдер
инвертирует яркость, если тема тёмная, и страница всё равно светлая (фото тогда выглядят негативом — если это важно,
задай светлую **тему на время чтения** и `paper`). Выключение — просто перезагрузка Hyprland: `hypr/customizer.lua`
заново применяет стиль, вкладку «Окна» и шейдер, а скрипт возвращает только яркость и тему. Перезагрузка конфига во
время чтения страницу не сбрасывает (блок чтения в `hypr/customizer.lua`, а восстановление Customizer после
`configreloaded` заканчивается вызовом `reading-mode.sh look`).

Настройки — **Окна → Шейдер**, под списком шейдеров (`~/.config/omarchy/customizer/reading-mode.json`): тёмная
тема как страница (`auto` / `paper` / `invert`), шейдер страницы (`reading`, `paper`, `film`, `gameboy`, `none`),
сила текстуры бумаги, яркость (`0` — не трогать), тема на время чтения, плоские окна, оставить анимации. Изменение во
время чтения применяется сразу. Идея — режим чтения из [surface-dots](https://github.com/snes19xx/surface-dots),
код свой.

Новые шейдеры экрана: `reading`, `film` (чёрно-белая плёнка: плёночная кривая, застывшее зерно, виньетка) и
`gameboy` (четыре зелёных, упорядоченный дизеринг, сетка LCD).

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

## Как устроено

- **Окно** — `Customizer.qml`, части — в `ui/` (карточки, контролы, рейл, вкладки) и `previews/` (живые сцены: бар,
  окна, стили, анимации, шейдеры экрана, LED-матрица Dotify, OSD, уведомления, дашборд, блокировка, Glyph, звуки).
- **Бэкенд** — Python, только стандартная библиотека: `backend/customizer/`. Пока окно открыто, оно говорит с одним
  процессом (`backend/run.py serve`, строки JSON по stdin/stdout); окно закрыли — процесс выходит: закрытый Customizer
  ничего не тратит, открытый в простое спит в `read()`. Шаг настройки и перечитывание списка — около 2 мс.
  `customizer.sh <команда> …` — тонкая обёртка для остальных вызовов (хук темы, меню, fzf-скрипт).
- **Файл настроек** — каждая настройка (тип, пределы, умолчание, подпись, файл, куда пишется) описана в
  [`settings.json`](settings.json), по таблице на файл настроек. Подписи на английском, перевод — `i18n/<язык>.json`.
- **Тесты** — `tests/compare_*.py` сверяют бэкенд с прежней bash-версией (`tests/legacy/customizer.sh`) в одноразовой
  песочнице HOME с заглушками `hyprctl`/`omarchy-shell`/`zenity`: списки, команды, каждый шаг настройки и каждый
  `apply` должны совпасть байт в байт. Команды, которых у bash не было (`wall-delete`, `launcher-open` со скином и
  возвратом), проверяет `tests/test_new_commands.py`.
- **Превью шейдеров экрана** — `scripts/build-preview-shaders.py` переводит `shaders/*.frag` в Qt-варианты в
  `previews/shaders/screen/` (запускать после правки шейдера).

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
