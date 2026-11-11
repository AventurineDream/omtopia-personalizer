import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Wayland
import Quickshell.Widgets
import QtQuick 6.11
import QtQuick.Effects
import qs.Commons
import qs.Ui
import "dotmatrix" as DotMatrix
import "ui"
import "previews" as Previews

// Quickshell port of scripts/bin/omarchy-customizer (the old fzf menu on
// SUPER+SHIFT+T), laid out like a Material 3 settings app: navigation rail
// (Home + groups) | page with breadcrumbs, title, global search, category tabs,
// a live-preview hero card and setting cards / gallery tiles, plus a key-hint footer.
// Everything works from the keyboard (yazi-style keys) and with the mouse.
// customizer.sh next to this file does the listing and applying, so the
// actions stay identical to the shell script. Visual pieces live in ui/.
Item {
  id: root

  property var shell: null
  property var manifest: null

  readonly property string thumbDir: Quickshell.env("XDG_CACHE_HOME") ? Quickshell.env("XDG_CACHE_HOME") + "/omarchy-customizer/thumbs"
    : Quickshell.env("HOME") + "/.cache/omarchy-customizer/thumbs"
  readonly property string script: decodeURIComponent(String(Qt.resolvedUrl("customizer.sh")).replace(/^file:\/\//, ""))
  readonly property string pluginDir: script.replace(/\/customizer\.sh$/, "")

  // key: customizer.sh category; image: preview pane shows the picture;
  // live: hovering a row previews it, Esc / leaving the category reverts;
  // bar: preview pane draws a bar mock (BarMock.qml); tweak: h/l step the row's value.
  readonly property var allCategories: [
    { group: "presets", key: "presets",   icon: "󰆓", title: "Presets",      hint: "Full desktop snapshots · D — delete",   image: false, live: false, presetStage: true },
    { group: "presets", key: "styles",    icon: "󰉦", title: "Style",        hint: "Form on any theme · D — delete",         image: false, live: false, presetStage: true },
    { group: "presets", key: "fonts",     icon: "󰛖", title: "Fonts",        hint: "System font profiles, by style",          image: false, live: false },
    { group: "presets", key: "sounds",    icon: "󰕾", title: "Sounds",       hint: "Sound packs · p — listen",               image: false, live: false },
    { group: "desk", key: "themes",       icon: "󰏘", title: "Theme",        hint: "omarchy theme set · f — favorite",      image: true,  live: false },
    { group: "desk", key: "theme-walls",  icon: "󰸉", title: "Wallpaper",    hint: "Categories as in SUPER+CTRL+SPACE",      image: true,  live: false },
    { group: "desk", key: "walls",        icon: "󰃣", title: "Recolor",      hint: "Lutgen · O folder · o image(s)",       image: true,  live: false },
    { group: "desk", key: "dotify",       icon: "󰇄", title: "Dotify",       hint: "LED dot-matrix · O folder · o image(s)", image: true, live: false },
    { group: "desk", key: "wallpaper-fx", icon: "󰗘", title: "Wallpaper FX", hint: "Wallpaper transitions · p — play",      image: false, live: false, fx: true },
    { group: "desk", key: "widgets",      icon: "󰖲", title: "Widgets",      hint: "Desktop widgets · h l change",           image: false, live: false, tweak: true },
    { group: "desk", key: "dashboard",    icon: "󰕮", title: "Dashboard",    hint: "Dashboard: player, calendar, weather, graphs", image: false, live: false, tweak: true },
    { group: "bar",  key: "bar-skins",    icon: "󰉼", title: "Bar Skin",     hint: "Live preview · form, colors, glass",   image: false, live: true,  bar: true },
    { group: "bar",  key: "bar-widgets",  icon: "󰕰", title: "Bar Widgets",  hint: "h l move · ⏎ on / off · shell.json",    image: false, live: false, tweak: true },
    { group: "bar",  key: "bar-layouts",  icon: "󰕮", title: "Bar Layout",   hint: "Sections & edge · shell.json",         image: false, live: false, bar: true },
    { group: "bar",  key: "bar-tweaks",   icon: "󰒓", title: "Bar Tweaks",   hint: "h l / − + change · ⏎ custom color",    image: false, live: false, bar: true, tweak: true },
    { group: "win",  key: "windows",      icon: "󰖲", title: "Windows",      hint: "Gaps, borders, rounding, shadow, dim · h l change", image: false, live: false },
    { group: "win",  key: "anims",        icon: "󰔡", title: "Animations",   hint: "Live preview while you browse",       image: false, live: true },
    { group: "win",  key: "opacity",      icon: "󰂵", title: "Transparency", hint: "Live preview while you browse",        image: false, live: true },
    { group: "win",  key: "blur",         icon: "󰂷", title: "Blur",         hint: "Live preview while you browse",        image: false, live: true },
    { group: "win",  key: "osd",          icon: "󰕾", title: "OSD",          hint: "Volume & brightness",                   image: false, live: false, tweak: true },
    { group: "win",  key: "notifications", icon: "󰂚", title: "Notifications", hint: "Toasts and sounds",                   image: false, live: false, tweak: true },
    { group: "win",  key: "glyph",        icon: "󰛨", title: "Glyph",        hint: "Perimeter edge lighting · p — test",    image: false, live: false },
    { group: "win",  key: "shaders",      icon: "󰍹", title: "Shader",       hint: "CRT, TFT · scripts/crt-toggle.sh",      image: false, live: false },
    { group: "lock", key: "lock",         icon: "󰌾", title: "Lock",         hint: "p — show it live · T — previews",       image: true,  live: false },
    { group: "lock", key: "lock-tweaks",  icon: "󰷛", title: "Lock Tweaks",  hint: "h l change · p — show",                 image: false, live: false, tweak: true },
    { group: "pick", key: "theme-switcher", icon: "󰸌", title: "Theme Switcher", hint: "Picker style · ⚡ cache · p — open", image: false, live: false, picker: true },
    { group: "pick", key: "launcher",     icon: "󰀻", title: "Launcher",     hint: "Application menu skins · p — open",     image: false, live: false }
  ]

  // Вкладки сверху: группы категорий (1–6, Tab / Shift+Tab); chips — какие чипы
  // статуса показывать в шапке, пока группа открыта.
  readonly property var allGroups: [
    { id: "presets", icon: "󰆓", title: "Presets", chips: ["preset", "style", "fonts", "sound", "theme", "bar-skin"] },
    { id: "desk", icon: "󰧨", title: "Desktop",  chips: ["theme", "wallpaper", "fx"] },
    { id: "bar",  icon: "󰕮", title: "Bar",      chips: ["bar-skin", "bar-layout"] },
    { id: "win",  icon: "󱂬", title: "Windows",  chips: ["anims", "opacity", "blur", "glyph", "shader"] },
    { id: "lock", icon: "󰌾", title: "Lock",     chips: ["lock"] },
    { id: "pick", icon: "󰸌", title: "Pickers",  chips: ["picker", "launcher"] }
  ]

  // Tweaks rows whose ⏎ opens a picker (color, text, file) instead of stepping.
  readonly property var colorTweaks: [
    "background", "gradient", "border", "text", "active", "moduleBackground", "wsActiveColor",
    "ownerMessage", "avatar", "tint", "osdBackground", "notifyBackground", "dashBackground",
    "weatherCity", "dotTint", "dotBackground", "glyphColor", "glyphCriticalColor",
    "dotmatrixBg", "dotmatrixFg", "dotmatrixDim", "dotmatrixMuted", "dotmatrixLine", "dotmatrixSurface", "dotmatrixLit", "dotmatrixSignal", "dotmatrixDanger"
  ]

  // Header chips: status key -> category key it opens.
  readonly property var allStatusChips: [
    { key: "preset",     icon: "󰆓", title: "Preset",       category: "presets" },
    { key: "style",      icon: "󰉦", title: "Style",        category: "styles" },
    { key: "fonts",      icon: "󰛖", title: "Fonts",        category: "fonts" },
    { key: "sound",      icon: "󰕾", title: "Sound",        category: "sounds" },
    { key: "theme",      icon: "󰏘", title: "Theme",        category: "themes" },
    { key: "wallpaper",  icon: "󰸉", title: "Wallpaper",    category: "theme-walls" },
    { key: "fx",         icon: "󰗘", title: "Transition",   category: "wallpaper-fx" },
    { key: "bar-skin",   icon: "󰉼", title: "Skin",         category: "bar-skins" },
    { key: "bar-layout", icon: "󰕮", title: "Layout",       category: "bar-layouts" },
    { key: "anims",      icon: "󰔡", title: "Animations",   category: "anims" },
    { key: "opacity",    icon: "󰂵", title: "Transparency", category: "opacity" },
    { key: "blur",       icon: "󰂷", title: "Blur",         category: "blur" },
    { key: "glyph",      icon: "󰛨", title: "Glyph",        category: "glyph" },
    { key: "shader",     icon: "󰍹", title: "Shader",       category: "shaders" },
    { key: "lock",       icon: "󰌾", title: "Design",       category: "lock" },
    { key: "picker",     icon: "󰸌", title: "Style",        category: "theme-switcher" },
    { key: "launcher",   icon: "󰀻", title: "Launcher",     category: "launcher" }
  ]

  // ── Перевод и что доступно на этой машине ────────────────────────────
  // Строки в коде — английские; i18n/<lang>.json переводит их (язык — `customizer.sh lang`:
  // "lang" в ~/.config/omarchy/customizer.json или $LANG). Категории, которым нужен
  // плагин-компаньон или программа (`customizer.sh available`), без них скрыты.
  property var i18n: ({})
  property var available: null       // null — ещё не знаем: показываем всё
  function tr(s) { return root.i18n[s] !== undefined ? root.i18n[s] : s }
  function localized(item) {
    var out = Object.assign({}, item)
    if (item.title !== undefined) out.title = root.tr(item.title)
    if (item.hint !== undefined) out.hint = root.tr(item.hint)
    return out
  }
  function setAvailable(raw) {
    var list = String(raw || "").split("\n").filter(function(s) { return s.length > 0 })
    var key = root.category ? root.category.key : ""
    var cats = root.allCategories.filter(function(c) { return list.indexOf(c.key) !== -1 })
    var idx = -1
    for (var i = 0; i < cats.length; i++) if (cats[i].key === key) { idx = i; break }
    // Сначала индекс (он меньше длины и старого, и нового списка), потом сам список.
    root.groupLast = ({})
    root.categoryIndex = Math.max(0, idx)
    root.available = list
    if (root.opened && idx < 0) root.setCategory(0, true)
  }
  function isAvailable(key) { return root.available === null || root.available.indexOf(key) !== -1 }
  readonly property var categories: allCategories.filter(function(c) { return root.isAvailable(c.key) }).map(root.localized)
  readonly property var groups: allGroups.filter(function(g) {
    return root.categories.some(function(c) { return c.group === g.id })
  }).map(root.localized)
  readonly property var statusChips: allStatusChips.filter(function(c) { return root.isAvailable(c.category) }).map(root.localized)

  property bool opened: false
  property int categoryIndex: 0
  property int pane: 0               // 0 = categories, 1 = items
  property string filterText: ""
  property int selectedIndex: 0
  property bool loading: false
  property var cache: ({})           // category key -> rows, dropped on every open
  property var items: []             // rows of the current category, unfiltered
  property string previewing: ""     // category key with a live preview applied
  property string previewText: ""
  property bool filtering: false     // "/" pressed: printable keys go to the filter
  property bool pendingG: false      // first "g" of "gg"
  property bool helpOpen: false
  // Обои: D — спросить здесь же («в корзину?»), ⏎/y — да, Esc/n — нет.
  property string wallDeletePath: ""
  property string wallDeleteMsg: ""
  // Домашняя страница (пункт 0 рейла) и выделение на ней (карточки, потом действия).
  property bool homeOpen: false
  property bool everOpened: false
  property int homeSel: 0
  // Поиск по всем настройкам: индекс (customizer.sh search-index) и выбранный результат (-1 — нет).
  property var searchIndex: []
  property int searchSel: -1
  property bool heroCollapsed: false  // v — свернуть карточку превью
  property bool noteOpen: false       // n — описание поверх сцены превью
  property bool heroFull: false       // z — превью на всё тело страницы
  // Значения настроек открытой категории (ключ -> raw, вместе с предсказанными): их читают сцены
  // превью — сцена меняется сразу при шаге, без своего FileView.
  property var tweakValues: ({})
  property bool pendingRandom: false  // «Случайная тема» с домашней: выбрать, как только темы загрузятся
  property string toast: ""           // ошибка записи значения мышью — в футере на 4 с
  property var status: ({})
  property var lastPointer: null     // window coords of the last hover event
  property string keepValue: ""      // row (by value) to stay on when a list reloads after a tweak
  property string wallPath: ""       // Wallpaper: папка-категория внутри ~/.config/omarchy/backgrounds/<тема>
  // Шаги, пришедшие, пока предыдущий ещё выполняется (зажатая клавиша, быстрые клики):
  // [{ key, dir }] — выполняются по очереди, ни один не теряется.
  property var tweakQueue: []
  // Значение (raw), показанное до ответа customizer.sh: value строки -> raw. Пока шаги идут,
  // оно накладывается на перечитанный список, чтобы переключатель не мигал назад.
  property var optimistic: ({})
  property var pendingSet: null      // { index, value } — значение мышью, пока пишется предыдущее
  // Ручной ввод значения (i): строка, которую правят, её начальный текст и ошибка проверки.
  property int editingIndex: -1
  property string editInitial: ""
  property string editError: ""
  property bool reloadQueued: false  // a reload asked for while the lister was busy
  property var themePalette: ({})    // colors.toml of the current theme, for the bar mock
  property var activeSkin: ({})      // ~/.config/omarchy/bar-skin.json
  property var activeBar: ({})       // ~/.config/omarchy/shell.json .bar
  property var activeFx: ({})        // ~/.config/omarchy/wallpaper-transition.json
  property var activePicker: ({})    // ~/.config/omarchy/image-picker.json
  property var activeSounds: ({})    // ~/.config/omarchy/sounds.json
  property bool soundEventsArmed: false
  readonly property bool windowSoundsEnabled: activeSounds.sounds !== false && activeSounds.windowSounds === true

  readonly property var category: categories[categoryIndex]

  // ── Группы ──────────────────────────────────────────────────────────
  readonly property int groupIndex: Math.max(0, groupIndexOf(category.group))
  readonly property var group: groups[groupIndex]
  // Индексы (в categories) категорий текущей группы — их показывает левая колонка.
  readonly property var groupCategories: {
    var out = []
    for (var i = 0; i < categories.length; i++) if (categories[i].group === group.id) out.push(i)
    return out
  }
  readonly property var groupChips: statusChips.filter(function(c) { return root.group.chips.indexOf(c.key) !== -1 })
  property var groupLast: ({})       // группа -> последняя открытая в ней категория

  function groupIndexOf(id) {
    for (var i = 0; i < groups.length; i++) if (groups[i].id === id) return i
    return -1
  }

  function setGroup(index) {
    var n = groups.length
    index = (index + n) % n
    if (root.homeOpen) { root.homeOpen = false; contentFade.restart() }
    var id = groups[index].id
    var target = root.groupLast[id]
    if (target === undefined) {
      for (var i = 0; i < categories.length; i++) if (categories[i].group === id) { target = i; break }
    }
    root.pane = 0
    root.setCategory(target)
  }
  property var selectedRow: null     // set by selectionChanged(); ListModel.get() isn't reactive

  // Рейл: 0 — Домой, дальше группы.
  readonly property var railItems: [{ icon: "󰋜", title: root.tr("Home") }].concat(root.groups.map(function(g) {
    return { icon: g.icon, title: g.title }
  }))
  readonly property int railIndex: root.homeOpen ? 0 : root.groupIndex + 1
  function setRail(index) {
    var n = root.railItems.length
    index = (index + n) % n
    if (index === 0) root.goHome()
    else root.setGroup(index - 1)
  }
  function goHome() {
    if (root.homeOpen) return
    root.revertPreview()
    root.heroFull = false
    root.homeOpen = true
    root.filtering = false
    root.homeSel = Math.min(root.homeSel, Math.max(0, root.homeCards.length + root.homeActions.length - 1))
    contentFade.restart()
    statusProc.running = false
    statusProc.running = true
    root.syncBarPreview()
  }
  // Tab / Shift+Tab: соседняя вкладка (категория) группы; с домашней — первая группа.
  function setTab(dir) {
    if (root.homeOpen) { root.setGroup(dir > 0 ? 0 : root.groups.length - 1); return }
    var cats = root.groupCategories
    var n = cats.length
    var pos = cats.indexOf(root.categoryIndex)
    root.setCategory(cats[(pos + dir + n) % n])
  }
  readonly property var groupTabs: root.groupCategories.map(function(i) {
    return { icon: root.categories[i].icon, title: root.categories[i].title }
  })
  function groupTitle(id) {
    var i = root.groupIndexOf(id)
    return i >= 0 ? root.groups[i].title : ""
  }

  // ── Домашняя страница ──
  readonly property var homeCards: root.statusChips.map(function(c) {
    return { key: c.key, icon: c.icon, title: c.title, value: root.statusText(c.key), category: c.category }
  })
  readonly property var homeActions: {
    var a = [{ id: "random-theme", icon: "󰒝", title: root.tr("Random theme") }]
    if (root.isAvailable("presets")) a.push({ id: "save-preset", icon: "󰆓", title: root.tr("Save preset") })
    a.push({ id: "picker", icon: "󰸌", title: root.tr("Theme picker") })
    a.push({ id: "launcher", icon: "󰀻", title: root.tr("Launcher") })
    a.push({ id: "keys", icon: "󰌌", title: root.tr("Keyboard shortcuts") })
    return a
  }
  readonly property var homePalette: {
    var keys = ["background", "foreground", "accent", "color1", "color2", "color3", "color4", "color5", "color6"]
    var out = []
    for (var i = 0; i < keys.length; i++) if (root.themePalette[keys[i]]) out.push(root.themePalette[keys[i]])
    return out
  }
  function greeting() {
    var h = new Date().getHours()
    return root.tr(h < 5 ? "Good night" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening")
  }
  // h j k l по сетке домашней: карточки, под ними действия. false — упёрлись в левый край.
  function homeMove(dx, dy) {
    var nC = root.homeCards.length, nA = root.homeActions.length
    var cols = Math.max(1, homePage.columns)
    var i = root.homeSel
    var inCards = i < nC
    if (dx !== 0) {
      var base = inCards ? 0 : nC, cnt = inCards ? nC : nA
      if (dx < 0 && (i - base) % cols === 0) return false
      var nx = i + dx
      if (nx >= base && nx < base + cnt) root.homeSel = nx
      return true
    }
    var lastStart = Math.floor(Math.max(0, nC - 1) / cols) * cols
    if (dy > 0) {
      if (inCards) root.homeSel = i + cols < nC ? i + cols : i < lastStart ? nC - 1 : (nA > 0 ? nC + Math.min(i % cols, nA - 1) : i)
      else if (i + cols < nC + nA) root.homeSel = i + cols
    } else {
      if (!inCards) root.homeSel = i - cols >= nC ? i - cols : (nC > 0 ? Math.min(lastStart + (i - nC) % cols, nC - 1) : i)
      else if (i - cols >= 0) root.homeSel = i - cols
    }
    return true
  }
  function homeActivate(i) {
    var nC = root.homeCards.length
    if (i < nC) { root.jumpTo({ cat: root.homeCards[i].category, value: "" }); return }
    var a = root.homeActions[i - nC]
    if (!a) return
    if (a.id === "random-theme") { root.pendingRandom = true; root.jumpTo({ cat: "themes", value: "" }) }
    else if (a.id === "save-preset") { root.dismiss(); Quickshell.execDetached([root.script, "apply", "presets", "save"]) }
    else if (a.id === "picker") { root.dismiss(); Quickshell.execDetached([root.script, "picker-open"]) }
    else if (a.id === "launcher") { root.dismiss(); Quickshell.execDetached([root.script, "launcher-open", "", "home"]) }
    else if (a.id === "keys") root.helpOpen = true
  }

  // ── Поиск по всем настройкам ──
  // Имена категорий, все твики (search-index) и строки уже загруженных категорий; текущую
  // категорию не повторяем — её фильтрует сама страница.
  readonly property var searchResults: {
    if (!root.filtering) return []
    var q = root.filterText.trim().toLowerCase()
    if (q.length < 2) return []
    var out = [], seen = ({}), limit = 8
    var push = function(r) {
      var id = r.cat + "\u0001" + r.value
      if (seen[id]) return
      seen[id] = true
      out.push(r)
    }
    for (var i = 0; i < root.categories.length && out.length < limit; i++) {
      var c = root.categories[i]
      if (c.title.toLowerCase().indexOf(q) !== -1)
        push({ cat: c.key, value: "", label: c.title, where: root.groupTitle(c.group), icon: c.icon })
    }
    for (var j = 0; j < root.searchIndex.length && out.length < limit; j++) {
      var e = root.searchIndex[j]
      if (!root.homeOpen && e.cat === root.category.key) continue
      if (e.label.toLowerCase().indexOf(q) === -1 && e.section.toLowerCase().indexOf(q) === -1) continue
      var ci = root.categoryIndexOf(e.cat)
      if (ci < 0) continue
      push({ cat: e.cat, value: e.value, label: e.label,
        where: root.categories[ci].title + (e.section ? "  ›  " + e.section : ""), icon: root.categories[ci].icon })
    }
    for (var key in root.cache) {
      if (out.length >= limit) break
      if (!root.homeOpen && key === root.category.key) continue
      var ck = root.categoryIndexOf(key)
      if (ck < 0 || root.categories[ck].tweak) continue
      var rows = root.cache[key]
      for (var r = 0; r < rows.length && out.length < limit; r++) {
        var row = rows[r]
        if (root.isHeader(row) || /^tweak:/.test(row.value) || row.label.toLowerCase().indexOf(q) === -1) continue
        push({ cat: key, value: row.value, label: row.label, where: root.categories[ck].title, icon: root.categories[ck].icon })
      }
    }
    return out
  }
  function startSearch() {
    root.filtering = true
    root.searchSel = -1
    if (root.searchIndex.length === 0 && !searchProc.running) searchProc.running = true
  }
  // Перейти к результату поиска / карточке домашней: категория и (если есть) строка в ней.
  function jumpTo(res) {
    root.filtering = false
    root.searchSel = -1
    var idx = root.categoryIndexOf(res.cat)
    if (idx < 0) return
    if (root.homeOpen) { root.homeOpen = false; contentFade.restart() }
    if (idx !== root.categoryIndex) root.setCategory(idx)
    else if (root.filterText) root.setFilter("")
    root.pane = 1
    if (res.value) {
      if (root.loading) root.keepValue = res.value
      else root.selectValue(res.value)
    } else if (root.pendingRandom && !root.loading) {
      root.pendingRandom = false
      Qt.callLater(root.randomPick)
    }
    root.selectionChanged()
  }
  function selectValue(value) {
    for (var i = 0; i < displayModel.count; i++) {
      if (displayModel.get(i).value !== value) continue
      root.selectedIndex = i
      root.ensureVisible()
      root.selectionChanged()
      return
    }
  }
  function loadSearchIndex(raw) {
    var out = []
    var lines = String(raw || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var f = lines[i].split("\t")
      if (f.length >= 3) out.push({ cat: f[0], value: f[1], label: f[2], section: f[3] || "" })
    }
    root.searchIndex = out
  }

  // Ошибка записи значения (мышью) — в футер на 4 с.
  function showToast(text) {
    root.toast = text
    toastTimer.restart()
  }

  // Цвет строки-твика: #hex, роль темы (colors.toml), роль DOT-MATRIX или цвета шелла.
  function resolveColor(v) {
    v = String(v || "")
    if (/^#[0-9a-fA-F]{3,8}$/.test(v)) return v
    if (/^dotmatrix\./.test(v)) {
      var pv = DotMatrix.Palette[v.slice(10)]
      return pv !== undefined ? pv : "transparent"
    }
    if (root.themePalette[v]) return root.themePalette[v]
    var map = { accent: Color.accent, bar: Color.bar.background, background: Color.background, foreground: Color.foreground, urgent: Color.urgent }
    return map[v] !== undefined ? map[v] : "transparent"
  }

  property color background: Color.menu.background
  property color foreground: Color.menu.text
  property color border: Color.menu.border
  property var borderSpec: Border.surfaceSpec("menu", "border", border, Math.max(1, Style.space(2)))
  property color scrim: Color.menu.scrim
  property color selectedBackground: Color.menu.selectedBackground
  property color selectedText: Color.menu.selectedText
  property color accent: Color.accent
  readonly property color muted: Util.alpha(foreground, 0.55)
  readonly property color faint: Util.alpha(foreground, 0.08)
  readonly property color hairline: Util.alpha(foreground, 0.10)

  // ── Стиль: ~/.config/omarchy/style.json (пишет Customizer → Пресеты → Стиль) ──
  // material: auto/glass — стекло, остальное — сплошная панель; cornerScale — скругления;
  // motion — множитель длительностей (0 — без анимаций); id dotmatrix — палитра и формы DOT-MATRIX.
  property var look: ({})
  readonly property bool dot: String(look.id || "") === "dotmatrix"
  readonly property string material: String(look.material || "auto")
  readonly property bool glass: material === "auto" || material === "glass"
  readonly property real cornerScale: look.cornerScale !== undefined && isFinite(Number(look.cornerScale)) ? Math.max(0, Number(look.cornerScale)) : 1
  readonly property real motionScale: look.motion !== undefined && isFinite(Number(look.motion)) ? Math.max(0, Number(look.motion)) : 1
  function ms(d) { return Math.round(d * root.motionScale) }

  // Цветовые роли Material 3 из темы (в DOT-MATRIX — из dotmatrix/Palette.qml, не hex).
  readonly property color primary: dot ? DotMatrix.Palette.signal : accent
  readonly property color inkOnPrimary: dot ? DotMatrix.Palette.onSignal : background
  readonly property color secondaryContainer: Util.alpha(primary, dot ? 0.22 : 0.26)
  readonly property color inkOnContainer: foreground
  readonly property color surface: dot ? DotMatrix.Palette.surface : Util.alpha(foreground, 0.05)
  readonly property color surfaceLow: Util.alpha(foreground, 0.07)
  readonly property color surfaceHi: Util.alpha(foreground, 0.10)
  readonly property color surfaceSelected: Util.alpha(primary, 0.12)
  readonly property color outline: dot ? DotMatrix.Palette.line : Util.alpha(foreground, 0.08)
  readonly property color outlineStrong: Util.alpha(foreground, 0.45)
  readonly property color unlit: dot ? DotMatrix.Palette.unlit : Util.alpha(foreground, 0.12)
  readonly property int rCard: dot ? Math.min(4, Math.round(16 * cornerScale)) : Math.round(16 * cornerScale)
  readonly property int rSmall: dot ? 2 : Math.max(2, Math.round(8 * cornerScale))
  // Иконки — шрифтом Omarchy: у профиля шрифтов может не быть Nerd-глифов.
  readonly property string iconFont: Style.font.family

  // Стекло + мягкие карточки: окно полупрозрачное (размытая копия обоев рисуется в QML —
  // блюр Hyprland у пользователя бывает выключен), панели и строки — карточки.
  readonly property int cornerRadius: dot ? 6 : Math.round(Math.max(Style.cornerRadius, 22) * cornerScale)
  readonly property int innerRadius: dot ? 3 : Math.round(12 * cornerScale)
  readonly property real glassAlpha: glass ? 0.78 : 0.97
  readonly property color panelFill: Util.alpha(foreground, 0.045)
  readonly property color panelBorder: Util.alpha(foreground, 0.08)
  property string fontFamily: Style.font.menuFamily
  // Профиль шрифтов dots («точки везде»): заголовки, вкладки, категории и разделы — DotMatrix Dot.
  readonly property bool dotHeads: DotMatrix.Palette.dotEverywhere
  readonly property string headFont: dotHeads ? DotMatrix.Palette.fontDot : fontFamily
  property int contentMargin: Style.spacing.panelPadding
  property int contentSpacing: Style.spacing.md
  property int rowHeight: Math.max(Style.space(30), Style.font.title + Style.spacing.controlPaddingY * 2)
  property int cardWidth: Math.min(Style.space(1300), panel.width - Style.gapsOut * 2)
  property int cardHeight: Math.min(Style.space(780), panel.height - Style.gapsOut * 2)

  // Галерея: плиток в ряд — сколько влезает по ширине страницы (не меньше двух).
  readonly property int tileGap: Style.space(10)
  readonly property int gridCols: Math.max(2, Math.floor((itemList.width + tileGap) / (Style.space(200) + tileGap)))
  readonly property real tileWidth: (itemList.width - (gridCols - 1) * tileGap) / gridCols
  readonly property real tileHeight: Math.round(tileWidth * 0.62) + Style.font.bodySmall + Style.space(22)
  onGridColsChanged: if (displayModel.count > 0) root.buildView(true)

  function open(payloadJson) {
    root.cache = ({})
    root.filtering = false
    root.searchSel = -1
    root.helpOpen = false
    root.lastPointer = null
    root.opened = true
    root.pane = 0
    // payload {"category": "<ключ>"} — открыть сразу на вкладке (например windows, widgets, themes).
    var payload = root.parseJson(payloadJson)
    var want = String(payload.category || "")
    var idx = -1
    for (var i = 0; want !== "" && i < root.categories.length; i++) if (root.categories[i].key === want) idx = i
    // Первое открытие — домашняя; потом — где остановились; payload — сразу его вкладка.
    var toHome = !root.everOpened && idx < 0 || root.homeOpen && idx < 0
    root.everOpened = true
    root.setCategory(idx >= 0 ? idx : root.categoryIndex, true)   // снимает homeOpen
    root.homeOpen = toHome
    if (idx >= 0) root.pane = 1
    // payload.value — встать на эту строку (возврат из лаунчера после p).
    if (idx >= 0 && payload.value) root.keepValue = String(payload.value)
    if (root.searchIndex.length === 0 && !searchProc.running) searchProc.running = true
    statusProc.running = false
    statusProc.running = true
    availableProc.running = false
    availableProc.running = true
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.revertPreview()
    root.opened = false
    backend.running = false
    root.syncBarPreview()
  }

  // Пока открыты категории бара, бар держится развёрнутым — иначе compact прячет
  // правки формы, высоты и цвета; на строках «Compact: …» бар показывает compact.
  property string barPreviewMode: ""
  function syncBarPreview() {
    var mode = "off"
    var k = root.category.key
    if (root.opened && !root.homeOpen && (k === "bar-skins" || k === "bar-tweaks" || k === "bar-layouts" || k === "bar-widgets")) {
      var row = root.selectedRow
      mode = row && root.isTweakRow(row) && /^compact/.test(root.tweakKey(row)) ? "compact" : "expanded"
    }
    if (mode === root.barPreviewMode) return
    root.barPreviewMode = mode
    Quickshell.execDetached(["omarchy-shell", "barskin", "preview", mode])
  }

  function dismiss() {
    root.close()
    if (root.shell && typeof root.shell.hide === "function")
      root.shell.hide((root.manifest && root.manifest.id) || "kamradsmeshnyavy.customizer")
  }

  function toggle() {
    if (root.opened) root.dismiss()
    else root.open("{}")
  }

  function revertPreview() {
    previewTimer.stop()
    var key = root.previewing
    if (!key) return
    root.previewing = ""
    Quickshell.execDetached([root.script, key === "anims" ? "anim-restore" : key + "-restore"])
  }

  function setCategory(index, force) {
    if (index < 0 || index >= categories.length) return
    if (index === root.categoryIndex && !force) return
    root.revertPreview()
    root.homeOpen = false
    root.heroFull = false
    root.categoryIndex = index
    var last = ({})
    for (var g in root.groupLast) last[g] = root.groupLast[g]
    last[categories[index].group] = index
    root.groupLast = last
    contentFade.restart()
    root.reloadQueued = false
    root.tweakQueue = []
    root.optimistic = ({})
    root.pendingSet = null
    root.keepValue = ""
    root.filtering = false
    root.filterText = ""
    root.selectedIndex = 0
    var key = categories[index].key
    if (root.cache[key]) {
      root.items = root.cache[key]
      root.selectedIndex = root.currentIndexOf(root.items)
      root.rebuild()
      Qt.callLater(root.ensureVisible)
    } else {
      root.items = []
      root.rebuild()
      root.loading = true
      // A busy lister is not killed (running=false/true in one tick never restarts it): its exit
      // starts the run for the tab that is open by then.
      if (!lister.running) {
        lister.category = key
        lister.running = true
      }
    }
  }

  function categoryIndexOf(key) {
    for (var i = 0; i < categories.length; i++) if (categories[i].key === key) return i
    return -1
  }

  function loadRows(key, raw) {
    var rows = []
    var lines = String(raw || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      if (!lines[i]) continue
      var f = lines[i].split("\t")
      // 7–10: тип настройки, его аргументы, сырое значение, имя без значения (list_tweaks).
      rows.push({ label: f[0] || "", value: f[1] || "", preview: f[2] || "", current: f[3] === "1",
        note: (f[4] || "").replace(/\\n/g, "\n"), sub: f[5] || "",
        kind: f[6] || "", args: f[7] || "", raw: f[8] || "", name: f[9] || "" })
    }
    var next = ({})
    for (var k in root.cache) next[k] = root.cache[k]
    next[key] = rows
    root.cache = next
    // Fill the thumbnail cache in the background; rows fall back to the source until then.
    var cat = categories[root.categoryIndexOf(key)]
    if (cat && cat.image) {
      thumbsProc.running = false
      thumbsProc.command = [root.script, "thumbs", key, key === "theme-walls" ? root.wallPath : ""]
      thumbsProc.running = true
    }
    if (key !== root.category.key) return
    if (root.stepsInFlight()) {
      for (var oi = 0; oi < rows.length; oi++)
        if (root.optimistic[rows[oi].value] !== undefined) rows[oi].raw = root.optimistic[rows[oi].value]
    } else root.optimistic = ({})
    root.loading = false
    root.items = rows
    // Индекс — в отфильтрованном списке (его показывает displayModel), заголовки разделов не выделяются.
    var shown = root.filteredRows(rows)
    var at = root.keepValue ? root.indexOfValue(shown, root.keepValue) : root.currentIndexOf(shown)
    root.selectedIndex = root.selectableFrom(shown, at, 1)
    root.keepValue = ""
    root.rebuild()
    Qt.callLater(root.ensureVisible)
    if (root.reloadQueued) { root.reloadQueued = false; root.reloadCategory() }
    if (root.pendingRandom && key === "themes") { root.pendingRandom = false; Qt.callLater(root.randomPick) }
  }

  function indexOfValue(rows, value) {
    for (var i = 0; i < rows.length; i++) if (rows[i].value === value) return i
    return root.currentIndexOf(rows)
  }

  function loadStatus(raw) {
    var s = ({})
    var lines = String(raw || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var tab = lines[i].indexOf("\t")
      if (tab > 0) s[lines[i].slice(0, tab)] = lines[i].slice(tab + 1)
    }
    root.status = s
  }

  function statusText(key) {
    var v = root.status[key] || ""
    if (key === "wallpaper") v = v.replace(/^.*\//, "").replace(/\.[^.]+$/, "")
    return v || "—"
  }

  // Open a list on the entry that is in use.
  function currentIndexOf(rows) {
    for (var i = 0; i < rows.length; i++) if (rows[i].current) return i
    return 0
  }

  // Заголовок раздела в списке настроек: value "section:<имя>" (строки "#Раздел" в *_TWEAKS).
  function isHeader(row) { return row !== null && row !== undefined && /^section:/.test(String(row.value || "")) }

  // Строки под фильтром. Совпало имя раздела — раздел виден целиком; заголовок остаётся,
  // если под ним есть хоть одна строка.
  function filteredRows(rows) {
    var needle = root.filterText.toLowerCase()
    if (!needle) return rows
    var out = [], header = null, headerHit = false, headerShown = false
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i]
      if (root.isHeader(row)) {
        header = row
        headerHit = row.label.toLowerCase().indexOf(needle) !== -1
        headerShown = false
        continue
      }
      if (!headerHit && row.label.toLowerCase().indexOf(needle) === -1) continue
      if (header && !headerShown) { out.push(header); headerShown = true }
      out.push(row)
    }
    return out
  }

  // Ближайшая выделяемая строка от index в сторону dir (заголовки пропускаются).
  function selectableFrom(rows, index, dir) {
    var n = rows.length
    if (n === 0) return 0
    var i = Math.max(0, Math.min(n - 1, index))
    for (var step = 0; step < n && root.isHeader(rows[i]); step++) {
      var next = i + dir
      if (next < 0 || next >= n) { dir = -dir; next = i + dir }
      i = Math.max(0, Math.min(n - 1, next))
    }
    return i
  }

  function rebuild() {
    var rows = root.filteredRows(root.items)
    // Тот же набор строк (шаг tweak, обновление значений) — правим на месте: ListView не теряет
    // прокрутку и выделение. Иначе полная пересборка с сохранённой прокруткой.
    var same = rows.length === displayModel.count
    for (var i = 0; same && i < rows.length; i++) same = displayModel.get(i).value === rows[i].value
    if (same) {
      for (var j = 0; j < rows.length; j++) displayModel.set(j, rows[j])
    } else {
      displayModel.clear()
      for (var k = 0; k < rows.length; k++) displayModel.append(rows[k])
    }
    if (root.selectedIndex >= displayModel.count) root.selectedIndex = Math.max(0, displayModel.count - 1)
    if (displayModel.count > 0 && root.isHeader(displayModel.get(root.selectedIndex)))
      root.selectedIndex = root.selectableFrom(rows, root.selectedIndex, 1)
    root.buildView(!same)
    if (!same) Qt.callLater(root.ensureVisible)
    root.refreshTweakValues()
    root.selectionChanged()
  }
  function refreshTweakValues() {
    var out = ({})
    for (var i = 0; i < root.items.length; i++) {
      var r = root.items[i]
      if (r.kind && !root.isHeader(r)) out[String(r.value).replace(/^tweak:/, "")] = r.raw
    }
    root.tweakValues = out
  }

  // Ряды страницы (viewModel): подряд идущие картинки (галерея) собираются по gridCols плиток,
  // остальное — по одному ряду: раздел, карточка настройки, строка. viewOf[i] — ряд строки i.
  // Тот же набор рядов (шаг твика) — правим на месте, иначе пересборка с сохранённой прокруткой.
  property var viewOf: []
  function rowObject(r) {
    return { label: r.label, value: r.value, preview: r.preview, current: r.current, note: r.note, sub: r.sub,
      kind: r.kind || "", args: r.args || "", raw: r.raw || "", name: r.name || "" }
  }
  function isTileRow(row) {
    return row !== null && row !== undefined && root.category.image === true && !root.isHeader(row) && !root.isTweakRow(row)
  }
  function buildView(reset) {
    var cols = root.gridCols
    var entries = [], map = []
    var n = displayModel.count
    var i = 0
    while (i < n) {
      var r = displayModel.get(i)
      var e = root.rowObject(r)
      e.idx = i
      e.tiles = []
      if (root.isTileRow(r)) {
        e.vkind = "tiles"
        while (i < n && e.tiles.length < cols && root.isTileRow(displayModel.get(i))) {
          e.tiles.push(root.rowObject(displayModel.get(i)))
          map[i] = entries.length
          i++
        }
      } else {
        e.vkind = root.isHeader(r) ? "header" : root.isTweakRow(r) ? "setting" : "row"
        map[i] = entries.length
        i++
      }
      e.n = e.vkind === "tiles" ? e.tiles.length : 1
      entries.push(e)
    }
    root.viewOf = map
    var same = !reset && entries.length === viewModel.count
    for (var k = 0; same && k < entries.length; k++) {
      var old = viewModel.get(k)
      same = old.vkind === entries[k].vkind && old.idx === entries[k].idx && old.n === entries[k].n
    }
    if (same) {
      for (var s = 0; s < entries.length; s++) viewModel.set(s, entries[s])
      return
    }
    var y = itemList.contentY
    viewModel.clear()
    for (var a = 0; a < entries.length; a++) viewModel.append(entries[a])
    itemList.contentY = Math.max(0, Math.min(y, itemList.contentHeight - itemList.height))
  }
  function ensureVisible() {
    if (displayModel.count === 0) return
    var v = root.viewOf[root.selectedIndex]
    if (v === undefined) return
    itemList.positionViewAtIndex(v, ListView.Contain)
    // Не прятать строку под закреплённым заголовком раздела.
    var item = itemList.itemAtIndex(v)
    var room = stickySection.height + Style.space(6)
    if (item && v > 0 && item.y - itemList.contentY < room)
      itemList.contentY = Math.max(itemList.originY, item.y - room)
  }
  // Начало и конец сплошного куска галереи вокруг строки i.
  function tileRun(i) {
    var s = i, e = i
    while (s > 0 && root.isTileRow(displayModel.get(s - 1))) s--
    while (e < displayModel.count - 1 && root.isTileRow(displayModel.get(e + 1))) e++
    return [s, e]
  }
  // h / l в галерее: соседняя плитка; false — левый край ряда (h уходит на рейл).
  function tileStep(dir) {
    var i = root.selectedIndex
    var run = root.tileRun(i)
    if (dir < 0 && (i - run[0]) % root.gridCols === 0) return false
    var t = i + dir
    if (t < run[0] || t > run[1]) return true
    root.selectedIndex = t
    root.ensureVisible()
    root.selectionChanged()
    return true
  }

  // [ / ]: к первой строке предыдущего / следующего раздела.
  function jumpSection(dir) {
    if (root.pane !== 1 || displayModel.count === 0) return
    var i = root.selectedIndex
    if (dir < 0) {
      // Назад: сначала к заголовку своего раздела, потом — к предыдущему.
      var own = i
      while (own > 0 && !root.isHeader(displayModel.get(own))) own--
      var target = own
      if (i - own <= 1 && own > 0) { target = own - 1; while (target > 0 && !root.isHeader(displayModel.get(target))) target-- }
      i = target
    } else {
      var j = i + 1
      while (j < displayModel.count && !root.isHeader(displayModel.get(j))) j++
      if (j >= displayModel.count) return
      i = j
    }
    var rows = []
    for (var r = 0; r < displayModel.count; r++) rows.push(displayModel.get(r))
    root.selectedIndex = root.selectableFrom(rows, i, 1)
    root.ensureVisible()
    root.selectionChanged()
  }

  // Раздел строки index (имя ближайшего заголовка выше), "" — если разделов нет.
  function sectionOf(index) {
    for (var i = Math.min(index, displayModel.count - 1); i >= 0; i--) {
      var row = displayModel.get(i)
      if (root.isHeader(row)) return row.label
    }
    return ""
  }

  function setFilter(text) {
    root.filterText = text
    root.searchSel = -1
    root.selectedIndex = 0
    if (!root.homeOpen) root.pane = 1
    root.rebuild()
  }

  function toCategories() {
    if (root.pane !== 1) return
    root.revertPreview()
    root.pane = 0
  }

  // Rows that fit on the page, halved: the Ctrl+D / Ctrl+U step (in the gallery — whole rows of tiles).
  function halfPage() {
    var rowH = root.category.image ? root.tileHeight + root.tileGap : root.category.tweak ? Style.space(86) : Style.space(66)
    var rows = Math.max(1, Math.floor(itemList.height / rowH / 2))
    return root.category.image ? rows * root.gridCols : rows
  }

  // Jump to a row (-1 = last); on the rail, to the first / last rail item.
  function moveTo(index) {
    if (root.pane === 0) {
      root.setRail(index < 0 ? root.railItems.length - 1 : Math.min(index, root.railItems.length - 1))
      return
    }
    if (root.homeOpen) {
      root.homeSel = index < 0 ? root.homeCards.length + root.homeActions.length - 1 : 0
      return
    }
    if (displayModel.count === 0) return
    root.move((index < 0 ? displayModel.count - 1 : index) - root.selectedIndex)
  }

  // Shift+J / Shift+K: scroll the text preview by five lines, like yazi.
  function scrollPreview(dir) {
    var step = previewLabel.font.pixelSize * 1.4 * 5
    var maxY = Math.max(0, previewFlick.contentHeight - previewFlick.height)
    previewFlick.contentY = Math.max(0, Math.min(maxY, previewFlick.contentY + dir * step))
  }

  function move(delta) {
    if (root.pane === 0) {
      var n = root.railItems.length
      root.setRail(Math.abs(delta) === 1 ? root.railIndex + delta : Math.max(0, Math.min(n - 1, root.railIndex + delta)))
      return
    }
    if (root.homeOpen) { root.homeMove(0, delta > 0 ? 1 : -1); return }
    if (displayModel.count === 0) return
    var target = Math.max(0, Math.min(displayModel.count - 1, root.selectedIndex + delta))
    // j / k в галерее — на ряд плиток вверх / вниз; с края куска — к строке до / после него.
    if (Math.abs(delta) === 1 && root.isTileRow(displayModel.get(root.selectedIndex))) {
      var run = root.tileRun(root.selectedIndex)
      var cols = root.gridCols
      target = root.selectedIndex + delta * cols
      if (target > run[1]) {
        var lastRowStart = run[0] + Math.floor((run[1] - run[0]) / cols) * cols
        target = root.selectedIndex < lastRowStart ? run[1] : run[1] + 1
      } else if (target < run[0]) target = run[0] - 1
      if (target < 0 || target >= displayModel.count) return
    }
    if (root.isHeader(displayModel.get(target))) {
      var rows = []
      for (var r = 0; r < displayModel.count; r++) rows.push(displayModel.get(r))
      target = root.selectableFrom(rows, target, delta < 0 ? -1 : 1)
    }
    root.selectedIndex = target
    root.ensureVisible()
    root.selectionChanged()
  }

  // Called whenever the highlighted row may have changed.
  function selectionChanged() {
    // Уход со строки закрывает её поле ввода.
    if (root.editingIndex >= 0 && root.editingIndex !== root.selectedIndex) {
      root.editingIndex = -1
      root.editError = ""
      keyCatcher.forceActiveFocus()
    }
    previewFlick.contentY = 0
    var row = root.selectedIndex >= 0 && root.selectedIndex < displayModel.count
      ? displayModel.get(root.selectedIndex) : null
    root.selectedRow = row ? root.rowObject(row) : null
    var rowHasImage = root.category.image && row !== null && !root.isTweakRow(row)
    previewFile.path = (row && !rowHasImage) ? row.preview : ""
    if (!row || rowHasImage || !row.preview) root.previewText = ""
    if (root.category.live && root.pane === 1 && row) previewTimer.restart()
    root.syncBarPreview()
  }

  // Wallpaper: зайти в папку-категорию (или выйти по ".."), не закрывая overlay.
  // focusValue — строка, на которой встать после загрузки (папка, из которой вышли).
  function openWallDir(path, focusValue) {
    root.wallPath = path
    root.filterText = ""
    root.filtering = false
    root.reloadCategory()
    root.keepValue = focusValue || ""
  }

  // h / ← / Esc внутри папки: на уровень выше, курсор — на папку, из которой вышли.
  function wallUp() {
    if (root.category.key !== "theme-walls" || root.pane !== 1 || root.wallPath === "") return false
    var from = root.wallPath
    var cut = from.lastIndexOf("/")
    root.openWallDir(cut < 0 ? "" : from.slice(0, cut), "dir:" + from)
    return true
  }

  function activate() {
    if (root.pane === 0) {
      root.pane = 1
      root.selectionChanged()
      return
    }
    if (root.homeOpen) { root.homeActivate(root.homeSel); return }
    if (!root.selectedRow || root.isHeader(root.selectedRow)) return
    if (root.category.key === "theme-walls" && /^dir:/.test(root.selectedRow.value)) {
      var target = root.selectedRow.value.slice(4)
      // ".." ведёт к родителю — встать на папку, из которой вышли.
      if (target.length < root.wallPath.length && root.wallPath.indexOf(target) === 0) root.wallUp()
      else root.openWallDir(target, "")
      return
    }
    if (root.category.key === "glyph" && /^test:/.test(root.selectedRow.value)) {
      Quickshell.execDetached([root.script, "apply", "glyph", root.selectedRow.value])
      return
    }
    // Виджеты бара: ⏎ убирает с бара / возвращает (h/l двигают), параметр виджета — переключает.
    if (root.isTweakRow(root.selectedRow) && /^wset?:/.test(root.tweakKey(root.selectedRow))) root.tweak("toggle")
    else if (root.isTweakRow(root.selectedRow) && root.colorTweaks.indexOf(root.tweakKey(root.selectedRow)) === -1) root.tweak("+")
    else root.run(root.selectedRow.value)
  }

  // Физическая клавиша → символ US-раскладки (xkb keycode = evdev + 8, его отдаёт nativeScanCode
  // на Wayland): клавиши работают и в русской раскладке. Пара — без Shift / с Shift.
  readonly property var scanKeys: ({
    10: "1!", 11: "2@", 12: "3#", 13: "4$", 14: "5%", 15: "6^", 16: "7&", 17: "8*", 18: "9(", 19: "0)", 20: "-_", 21: "=+",
    24: "qQ", 25: "wW", 26: "eE", 27: "rR", 28: "tT", 29: "yY", 30: "uU", 31: "iI", 32: "oO", 33: "pP", 34: "[{", 35: "]}",
    38: "aA", 39: "sS", 40: "dD", 41: "fF", 42: "gG", 43: "hH", 44: "jJ", 45: "kK", 46: "lL", 47: ";:", 48: "'\"", 49: "`~",
    52: "zZ", 53: "xX", 54: "cC", 55: "vV", 56: "bB", 57: "nN", 58: "mM", 59: ",<", 60: ".>", 61: "/?"
  })
  function latinKey(event) {
    var pair = root.scanKeys[event.nativeScanCode]
    if (!pair) return ""
    return (event.modifiers & Qt.ShiftModifier) ? pair.charAt(1) : pair.charAt(0)
  }

  // Клавиши по фокусу: рейл (pane 0), домашняя, страница (pane 1). true — обработано.
  function handlePaneKey(event, k, t, ctrl, printable) {
    var esc = k === Qt.Key_Escape
    var enter = k === Qt.Key_Return || k === Qt.Key_Enter
    var left = k === Qt.Key_Left || (!ctrl && t === "h")
    var right = k === Qt.Key_Right || (!ctrl && t === "l")
    var down = k === Qt.Key_Down || (!ctrl && t === "j")
    var up = k === Qt.Key_Up || (!ctrl && t === "k")

    if (root.pane === 0) {
      if (down) root.move(1)
      else if (up) root.move(-1)
      else if (right || enter) root.activate()
      else if (esc) root.dismiss()
      else return false
      return true
    }

    if (root.homeOpen) {
      if (left) { if (!root.homeMove(-1, 0)) root.pane = 0 }
      else if (right) root.homeMove(1, 0)
      else if (down) root.homeMove(0, 1)
      else if (up) root.homeMove(0, -1)
      else if (enter) root.homeActivate(root.homeSel)
      else if (esc) root.pane = 0
      else return false
      return true
    }

    var key = root.category.key
    var row = root.selectedRow
    var tweaking = !ctrl && root.isTweakRow(row)
    var tile = root.isTileRow(row)
    if (tweaking && (t === "h" || t === "-" || k === Qt.Key_Left)) root.tweak("-")
    else if (tweaking && (t === "l" || t === "+" || t === "=" || k === Qt.Key_Right)) root.tweak("+")
    else if (tweaking && t === "x") root.tweak("reset")
    else if (tweaking && t === "i" && key !== "bar-widgets") root.startEdit()
    // Галерея: h / l — соседняя плитка; с левого края — папкой выше (Wallpaper) или на рейл.
    else if (tile && left) { if (!root.tileStep(-1) && !root.wallUp()) root.toCategories() }
    else if (tile && right) root.tileStep(1)
    else if (!ctrl && t === "[") root.jumpSection(-1)
    else if (!ctrl && t === "]") root.jumpSection(1)
    else if (!ctrl && t === "p" && (key === "lock" || key === "lock-tweaks")) root.previewLock()
    // T: недостающие снимки, если такие есть, иначе — все.
    else if (!ctrl && t === "T" && key === "lock") root.run(root.hasRow("missing-thumbs") ? "missing-thumbs" : "regen-thumbs")
    else if (!ctrl && t === "p" && key === "wallpaper-fx") root.playFx()
    else if (!ctrl && t === "p" && key === "theme-switcher") { root.dismiss(); Quickshell.execDetached([root.script, "picker-open"]) }
    else if (!ctrl && t === "p" && key === "launcher") root.openLauncher()
    else if (!ctrl && t === "p" && key === "glyph") Quickshell.execDetached([root.script, "glyph-test", "false"])
    else if (!ctrl && t === "p" && key === "sounds") root.listenSound()
    else if (ctrl && (key === "walls" || key === "dotify") && k === Qt.Key_O) root.run("pick-files")
    else if (esc) { if (root.filterText) root.setFilter(""); else if (!root.wallUp()) root.toCategories() }
    else if (enter) root.activate()
    else if (down) root.move(1)
    else if (up) root.move(-1)
    else if (left) { if (!root.wallUp()) root.toCategories() }
    else if (right) {}
    else if (ctrl || !printable) return false
    else if (t === "J") root.scrollPreview(1)
    else if (t === "K") root.scrollPreview(-1)
    else if (t === "r") root.randomPick()
    else if (t === "D" && key === "theme-walls") root.askWallDelete()
    else if (t === "D") root.deletePreset()
    else if (t === "f" && (key === "themes" || key === "theme-walls")) root.toggleFavorite()
    else if ((key === "walls" || key === "dotify") && t === "o") root.run("pick-files")
    else if ((key === "walls" || key === "dotify") && t === "O") root.run("pick-dir")
    else return false
    return true
  }

  // Карточка превью над страницей: есть ли у категории сцена или текст для неё.
  readonly property bool heroAvailable: {
    var c = root.category
    return c.image === true || c.bar === true || c.fx === true || c.picker === true || c.presetStage === true
      || ["opacity", "blur", "fonts", "windows", "widgets", "anims", "shaders"].indexOf(c.key) !== -1
      || root.sceneCategories.indexOf(c.key) !== -1
  }
  // Категории с макетом из previews/ (сцена всегда, описание — по n).
  readonly property var sceneCategories: ["dotify", "osd", "notifications", "dashboard", "lock-tweaks", "glyph", "sounds", "launcher"]
  readonly property string wallpaperUrl: root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
  // Картинка для превью Dotify: файл строки, если это картинка, иначе текущие обои.
  readonly property string dotifySource: {
    var row = root.selectedRow
    var p = row ? String(row.preview || "") : ""
    if (/\.(jpe?g|png|webp|bmp|gif)$/i.test(p)) return root.fileUrl(p)
    return root.wallpaperUrl
  }
  // Снимок дизайна экрана блокировки (как lock_thumb_name в customizer.sh).
  readonly property string lockShot: root.status.lock
    ? root.fileUrl(root.thumbDir.replace(/\/thumbs$/, "") + "/lock/" + String(root.status.lock).replace(/[^A-Za-z0-9._-]/g, "-") + ".jpg") : ""
  // Звуки: пакет под курсором (pack:<имя>) или выбранный; его описание из строки списка.
  readonly property string soundPack: {
    var row = root.selectedRow
    if (row && /^pack:/.test(row.value)) return row.value.slice(5)
    return String(root.tweakValues.soundPack || root.status.sound || "theme")
  }
  readonly property string soundPackNote: {
    for (var i = 0; i < root.items.length; i++) if (root.items[i].value === "pack:" + root.soundPack) return root.items[i].note
    return ""
  }
  readonly property bool heroCode: root.category.key === "anims" || root.category.key === "shaders"
  // Текст справа от сцены: заметка строки и то, что раньше было под сценой.
  function heroNote() {
    var row = root.selectedRow
    if (!row) return ""
    var k = root.category.key
    if (root.heroCode) return root.previewText || row.note
    if (k === "windows") return (windowsStage.noGaps ? root.tr("No gaps (Omarchy) is on: gaps, borders and rounding are off.")
      : (windowsStage.master ? "master" : "dwindle") + "  ·  " + root.tr("gaps") + " " + windowsStage.n("windowGapsIn", 2) + " / "
        + windowsStage.n("windowGapsOut", 4) + "  ·  " + root.tr("border") + " " + windowsStage.n("windowBorder", 2)
        + "  ·  " + root.tr("rounding") + " " + windowsStage.n("windowDecoRounding", 10)) + "\n\n" + row.note
    if (k === "widgets") return (widgetsStage.clash ? root.tr("Widgets overlap — move one of the red ones to another position.")
      : root.tr("Layout of the enabled widgets; the one you are editing is highlighted.")) + "\n\n" + row.note
    if (root.isTweakRow(row)) return row.note
    if (k === "bar-skins" || k === "presets" || k === "styles") return row.note + (root.previewText ? "\n\n" + root.previewText : "")
    if (root.category.fx) return row.note + "\n\n" + root.tr("The preview plays the transition at half speed.")
    if (k === "fonts") return row.note + "\n\n" + root.tr("Interface") + ": " + fontStage.sans
      + "\n" + root.tr("Code") + ": " + fontStage.mono + "\n" + root.tr("Titles") + ": " + fontStage.title
    if (root.category.image) return row.label + (root.paletteOf(row.note).length === 0 && row.note ? "\n\n" + row.note : "")
    return row.note || root.previewText
  }

  // Шаг настройки: значение на экране меняется сразу (predictStep — те же правила, что у
  // `customizer.sh tweak`), сам шаг уходит в customizer.sh. Зажатая клавиша шагает быстрее,
  // чем отвечает скрипт: шаги встают в tweakQueue и выполняются по очереди, список
  // перечитывается один раз, когда очередь опустела, — и правит предсказание, если оно
  // разошлось. Убивать идущий lister нельзя: он отдавал половину вывода и сбрасывал выделение.
  // Строка-настройка: вся категория tweak или строка "tweak:<key>" внутри галереи.
  function isTweakRow(row) {
    return row !== null && !root.isHeader(row) && (root.category.tweak === true || /^tweak:/.test(row.value))
  }
  function tweakKey(row) { return String(row.value).replace(/^tweak:/, "") }

  function clickSelect(index) {
    root.pane = 1
    if (root.selectedIndex === index) return
    root.selectedIndex = index
    root.selectionChanged()
  }
  // Qt шлёт hover и строкам, приехавшим под неподвижный указатель (загрузка, прокрутка) —
  // такие события выделение не забирают: только реальное движение указателя.
  function hoverSelect(index, p) {
    var last = root.lastPointer
    root.lastPointer = { x: p.x, y: p.y }
    if (!last || (Math.abs(p.x - last.x) < 1 && Math.abs(p.y - last.y) < 1)) return
    if (root.pane === 1 && root.editingIndex < 0 && root.selectedIndex !== index) {
      root.selectedIndex = index
      root.selectionChanged()
    }
  }
  // Значение мышью (ползунок, сегмент): tweak <key> set <value>, как ручной ввод (i).
  // На экране — сразу; пока пишется предыдущее, ждёт последнее (pendingSet).
  function setTweakAt(index, value) {
    if (index < 0 || index >= displayModel.count) return
    var row = displayModel.get(index)
    if (!root.isTweakRow(row)) return
    root.clickSelect(index)
    if (row.kind === "num" || row.kind === "enum" || row.kind === "bool") root.setRowRaw(index, String(value))
    if (editor.running) { root.pendingSet = { index: index, value: String(value) }; return }
    editor.key = root.tweakKey(row)
    editor.command = [root.script, "tweak", editor.key, "set", String(value)]
    editor.running = true
  }

  // Что покажет строка после шага dir — те же правила, что у tweak() в customizer.sh.
  // null — не берёмся угадывать (цвета, шрифты, виджеты бара): ждём ответа скрипта.
  function predictStep(row, dir) {
    var kind = String(row.kind || ""), args = String(row.args || ""), raw = String(row.raw || "")
    var key = root.tweakKey(row)
    if (/^(w|wset):/.test(key) || key === "fontProfile") return null
    if (kind === "bool") {
      if (dir === "reset") return args
      return raw === "true" ? "false" : "true"
    }
    if (kind === "enum") {
      var list = args.split(" ").filter(function(x) { return x !== "" })
      if (dir === "reset") return list.length ? list[0] : null
      var i = list.indexOf(raw)
      if (i < 0 || list.length === 0) return null
      return list[(i + (dir === "-" ? -1 : 1) + list.length) % list.length]
    }
    if (kind === "num") {
      var a = args.split(" ").map(Number)
      if (a.length < 4) return null
      var lo = a[0], hi = a[1], st = a[2], def = a[3]
      if (dir === "reset") return String(def)
      var c = Number(raw), d = dir === "-" ? -1 : 1, v
      if (!isFinite(c) || !(st > 0)) return null
      // -1 = «как в стоке»: шаг вверх из него — 0, вниз до него — с нуля.
      if (lo === -1 && c < 0) v = d > 0 ? 0 : -1
      else {
        v = c + d * st
        v = (v >= 0 ? Math.floor(v / st + 0.5) : Math.ceil(v / st - 0.5)) * st
        if (lo === -1 && v < 0) v = -1
      }
      v = Math.max(lo, Math.min(hi, v))
      if (st === Math.floor(st)) return String(Math.round(v))
      return v.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")
    }
    return null
  }
  // Показать новое значение строки сразу (до ответа customizer.sh).
  function setRowRaw(index, raw) {
    if (index < 0 || index >= displayModel.count) return
    var value = displayModel.get(index).value
    var o = ({})
    for (var k in root.optimistic) o[k] = root.optimistic[k]
    o[value] = raw
    root.optimistic = o
    displayModel.setProperty(index, "raw", raw)
    for (var i = 0; i < root.items.length; i++) if (root.items[i].value === value) root.items[i].raw = raw
    root.refreshTweakValues()
    var v = root.viewOf[index]
    if (v !== undefined && v < viewModel.count && viewModel.get(v).idx === index) viewModel.setProperty(v, "raw", raw)
    if (root.selectedIndex === index && root.selectedRow) {
      var r = root.rowObject(displayModel.get(index))
      root.selectedRow = r
    }
  }

  function tweak(dir) {
    if (root.pane !== 1 || !root.selectedRow || !root.isTweakRow(root.selectedRow)) return
    var key = root.tweakKey(root.selectedRow)
    var next = root.predictStep(displayModel.get(root.selectedIndex), dir)
    if (next !== null) root.setRowRaw(root.selectedIndex, next)
    if (tweaker.running) { root.tweakQueue = root.tweakQueue.concat([{ key: key, dir: dir }]); return }
    tweaker.key = key
    tweaker.command = [root.script, "tweak", key, dir]
    tweaker.running = true
  }

  // i: поле ввода прямо в строке. Проверяет customizer.sh (tweak <key> set <value>):
  // неверное значение не записывается, причина приходит в stderr и остаётся под полем.
  function startEdit() {
    var row = root.selectedRow
    if (root.pane !== 1 || !root.isTweakRow(row)) return
    var parts = String(row.label).split(":  ")
    root.editInitial = parts.length > 1 ? parts[parts.length - 1].trim() : ""
    root.editError = ""
    root.editingIndex = root.selectedIndex
  }
  function submitEdit(text) {
    var row = root.editingIndex >= 0 && root.editingIndex < displayModel.count ? displayModel.get(root.editingIndex) : null
    if (!row || editor.running) return
    editor.key = root.tweakKey(row)
    editor.command = [root.script, "tweak", editor.key, "set", String(text)]
    editor.running = true
  }
  function cancelEdit() {
    root.editingIndex = -1
    root.editError = ""
    keyCatcher.forceActiveFocus()
  }

  function tweakDone() {
    if (root.tweakQueue.length > 0) {
      var q = root.tweakQueue
      var step = q[0]
      root.tweakQueue = q.slice(1)
      tweaker.key = step.key
      tweaker.command = [root.script, "tweak", step.key, step.dir]
      tweaker.running = true
      return
    }
    root.reloadCategory()
  }
  // Шаги или запись ещё идут — перечитанный список не должен перебить показанное значение.
  function stepsInFlight() {
    return tweaker.running || root.tweakQueue.length > 0 || editor.running || root.pendingSet !== null
  }

  function reloadCategory() {
    if (lister.running) { root.reloadQueued = true; return }
    var key = root.category.key
    var next = ({})
    for (var k in root.cache) if (k !== key) next[k] = root.cache[k]
    root.cache = next
    root.keepValue = root.selectedRow ? root.selectedRow.value : ""
    lister.category = key
    lister.running = true
  }

  function parseJson(text) {
    try {
      var v = JSON.parse(String(text || ""))
      return v && typeof v === "object" ? v : ({})
    } catch (e) {
      return ({})
    }
  }

  function parsePalette(text) {
    var out = ({})
    var lines = String(text || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var m = lines[i].match(/^\s*([A-Za-z0-9_]+)\s*=\s*["'](#[0-9A-Fa-f]{6})["']/)
      if (m) out[m[1]] = m[2]
    }
    root.themePalette = out
  }

  // What the bar mock draws: the row's own skin / layout, the live one otherwise.
  function mockSkin() {
    if (root.category.key === "bar-skins" && root.previewText) return root.parseJson(root.previewText)
    return root.activeSkin
  }

  function mockBar() {
    if (root.category.key !== "bar-layouts" || !root.previewText) {
      if (root.category.key !== "bar-skins" || !root.previewText) return root.activeBar
      var b = ({})
      for (var k in root.activeBar) b[k] = root.activeBar[k]
      b.transparent = root.parseJson(root.previewText).transparent === true
      return b
    }
    var preset = root.parseJson(root.previewText)
    preset.transparent = root.activeBar.transparent === true
    return preset
  }

  // Rows "r" may land on: no picker / toggle actions, and not the one in use.
  function randomCandidates() {
    var out = []
    for (var i = 0; i < displayModel.count; i++) {
      var r = displayModel.get(i)
      if (/^(pick-|toggle$|next$|save$|regen-thumbs$|tweak:|section:|cache$|prune$|none$|dir:|current$|arch$|test:|open$)/.test(r.value) || r.current || i === root.selectedIndex) continue
      out.push(i)
    }
    return out
  }

  function randomPick() {
    if (root.category.key === "walls" || root.category.key === "dotify" || root.category.key === "presets" || root.category.key === "styles" || root.category.key === "fonts" || root.category.key === "sounds" || root.category.key === "glyph") return
    if (root.category.tweak) return
    if (root.pane === 0) { root.pane = 1 }
    var c = root.randomCandidates()
    if (c.length === 0) return
    root.selectedIndex = c[Math.floor(Math.random() * c.length)]
    var v = root.viewOf[root.selectedIndex]
    if (v !== undefined) itemList.positionViewAtIndex(v, ListView.Center)
    root.selectionChanged()
    root.run(root.selectedRow.value)
  }

  // Apply <value> in the current category. The overlay closes first: it holds
  // exclusive keyboard focus on the overlay layer, so a zenity picker opened by
  // customizer.sh would otherwise sit underneath it.
  function run(value) {
    var key = root.category.key
    // Apply owns the previewed setting from here, so no revert on close.
    if (root.previewing === key) { previewTimer.stop(); root.previewing = "" }
    root.dismiss()
    Quickshell.execDetached([root.script, "apply", key, value])
  }

  // Bar Skin / Bar Layout / Presets: удалить свой пресет (★) — с подтверждением в customizer.sh.
  function isUserPreset(row) {
    if (row === null) return false
    var k = root.category.key
    if (k === "presets")
      return /\/\.config\/omarchy\/customizer\/presets\/[^/]+\.json$/.test(row.value) && !/\/my-settings\.json$/.test(row.value)
    if (k === "styles")
      return /\/\.config\/omarchy\/customizer\/styles\/[^/]+\.json$/.test(row.value)
    return (k === "bar-skins" || k === "bar-layouts") && new RegExp("/\\.config/omarchy/" + k + "/[^/]+\\.json$").test(row.value)
  }
  function deletePreset() {
    var row = root.selectedRow
    if (!root.isUserPreset(row)) return
    root.dismiss()
    var k = root.category.key
    var cmd = k === "presets" ? "preset-delete" : k === "styles" ? "style-delete" : (k === "bar-skins" ? "skin-delete" : "layout-delete")
    Quickshell.execDetached([root.script, cmd, row.value])
  }

  // Lock: показать дизайн по-настоящему (окно превью экрана блокировки поверх
  // всего). Overlay закрывается первым, иначе превью окажется под ним.
  function previewLock() {
    var id = root.category.key === "lock" && root.selectedRow ? root.selectedRow.value : ""
    if (id === "regen-thumbs") return
    root.dismiss()
    Quickshell.execDetached([root.script, "lock-preview", id])
  }

  // Wallpaper FX: выбрать эффект строки (если это эффект) и проиграть его на рабочем столе.
  // Темы и обои: f — в избранное / из избранного; оверлей открыт, список перечитывается,
  // курсор остаётся на строке. У обоев — только файлы (не папки-категории).
  function isOwnWall(row) {
    return !!row && root.category.key === "theme-walls"
      && /\/\.config\/omarchy\/(backgrounds|themes\/[^/]+\/backgrounds)\/.+\.(jpe?g|png|webp|gif|bmp)$/i.test(String(row.value))
  }
  function askWallDelete() {
    var row = root.selectedRow
    if (!root.isOwnWall(row)) {
      if (root.category.key === "theme-walls" && row && !/^dir:|^section:/.test(String(row.value)))
        root.wallDeleteMsg = root.tr("Only your own wallpapers can be deleted (theme copies come back on theme change)")
      return
    }
    root.wallDeleteMsg = ""
    root.wallDeletePath = String(row.value)
  }
  function confirmWallDelete() {
    var path = root.wallDeletePath
    root.wallDeletePath = ""
    if (!path) return
    root.call(["wall-delete", path], function(r) {
      root.wallDeleteMsg = r.code === 0 ? "" : (r.out || r.err || "").trim()
      // Курсор — на соседнюю строку (удалённой в новом списке нет).
      if (r.code === 0 && root.selectedRow && String(root.selectedRow.value) === path) {
        var before = root.selectedIndex
        if (root.isTileRow(root.selectedRow)) root.tileStep(1)
        else root.move(1)
        if (root.selectedIndex === before && root.isTileRow(root.selectedRow)) root.tileStep(-1)
        if (root.selectedIndex === before) root.move(-1)
      }
      root.reloadCategory()
    })
  }

  function toggleFavorite() {
    var row = root.selectedRow
    if (root.pane !== 1 || !row || root.isHeader(row) || favProc.running) return
    var v = String(row.value)
    var walls = root.category.key === "theme-walls"
    if (walls ? /^dir:/.test(v) : /^dynamic:/.test(v)) return
    favProc.slug = v
    favProc.command = [root.script, walls ? "wall-fav" : "theme-fav", v]
    favProc.running = true
  }

  // Sounds: p — послушать пакет под курсором (не выбирая) или событие текущим пакетом; оверлей не закрывается.
  function hasRow(value) {
    for (var i = 0; i < displayModel.count; i++) if (displayModel.get(i).value === value) return true
    return false
  }

  function listenSound() {
    var v = root.selectedRow ? String(root.selectedRow.value) : ""
    if (v.indexOf("pack:") === 0) Quickshell.execDetached([root.script, "sound-preview", v.slice(5), "notify"])
    else if (v.indexOf("test:") === 0) Quickshell.execDetached([root.script, "apply", "sounds", v])
  }

  // Launcher: p — открыть лаунчер; на строке скина — с этим скином (только на этот раз, без сохранения).
  // После закрытия лаунчера Customizer открывается снова на той же строке.
  function openLauncher() {
    var v = root.selectedRow ? String(root.selectedRow.value) : ""
    var skin = v.indexOf("skin:") === 0 ? v.slice(5) : ""
    root.dismiss()
    Quickshell.execDetached([root.script, "launcher-open", skin, v])
  }

  function playFx() {
    var row = root.selectedRow
    var effect = row && !root.isTweakRow(row) ? row.value : ""
    root.dismiss()
    Quickshell.execDetached(["bash", "-c", (effect ? '"$0" apply wallpaper-fx "$1" && ' : "") + 'sleep 0.3; "$0" fx-replay',
      root.script, effect])
  }

  // Миниатюры дописались — строки, ушедшие на полную картинку, возвращаются к лёгкой миниатюре.
  property int thumbVersion: 0
  Process {
    id: thumbsProc
    onExited: root.thumbVersion++
  }

  function thumbUrl(path) {
    return root.fileUrl(root.thumbDir + "/" + Qt.md5(path) + ".jpg")
  }

  function fileUrl(path) {
    return "file://" + String(path).split("/").map(encodeURIComponent).join("/")
  }

  // The old fzf preview for shaders showed just the header comments and consts.
  function formatPreview(text) {
    // Описание пресета уже есть в заметке над JSON — переводы note_* в нём только мешают.
    if (root.category.key === "bar-skins" || root.category.key === "bar-layouts" || root.category.key === "presets" || root.category.key === "styles")
      return text.split("\n").filter(function(l) { return !/^\s*"(note|name)(_[a-z]+)?":/.test(l) }).join("\n")
    if (root.category.key !== "shaders") return text
    return text.split("\n").filter(function(l) { return /^(\/\/|const)/.test(l) }).join("\n")
  }

  // Theme rows carry "#bg #fg #accent #red …" in the note column.
  function paletteOf(note) {
    return /^#[0-9a-fA-F]{3,8}( |$)/.test(note || "") ? note.split(" ") : []
  }

  // Numbers out of a note or status value, e.g. "size 6 passes 3 …" -> [6, 3, …].
  function numbersOf(text) {
    return (String(text || "").match(/\d+(\.\d+)?/g) || []).map(Number)
  }

  // What the preview stage shows: the row under the cursor for its own
  // setting, the saved preset for the other one.
  function stageOpacity() {
    var n = root.numbersOf(root.category.key === "opacity" && root.selectedRow ? root.selectedRow.note : root.status["opacity-values"])
    return n.length >= 2 ? [n[0], n[1]] : [1, 0.9]
  }

  // Hyprland blur size × passes squeezed into MultiEffect's 0..1 range.
  function stageBlur() {
    var n = root.numbersOf(root.category.key === "blur" && root.selectedRow ? root.selectedRow.note : root.status["blur-values"])
    if (n.length < 2 || n[0] === 0) return 0
    return Math.min(1, n[0] * n[1] / 48)
  }

  function keyHints() {
    if (root.filtering) return [["↑ ↓", "results"], ["⏎", root.searchSel >= 0 ? "go there" : "keep filter"], ["Esc", "clear"]]
    if (root.pane === 0) return [["j k", "sections"], ["l ⏎", "open"], ["Tab", "next tab"], ["0–" + root.groups.length, "jump"], ["/", "search"], ["?", "keys"], ["q", "close"]]
    if (root.homeOpen) return [["h j k l", "move"], ["⏎", "open"], ["Tab", "first section"], ["/", "search"], ["Esc", "back"], ["?", "keys"]]
    if (root.category.image && root.isTileRow(root.selectedRow)) {
      var g = [["h j k l", "move"], ["⏎", "apply"]]
      if (root.category.key !== "theme-walls") g.push(["Tab", "next tab"])
      g.push(["/", "search"])
      if (root.category.key === "lock") g.push(["p", "preview live"], ["T", "refresh previews"])
      else if (root.category.key === "walls" || root.category.key === "dotify") g.push(["o O", "pick"])
      else g.push(["r", "random"])
      if (root.category.key === "themes" || root.category.key === "theme-walls") g.push(["f", "favorite"])
      if (root.isOwnWall(root.selectedRow)) g.push(["D", "to trash"])
      g.push(["v", "preview"], ["z", "full size"], ["n", "description"], ["?", "keys"])
      return g
    }
    if (root.category.key === "lock-tweaks") return [["j k", "move"], ["h l  − +", "change (hold)"], ["i", "type a value"], ["x", "default"], ["⏎", "step · pick"], ["p", "preview"], ["Esc", "back"]]
    if (root.category.key === "bar-widgets") return [["j k", "move"], ["h l", "move widget"], ["⏎ x", "on / off"], ["[ ]", "section"], ["Esc", "back"]]
    if (root.category.tweak) {
      var tw = [["j k", "move"], ["h l  − +", "change (hold)"], ["i", "type a value"], ["[ ]", "section"], ["x", "default"], ["⏎", "step · pick color"]]
      if (root.sceneCategories.indexOf(root.category.key) !== -1) tw.push(["z", "full size"], ["n", "description"])
      tw.push(["Esc", "back"])
      return tw
    }
    if (root.category.fx || root.category.picker || root.category.key === "glyph" || root.category.key === "launcher" || root.category.key === "dotify") {
      var tw = root.isTweakRow(root.selectedRow)
      var pLabel = root.category.fx ? "play" : root.category.key === "glyph" ? "test" : "open"
      if (tw) {
        var th = [["j k", "move"], ["h l  − +", "change (hold)"], ["i", "type a value"], ["x", "default"]]
        if (root.category.key !== "dotify") th.push(["p", pLabel])
        th.push(["Esc", "back"])
        return th
      }
      if (root.category.key === "dotify") return [["j k", "move"], ["⏎", "dotify"], ["o O", "pick"], ["/", "search"], ["h", "back"], ["?", "keys"]]
      var ph = [["j k", "move"], ["⏎", "apply"], ["p", root.category.fx ? "play on desktop" : root.category.key === "glyph" ? "test sweep" : "open"], ["/", "search"], ["h", "back"]]
      if (root.category.key === "launcher") ph.push(["v", "preview"], ["z", "full size"])
      ph.push(["?", "keys"])
      return ph
    }
    if (root.category.key === "lock") return [["j k", "move"], ["⏎", "apply"], ["p", "preview live"], ["T", "refresh previews"], ["/", "search"], ["h", "back"], ["?", "keys"]]
    if (root.category.key === "sounds" && !root.isTweakRow(root.selectedRow)) return [["j k", "move"], ["⏎", "use"], ["p", "listen"], ["/", "search"], ["h", "back"], ["?", "keys"]]
    var h = [["j k", "move"], ["⏎", "apply"], ["/", "search"], ["h", "back"]]
    if (root.category.key !== "walls" && !root.category.presetStage) h.push(["r", "random"])
    else if (root.category.key === "walls") h.push(["o O", "pick"])
    if (root.isUserPreset(root.selectedRow))
      h.push(["D", root.category.key === "presets" ? "delete preset" : root.category.key === "styles" ? "delete style" : (root.category.key === "bar-skins" ? "delete skin" : "delete layout")])
    if (!root.category.image && !root.category.bar && !root.category.presetStage && root.category.key !== "opacity" && root.category.key !== "blur") h.push(["J K", "scroll"])
    h.push(["?", "keys"])
    return h
  }

  ListModel { id: displayModel }
  ListModel { id: viewModel }       // ряды страницы, см. buildView()

  // Смена категории: список и превью мягко проявляются со сдвигом снизу.
  ParallelAnimation {
    id: contentFade
    NumberAnimation { target: pageBody; property: "opacity"; from: 0.25; to: 1; duration: root.ms(220); easing.type: Easing.OutCubic }
    NumberAnimation { target: pageShift; property: "y"; from: 12; to: 0; duration: root.ms(260); easing.type: Easing.OutCubic }
  }

  Timer { id: gTimer; interval: 700; onTriggered: root.pendingG = false }
  Timer { id: toastTimer; interval: 4000; onTriggered: root.toast = "" }

  // ── Бэкенд: один процесс, пока открыт overlay ───────────────────────
  // backend/run.py serve — запрос/ответ строками JSON. Запускается при первом запросе,
  // останавливается в close(): окно закрыто — процесса нет. В простое спит в read().
  // Не перенесённые на Python команды бэкенд сам отдаёт старому customizer.sh.
  property int rpcId: 0
  property var rpcPending: ({})
  property var rpcQueue: []
  property bool backendReady: false
  function call(args, cb) {
    // Окно закрыто — бэкенд не поднимаем (энергия): отказ, но асинхронно и один раз.
    if (!root.opened) { Qt.callLater(function() { cb({ code: 1, out: "", err: "closed" }) }); return }
    var id = ++root.rpcId
    root.rpcPending[id] = cb
    var line = JSON.stringify({ id: id, cmd: args }) + "\n"
    if (root.backendReady) backend.write(line)
    else {
      root.rpcQueue = root.rpcQueue.concat([line])
      if (!backend.running) backend.running = true
    }
  }
  function onBackendLine(line) {
    var r
    try { r = JSON.parse(line) } catch (e) { return }
    var cb = root.rpcPending[r.id]
    delete root.rpcPending[r.id]
    if (cb) cb(r)
  }
  // Процесс закончился (окно закрыли или он упал): ждущие ответа получают ошибку, чтобы
  // флаги running у запросов не застряли.
  function backendReset() {
    root.backendReady = false
    root.rpcQueue = []
    var pending = root.rpcPending
    root.rpcPending = ({})
    for (var k in pending) pending[k]({ code: 1, out: "", err: "backend stopped" })
  }
  Process {
    id: backend
    command: ["/usr/bin/python3", "-I", root.pluginDir + "/backend/run.py", "serve"]
    stdinEnabled: true
    stdout: SplitParser { onRead: function(data) { root.onBackendLine(data) } }
    stderr: SplitParser { onRead: function(data) { console.warn("customizer backend:", data) } }
    onStarted: {
      root.backendReady = true
      var q = root.rpcQueue
      root.rpcQueue = []
      for (var i = 0; i < q.length; i++) backend.write(q[i])
    }
    onExited: root.backendReset()
  }

  BackendJob {
    id: searchProc
    host: root
    command: [root.script, "search-index"]
    onExited: root.loadSearchIndex(out)
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/style.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.look = root.parseJson(text())
    onLoadFailed: root.look = ({})
  }

  BackendJob {
    id: lister
    host: root
    property string category: ""
    // Ответ подписан категорией, с которой запрос ушёл (ranCommand): ответ для прошлой вкладки
    // (быстрое переключение) не попадёт в открытую сейчас.
    command: [root.script, "list", category, category === "theme-walls" ? root.wallPath : ""]
    onExited: {
      root.loadRows(lister.ranCommand[2], lister.out)
      var key = root.category.key
      if (root.opened && root.loading && lister.category !== key && !root.cache[key] && !lister.running) {
        lister.category = key
        lister.running = true
      }
    }
  }

  Process {
    id: langProc
    command: [root.script, "lang"]
    stdout: StdioCollector {
      onStreamFinished: {
        var lang = text.trim()
        if (lang && lang !== "en") i18nFile.path = root.pluginDir + "/i18n/" + lang + ".json"
        else root.i18n = ({})
      }
    }
  }

  FileView {
    id: i18nFile
    printErrors: false
    onLoaded: root.i18n = root.parseJson(text())
    onLoadFailed: root.i18n = ({})
  }

  Process {
    id: availableProc
    command: [root.script, "available"]
    stdout: StdioCollector {
      onStreamFinished: root.setAvailable(text)
    }
  }

  // После `hyprctl reload` (и при старте шелла) вернуть сохранённые анимации, прозрачность,
  // блюр и шейдер — так Customizer работает и без строки в конфиге Hyprland.
  Process {
    id: restoreProc
    command: [root.script, "restore"]
  }
  Timer {
    id: soundArmTimer
    interval: 2500
    running: true
    onTriggered: root.soundEventsArmed = true
  }
  Timer {
    id: reloadSilenceTimer
    interval: 1000
  }
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (event.name === "configreloaded") {
        reloadSilenceTimer.restart()
        restoreProc.running = false
        restoreProc.running = true
        return
      }
      if (!root.soundEventsArmed || reloadSilenceTimer.running || !root.windowSoundsEnabled) return
      var snd = ""
      if (event.name === "workspace" || event.name === "workspacev2") snd = "switch"
      else if (event.name === "activespecial" || event.name === "activespecialv2") snd = "special"
      else if (event.name === "openwindow") snd = "open"
      else if (event.name === "closewindow") snd = "close"
      else if (event.name === "fullscreen") snd = "fullscreen"
      if (snd !== "") Quickshell.execDetached([root.pluginDir + "/scripts/play-sound.sh", snd])
    }
  }
  Component.onCompleted: {
    langProc.running = true
    availableProc.running = true
    restoreProc.running = true
  }

  BackendJob {
    id: statusProc
    host: root
    command: [root.script, "status"]
    onExited: root.loadStatus(out)
  }

  FileView {
    id: previewFile
    blockLoading: false
    printErrors: false
    // Bar Tweaks rows all preview bar-skin.json, which changes under them.
    watchChanges: true
    onFileChanged: reload()
    onLoaded: root.previewText = root.formatPreview(text())
    onLoadFailed: root.previewText = ""
  }

  BackendJob {
    id: tweaker
    host: root
    property string key: ""
    onExited: root.tweakDone()
  }

  BackendJob {
    id: favProc
    host: root
    property string slug: ""
    onExited: root.reloadCategory()
  }

  BackendJob {
    id: editor
    host: root
    property string key: ""
    onExited: function(code) {
      if (root.pendingSet !== null) {
        var ps = root.pendingSet
        root.pendingSet = null
        if (ps.index < displayModel.count) {
          editor.key = root.tweakKey(displayModel.get(ps.index))
          editor.command = [root.script, "tweak", editor.key, "set", ps.value]
          editor.running = true
          return
        }
      }
      if (code === 0) {
        if (root.editingIndex >= 0) root.cancelEdit()
        root.reloadCategory()
      } else {
        var msg = editor.err.trim() || root.tr("Not applied")
        if (root.editingIndex >= 0) root.editError = msg
        else root.showToast(msg)
      }
    }
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/bar-skin.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.activeSkin = root.parseJson(text())
    onLoadFailed: root.activeSkin = ({})
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/wallpaper-transition.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.activeFx = root.parseJson(text())
    onLoadFailed: root.activeFx = ({})
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/image-picker.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.activePicker = root.parseJson(text())
    onLoadFailed: root.activePicker = ({})
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/shell.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.activeBar = root.parseJson(text()).bar || ({})
  }

  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.parsePalette(text())
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/sounds.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.activeSounds = root.parseJson(text())
    onLoadFailed: root.activeSounds = ({})
  }

  GlyphOverlay {
    id: glyphOverlay
    activeSkin: root.activeSkin
    activeBar: root.activeBar
    palette: root.themePalette
    soundScript: root.pluginDir + "/scripts/play-sound.sh"
  }

  // Live preview, debounced so scrolling doesn't reload Hyprland per row.
  Timer {
    id: previewTimer
    interval: 250
    onTriggered: {
      var row = root.selectedRow
      var key = root.category.key
      if (!row || !root.opened || !root.category.live) return
      root.previewing = key
      Quickshell.execDetached([root.script, key === "anims" ? "anim-preview" : key + "-preview", row.value])
    }
  }

  // ── Small building blocks ──────────────────────────────────────────

  // Inline components cannot see ids of this file, so only singletons here.
  component Keycap: Rectangle {
    property string label: ""
    implicitWidth: Math.max(height, capText.implicitWidth + Style.space(10))
    implicitHeight: Style.font.caption + Style.space(8)
    radius: Style.space(4)
    color: Util.alpha(Color.menu.text, 0.08)
    border.width: 1
    border.color: Util.alpha(Color.menu.text, 0.10)
    Text {
      id: capText
      anchors.centerIn: parent
      text: parent.label
      color: Color.menu.text
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
      font.bold: true
    }
  }

  component Hint: Row {
    property string keys: ""
    property string label: ""
    spacing: Style.space(6)
    Keycap { label: parent.keys; anchors.verticalCenter: parent.verticalCenter }
    Text {
      anchors.verticalCenter: parent.verticalCenter
      text: parent.label
      color: Util.alpha(Color.menu.text, 0.55)
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
    }
  }

  component Pill: Rectangle {
    property string label: ""
    property color tone: Color.accent
    implicitWidth: pillText.implicitWidth + Style.space(14)
    implicitHeight: Style.font.caption + Style.space(8)
    radius: height / 2
    color: Util.alpha(tone, 0.16)
    border.width: 1
    border.color: Util.alpha(tone, 0.45)
    Text {
      id: pillText
      anchors.centerIn: parent
      text: parent.label
      color: parent.tone
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 0.6
    }
  }

  // ── Window ─────────────────────────────────────────────────────────

  PanelWindow {
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "omarchy-customizer"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    exclusionMode: ExclusionMode.Ignore

    Rectangle {
      anchors.fill: parent
      color: root.scrim
      opacity: root.opened ? 1 : 0
      Behavior on opacity { NumberAnimation { duration: 160 } }
    }
    MouseArea { anchors.fill: parent; onClicked: root.dismiss() }

    BorderSurface {
      id: card
      width: root.cardWidth
      height: root.cardHeight
      radius: root.cornerRadius
      anchors.centerIn: parent
      color: "transparent"
      borderSpec: Border.flat(Util.alpha(root.foreground, 0.14), 1)
      padding: root.contentMargin + Style.space(4)

      // Стекло: размытая копия обоев, совмещённая с экраном, + тон темы поверх.
      // Свой блюр, а не Hyprland: тот у пользователя бывает выключен (Blur = off).
      ClippingRectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        color: root.background
        z: -1

        Image {
          id: glassWall
          x: -card.x
          y: -card.y
          width: panel.width
          height: panel.height
          source: root.opened && root.glass && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
          sourceSize.width: Math.max(1, panel.width / 2)
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          visible: false
        }
        MultiEffect {
          x: glassWall.x
          y: glassWall.y
          width: glassWall.width
          height: glassWall.height
          source: glassWall
          visible: root.glass && glassWall.status === Image.Ready
          autoPaddingEnabled: false
          blurEnabled: true
          blur: 1
          blurMax: 64
          blurMultiplier: 1.5
          saturation: 0.15
        }
        Rectangle {
          anchors.fill: parent
          color: Util.alpha(root.background, root.glassAlpha)
          radius: root.cornerRadius
          border.width: 1
          border.color: Util.alpha(root.foreground, 0.14)
        }
      }

      // Pop in on open.
      opacity: root.opened ? 1 : 0
      scale: root.opened ? 1 : 0.97
      Behavior on opacity { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
      Behavior on scale { NumberAnimation { duration: root.ms(220); easing.type: Easing.OutBack; easing.overshoot: 1.2 } }

      MouseArea { anchors.fill: parent; onClicked: {} }

      Item {
        id: keyCatcher
        anchors.fill: parent
        focus: true

        Keys.priority: Keys.BeforeItem
        // Yazi-style keys. Normal mode: letters are commands; "/" starts a
        // filter, Enter/Esc leave it. Arrows, Tab and PageUp/Down work too.
        Keys.onPressed: function(event) {
          var k = event.key
          var ctrl = event.modifiers & Qt.ControlModifier
          var t = event.text
          var printable = t && t.length === 1 && t.charCodeAt(0) >= 32 && t.charCodeAt(0) !== 127
          // Нелатинская раскладка (или Ctrl без текста): команда — по физической клавише, как в US.
          // Текст для поиска (t) не трогаем до проверки режима поиска — там нужна сама буква.
          var lk = (!t || t.charCodeAt(0) > 127) ? root.latinKey(event) : ""
          if (ctrl && /^[a-z]$/i.test(lk)) k = Qt.Key_A + (lk.toUpperCase().charCodeAt(0) - 65)
          var pendingG = root.pendingG
          root.pendingG = false

          if (root.wallDeletePath) {
            if (k === Qt.Key_Return || k === Qt.Key_Enter || (lk || t) === "y") root.confirmWallDelete()
            else root.wallDeletePath = ""
            event.accepted = true
            return
          }
          if (root.wallDeleteMsg) root.wallDeleteMsg = ""

          if (root.helpOpen) {
            if (k === Qt.Key_Escape || (lk || t) === "?" || (lk || t) === "q") root.helpOpen = false
            event.accepted = true
            return
          }

          // Поиск: текст фильтрует страницу, ↑↓ — по результатам из других мест, ⏎ — туда
          // (или оставить фильтр, если результат не выбран), Esc — сбросить.
          if (root.filtering) {
            var res = root.searchResults
            if (k === Qt.Key_Escape) { root.filtering = false; root.setFilter("") }
            else if (k === Qt.Key_Return || k === Qt.Key_Enter) {
              if (root.searchSel >= 0 && root.searchSel < res.length) root.jumpTo(res[root.searchSel])
              else { root.filtering = false; root.searchSel = -1 }
            }
            else if (k === Qt.Key_Backspace && !root.filterText) root.filtering = false
            else if (Util.editsFilter(event, root.filterText)) root.setFilter(Util.editedFilter(event, root.filterText))
            else if (k === Qt.Key_Up || k === Qt.Key_Backtab || (ctrl && (k === Qt.Key_K || k === Qt.Key_P))) root.searchSel = Math.max(-1, root.searchSel - 1)
            else if (k === Qt.Key_Down || k === Qt.Key_Tab || (ctrl && (k === Qt.Key_J || k === Qt.Key_N))) root.searchSel = Math.min(res.length - 1, root.searchSel + 1)
            else if (printable && !ctrl) root.setFilter(root.filterText + t)
            else return
            event.accepted = true
            return
          }

          if (lk) { t = lk; printable = true }

          // Везде: вкладки, рейл по цифрам, поиск, помощь, закрыть.
          if (k === Qt.Key_Backtab) root.setTab(-1)
          else if (k === Qt.Key_Tab) root.setTab(1)
          else if (!ctrl && t === "/") root.startSearch()
          else if (!ctrl && t === "?") root.helpOpen = true
          else if (!ctrl && t === "q") root.dismiss()
          else if (!ctrl && t === "0") root.goHome()
          else if (!ctrl && t >= "1" && t <= String(root.groups.length)) root.setGroup(Number(t) - 1)
          else if (!ctrl && t === "v" && !root.homeOpen) root.heroCollapsed = !root.heroCollapsed
          else if (!ctrl && t === "n" && !root.homeOpen) root.noteOpen = !root.noteOpen
          else if (!ctrl && t === "z" && !root.homeOpen && root.heroAvailable) { root.heroFull = !root.heroFull; if (root.heroFull) root.heroCollapsed = false }
          else if (k === Qt.Key_Escape && root.heroFull) root.heroFull = false
          else if (ctrl && k === Qt.Key_D) root.move(root.halfPage())
          else if (ctrl && k === Qt.Key_U) root.move(-root.halfPage())
          else if (ctrl && k === Qt.Key_F) root.move(root.halfPage() * 2)
          else if (ctrl && k === Qt.Key_B) root.move(-root.halfPage() * 2)
          else if (ctrl && k === Qt.Key_N) root.move(1)
          else if (ctrl && k === Qt.Key_P) root.move(-1)
          else if (k === Qt.Key_PageUp) root.move(-root.halfPage() * 2)
          else if (k === Qt.Key_PageDown) root.move(root.halfPage() * 2)
          else if (k === Qt.Key_Home) root.moveTo(0)
          else if (k === Qt.Key_End) root.moveTo(-1)
          else if (!ctrl && t === "g") { if (pendingG) root.moveTo(0); else { root.pendingG = true; gTimer.restart() } }
          else if (!ctrl && t === "G") root.moveTo(-1)
          else {
            if (!root.handlePaneKey(event, k, t, ctrl, printable)) return
          }
          event.accepted = true
        }
      }

      Item {
        id: content
        anchors.fill: parent
        anchors.topMargin: card.contentTopInset
        anchors.rightMargin: card.contentRightInset
        anchors.bottomMargin: card.contentBottomInset
        anchors.leftMargin: card.contentLeftInset

        // ── Рейл: Домой + группы ──────────────────────────────────
        NavRail {
          id: rail
          anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
          width: implicitWidth
          t: root
          items: root.railItems
          currentIndex: root.railIndex
          focused: root.pane === 0 && !root.filtering
          onPicked: function(i) { root.setRail(i); root.pane = 0 }
        }

        Item {
          id: page
          anchors { top: parent.top; bottom: parent.bottom; left: rail.right; leftMargin: Style.space(14); right: parent.right }

          // ── Шапка: крошки, заголовок, поиск, закрыть ─────────────
          Item {
            id: header
            z: 10
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: Style.space(66)

            Column {
              anchors.left: parent.left
              anchors.right: searchBox.left
              anchors.rightMargin: Style.space(16)
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(4)
              Text {
                width: parent.width
                text: (root.homeOpen ? "Customizer  ·  " + root.tr("Look & feel")
                  : root.group.title + "  ·  " + root.category.hint
                    + (root.category.key === "theme-walls" && root.wallPath ? "  ·  󰉋 " + root.wallPath : "")).toUpperCase()
                elide: Text.ElideRight
                color: root.primary
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                font.bold: true
                font.letterSpacing: 1.2
              }
              Text {
                width: parent.width
                text: root.homeOpen ? root.tr("Home") : root.category.title
                elide: Text.ElideRight
                color: root.foreground
                font.family: root.headFont
                font.pixelSize: Style.font.display
                font.bold: true
              }
            }

            Rectangle {
              id: searchBox
              anchors.right: closeBtn.left
              anchors.rightMargin: Style.space(10)
              anchors.verticalCenter: parent.verticalCenter
              width: Math.min(Style.space(340), parent.width * 0.36)
              height: Style.space(44)
              radius: root.dot ? Style.space(3) : height / 2
              color: root.filtering ? root.surfaceHi : root.surfaceLow
              border.width: root.filtering ? Style.space(2) : (root.dot ? 1 : 0)
              border.color: root.filtering ? root.primary : root.outline
              Behavior on color { ColorAnimation { duration: root.ms(140) } }

              Text {
                id: searchIcon
                anchors.left: parent.left
                anchors.leftMargin: Style.space(16)
                anchors.verticalCenter: parent.verticalCenter
                text: "󰍉"
                color: root.filtering ? root.primary : root.muted
                font.family: root.iconFont
                font.pixelSize: Style.font.title
              }
              Text {
                anchors.left: searchIcon.right
                anchors.leftMargin: Style.space(10)
                anchors.right: searchKey.left
                anchors.rightMargin: Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.PlainText
                text: root.filtering ? root.filterText + "▏" : root.filterText ? root.filterText : root.tr("Search settings")
                color: root.filtering || root.filterText ? root.foreground : root.muted
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
                elide: Text.ElideLeft
              }
              Keycap {
                id: searchKey
                anchors.right: parent.right
                anchors.rightMargin: Style.space(12)
                anchors.verticalCenter: parent.verticalCenter
                label: root.filtering ? "Esc" : "/"
              }
              MouseArea {
                anchors.fill: parent
                cursorShape: Qt.IBeamCursor
                onClicked: root.startSearch()
              }
            }

            Rectangle {
              id: closeBtn
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              width: Style.space(40); height: width
              radius: root.dot ? Style.space(3) : width / 2
              color: closeHover.containsMouse ? root.surfaceHi : "transparent"
              Text {
                anchors.centerIn: parent
                text: "󰅖"
                color: root.foreground
                font.family: root.iconFont
                font.pixelSize: Style.font.title
              }
              MouseArea {
                id: closeHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.dismiss()
              }
            }

            // Результаты поиска из других мест: ↑↓ — выбрать, ⏎ — перейти.
            Rectangle {
              id: searchDrop
              visible: root.filtering && root.searchResults.length > 0
              anchors.top: searchBox.bottom
              anchors.topMargin: Style.space(6)
              anchors.right: closeBtn.right
              width: Math.max(searchBox.width + closeBtn.width + Style.space(10), Style.space(460))
              height: dropCol.implicitHeight + Style.space(12)
              radius: root.rCard
              color: Qt.rgba(root.background.r, root.background.g, root.background.b, 0.98)
              border.width: 1
              border.color: root.outline
              layer.enabled: visible
              layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#000000"
                shadowOpacity: 0.45
                shadowBlur: 0.8
                shadowVerticalOffset: 4
              }

              Column {
                id: dropCol
                anchors { top: parent.top; left: parent.left; right: parent.right; margins: Style.space(6) }
                spacing: Style.space(2)
                Text {
                  leftPadding: Style.space(10)
                  topPadding: Style.space(4)
                  bottomPadding: Style.space(4)
                  text: root.tr("In other sections")
                  color: root.muted
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption
                  font.bold: true
                }
                Repeater {
                  model: root.searchResults
                  delegate: Rectangle {
                    id: hit
                    required property int index
                    required property var modelData
                    readonly property bool sel: index === root.searchSel
                    width: dropCol.width
                    height: Style.space(50)
                    radius: Math.max(2, root.rCard - Style.space(6))
                    color: sel ? root.secondaryContainer : (hitHover.containsMouse ? root.surfaceHi : "transparent")
                    Text {
                      id: hitIcon
                      anchors.left: parent.left
                      anchors.leftMargin: Style.space(12)
                      anchors.verticalCenter: parent.verticalCenter
                      text: hit.modelData.icon
                      color: root.primary
                      font.family: root.iconFont
                      font.pixelSize: Style.font.title
                    }
                    Column {
                      anchors.left: hitIcon.right
                      anchors.leftMargin: Style.space(12)
                      anchors.right: parent.right
                      anchors.rightMargin: Style.space(12)
                      anchors.verticalCenter: parent.verticalCenter
                      spacing: Style.space(2)
                      Text {
                        width: parent.width
                        text: hit.modelData.label
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                        color: root.foreground
                        font.family: root.fontFamily
                        font.pixelSize: Style.font.body
                        font.bold: hit.sel
                      }
                      Text {
                        width: parent.width
                        text: hit.modelData.where
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                        color: root.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.font.caption
                      }
                    }
                    MouseArea {
                      id: hitHover
                      anchors.fill: parent
                      hoverEnabled: true
                      cursorShape: Qt.PointingHandCursor
                      onClicked: root.jumpTo(hit.modelData)
                    }
                  }
                }
              }
            }
          }

          // ── Вкладки группы + «Удиви меня» ─────────────────────────
          TabStrip {
            id: tabs
            visible: !root.homeOpen
            anchors { top: header.bottom; topMargin: Style.space(4); left: parent.left; right: tabTools.left; rightMargin: Style.space(10) }
            height: implicitHeight
            t: root
            items: root.groupTabs
            currentIndex: root.groupCategories.indexOf(root.categoryIndex)
            onPicked: function(i) { root.setCategory(root.groupCategories[i]) }
          }
          Row {
            id: tabTools
            visible: !root.homeOpen
            anchors.right: parent.right
            anchors.verticalCenter: tabs.verticalCenter
            spacing: Style.space(8)
            Rectangle {
              visible: root.category.key !== "walls" && root.category.key !== "dotify" && !root.category.presetStage && root.category.key !== "glyph" && !root.category.tweak
              height: Style.space(34)
              width: randomRow.implicitWidth + Style.space(24)
              radius: root.dot ? Style.space(3) : height / 2
              color: randomHover.containsMouse ? root.secondaryContainer : root.surfaceLow
              Row {
                id: randomRow
                anchors.centerIn: parent
                spacing: Style.space(8)
                Text { text: "󰒝"; color: root.primary; font.family: root.iconFont; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
                Text { text: root.tr("Surprise me"); color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall; anchors.verticalCenter: parent.verticalCenter }
                Keycap { label: "r"; anchors.verticalCenter: parent.verticalCenter }
              }
              MouseArea { id: randomHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.randomPick() }
            }
            Rectangle {
              visible: root.heroAvailable
              height: Style.space(34)
              width: heroRow.implicitWidth + Style.space(24)
              radius: root.dot ? Style.space(3) : height / 2
              color: heroHover.containsMouse ? root.secondaryContainer : root.surfaceLow
              Row {
                id: heroRow
                anchors.centerIn: parent
                spacing: Style.space(8)
                Text { text: root.heroCollapsed ? "󰈈" : "󰈉"; color: root.primary; font.family: root.iconFont; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
                Text { text: root.tr("Preview"); color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall; anchors.verticalCenter: parent.verticalCenter }
                Keycap { label: "v"; anchors.verticalCenter: parent.verticalCenter }
              }
              MouseArea { id: heroHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.heroCollapsed = !root.heroCollapsed }
            }
          }

          // ── Футер: подсказки клавиш, счётчик / ошибка ─────────────
          Item {
            id: footer
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: Style.font.caption + Style.space(12)

            Row {
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(16)
              Repeater {
                model: root.keyHints()
                delegate: Hint {
                  required property var modelData
                  keys: modelData[0]
                  label: root.tr(modelData[1])
                }
              }
            }

            Text {
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              width: Math.min(implicitWidth, parent.width * 0.4)
              elide: Text.ElideRight
              textFormat: Text.PlainText
              text: root.toast ? "⚠ " + root.toast
                : !root.homeOpen && displayModel.count ? (root.selectedIndex + 1) + " / " + displayModel.count : ""
              color: root.toast ? Color.urgent : root.muted
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
          }

          // ── Тело страницы ─────────────────────────────────────────
          Item {
            id: pageBody
            anchors {
              top: tabs.visible ? tabs.bottom : header.bottom
              topMargin: Style.space(14)
              bottom: footer.top
              bottomMargin: Style.space(10)
              left: parent.left
              right: parent.right
            }
            transform: Translate { id: pageShift }

            HomePage {
              id: homePage
              anchors.fill: parent
              visible: root.homeOpen
              t: root
              cards: root.homeCards
              actions: root.homeActions
              wallpaper: root.homeOpen && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
              palette: root.homePalette
              selectedIndex: root.homeSel
              focused: root.pane === 1 && !root.filtering
              onOpenCard: function(i) { root.pane = 1; root.homeSel = i; root.homeActivate(i) }
            }

            // Карточка превью: сцена слева, заметка справа (v — свернуть).
            Item {
              id: hero
              clip: true
              visible: !root.homeOpen && root.heroAvailable && (!root.heroCollapsed || root.heroFull) && root.selectedRow !== null
              anchors { top: parent.top; left: parent.left; right: parent.right }
              // Макетам (previews/) — больше места: в них мелкие детали.
              height: !visible ? 0 : root.heroFull ? pageBody.height : Math.max(Style.space(200), Math.round(pageBody.height
                * (root.sceneCategories.indexOf(root.category.key) !== -1 ? 0.5 : 0.38)))
              Behavior on height { NumberAnimation { duration: root.ms(220); easing.type: Easing.OutCubic } }
              // Не через .visible сцен: они невидимы, пока невидим сам stageArea (замкнутый круг).
              readonly property bool hasVisual: {
                var c = root.category, row = root.selectedRow
                if (c.key === "windows" || c.key === "widgets" || root.sceneCategories.indexOf(c.key) !== -1) return true
                if (!row) return false
                return c.key === "opacity" || c.key === "blur" || c.bar === true || c.fx === true || c.picker === true
                  || c.presetStage === true || c.key === "anims" || c.key === "shaders"
                  || (c.key === "fonts" && !root.isHeader(row))
                  || (c.image === true && !root.isTweakRow(row))
              }
              // Описание поверх сцены (n / ⓘ); без сцены — описание и есть содержимое.
              readonly property bool noteShown: !hasVisual || root.noteOpen

              ClippingRectangle {
                id: stageArea
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: hero.hasVisual ? hero.width : 0
                visible: width > 0
                radius: root.rCard
                color: root.surface
                border.width: root.dot ? 1 : 0
                border.color: root.outline

                // Pictures: crop wallpapers to fill, keep theme screenshots whole.
                Image {
                  id: previewImage
                  anchors.fill: parent
                  readonly property bool showImage: root.category.image && root.category.key !== "dotify" && root.selectedRow !== null && !root.isTweakRow(root.selectedRow)
                  visible: showImage
                  source: showImage && root.selectedRow.preview ? root.fileUrl(root.selectedRow.preview) : ""
                  sourceSize.width: Math.max(1, stageArea.width * 2)
                  sourceSize.height: Math.max(1, stageArea.height * 2)
                  fillMode: root.category.key === "themes" ? Image.PreserveAspectFit : Image.PreserveAspectCrop
                  asynchronous: true
                  cache: false
                  opacity: status === Image.Ready ? 1 : 0
                  Behavior on opacity { NumberAnimation { duration: 200 } }
                }

                // Картинки нет (снимок лока ещё не снят, файл удалён) — подсказка вместо пустого поля.
                Text {
                  anchors.centerIn: parent
                  width: parent.width - Style.space(40)
                  visible: previewImage.showImage && root.selectedRow !== null && !!root.selectedRow.preview && previewImage.status === Image.Error
                  horizontalAlignment: Text.AlignHCenter
                  wrapMode: Text.Wrap
                  text: root.category.key === "lock" ? root.tr("No preview yet — T captures the missing ones, p shows the design live.")
                    : root.tr("No preview for this item.")
                  color: root.foreground
                  opacity: 0.6
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                }

                // Theme palette strip along the bottom edge.
                Row {
                  id: paletteStrip
                  visible: root.category.key === "themes" && root.selectedRow !== null && root.paletteOf(root.selectedRow.note).length > 0
                  anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                  height: Style.space(30)
                  Repeater {
                    model: root.selectedRow ? root.paletteOf(root.selectedRow.note) : []
                    delegate: Rectangle {
                      required property string modelData
                      width: paletteStrip.width / Math.max(1, root.paletteOf(root.selectedRow ? root.selectedRow.note : "").length)
                      height: paletteStrip.height
                      color: modelData
                    }
                  }
                }

                Column {
                  anchors.centerIn: parent
                  visible: root.category.image && root.selectedRow !== null && !root.isTweakRow(root.selectedRow) && !root.selectedRow.preview
                  width: parent.width * 0.8
                  spacing: Style.space(8)
                  Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "󰋩"
                    color: root.accent
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.displayLarge * 2
                  }
                  Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: root.selectedRow && root.selectedRow.note ? root.selectedRow.note
                      : root.category.key === "lock" ? root.tr("No preview yet — T captures the missing ones, p shows the design live.")
                      : root.tr("No preview image")
                    color: root.muted
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.title
                  }
                }

                // Transparency / blur: two mock windows over the current wallpaper.
                // Like Hyprland with xray on, each window blurs the wallpaper
                // behind it and lays its own background on top at its opacity.
                Item {
                  id: opacityStage
                  anchors.fill: parent
                  visible: (root.category.key === "opacity" || root.category.key === "blur") && root.selectedRow !== null
                  readonly property var values: root.stageOpacity()
                  readonly property real blurAmount: root.stageBlur()
                  readonly property url wallpaper: visible && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""

                  Image {
                    anchors.fill: parent
                    source: opacityStage.wallpaper
                    sourceSize.width: Math.max(1, stageArea.width)
                    sourceSize.height: Math.max(1, stageArea.height)
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                  }

                  Repeater {
                    model: [
                      { name: "inactive", x: 0.08, y: 0.12, w: 0.55, h: 0.55, value: 1 },
                      { name: "active",   x: 0.36, y: 0.34, w: 0.56, h: 0.54, value: 0 }
                    ]
                    delegate: Item {
                      id: mockWindow
                      required property var modelData
                      readonly property bool isActive: modelData.name === "active"
                      readonly property real level: opacityStage.values[modelData.value]
                      x: opacityStage.width * modelData.x
                      y: opacityStage.height * modelData.y
                      width: opacityStage.width * modelData.w
                      height: opacityStage.height * modelData.h

                      ClippingRectangle {
                        anchors.fill: parent
                        radius: root.innerRadius
                        color: "transparent"

                        Image {
                          x: -mockWindow.x
                          y: -mockWindow.y
                          width: opacityStage.width
                          height: opacityStage.height
                          source: opacityStage.wallpaper
                          sourceSize.width: Math.max(1, stageArea.width)
                          sourceSize.height: Math.max(1, stageArea.height)
                          fillMode: Image.PreserveAspectCrop
                          asynchronous: true
                          visible: opacityStage.blurAmount > 0
                          layer.enabled: visible
                          layer.effect: MultiEffect {
                            blurEnabled: true
                            blur: opacityStage.blurAmount
                            blurMax: 48
                            autoPaddingEnabled: false
                          }
                        }
                      }

                      Rectangle {
                        anchors.fill: parent
                        radius: root.innerRadius
                        color: Util.alpha(Color.background, mockWindow.level)
                        border.width: 2
                        border.color: mockWindow.isActive ? root.accent : Util.alpha(root.foreground, 0.25)
                        Behavior on color { ColorAnimation { duration: 200 } }
                      }

                      Column {
                        anchors.fill: parent
                        anchors.margins: Style.space(14)
                        spacing: Style.space(8)
                        Row {
                          spacing: Style.space(6)
                          Repeater {
                            model: 3
                            delegate: Rectangle {
                              width: Style.space(9); height: width; radius: width / 2
                              color: Util.alpha(root.foreground, 0.35)
                            }
                          }
                        }
                        Text {
                          text: (mockWindow.isActive ? "active" : "inactive") + "  " + mockWindow.level.toFixed(2)
                          color: Color.foreground
                          font.family: root.fontFamily
                          font.pixelSize: Style.font.heading
                          font.bold: true
                        }
                        Repeater {
                          model: [0.9, 0.7, 0.8, 0.5]
                          delegate: Rectangle {
                            required property real modelData
                            width: (opacityStage.width * 0.4) * modelData
                            height: Style.space(6)
                            radius: 3
                            color: Util.alpha(Color.foreground, 0.3)
                          }
                        }
                      }
                    }
                  }

                  // Which preset each half of the stage comes from.
                  Pill {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.margins: Style.space(12)
                    tone: Color.foreground
                    label: "opacity " + (root.category.key === "opacity" && root.selectedRow ? root.selectedRow.value : root.status.opacity || "—")
                      + "  ·  blur " + (root.category.key === "blur" && root.selectedRow ? root.selectedRow.value : root.status.blur || "—")
                  }
                }

                // Bar: a mock of kamradsmeshnyavy.bar over the wallpaper, then the row's note.
                Item {
                  id: barStage
                  anchors.fill: parent
                  visible: root.category.bar === true && root.selectedRow !== null
                  readonly property url wallpaper: visible && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
                  readonly property var bar: root.mockBar()
                  readonly property bool vertical: bar.position === "left" || bar.position === "right"

                  // Горизонтальный бар — полоса экрана в настоящем масштабе (как было). Вертикальный во всю
                  // высоту экрана в низкую карточку не влезал и обрезался: экран рисуется в настоящем размере
                  // и уменьшается так, чтобы вся его высота вошла в карточку, у той стороны, где бар.
                  Item {
                    id: barCanvas
                    readonly property real sw: panel.screen ? panel.screen.width : 1440
                    readonly property real sh: panel.screen ? panel.screen.height : 900
                    readonly property real k: barStage.vertical ? Math.min(1, barStage.height / sh) : 1
                    width: barStage.vertical ? Math.min(sw, barStage.width / k) : barStage.width
                    height: barStage.vertical ? sh : barStage.height
                    scale: k
                    transformOrigin: Item.TopLeft
                    x: barStage.vertical ? Math.round((barStage.width - width * k) / 2) : 0

                    ClippingRectangle {
                      id: barScreen
                      anchors.fill: parent
                      radius: root.innerRadius / barCanvas.k
                      color: "transparent"

                      Image {
                        anchors.fill: parent
                        source: barStage.wallpaper
                        sourceSize.width: Math.max(1, barCanvas.width * barCanvas.k * 2)
                        fillMode: Image.PreserveAspectCrop
                        verticalAlignment: barStage.bar.position === "bottom" ? Image.AlignBottom : Image.AlignTop
                        horizontalAlignment: barStage.bar.position === "right" ? Image.AlignRight : Image.AlignLeft
                        asynchronous: true
                      }

                      BarMock {
                        anchors.fill: parent
                        skin: root.mockSkin()
                        bar: barStage.bar
                        palette: root.themePalette
                        screenWidth: barCanvas.sw
                      }
                    }
                  }

                }

                // Wallpaper FX: выбранный эффект крутится между текущими и следующими обоями.
                Item {
                  id: fxStage
                  anchors.fill: parent
                  visible: root.category.fx === true && root.selectedRow !== null
                  readonly property string effect: {
                    var row = root.selectedRow
                    // Строки-действия и заголовки — не переходы: на них превью играет текущий переход.
                    var action = !row || root.isTweakRow(row) || root.isHeader(row)
                      || ["outline-warm", "outline-install", "enable-plugin"].indexOf(String(row.value)) !== -1
                    var e = action ? String(root.activeFx.type || "slant") : row.value
                    return e === "none" || e === "random" ? "fade" : e
                  }
                  readonly property bool scene: effect === "contagion" || effect === "outline" || effect === "outline-cut"
                  // contagion / outline — «сцены»: своя длительность, линейно (кривые внутри шейдера)
                  readonly property int duration: scene ? Math.max(600, Number(root.activeFx.durationScene) || 1900) / 2
                                                        : Math.max(150, Number(root.activeFx.duration) || 420)

                  ClippingRectangle {
                    id: fxScreen
                    anchors.centerIn: parent
                    width: Math.min(parent.width, parent.height * 16 / 9)
                    height: width * 0.5625
                    radius: root.innerRadius
                    color: "transparent"

                    Image {
                      id: fxFrom
                      anchors.fill: parent
                      source: fxStage.visible && root.status["wallpaper-next"] ? root.fileUrl(root.status["wallpaper-next"]) : ""
                      sourceSize.width: Math.max(1, fxScreen.width)
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                    }
                    Image {
                      id: fxTo
                      anchors.fill: parent
                      source: fxStage.visible && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
                      sourceSize.width: Math.max(1, fxScreen.width)
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                    }
                    // Тот же шейдер переходов, что у обоев: берём его из плагина kamradsmeshnyavy.background,
                    // если он стоит (без него категория Wallpaper FX скрыта).
                    Loader {
                      id: fxEffect
                      anchors.fill: parent
                      property real progress: 0
                      active: root.isAvailable("wallpaper-fx")
                      source: active ? "file://" + Quickshell.env("HOME") + "/.config/omarchy/plugins/kamradsmeshnyavy.background/TransitionEffect.qml" : ""
                      visible: fxStage.visible && fxFrom.status === Image.Ready && fxTo.status === Image.Ready && status === Loader.Ready
                      onLoaded: {
                        item.fromItem = fxFrom
                        item.toItem = fxTo
                        item.origin = Qt.point(0.5, 0.5)
                        item.effect = Qt.binding(function() { return fxStage.effect })
                        item.angleDegrees = Qt.binding(function() { return Number(root.activeFx.angle || 0) })
                        item.softness = Qt.binding(function() { return root.activeFx.softness !== undefined ? Number(root.activeFx.softness) : 0.02 })
                        item.progress = Qt.binding(function() { return fxEffect.progress })
                        if (item.cell !== undefined) {
                          item.cell = Qt.binding(function() { return Number(root.activeFx.cell) || 6 })
                          item.glow = Qt.binding(function() { return root.activeFx.frontGlow !== undefined ? Number(root.activeFx.frontGlow) : 0.9 })
                          item.lineW = Qt.binding(function() { return Number(root.activeFx.lineWidth) || 1.5 })
                          item.capturePalette()
                        }
                      }
                      // Цикл: переход (длительность из настроек), пауза, заново.
                      SequentialAnimation on progress {
                        running: fxEffect.visible
                        loops: Animation.Infinite
                        NumberAnimation { from: 0; to: 1; duration: fxStage.duration * 2
                          easing.type: fxStage.scene ? Easing.Linear : Easing.InOutCubic }
                        PauseAnimation { duration: 700 }
                      }
                    }
                  }

                }

                // Theme Switcher: макет карусели в выбранном (или текущем) стиле.
                Item {
                  id: pickerStage
                  anchors.fill: parent
                  visible: root.category.picker === true && root.selectedRow !== null
                  readonly property string style: {
                    var row = root.selectedRow
                    return row && /^style:/.test(row.value) ? row.value.slice(6) : String(root.activePicker.style || "slices")
                  }

                  Rectangle {
                    id: pickerScreen
                    anchors.fill: parent
                    radius: root.innerRadius
                    color: Util.alpha(Color.background, 0.9)
                    clip: true
                    PickerMock {
                      anchors.fill: parent
                      anchors.margins: Style.space(10)
                      style: pickerStage.style
                      config: root.activePicker
                      images: root.status["picker-previews"] ? String(root.status["picker-previews"]).split("|") : []
                    }
                  }

                }

                // Global Presets: hero wallpaper preview + description and JSON summary.
                // Стиль / пресет: мини-стол с его баром, окнами и обоями (описание — по n).
                Item {
                  id: presetStage
                  anchors.fill: parent
                  visible: root.category.presetStage === true && root.selectedRow !== null
                  // Строки-переключатели (что применять) и «Сохранить» — показывают стол как сейчас.
                  readonly property var presetData: visible && root.selectedRow && !root.isTweakRow(root.selectedRow) && root.previewText
                    ? root.parseJson(root.previewText) : ({})
                  Previews.StylePreview {
                    anchors.fill: parent
                    anchors.margins: Style.space(10)
                    t: root
                    doc: presetStage.presetData
                    currentWallpaper: root.wallpaperUrl
                    activeSkin: root.activeSkin
                    activeBar: root.activeBar
                    palette: root.themePalette
                    screenWidth: panel.screen ? panel.screen.width : 1440
                    screenHeight: panel.screen ? panel.screen.height : 900
                  }
                }

                // Анимации: мини-сцена с кривыми пресета (код .lua — по n).
                Previews.AnimsPreview {
                  anchors.fill: parent
                  anchors.margins: Style.space(10)
                  visible: root.category.key === "anims" && root.selectedRow !== null
                  t: root
                  lua: visible ? root.previewText : ""
                  wallpaper: visible ? root.wallpaperUrl : ""
                  screenWidth: panel.screen ? panel.screen.width : 1440
                  screenHeight: panel.screen ? panel.screen.height : 900
                }

                // Шейдер экрана: мини-стол через Qt-вариант шейдера (код .frag — по n).
                Previews.ShaderPreview {
                  anchors.fill: parent
                  anchors.margins: Style.space(10)
                  visible: root.category.key === "shaders" && root.selectedRow !== null
                  t: root
                  shader: !visible ? "" : /^(toggle|next)$/.test(root.selectedRow.value) ? String(root.status.shader || "") : String(root.selectedRow.value)
                  wallpaper: visible ? root.wallpaperUrl : ""
                  screenWidth: panel.screen ? panel.screen.width : 1440
                  screenHeight: panel.screen ? panel.screen.height : 900
                }

                // Fonts: образцы текста шрифтами профиля — заголовок (title), интерфейс (sans), код (mono).
                Item {
                  id: fontStage
                  anchors.fill: parent
                  anchors.margins: Style.space(14)
                  visible: root.category.key === "fonts" && root.selectedRow !== null && !root.isHeader(root.selectedRow)
                  readonly property var faces: visible ? String(root.selectedRow.sub).split(" · ") : []
                  readonly property string sans: faces.length > 0 ? faces[0] : Style.font.family
                  readonly property string mono: faces.length > 1 ? faces[1] : Style.font.family
                  readonly property string title: faces.length > 2 ? faces[2] : sans

                  // Специмен: три колонки — заголовки, интерфейс, код — крупное «Aa», алфавит, цифры.
                  Row {
                    anchors.fill: parent
                    spacing: Style.space(14)
                    Repeater {
                      model: [
                        { face: fontStage.title, role: "Titles" },
                        { face: fontStage.sans, role: "Interface" },
                        { face: fontStage.mono, role: "Code" }
                      ]
                      Rectangle {
                        required property var modelData
                        width: (parent.width - 2 * Style.space(14)) / 3
                        height: parent.height
                        radius: root.rCard
                        color: root.surfaceLow
                        Column {
                          anchors.centerIn: parent
                          width: parent.width - Style.space(28)
                          spacing: Style.space(6)
                          Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: "Aa Яя"
                            font.family: modelData.face
                            font.pixelSize: Math.round(Math.min(parent.width / 3.2, fontStage.height * 0.28))
                            color: root.foreground
                          }
                          Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.role === "Code" ? "{ } => != >= 0O 1lI" : "AaBbCc АаБбВв 0123"
                            font.family: modelData.face
                            font.pixelSize: Style.font.title
                            elide: Text.ElideRight
                            color: root.foreground
                            opacity: 0.85
                          }
                          Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: root.tr(modelData.role) + " · " + modelData.face
                            elide: Text.ElideRight
                            font.family: root.fontFamily
                            font.pixelSize: Style.font.caption
                            color: root.muted
                          }
                        }
                      }
                    }
                  }
                }

                // Windows: мини-экран с тремя окнами — отступы, рамки, скругление, тень, затемнение и
                // раскладка из windows.json (меняются h/l — сцена перерисовывается сразу).
                Item {
                  id: windowsStage
                  anchors.fill: parent
                  anchors.margins: Style.space(12)
                  visible: root.category.key === "windows"
                  property var cfg: ({})
                  FileView {
                    path: Quickshell.env("HOME") + "/.config/omarchy/customizer/windows.json"
                    watchChanges: true; printErrors: false
                    onFileChanged: reload()
                    onLoaded: windowsStage.cfg = root.parseJson(text())
                    onLoadFailed: windowsStage.cfg = ({})
                  }
                  function n(k, d) { var v = Number(cfg[k]); return cfg[k] === undefined || !isFinite(v) ? d : v }
                  function b(k, d) { return cfg[k] === undefined ? d : cfg[k] === true }
                  readonly property bool noGaps: b("windowNoGaps", false)
                  readonly property real k: screenBox.width / 1440
                  readonly property real gin: noGaps ? 0 : n("windowGapsIn", 2) * k
                  readonly property real gout: noGaps ? 0 : n("windowGapsOut", 4) * k
                  readonly property real bw: noGaps ? 0 : n("windowBorder", 2) > 0 ? Math.max(1, n("windowBorder", 2) * k) : 0
                  readonly property real rad: noGaps ? 0 : n("windowDecoRounding", 10) * k
                  readonly property bool shadow: b("windowShadow", true)
                  readonly property bool dim: b("windowDim", true)
                  readonly property real dimStrength: n("windowDimStrength", 0.1)
                  readonly property bool master: String(cfg.windowLayout || "dwindle") === "master"

                  ClippingRectangle {
                    id: screenBox
                    anchors.centerIn: parent
                    width: Math.min(parent.width, parent.height * 1.6)
                    height: width / 1.6
                    radius: root.innerRadius
                    color: root.faint
                    Image {
                      anchors.fill: parent
                      source: windowsStage.visible && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                      sourceSize.width: 640
                    }
                    Rectangle { width: parent.width; height: Math.max(6, parent.height * 0.045); color: Color.bar.background }
                    Item {
                      id: area
                      x: windowsStage.gout
                      y: Math.max(6, screenBox.height * 0.045) + windowsStage.gout
                      width: screenBox.width - 2 * windowsStage.gout
                      height: screenBox.height - y - windowsStage.gout
                      readonly property real split: windowsStage.master ? 0.62 : 0.5
                      Repeater {
                        model: 3
                        Rectangle {
                          required property int index
                          readonly property bool active: index === 0
                          readonly property real g: windowsStage.gin / 2
                          x: index === 0 ? 0 : area.width * area.split + g
                          y: index === 2 ? area.height / 2 + g : 0
                          width: index === 0 ? area.width * area.split - g : area.width * (1 - area.split) - g
                          height: index === 0 ? area.height : area.height / 2 - g
                          radius: windowsStage.rad
                          color: Qt.tint(Color.background, Qt.rgba(0, 0, 0, !active && windowsStage.dim ? windowsStage.dimStrength : 0))
                          border.width: windowsStage.bw
                          border.color: active ? root.accent : Util.alpha(root.foreground, 0.25)
                          layer.enabled: windowsStage.shadow
                          layer.effect: MultiEffect { shadowEnabled: true; shadowColor: "#000000"; shadowOpacity: 0.45; shadowBlur: 0.5; shadowVerticalOffset: 2 }
                          Column {
                            x: 8; y: 8; spacing: 4
                            Repeater {
                              model: 4
                              Rectangle { required property int index; width: 30 + (index * 23) % 50; height: 3; radius: 1.5; color: Util.alpha(root.foreground, 0.3) }
                            }
                          }
                        }
                      }
                    }
                  }
                }

                // Widgets: мини-стол с раскладкой включённых виджетов (widgets.json): позиции по якорям, как
                // place() в Widgets.qml; виджет выбранной строки подсвечен, наложения — красным.
                Item {
                  id: widgetsStage
                  anchors.fill: parent
                  anchors.margins: Style.space(12)
                  visible: root.category.key === "widgets"
                  property var cfg: ({})
                  FileView {
                    path: Quickshell.env("HOME") + "/.config/omarchy/widgets.json"
                    watchChanges: true; printErrors: false
                    onFileChanged: reload()
                    onLoaded: widgetsStage.cfg = root.parseJson(text())
                    onLoadFailed: widgetsStage.cfg = ({})
                  }
                  // Имя, ключ включения, якорь по умолчанию, размер на экране 1440 px (примерно как у виджетов).
                  readonly property var defs: [
                    { key: "clock", title: "Clock", on: true, anchor: "top-left", w: 280, h: 130 },
                    { key: "network", title: "Network", on: false, anchor: "top-left", w: 320, h: 90 },
                    { key: "media", title: "Now playing", on: true, anchor: "bottom-left", w: 400, h: 120 },
                    { key: "sysinfo", title: "System rings", on: true, anchor: "top-right", w: 380, h: 110 },
                    { key: "todo", title: "Todo", on: false, anchor: "right", w: 300, h: 170 },
                    { key: "quote", title: "Quote", on: false, anchor: "bottom-right", w: 320, h: 110 },
                    { key: "photo", title: "Photo", on: false, anchor: "left", w: 260, h: 210 }
                  ]
                  readonly property string focusKey: {
                    var v = root.selectedRow ? String(root.selectedRow.value).replace(/^tweak:/, "") : ""
                    for (var i = 0; i < defs.length; i++) if (v.indexOf(defs[i].key) === 0) return defs[i].key
                    return v.indexOf("visualizer") === 0 ? "visualizer" : ""
                  }
                  readonly property real k: deskBox.width / 1440
                  readonly property real margin: (cfg.edgeMargin !== undefined ? Number(cfg.edgeMargin) : 24) * k
                  // Как place() в Widgets.qml: виджеты с одним якорем встают колонкой с зазором 14 px.
                  readonly property var boxes: {
                    var out = []
                    var W = deskBox.width, H = deskBox.height, gap = 14 * k
                    var groups = ({})
                    for (var i = 0; i < defs.length; i++) {
                      var d = defs[i]
                      var on = cfg[d.key] === undefined ? d.on : cfg[d.key] === true
                      if (!on) continue
                      var a = String(cfg[d.key + "Anchor"] || d.anchor)
                      if (!groups[a]) groups[a] = []
                      groups[a].push({ key: d.key, title: d.title, w: d.w * k, h: d.h * k })
                    }
                    for (var a2 in groups) {
                      var g = groups[a2], total = 0
                      for (var j = 0; j < g.length; j++) total += g[j].h + (j < g.length - 1 ? gap : 0)
                      var off = 0
                      for (var j2 = 0; j2 < g.length; j2++) {
                        var b = g[j2]
                        b.x = a2.indexOf("left") !== -1 ? margin : a2.indexOf("right") !== -1 ? W - b.w - margin : (W - b.w) / 2
                        b.y = a2.indexOf("top") !== -1 ? margin + off : a2.indexOf("bottom") !== -1 ? H - margin - total + off : (H - total) / 2 + off
                        off += b.h + gap
                        out.push(b)
                      }
                    }
                    for (var p = 0; p < out.length; p++) {
                      out[p].clash = false
                      for (var q = 0; q < out.length; q++) {
                        if (p === q) continue
                        var A = out[p], B = out[q]
                        if (A.x < B.x + B.w && B.x < A.x + A.w && A.y < B.y + B.h && B.y < A.y + A.h) out[p].clash = true
                      }
                    }
                    return out
                  }
                  readonly property bool clash: boxes.some(function(b) { return b.clash })

                  ClippingRectangle {
                    id: deskBox
                    anchors.centerIn: parent
                    width: Math.min(parent.width, parent.height * 1.6)
                    height: width / 1.6
                    radius: root.innerRadius
                    color: root.faint
                    Image {
                      anchors.fill: parent
                      source: widgetsStage.visible && root.status.wallpaper ? root.fileUrl(root.status.wallpaper) : ""
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                      sourceSize.width: 640
                    }
                    Rectangle {
                      visible: widgetsStage.cfg.visualizer !== false
                      anchors.bottom: parent.bottom
                      width: parent.width
                      height: (widgetsStage.cfg.visualizerHeight !== undefined ? Number(widgetsStage.cfg.visualizerHeight) : 140) * widgetsStage.k
                      color: Util.alpha(root.accent, widgetsStage.focusKey === "visualizer" ? 0.45 : 0.18)
                    }
                    Repeater {
                      model: widgetsStage.boxes
                      Rectangle {
                        required property var modelData
                        readonly property bool hot: modelData.key === widgetsStage.focusKey
                        x: modelData.x; y: modelData.y; width: modelData.w; height: modelData.h
                        radius: 6
                        color: Util.alpha(Color.background, hot ? 0.92 : 0.78)
                        border.width: hot || modelData.clash ? 2 : 1
                        border.color: modelData.clash ? Color.urgent : (hot ? root.accent : Util.alpha(root.foreground, 0.3))
                        Text {
                          anchors.centerIn: parent
                          text: root.tr(modelData.title)
                          color: parent.hot ? root.accent : root.foreground
                          font.family: Style.font.family
                          font.pixelSize: Math.max(9, Style.font.body - 2)
                        }
                      }
                    }
                  }
                }

                // Макеты из previews/ — по категории; значения — tweakValues (сразу при шаге).
                Previews.DotifyPreview {
                  anchors.fill: parent
                  visible: root.category.key === "dotify"
                  t: root
                  v: root.tweakValues
                  source: visible ? root.dotifySource : ""
                  screenWidth: panel.screen ? panel.screen.width : 1440
                  screenHeight: panel.screen ? panel.screen.height : 900
                }
                Previews.OsdPreview {
                  anchors.fill: parent; anchors.margins: Style.space(12)
                  visible: root.category.key === "osd"
                  t: root; v: root.tweakValues; wallpaper: visible ? root.wallpaperUrl : ""
                }
                Previews.NotifyPreview {
                  anchors.fill: parent; anchors.margins: Style.space(12)
                  visible: root.category.key === "notifications"
                  t: root; v: root.tweakValues; wallpaper: visible ? root.wallpaperUrl : ""
                }
                Previews.DashPreview {
                  anchors.fill: parent; anchors.margins: Style.space(12)
                  visible: root.category.key === "dashboard"
                  t: root; v: root.tweakValues; wallpaper: visible ? root.wallpaperUrl : ""
                }
                Previews.LockPreview {
                  anchors.fill: parent; anchors.margins: Style.space(12)
                  visible: root.category.key === "lock-tweaks"
                  t: root; v: root.tweakValues; image: visible ? root.lockShot : ""; design: String(root.status.lock || "")
                }
                Previews.GlyphPreview {
                  anchors.fill: parent; anchors.margins: Style.space(12)
                  visible: root.category.key === "glyph"
                  t: root; v: root.tweakValues; wallpaper: visible ? root.wallpaperUrl : ""
                }
                // Launcher: скин под курсором вживую (на твиках и «Открыть» — текущий).
                Previews.LauncherPreview {
                  anchors.fill: parent
                  visible: root.category.key === "launcher"
                  t: root
                  skin: root.selectedRow && String(root.selectedRow.value).indexOf("skin:") === 0 ? String(root.selectedRow.value).slice(5) : ""
                  backdrop: isFinite(Number(root.tweakValues.backdrop)) && root.tweakValues.backdrop !== undefined && root.tweakValues.backdrop !== "" ? Number(root.tweakValues.backdrop) : -1
                  wallpaper: visible ? root.wallpaperUrl : ""
                  screenWidth: panel.screen ? panel.screen.width : 1440
                  screenHeight: panel.screen ? panel.screen.height : 900
                }
                Previews.SoundsPreview {
                  anchors.fill: parent
                  visible: root.category.key === "sounds"
                  t: root; v: root.tweakValues; pack: root.soundPack; packNote: root.soundPackNote
                  onPlay: function(pack, event) { Quickshell.execDetached([root.script, "sound-preview", pack, event]) }
                }

                // ⤢ — превью на всё тело страницы (z).
                Rectangle {
                  anchors.right: infoBtn.left
                  anchors.rightMargin: Style.space(6)
                  anchors.bottom: infoBtn.bottom
                  visible: hero.hasVisual
                  height: Style.space(30)
                  width: zoomRow.implicitWidth + Style.space(18)
                  radius: root.dot ? Style.space(3) : height / 2
                  color: zoomHover.containsMouse || root.heroFull ? root.secondaryContainer : Util.alpha(root.background, 0.8)
                  z: 4
                  Row {
                    id: zoomRow
                    anchors.centerIn: parent
                    spacing: Style.space(6)
                    Text { text: root.heroFull ? "󰘕" : "󰘖"; color: root.primary; font.family: root.iconFont; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
                    Keycap { label: "z"; anchors.verticalCenter: parent.verticalCenter }
                  }
                  MouseArea { id: zoomHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.heroFull = !root.heroFull }
                }

                // ⓘ — описание поверх сцены (n).
                Rectangle {
                  id: infoBtn
                  anchors.right: parent.right
                  anchors.bottom: parent.bottom
                  anchors.rightMargin: Style.space(10)
                  // Над полосой палитры темы, а не поверх неё.
                  anchors.bottomMargin: Style.space(10) + (paletteStrip.visible ? paletteStrip.height : 0)
                  visible: hero.hasVisual
                  height: Style.space(30)
                  width: infoRow.implicitWidth + Style.space(18)
                  radius: root.dot ? Style.space(3) : height / 2
                  color: infoHover.containsMouse || root.noteOpen ? root.secondaryContainer : Util.alpha(root.background, 0.8)
                  z: 4
                  Row {
                    id: infoRow
                    anchors.centerIn: parent
                    spacing: Style.space(6)
                    Text { text: "󰋽"; color: root.primary; font.family: root.iconFont; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: root.tr("Description"); color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption; anchors.verticalCenter: parent.verticalCenter }
                    Keycap { label: "n"; anchors.verticalCenter: parent.verticalCenter }
                  }
                  MouseArea { id: infoHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.noteOpen = !root.noteOpen }
                }

                Pill {
                  id: headPill
                  anchors.right: parent.right
                  anchors.top: parent.top
                  anchors.margins: Style.space(10)
                  visible: root.selectedRow !== null && (root.selectedRow.current || root.previewing === root.category.key)
                  label: root.selectedRow && root.selectedRow.current ? root.tr("IN USE") : root.tr("LIVE PREVIEW")
                  tone: root.selectedRow && root.selectedRow.current ? root.primary : Color.urgent
                }
              }

              Rectangle {
                id: noteArea
                anchors { top: parent.top; bottom: parent.bottom; topMargin: hero.hasVisual ? Style.space(8) : 0; bottomMargin: hero.hasVisual ? Style.space(48) : 0 }
                width: hero.hasVisual ? Math.round(hero.width * 0.42) : hero.width
                x: !hero.hasVisual ? 0 : hero.noteShown ? hero.width - width - Style.space(8) : hero.width + Style.space(8)
                visible: hero.noteShown || x < hero.width
                Behavior on x { NumberAnimation { duration: root.ms(200); easing.type: Easing.OutCubic } }
                radius: root.rCard
                color: hero.hasVisual ? Qt.rgba(root.background.r, root.background.g, root.background.b, 0.94) : root.surface
                z: 5
                border.width: root.dot ? 1 : 0
                border.color: root.outline

                Flickable {
                  id: previewFlick
                  anchors.fill: parent
                  anchors.margins: Style.space(16)
                  contentHeight: previewLabel.implicitHeight
                  boundsBehavior: Flickable.StopAtBounds
                  clip: true

                  Text {
                    id: previewLabel
                    width: parent.width
                    wrapMode: root.heroCode ? Text.WrapAnywhere : Text.Wrap
                    textFormat: Text.PlainText
                    text: root.heroNote()
                    color: root.foreground
                    opacity: 0.85
                    font.family: Style.font.family
                    font.pixelSize: root.heroCode ? Style.font.bodySmall : Style.font.body
                    lineHeight: 1.18
                  }
                }
              }
            }

            ListView {
              id: itemList
              visible: !root.homeOpen && !root.heroFull
              anchors {
                top: hero.visible ? hero.bottom : parent.top
                topMargin: hero.visible ? Style.space(14) : 0
                bottom: parent.bottom; left: parent.left; right: parent.right
              }
              model: viewModel
              clip: true
              spacing: Style.space(8)
              cacheBuffer: Style.space(600)
              boundsBehavior: Flickable.StopAtBounds
              highlightFollowsCurrentItem: false

              delegate: Item {
                id: vrow
                required property int index
                required property string vkind
                required property int idx
                required property var tiles
                required property string label
                required property string value
                required property string preview
                required property string note
                required property string sub
                required property bool current
                required property string kind
                required property string args
                required property string raw
                required property string name

                width: itemList.width
                height: loader.item ? loader.item.height : 0

                Loader {
                  id: loader
                  width: parent.width
                  sourceComponent: vrow.vkind === "header" ? headerC
                    : vrow.vkind === "setting" ? settingC
                    : vrow.vkind === "tiles" ? tilesC : rowC
                }

                // Заголовок раздела — крупно, как разделы в образце.
                Component {
                  id: headerC
                  Item {
                    width: vrow.width
                    height: Style.space(vrow.idx === 0 ? 30 : 44)
                    Text {
                      anchors.left: parent.left
                      anchors.leftMargin: Style.space(4)
                      anchors.bottom: parent.bottom
                      anchors.bottomMargin: Style.space(2)
                      text: vrow.label
                      color: root.foreground
                      font.family: root.headFont
                      font.pixelSize: Style.font.heading
                      font.bold: true
                    }
                  }
                }

                Component {
                  id: settingC
                  SettingCard {
                    width: vrow.width
                    height: implicitHeight
                    t: root
                    index: vrow.idx
                    label: vrow.label
                    name: vrow.name
                    sub: vrow.sub
                    note: vrow.note
                    kind: vrow.kind
                    args: vrow.args
                    raw: vrow.raw
                    selected: vrow.idx === root.selectedIndex
                    focused: root.pane === 1 && !root.filtering
                    editing: vrow.idx === root.editingIndex
                    editInitial: root.editInitial
                    editError: root.editError
                    onSelectMe: root.clickSelect(vrow.idx)
                    onStep: function(dir) { root.clickSelect(vrow.idx); root.tweak(dir > 0 ? "+" : "-") }
                    onSetValue: function(v) { root.setTweakAt(vrow.idx, v) }
                    onActivateMe: { root.clickSelect(vrow.idx); root.activate() }
                    onReset: { root.clickSelect(vrow.idx); root.tweak("reset") }
                    onSubmit: function(text) { root.submitEdit(text) }
                    onCancel: root.cancelEdit()
                    onStartEdit: { root.clickSelect(vrow.idx); root.startEdit() }
                    onEdited: root.editError = ""
                    onHoverAt: function(p) { root.hoverSelect(vrow.idx, p) }
                  }
                }

                Component {
                  id: rowC
                  ListCard {
                    width: vrow.width
                    height: implicitHeight
                    t: root
                    index: vrow.idx
                    label: vrow.label
                    sub: vrow.sub
                    current: vrow.current
                    icon: root.category.icon
                    palette: root.paletteOf(vrow.note)
                    selected: vrow.idx === root.selectedIndex
                    focused: root.pane === 1 && !root.filtering
                    onActivated: { root.clickSelect(vrow.idx); root.activate() }
                    onHoverAt: function(p) { root.hoverSelect(vrow.idx, p) }
                  }
                }

                Component {
                  id: tilesC
                  Row {
                    width: vrow.width
                    height: root.tileHeight
                    spacing: root.tileGap
                    Repeater {
                      model: vrow.tiles
                      delegate: Tile {
                        required index
                        required label
                        required preview
                        required note
                        required current
                        readonly property int at: vrow.idx + index
                        width: root.tileWidth
                        height: root.tileHeight
                        t: root
                        icon: /folder|папк/i.test(label) || /^\.\.$/.test(label) ? "󰉋" : "󰋩"
                        palette: root.paletteOf(note)
                        selected: at === root.selectedIndex
                        focused: root.pane === 1 && !root.filtering
                        onActivated: { root.clickSelect(at); root.activate() }
                        onHoverAt: function(p) { root.hoverSelect(at, p) }
                      }
                    }
                  }
                }
              }
            }

            // Раздел верхней видимой строки — закреплён над списком, пока его заголовок прокручен вверх.
            Rectangle {
              id: stickySection
              readonly property int topView: { itemList.contentY; viewModel.count; return itemList.indexAt(Style.space(20), itemList.contentY + 2) }
              readonly property int topIndex: topView >= 0 && topView < viewModel.count ? viewModel.get(topView).idx : -1
              readonly property string name: topIndex >= 0 ? root.sectionOf(topIndex) : ""
              visible: itemList.visible && name !== "" && topIndex >= 0 && !root.isHeader(displayModel.get(topIndex)) && itemList.contentY > 0
              anchors { top: itemList.top; left: itemList.left; right: itemList.right }
              height: Style.space(32)
              radius: root.rSmall
              color: Qt.rgba(root.background.r, root.background.g, root.background.b, 1)
              z: 5
              Text {
                anchors.left: parent.left
                anchors.leftMargin: Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                text: stickySection.name
                color: root.primary
                font.family: root.headFont
                font.pixelSize: Style.font.body
                font.bold: true
              }
              Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: root.outline }
            }

            Column {
              anchors.centerIn: itemList
              visible: itemList.visible && displayModel.count === 0
              spacing: Style.space(6)
              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.loading ? "󰔟" : "󰈈"
                color: root.muted
                font.family: root.iconFont
                font.pixelSize: Style.font.displayLarge
              }
              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                textFormat: Text.PlainText
                text: root.loading ? root.tr("Loading…") : (root.filterText ? root.tr("No matches for “%1”").arg(root.filterText) : root.tr("Nothing here"))
                color: root.muted
                font.family: root.fontFamily
                font.pixelSize: Style.font.title
              }
            }
          }
        }

        // ── Обои: «в корзину?» (D) или отказ ──────────────────────
        Rectangle {
          id: wallDeleteBar
          readonly property bool asking: root.wallDeletePath !== ""
          visible: asking || root.wallDeleteMsg !== ""
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.bottom: parent.bottom
          anchors.bottomMargin: Style.space(64)
          width: Math.min(parent.width - Style.space(48), wdRow.implicitWidth + Style.space(36))
          height: Style.space(48)
          radius: root.dot ? Style.space(3) : height / 2
          // Непрозрачно: полоса лежит поверх плиток.
          color: Qt.tint(root.background, asking ? Util.alpha(root.primary, 0.32) : Util.alpha(root.foreground, 0.12))
          border.width: 1
          border.color: Util.alpha(root.foreground, 0.15)
          z: 19
          Row {
            id: wdRow
            anchors.centerIn: parent
            spacing: Style.space(10)
            Text {
              text: wallDeleteBar.asking ? "󰩹" : "󰀦"
              color: root.foreground; font.family: root.iconFont; font.pixelSize: Style.font.title
              anchors.verticalCenter: parent.verticalCenter
            }
            Text {
              text: wallDeleteBar.asking
                ? root.tr("Move %1 to the trash?").replace("%1", root.wallDeletePath.split("/").pop())
                : root.wallDeleteMsg
              color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body
              elide: Text.ElideMiddle
              width: Math.min(implicitWidth, wallDeleteBar.parent.width * 0.5)
              anchors.verticalCenter: parent.verticalCenter
            }
            Keycap { visible: wallDeleteBar.asking; label: "⏎ y"; anchors.verticalCenter: parent.verticalCenter }
            Text { visible: wallDeleteBar.asking; text: root.tr("delete"); color: root.foreground; opacity: 0.7; font.family: root.fontFamily; font.pixelSize: Style.font.caption; anchors.verticalCenter: parent.verticalCenter }
            Keycap { visible: wallDeleteBar.asking; label: "Esc"; anchors.verticalCenter: parent.verticalCenter }
            Text { visible: wallDeleteBar.asking; text: root.tr("cancel"); color: root.foreground; opacity: 0.7; font.family: root.fontFamily; font.pixelSize: Style.font.caption; anchors.verticalCenter: parent.verticalCenter }
          }
        }

        // ── Key help overlay ("?") ─────────────────────────────────
        Rectangle {
          anchors.fill: parent
          visible: opacity > 0
          opacity: root.helpOpen ? 1 : 0
          Behavior on opacity { NumberAnimation { duration: root.ms(140) } }
          color: Util.alpha(root.background, 0.96)
          radius: root.innerRadius
          z: 20

          MouseArea { anchors.fill: parent; enabled: root.helpOpen; onClicked: root.helpOpen = false }

          Column {
            anchors.centerIn: parent
            spacing: Style.space(14)

            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: root.tr("Keys")
              color: root.foreground
              font.family: root.headFont
              font.pixelSize: Style.font.display
              font.bold: true
            }

            Grid {
              columns: 2
              columnSpacing: Style.space(48)
              rowSpacing: Style.space(10)
              Repeater {
                model: [
                  ["j k  ↑ ↓", "move"], ["h l  ← →", "rail ⇄ page · tiles"],
                  ["Tab  ⇧Tab", "next / previous tab"], ["0 · 1 – " + root.groups.length, "home · section"],
                  ["gg  G", "first / last"], ["^d ^u  ^f ^b", "half / full page"],
                  ["⏎", "apply · toggle · open"], ["/", "search all settings"],
                  ["h l  − +", "settings: change (hold)"], ["x", "settings: reset to default"],
                  ["i", "settings: type a value"], ["[ ]", "previous / next section"],
                  ["v", "show / hide preview"], ["n", "show / hide the description"],
                  ["z", "preview full size / back"],
                  ["J K", "scroll the description"],
                  ["r", "random pick (not Recolor)"], ["o  O  ^o", "Recolor / Dotify: image(s) / folder"],
                  ["p", "Lock / FX / Switcher / Sounds: try it"], ["T", "Lock: refresh previews"],
                  ["f", "Theme: favorite"], ["D", "delete own preset / skin / wallpaper"],
                  ["Esc", "back · revert live preview"], ["q", "close"]
                ]
                delegate: Row {
                  required property var modelData
                  spacing: Style.space(12)
                  Keycap { label: modelData[0]; width: Style.space(120) }
                  Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.tr(modelData[1])
                    color: root.foreground
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.body
                  }
                }
              }
            }

            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: root.tr("Press ? or Esc to close")
              color: root.muted
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
        }
      }
    }
  }
}
