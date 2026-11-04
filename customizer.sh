#!/usr/bin/env bash
# Backend for the Customizer overlay (Customizer.qml). Same actions as the old
# fzf script scripts/bin/omarchy-customizer, split into list/preview/apply so
# the overlay can drive them.
#
#   customizer.sh list <category> [path]   TSV: label, value, preview path, current(0/1), note[, sub — подпись под строкой]
#   customizer.sh anim-preview <file>      load an animation set without committing
#   customizer.sh anim-restore             undo previews (back to what `list anims` saw)
#   customizer.sh apply <category> <value>
#   customizer.sh thumbs <category>        fill the thumbnail cache for an image category
#   customizer.sh status                   TSV: key, value (header chips)
#   customizer.sh opacity-preview <name>   apply a transparency preset without saving
#   customizer.sh opacity-restore          back to the saved preset
#   customizer.sh blur-preview <name>      same pair for the blur presets
#   customizer.sh blur-restore
#   customizer.sh bar-skins-preview <file> примерить скин бара, не сохраняя
#   customizer.sh bar-skins-restore        вернуть скин, который видел `list bar-skins`
#   customizer.sh tweak <key> <+|-|pick|reset>  шаг / сброс одного параметра скина (Bar Tweaks)
#
# Categories: presets styles anims bar-layouts bar-skins bar-tweaks themes theme-walls walls shaders opacity blur
set -uo pipefail

CUSTOMIZER_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
# shellcheck source=scripts/i18n.sh
source "$CUSTOMIZER_DIR/scripts/i18n.sh"

# Пресеты анимаций: свои из плагина + пользовательские (с тем же именем — пользовательский).
# Выбранный лежит в state: его подхватывает hypr/customizer.lua и `restore`.
ANIM_DIR="$CUSTOMIZER_DIR/animations"
ANIM_USER_DIR="$HOME/.config/omarchy/customizer/animations"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-customizer"
ANIM_ACTIVE="$STATE_DIR/animations.lua"
PRESET_DIR="$CUSTOMIZER_DIR/presets"
USER_PRESETS="$HOME/.config/omarchy/customizer/presets"
LAST_PRESET="$STATE_DIR/last-preset.json"
ACTIVE_PRESET="$STATE_DIR/active-preset"
# Что применять из пресета (PRESET_TWEAKS): тема, обои, геометрия окон и т. д.
PRESET_CFG="$HOME/.config/omarchy/customizer/preset-apply.json"
# Стили — форма без цвета (геометрия, материал, скины, шрифты, анимации, звуки) поверх любой темы.
# Формат как у пресета, но без theme/wallpaper; разделы вливаются в текущие настройки.
STYLE_DIR="$CUSTOMIZER_DIR/styles"
USER_STYLES="$HOME/.config/omarchy/customizer/styles"
ACTIVE_STYLE="$STATE_DIR/active-style"
STYLE_CFG="$HOME/.config/omarchy/customizer/style-apply.json"
# Токены стиля для панелей (BarStyle.qml в widgets / osd / notifications): тени, анимации, материал, углы, шрифт.
LOOK_CFG="$HOME/.config/omarchy/style.json"
# Углы окон: правило окон Hyprland из hypr/customizer.lua (действует и при «без отступов»).
WINDOW_CFG="$HOME/.config/omarchy/customizer/windows.json"
# Бар (плагин kamradsmeshnyavy.bar): пресеты лежат в самом плагине, активный скин и shell.json — в ~/.config.
# Плагины берём по ссылкам в ~/.config/omarchy/plugins: они — сабмодули и могут жить где угодно.
BAR_DIR="$HOME/.config/omarchy/plugins/kamradsmeshnyavy.bar"
BAR_SKIN="$HOME/.config/omarchy/bar-skin.json"
# Свои скины бара (Bar Skin → «Сохранить текущий»): по файлу на скин, как пресеты плагина.
USER_SKINS="$HOME/.config/omarchy/bar-skins"
# Свои раскладки бара (Bar Layout → «Сохранить текущую»): вне плагина, чтобы не пачкать его репо.
USER_LAYOUTS="$HOME/.config/omarchy/bar-layouts"
# Экран блокировки (плагин kamradsmeshnyavy.lock): выбор и настройки — lock-design.json.
LOCK_PLUGIN="$HOME/.config/omarchy/plugins/kamradsmeshnyavy.lock"
LOCK_CFG="$HOME/.config/omarchy/lock-design.json"
WIDGET_CFG="$HOME/.config/omarchy/widgets.json"
OSD_CFG="$HOME/.config/omarchy/osd.json"
NOTIFY_CFG="$HOME/.config/omarchy/notify-style.json"
SOUND_CFG="$HOME/.config/omarchy/sounds.json"
GLYPH_CFG="$HOME/.config/omarchy/glyph.json"
# Палитра стиля Nihil во всех плагинах (nihil/Palette.qml): theme | mono.
NIHIL_CFG="$HOME/.config/omarchy/nihil.json"
DOTIFY_CFG="$HOME/.config/omarchy/dotify.json"
MENU_PLUGIN="$HOME/.config/omarchy/plugins/kamradsmeshnyavy.menu"
MENU_CFG="$HOME/.config/omarchy/extensions/menu-skin.json"
LOCK_USER_DIR="$HOME/.config/omarchy/lock-designs"
LOCK_THUMBS="${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-customizer/lock"
# Переходы обоев (kamradsmeshnyavy.background) и вид пикера тем/обоев (kamradsmeshnyavy.image-picker).
FX_CFG="$HOME/.config/omarchy/wallpaper-transition.json"
PICKER_CFG="$HOME/.config/omarchy/image-picker.json"
PICKER_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/omarchy/image-selector"
# Файл, который правят твики (bar-skin.json или lock-design.json), — см. tweak_file.
TW_FILE="$BAR_SKIN"
SHELL_JSON="$HOME/.config/omarchy/shell.json"
TOGGLE="$CUSTOMIZER_DIR/scripts/crt-toggle.sh"
OPACITY="$CUSTOMIZER_DIR/scripts/opacity.sh"
BLUR="$CUSTOMIZER_DIR/scripts/blur.sh"
RECOLOR="$CUSTOMIZER_DIR/scripts/recolor-wallpapers"
DOTIFY="$CUSTOMIZER_DIR/scripts/dotify.py"
PLAY_SOUND="$CUSTOMIZER_DIR/scripts/play-sound.sh"
RUN_DIR="${XDG_RUNTIME_DIR:-/tmp}/omarchy-customizer"
ANIM_BACKUP="$RUN_DIR/active_animations.lua"
SKIN_BACKUP="$RUN_DIR/bar-skin.json"
TRANSPARENT_BACKUP="$RUN_DIR/bar-transparent"
# Thumbnails are named md5(<source path>).jpg, the same Qt.md5() the overlay uses.
THUMB_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-customizer/thumbs"

theme_name() { cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || echo default; }

images_in() {
  find -L "$1" -maxdepth "$2" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) 2>/dev/null | sort
}

# Same lookup as omarchy-theme-switcher: preview.* first, then the first background.
theme_preview() {
  local p
  shopt -s nullglob nocaseglob
  for p in "$1"/preview.{png,jpg,jpeg,webp} "$1"/backgrounds/*.{jpg,jpeg,png,webp}; do
    [[ -f $p ]] && { echo "$p"; break; }
  done
  shopt -u nullglob nocaseglob
}

# Swatches for the overlay: background foreground accent + five hues.
theme_palette() {
  [[ -f $1/colors.toml ]] || return 0
  awk -F'"' '/^(background|foreground|accent|red|yellow|green|blue|magenta) *=/ { sub(/ .*/, "", $1); c[$1] = $2 }
    END { n = split("background foreground accent red yellow green blue magenta", k, " ")
          for (i = 1; i <= n; i++) if (c[k[i]] != "") printf "%s%s", (o++ ? " " : ""), c[k[i]] }' "$1/colors.toml"
}

walls_dir() {
  if [[ -d $HOME/Wallpapers ]]; then echo "$HOME/Wallpapers"; else echo "$HOME/Pictures"; fi
}

# Recolor every image directly in <src> into the current theme, then set the
# background when there was exactly one image.
recolor() {
  local src=$1 theme_dir files
  theme_dir="$HOME/.config/omarchy/themes/$(theme_name)"
  if [[ ! -d $theme_dir ]]; then
    notify-send "Wallpaper" "$(t "Cannot recolor a stock Omarchy theme. Use a custom theme.")"
    exit 1
  fi
  mapfile -t files < <(images_in "$src" 1)
  if ((${#files[@]} == 0)); then
    notify-send "Wallpaper" "$(t "No images in %s" "$src")"
    exit 1
  fi
  if ((${#files[@]} == 1)); then
    notify-send -t 3000 "Wallpaper" "$(t "Recoloring %s with lutgen…" "$(basename "${files[0]}")")"
  else
    notify-send -t 3000 "Wallpaper" "$(t "Recoloring %s images from %s with lutgen…" "${#files[@]}" "$(basename "$src")")"
  fi
  if ! "$RECOLOR" "$theme_dir" "$src"; then
    notify-send -u critical "Wallpaper" "$(t "lutgen failed")"
    exit 1
  fi
  if ((${#files[@]} == 1)); then
    omarchy theme bg set "$theme_dir/backgrounds/$(basename "${files[0]}")"
    notify-send -t 3000 "Wallpaper" "$(t "Applied %s" "$(basename "${files[0]}")")"
  else
    notify-send -t 5000 "Wallpaper" "$(t "Added %s recolored wallpapers to %s. Pick one in Wallpaper." "${#files[@]}" "$(theme_name)")"
  fi
}

# Copy the given files into a fresh dir so recolor() sees only them.
recolor_files() {
  local src
  src=$(mktemp -d "${TMPDIR:-/tmp}/omarchy-lutgen-src.XXXXXX")
  cp -- "$@" "$src/"
  recolor "$src"
}

# Resolve a hex color or theme role (foreground, accent, background, bar, urgent, …) to #rrggbb.
resolve_hex_color() {
  local spec=${1:-} fallback=${2:-#f2f2f2} colors="$HOME/.local/state/omarchy/current/theme/colors.toml" key hex
  [[ $spec =~ ^#[0-9A-Fa-f]{6}$ ]] && { echo "$spec"; return; }
  key=$spec
  [[ $key == bar ]] && key=background
  [[ $key == urgent ]] && key=red
  if [[ -n $key && -f $colors ]]; then
    hex=$(awk -F'"' -v k="$key" '$1 ~ "^" k " *=" { print $2; exit }' "$colors" 2>/dev/null)
    [[ $hex =~ ^#[0-9A-Fa-f]{6}$ ]] && { echo "$hex"; return; }
  fi
  echo "$fallback"
}

# Свои обои темы — в ~/.config/omarchy/backgrounds/<тема> (omarchy подхватывает их рядом с обоями
# темы). В каталог самой темы не пишем: это бывает git-клон или симлинк в dotfiles.
dotify_dest_dir() {
  local theme
  theme=$(theme_name)
  mkdir -p "$HOME/.config/omarchy/backgrounds/$theme"
  echo "$HOME/.config/omarchy/backgrounds/$theme"
}

dotify_opts() {
  TW_FILE="$DOTIFY_CFG"
  local pitch gamma off tint bg
  pitch=$(tweak_value dotPitch 9)
  gamma=$(tweak_value dotGamma 1.25)
  off=$(tweak_value dotOff 0.07)
  tint=$(resolve_hex_color "$(tweak_value dotTint foreground)" '#f2f2f2')
  bg=$(resolve_hex_color "$(tweak_value dotBackground background)" '#000000')
  printf '%s\n' --pitch "$pitch" --gamma "$gamma" --off "$off" --tint "$tint" --background "$bg"
}

dotify_files() {
  local dest out stem base count=0 last_out=""
  dest=$(dotify_dest_dir)
  local -a opts
  mapfile -t opts < <(dotify_opts)
  if (($# == 0)); then
    notify-send "Dotify" "$(t "No images selected")"
    exit 1
  fi
  if (($# == 1)); then
    notify-send -t 3000 "Dotify" "$(t "Rendering LED dot-matrix for %s…" "$(basename "$1")")"
  else
    notify-send -t 3000 "Dotify" "$(t "Rendering %s LED dot-matrix wallpapers…" "$#")"
  fi
  for src in "$@"; do
    [[ -f $src ]] || continue
    base=$(basename "$src")
    stem=${base%.*}
    [[ $stem == dot-* ]] || stem="dot-$stem"
    out="$dest/$stem.png"
    if ! "$DOTIFY" "$src" "$out" "${opts[@]}" >/dev/null; then
      notify-send -u critical "Dotify" "$(t "Dotify failed on %s" "$base")"
      exit 1
    fi
    last_out=$out
    ((count++))
  done
  if ((count == 1)) && [[ -n $last_out ]]; then
    omarchy theme bg set "$last_out"
    notify-send -t 3000 "Dotify" "$(t "Applied %s" "$(basename "$last_out")")"
  elif ((count > 1)); then
    notify-send -t 5000 "Dotify" "$(t "Added %s dot-matrix wallpapers to %s. Pick one in Wallpaper." "$count" "$(theme_name)")"
  fi
}

dotify_glyph() {
  local glyph=${1:-󰣇} slug=${2:-arch} dest out
  dest=$(dotify_dest_dir)
  out="$dest/dot-$slug.png"
  local -a opts
  mapfile -t opts < <(dotify_opts)
  notify-send -t 3000 "Dotify" "$(t "Rendering Arch Linux LED dot-matrix wallpaper…")"
  if ! "$DOTIFY" --glyph "$glyph" "$out" "${opts[@]}" >/dev/null; then
    notify-send -u critical "Dotify" "$(t "Dotify failed")"
    exit 1
  fi
  omarchy theme bg set "$out"
  notify-send -t 3000 "Dotify" "$(t "Applied %s" "$(basename "$out")")"
}

# Пресеты анимаций по имени: пользовательский с тем же именем перекрывает встроенный.
anim_files() {
  local f
  for f in "$ANIM_USER_DIR"/*.lua "$ANIM_DIR"/*.lua; do
    [[ -f $f ]] && printf '%s\t%s\n' "$(basename "$f")" "$f"
  done | sort -t$'\t' -k1,1 -u | cut -f2
}

current_shader() {
  local cur
  cur=$(hyprctl getoption decoration:screen_shader -j 2>/dev/null | jq -r '.str // empty')
  if [[ -z $cur || $cur == "[[EMPTY]]" ]]; then echo off; else basename "$cur" .frag; fi
}

# ── Бар ────────────────────────────────────────────────────────────────
# Файлы пишем на месте (cp поверх), а не mv: бар и шелл следят за ними через
# FileView, и подмена inode может оборвать слежку. Временные файлы — с
# фиксированными именами в $RUN_DIR, их просто перезаписывает следующий вызов.

# jq-фильтр поверх $TW_FILE (нет файла — начинаем с {}).
skin_edit() {
  local tmp="$RUN_DIR/tweak.tmp"
  mkdir -p "$(dirname "$TW_FILE")"
  { [[ -s $TW_FILE ]] && cat "$TW_FILE" || echo '{}'; } | jq "$@" >"$tmp" && cp "$tmp" "$TW_FILE"
}

shell_edit() {
  local tmp="$RUN_DIR/shell.tmp"
  jq "$@" "$SHELL_JSON" >"$tmp" && cp "$tmp" "$SHELL_JSON"
}

# Применить раскладку бара из файла $1 в shell.json:
# - вычищает поля note / note_* из объекта раскладки и из .bar;
# - гарантирует, что плагины-клоны из cloneSourceRestores (например, kamradsmeshnyavy.menu,
#   который раньше мог быть включён только через присутствие в bar.layout) остаются в .plugins,
#   чтобы смена раскладки бара не отключала лаунчер и другие клоны.
shell_apply_layout() {
  local layout_file=$1
  shell_edit --slurpfile p "$layout_file" '
    .bar = ((.bar | with_entries(select(.key | test("^note(_[a-z]+)?$") | not)))
      + ($p[0] | with_entries(select(.key | test("^note(_[a-z]+)?$") | not))))
    | reduce (.cloneSourceRestores // [])[] as $id (.;
        if ((.bar.id // "") != $id) and (((.plugins // []) | map(.id) | index($id)) == null)
        then .plugins = ((.plugins // []) + [{"id": $id}])
        else .
        end)
  '
}

# Стоковый флаг transparent живёт в shell.json; пишем, только если он меняется,
# чтобы зря не дёргать перечитывание всего конфига шелла.
set_transparent() {
  [[ $(jq -r '.bar.transparent // false' "$SHELL_JSON") == "$1" ]] && return 0
  shell_edit --argjson t "$1" '.bar.transparent = $t'
}

skin_canon() { jq -S 'with_entries(select(.key | test("^note(_[a-z]+)?$") | not))' "$1" 2>/dev/null; }

# Имя пресета, совпадающего с активным скином, иначе custom (stock, если файла нет).
current_skin() {
  [[ -s $BAR_SKIN ]] || { echo stock; return; }
  local f cur
  cur=$(skin_canon "$BAR_SKIN")
  for f in "$USER_SKINS"/*.json "$BAR_DIR"/skins/*.json; do
    [[ -f $f && $(skin_canon "$f") == "$cur" ]] && { basename "$f" .json; return; }
  done
  echo custom
}

# Описание пресета на языке интерфейса: note_<lang>, иначе note.
note_of() { jq -r --arg l "$UI_LANG" '.["note_" + $l] // .note // ""' "$1" 2>/dev/null; }

layout_canon() { jq -S '{position: (.position // "top"), centerAnchor: (.centerAnchor // ""), layout}' "$@" 2>/dev/null; }

current_layout() {
  local f cur
  cur=$(jq '.bar' "$SHELL_JSON" | layout_canon)
  for f in "$USER_LAYOUTS"/*.json "$BAR_DIR"/layouts/*.json; do
    [[ -f $f && $(layout_canon "$f") == "$cur" ]] && { basename "$f" .json; return; }
  done
  echo custom
}

# Краткая сводка раскладки для заметки: "top · L: menu workspaces · C: clock · R: …".
layout_summary() {
  jq -r '[(.position // "top"),
          ("L: " + ([.layout.left[]?.id | sub("^[a-z]+\\."; "")] | join(" "))),
          ("C: " + ([.layout.center[]?.id | sub("^[a-z]+\\."; "")] | join(" "))),
          ("R: " + ([.layout.right[]?.id | sub("^[a-z]+\\."; "")] | join(" ")))] | join("  ·  ")' "$1"
}

# Параметры Bar Tweaks: ключ|тип|аргументы|подпись. Дефолты совпадают с BarSkin.qml:
# у num последнее число, у enum первое слово, у color/bool — сами аргументы.
TWEAKS=(
  "#Shape & size"
  "shape|enum|full floating pill islands notch underline hug frame|Shape"
  "height|num|0 48 2 0|Height"
  "gap|num|0 24 2 0|Gap from the screen edge"
  "margin|num|0 300 10 0|Left/right margins"
  "width|num|0.3 1 0.05 1|Width (floating/pill/notch)"
  "radius|num|0 24 2 0|Radius (hug, frame: corners)"
  "frameWidth|num|1 24 1 8|Frame: width around the screen"
  "padding|num|-1 40 2 -1|Module padding"
  "islandGap|num|0 20 2 0|Island padding"
  "#Colours"
  "background|color|bar|Background"
  "backgroundAlpha|num|-1 1 0.05 -1|Background alpha"
  "gradient|color|none|Gradient: second colour"
  "border|color|accent|Border"
  "borderWidth|num|0 4 1 0|Border width"
  "borderAlpha|num|0 1 0.1 1|Border alpha"
  "text|color|bar|Text"
  "active|color|bar|Attention colour (recording, updates)"
  "#Modules"
  "moduleStyle|enum|plain pills hover|Module background"
  "moduleBackground|color|foreground|Module background colour"
  "moduleAlpha|num|0 1 0.02 0.08|Module background alpha"
  "spacing|num|0 20 2 0|Gap between modules"
  "font|font||Font"
  "#Effects"
  "shadow|bool|false|Shadow"
  "glow|bool|false|Glow in the border colour"
  "autoHide|bool|false|Auto-hide (slides out on hover)"
  "transparent|bool|false|Transparent (stock, text over the wallpaper)"
  "#Workspaces"
  "wsLabelStyle|enum|omarchy numbers leds circled circled-filled circled-sans circled-sans-filled parens fullwidth superscript roman roman-small kanji greek cyrillic braille dots squares diamonds stars triangles hearts hexagons bars none|Workspaces: labels"
  "wsWindowIcons|bool|false|Workspaces: window icons"
  "wsIconStyle|enum|color mono tinted accent bubble faded glyph letter dots count|Workspaces: window icon style"
  "wsMaxIcons|num|1 8 1 3|Workspaces: icons per workspace (then +N)"
  "wsDedupe|bool|true|Workspaces: one icon per app"
  "wsShown|num|1 10 1 5|Workspaces: always visible"
  "wsShowEmpty|bool|true|Workspaces: show empty"
  "wsActivePill|bool|false|Workspaces: pill under the active one"
  "wsActiveColor|color|default|Workspaces: active colour"
  "#Compact"
  "compact|enum|off single fullscreen always|Compact: when to shrink"
  "compactHeight|num|0 40 2 22|Compact: height"
  "compactModules|enum|essentials all center minimal|Compact: visible modules"
  "compactShape|enum|full same floating pill notch underline hug|Compact: shape"
  "compactAlpha|num|-1 1 0.05 -1|Compact: background alpha"
  "compactReserve|enum|keep shrink|Compact: space under the bar"
  "compactExpandOnHover|bool|true|Compact: expand on hover"
)

# Как показывать дефолт в подписи: особые значения — словами.
default_label() {
  case "$1:$2" in
  height:0) t "auto" ;;
  ownerMessage:) t "Hello, %s" "$USER" ;;
  wsActiveColor:default) t "as in the style (omarchy — text colour, otherwise accent)" ;;
  nihil*:default) t "auto (theme or mono palette)" ;;
  avatar:) t "~/.face (or the first letter of the name)" ;;
  wallpaperBlur:1) t "1 (stock)" ;;
  expandedWidth:0 | expandedHeight:0 | sliceWidth:0 | sliceHeight:0) t "from the style" ;;
  cardRadius:-1) t "from the style" ;;
  scrimAlpha:-1) t "from the theme" ;;
  duration:420) t "420 (stock)" ;;
  compactHeight:0) t "unchanged" ;;
  compactAlpha:-1) t "as usual" ;;
  compact:off) t "off" ;;
  compact:single) t "one window on the workspace" ;;
  compact:fullscreen) t "fullscreen window" ;;
  compact:always) t "always" ;;
  compactModules:essentials) t "essentials (menu, workspaces, clock, network, audio, power)" ;;
  compactModules:center) t "center (center only)" ;;
  compactModules:minimal) t "minimal (workspaces + clock)" ;;
  compactModules:all) t "all (everything)" ;;
  compactShape:same) t "same (as usual)" ;;
  compactReserve:keep) t "keep (unchanged, windows don't jump)" ;;
  compactReserve:shrink) t "shrink (windows take the space)" ;;
  padding:-1) t "stock" ;;
  backgroundAlpha:-1) t "from the theme" ;;
  gradient:none) t "none" ;;
  font:) t "system" ;;
  *:bar) t "bar (theme colour)" ;;
  *) echo "$2" ;;
  esac
}

# Параметры экрана блокировки (Lock Tweaks) — те же типы, файл lock-design.json.
LOCK_TWEAKS=(
  "clock24|bool|true|Clock: 24-hour"
  "showSeconds|bool|false|Clock: seconds"
  "showDate|bool|true|Date"
  "wallpaperBlur|num|0 1 0.1 1|Wallpaper: blur"
  "wallpaperDim|num|0 0.9 0.05 0|Wallpaper: dim"
  "reduceMotion|bool|false|Reduce motion"
  "ownerMessage|text||Greeting"
  "avatar|file||Avatar"
)

# Настройки переходов обоев — строки tweak:<key> в категории Wallpaper FX.
FX_TWEAKS=(
  "duration|num|100 3000 50 420|Duration, ms"
  "easing|enum|InOutCubic InOutQuad InOutQuart InOutSine InOutExpo OutCubic OutExpo OutQuint OutBack OutBounce OutElastic InCubic InExpo Linear|Easing"
  "angle|num|0 345 15 0|Angle (wipe, wave, slide)"
  "origin|enum|center cursor random|Where circles/drops start"
  "softness|num|0 0.2 0.01 0.02|Edge softness"
)

# Вид пикера тем и обоев — строки tweak:<key> в категории Theme Switcher.
# 0 / -1 = значение из стиля-пресета или темы (ключ в файле тогда не хранится).
PICKER_TWEAKS=(
  "expandedWidth|num|0 1600 20 0|Selected width"
  "expandedHeight|num|0 1000 20 0|Selected height"
  "sliceWidth|num|0 600 10 0|Neighbour width"
  "sliceHeight|num|0 900 10 0|Neighbour height"
  "cardRadius|num|-1 40 2 -1|Corner radius"
  "dim|num|0 0.9 0.05 0.42|Neighbour dim"
  "selectedBorder|num|0 8 1 3|Selected border"
  "animMs|num|0 600 20 160|Scroll animation, ms"
  "scrimAlpha|num|-1 1 0.05 -1|Background dim"
  "labels|bool|false|Always show labels"
  "autoCache|bool|false|Cache wallpapers on theme change"
)

# Виджеты рабочего стола (плагин kamradsmeshnyavy.widgets) — файл widgets.json.
WIDGET_TWEAKS=(
  "#Clock"
  "clock|bool|true|Clock"
  "clockStyle|enum|big stacked terminal minimal|Clock: style"
  "clockAnchor|enum|top-left top top-right left center right bottom-left bottom bottom-right|Clock: position"
  "clock24|bool|true|Clock: 24-hour"
  "clockSeconds|bool|false|Clock: seconds"
  "#Now playing"
  "media|bool|true|Now playing"
  "mediaAnchor|enum|bottom-left bottom bottom-right top-left top top-right left center right|Now playing: position"
  "#Visualizer"
  "visualizer|bool|true|Visualizer (cava)"
  "visualizerStyle|enum|bars mirror wave|Visualizer: style"
  "visualizerBars|num|8 128 4 48|Visualizer: bars"
  "visualizerHeight|num|40 400 20 140|Visualizer: height"
  "visualizerAlpha|num|0.05 1 0.05 0.45|Visualizer: opacity"
  "visualizerIdle|bool|false|Visualizer: also without music"
  "#System rings"
  "sysinfo|bool|true|System rings"
  "sysinfoAnchor|enum|top-right left center right bottom-left bottom bottom-right top-left top|System rings: position"
  "#General"
  "widgetStyle|enum|default nihil|Widgets: card style"
  "edgeHover|bool|false|Edge hotzones (top — dashboard, top-right — settings, bottom — launcher)"
  "edgeMargin|num|0 200 8 56|Margin from the screen edges"
  "tint|color|accent|Accent colour"
  "screens|enum|all primary|Screens"
)

# OSD (клон kamradsmeshnyavy.osd): громкость/яркость у края экрана или стоковой карточкой — osd.json.
OSD_TWEAKS=(
  "#Style"
  "osdStyle|enum|edge nihil stock|OSD: style (edge — slides out of the screen edge / frame)"
  "osdFollowBar|bool|true|Follow the bar style (colour, alpha, border, radius)"
  "osdAttach|enum|auto attached floating|Attach to the edge (auto — only to a solid bar / frame)"
  "osdBackground|color|background|Background"
  "osdAlpha|num|0.3 1 0.05 0.94|Background alpha"
  "osdRadius|num|0 40 2 18|Corner radius"
  "#Size & position"
  "osdSide|enum|right left|OSD: screen edge"
  "osdAlign|enum|center top bottom|Position along the edge"
  "osdSize|enum|normal compact large|Size"
  "#Behaviour"
  "osdShowValue|bool|true|Show the percentage"
  "osdTimeout|num|-1 5000 100 -1|Hide after, ms"
)
# Уведомления (клон kamradsmeshnyavy.notifications): общая подложка у бара или стоковые карточки.
NOTIFY_TWEAKS=(
  "#Style"
  "notifyStyle|enum|drawer stock|Notifications: style (drawer — one panel glued to the bar and the edge)"
  "notifyFollowBar|bool|true|Follow the bar style (colour, alpha, border, radius)"
  "notifyAttach|enum|auto attached floating|Attach to the bar (auto — only to a solid bar at the edge)"
  "notifyBackground|color|background|Background"
  "notifyAlpha|num|0.3 1 0.05 0.94|Background alpha"
  "notifyRadius|num|0 40 2 18|Corner radius"
  "notifyCards|enum|flat bordered nihil|Cards"
  "#Size & position"
  "notifyCorner|enum|top-right top-left top-center|Corner"
  "notifyWidth|num|280 600 20 380|Width"
  "notifyMax|num|0 10 1 0|Visible at once (0 — all)"
)
# Звуки интерфейса (omarchy-sound + play-sound.sh): уведомления, громкость, окна, воркспейсы — sounds.json.
SOUND_TWEAKS=(
  "#Sounds"
  "sounds|bool|true|Sounds: on"
  "soundPack|enum|theme nihil classic flat glass fluent paper neumorph brutal retro neon|Sounds: pack"
  "soundVolume|num|0.1 1 0.1 0.6|Sounds: volume"
  "windowSounds|bool|false|Sounds: window & workspace events"
)
# Дашборд (плагин kamradsmeshnyavy.widgets) — тот же widgets.json.
DASH_TWEAKS=(
  "#Look"
  "dashStyle|enum|default nihil|Dashboard: style"
  "dashFollowBar|bool|true|Follow the bar style (colour, alpha, border, radius)"
  "dashAttach|enum|auto attached floating|Attach to the bar (auto — only to a solid bar at the edge)"
  "dashBackground|color|background|Background"
  "dashAlpha|num|0.3 1 0.05 0.94|Background alpha"
  "dashRadius|num|0 40 2 22|Corner radius"
  "dashBorder|bool|false|Border"
  "#Blocks"
  "dashMedia|bool|true|Player"
  "dashCalendar|bool|true|Calendar"
  "dashWeather|bool|true|Weather"
  "dashStats|bool|true|CPU / RAM graphs"
  "#Weather"
  "weatherCity|text||Weather city"
  "weatherUnits|enum|celsius fahrenheit|Temperature units"
  "#Animation"
  "dashAnimation|enum|grow slide fade|Animation"
  "dashDuration|num|100 1000 20 340|Animation, ms"
)

# Контурная подсветка экрана Glyph (GlyphOverlay.qml) — glyph.json.
GLYPH_TWEAKS=(
  "#Glyph lighting"
  "glyphEnabled|bool|false|Glyph: perimeter lighting"
  "glyphCriticalRed|bool|true|Glyph: signal red on critical alerts"
  "glyphCharger|bool|true|Glyph: rising beams on charger plug-in"
  "glyphInsetMode|enum|auto frame edge|Glyph: path around the screen"
  "#Appearance"
  "glyphColor|color|foreground|Glyph: light colour"
  "glyphCriticalColor|color|urgent|Glyph: critical colour"
  "glyphDuration|num|300 3000 100 1100|Glyph: sweep duration, ms"
  "glyphThickness|num|1 8 0.5 2.5|Glyph: core thickness"
)

# Генератор матричных LED-обоев Dotify (scripts/dotify.py) — dotify.json.
DOTIFY_TWEAKS=(
  "#Dot matrix"
  "dotPitch|num|6 24 1 9|Cell pitch, px (logical)"
  "dotGamma|num|0.4 2.2 0.05 1.25|Brightness gamma"
  "dotOff|num|0 0.25 0.01 0.07|Unlit LED grid level"
  "dotTint|color|foreground|Lit LED colour"
  "dotBackground|color|background|Void background colour"
)

# Лаунчер приложений (kamradsmeshnyavy.menu) — extensions/menu-skin.json.
LAUNCHER_TWEAKS=(
  "backdrop|num|0.2 1 0.05 0.94|Background dim"
)

# Стиль Nihil (dot-matrix) — nihil.json, его читает nihil/Palette.qml в каждом плагине.
NIHIL_TWEAKS=(
  "#Nihil palette"
  "palette|enum|theme mono|Nihil: palette (theme — omarchy colours, mono — original black & white)"
  "#Nihil colours"
  "nihilBg|color|default|Nihil: background (bar, drawers, cards)"
  "nihilFg|color|default|Nihil: text"
  "nihilDim|color|default|Nihil: secondary text"
  "nihilMuted|color|default|Nihil: labels and app names"
  "nihilLine|color|default|Nihil: hairlines and card borders"
  "nihilSurface|color|default|Nihil: raised surfaces (rows, fields)"
  "nihilLit|color|default|Nihil: lit LEDs, sliders, active toggles"
  "nihilSignal|color|default|Nihil: signal (accent marks and indicators)"
  "nihilDanger|color|default|Nihil: danger (critical, confirmations)"
)

# Что применять из пресета — preset-apply.json. Выключенный раздел пресет не трогает.
PRESET_TWEAKS=(
  "#Apply from presets"
  "presetTheme|bool|true|Presets: apply theme"
  "presetWallpaper|bool|true|Presets: apply wallpaper"
  "presetGeometry|bool|true|Presets: apply window geometry (gaps, borders, rounding, shadow)"
  "presetAnims|bool|true|Presets: apply animations"
  "presetOpacity|bool|true|Presets: apply opacity and blur"
  "presetShader|bool|true|Presets: apply screen shader"
  "presetBar|bool|true|Presets: apply bar skin and layout"
  "presetLock|bool|true|Presets: apply lock screen"
  "presetLauncher|bool|true|Presets: apply launcher"
  "presetWallpaperFx|bool|true|Presets: apply wallpaper transition and picker"
  "presetWidgets|bool|true|Presets: apply widgets and dashboard"
  "presetOsd|bool|true|Presets: apply OSD"
  "presetNotifications|bool|true|Presets: apply notifications"
  "presetSounds|bool|true|Presets: apply sounds"
  "presetGlyph|bool|true|Presets: apply Glyph"
  "presetFonts|bool|true|Presets: apply system fonts of the preset's style"
  "presetLook|bool|true|Presets: apply panel surfaces (shadows, motion, material, corners, typeface)"
)

# Что применять при смене стиля — style-apply.json. Ключи — как у пресетов, с префиксом style.
STYLE_TWEAKS=(
  "#Apply from styles"
  "styleGeometry|bool|true|Styles: apply window geometry (gaps, borders, rounding, shadow)"
  "styleAnims|bool|true|Styles: apply animations"
  "styleOpacity|bool|true|Styles: apply opacity and blur"
  "styleShader|bool|true|Styles: apply screen shader"
  "styleBar|bool|true|Styles: apply bar skin and layout"
  "styleLock|bool|true|Styles: apply lock screen"
  "styleLauncher|bool|true|Styles: apply launcher"
  "styleWallpaperFx|bool|true|Styles: apply wallpaper transition and picker"
  "styleWidgets|bool|true|Styles: apply widgets and dashboard"
  "styleOsd|bool|true|Styles: apply OSD"
  "styleNotifications|bool|true|Styles: apply notifications"
  "styleSounds|bool|true|Styles: apply sounds"
  "styleGlyph|bool|true|Styles: apply Glyph"
  "styleFonts|bool|true|Styles: apply system fonts (terminals, GTK, browser)"
  "styleLook|bool|true|Styles: apply panel surfaces (shadows, motion, material, corners, typeface)"
  "styleTheme|enum|current off dark light|Styles: theme (current — same brightness as the theme now · off · dark · light)"
)

# Углы окон. Скругление — правилом окон, а не decoration.rounding: оно сильнее общей настройки и
# переключателя Omarchy «без отступов», и тайловую сетку можно оставить сплошной (её внешние углы и так
# скругляет рамка экрана). float — плавающие и pop-окна, all — все, off — как в конфиге Hyprland.
WINDOW_TWEAKS=(
  "#Window corners"
  "windowRounding|enum|float all off|Rounded windows: floating only · all · off"
  "windowRadius|num|0 32 2 16|Window corner radius"
  "windowRoundingPower|num|2 4 0.5 2.5|Corner shape: 2 — circle, 4 — squircle"
)

tweak_spec() {
  local t
  for t in "${WINDOW_TWEAKS[@]}" "${TWEAKS[@]}" "${LOCK_TWEAKS[@]}" "${FX_TWEAKS[@]}" "${PICKER_TWEAKS[@]}" "${WIDGET_TWEAKS[@]}" "${OSD_TWEAKS[@]}" "${NOTIFY_TWEAKS[@]}" "${SOUND_TWEAKS[@]}" "${DASH_TWEAKS[@]}" "${GLYPH_TWEAKS[@]}" "${DOTIFY_TWEAKS[@]}" "${LAUNCHER_TWEAKS[@]}" "${PRESET_TWEAKS[@]}" "${STYLE_TWEAKS[@]}" "${NIHIL_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$t"; return; }; done
  return 1
}

# Какой файл правит параметр: lock-design.json для LOCK_TWEAKS, иначе bar-skin.json.
tweak_file() {
  local t
  for t in "${LOCK_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$LOCK_CFG"; return; }; done
  for t in "${FX_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$FX_CFG"; return; }; done
  for t in "${PICKER_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$PICKER_CFG"; return; }; done
  for t in "${WIDGET_TWEAKS[@]}" "${DASH_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$WIDGET_CFG"; return; }; done
  for t in "${OSD_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$OSD_CFG"; return; }; done
  for t in "${NOTIFY_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$NOTIFY_CFG"; return; }; done
  for t in "${SOUND_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$SOUND_CFG"; return; }; done
  for t in "${GLYPH_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$GLYPH_CFG"; return; }; done
  for t in "${DOTIFY_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$DOTIFY_CFG"; return; }; done
  for t in "${LAUNCHER_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$MENU_CFG"; return; }; done
  for t in "${PRESET_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$PRESET_CFG"; return; }; done
  for t in "${STYLE_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$STYLE_CFG"; return; }; done
  for t in "${WINDOW_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$WINDOW_CFG"; return; }; done
  for t in "${NIHIL_TWEAKS[@]}"; do [[ ${t%%|*} == "$1" ]] && { echo "$NIHIL_CFG"; return; }; done
  echo "$BAR_SKIN"
}

# Роли для цветовых параметров: стоковый цвет бара, роли шелла и ключи colors.toml темы.
color_roles() {
  local colors="$HOME/.local/state/omarchy/current/theme/colors.toml"
  printf '%s\n' bar background foreground accent muted urgent
  # Палитра Nihil (nihil/Palette.qml): тема или монохром — по nihil.json.
  printf '%s\n' nihil.bg nihil.fg nihil.dim nihil.line nihil.surface nihil.signal nihil.danger
  awk -F'=' '/^[a-z_]+ *= *"#/ { gsub(/ /, "", $1); print $1 }' "$colors" 2>/dev/null |
    grep -vxE 'background|foreground|accent|muted'
}

font_list() {
  echo ""
  fc-list : family | tr ',' '\n' | grep -iE 'nerd font$|( |^)NF$' | sort -u
}

tweak_value() {
  local key=$1 def=$2
  if [[ $key == transparent ]]; then jq -r '.bar.transparent // false' "$SHELL_JSON"; return; fi
  { [[ -s $TW_FILE ]] && cat "$TW_FILE" || echo '{}'; } |
    jq -r --arg k "$key" --arg d "$def" 'if has($k) and .[$k] != null then .[$k] | tostring else $d end'
}

# Следующий элемент списка по кругу: $1 = текущее, $2 = +1/-1, остальное — список.
cycle() {
  local cur=$1 dir=$2 i n
  shift 2
  local -a list=("$@")
  n=${#list[@]}
  for ((i = 0; i < n; i++)); do [[ ${list[i]} == "$cur" ]] && break; done
  # Не нашли (значение задано руками): вперёд — первый, назад — последний.
  if ((i == n)); then
    if ((dir > 0)); then i=$((n - 1)); else i=0; fi
  fi
  echo "${list[((i + dir + n) % n)]}"
}

tweak() {
  local key=$1 how=$2 spec kind args cur next dir=1
  case "$key" in
  w:*) widget_step "${key#w:}" "$how"; return ;;
  fontProfile) font_profile_step "$how"; return ;;
  wset:*) widget_setting "${key#wset:}"; return ;;
  esac
  spec=$(tweak_spec "$key") || exit 1
  TW_FILE=$(tweak_file "$key")
  IFS='|' read -r _ kind args _ <<<"$spec"
  [[ $how == - ]] && dir=-1
  if [[ $how == reset ]]; then
    if [[ $key == transparent ]]; then
      set_transparent false
    fi
    skin_edit --arg k "$key" 'del(.[$k])'
    return
  fi
  case "$kind" in
  enum)
    read -ra list <<<"$args"
    next=$(cycle "$(tweak_value "$key" "${list[0]}")" "$dir" "${list[@]}")
    skin_edit --arg k "$key" --arg v "$next" '.[$k] = $v'
    ;;
  font)
    mapfile -t list < <(font_list)
    next=$(cycle "$(tweak_value "$key" "")" "$dir" "${list[@]}")
    skin_edit --arg k "$key" --arg v "$next" '.[$k] = $v'
    ;;
  bool)
    cur=$(tweak_value "$key" "$args")
    next=$([[ $cur == true ]] && echo false || echo true)
    if [[ $key == transparent ]]; then
      set_transparent "$next"
      skin_edit --argjson v "$next" '.transparent = $v'
    else
      skin_edit --arg k "$key" --argjson v "$next" '.[$k] = $v'
    fi
    ;;
  num)
    local lo hi step def
    read -r lo hi step def <<<"$args"
    cur=$(tweak_value "$key" "$def")
    next=$(awk -v c="$cur" -v d="$dir" -v lo="$lo" -v hi="$hi" -v s="$step" 'BEGIN {
      # -1 = «как в стоке»: шаг вверх от него сразу на ноль.
      if (lo == -1 && c < 0) { v = d > 0 ? 0 : -1 }
      else { v = c + d * s; v = int(v / s + (v >= 0 ? 0.5 : -0.5)) * s; if (lo == -1 && v < 0) v = -1 }
      if (v < lo) v = lo; if (v > hi) v = hi
      if (s == int(s)) printf "%d", v; else { out = sprintf("%.2f", v); sub(/0+$/, "", out); sub(/\.$/, "", out); print out }
    }')
    # Заглушка «из стиля / из темы» — ключ убираем, чтобы работал пресет пикера.
    if [[ $TW_FILE == "$PICKER_CFG" && $next == "$def" && ($def == 0 || $def == -1) ]]; then
      skin_edit --arg k "$key" 'del(.[$k])'
    else
      skin_edit --arg k "$key" --argjson v "$next" '.[$k] = $v'
    fi
    ;;
  text)
    # Только ⏎ (pick): строку вводят в zenity; h/l ничего не делают.
    [[ $how == pick ]] || return 0
    next=$(zenity --entry --title="$key" --text="$(t "Text (empty — default):")" \
      --entry-text="$(tweak_value "$key" "")" 2>/dev/null) || exit 0
    if [[ -z $next ]]; then skin_edit --arg k "$key" 'del(.[$k])'; else skin_edit --arg k "$key" --arg v "$next" '.[$k] = $v'; fi
    ;;
  file)
    [[ $how == pick ]] || return 0
    next=$(zenity --file-selection --title="$(t "Avatar")" --filename="$HOME/" \
      --file-filter="Images | *.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP" 2>/dev/null) || exit 0
    skin_edit --arg k "$key" --arg v "$next" '.[$k] = $v'
    ;;
  color)
    if [[ $how == pick ]]; then
      local picked
      picked=$(zenity --color-selection --title="$key" 2>/dev/null) || exit 0
      # zenity отдаёт rgb(r,g,b) — переводим в #rrggbb.
      next=$(sed -E 's/rgba?\(([0-9]+),([0-9]+),([0-9]+).*/\1 \2 \3/' <<<"$picked" | xargs printf '#%02x%02x%02x')
    else
      mapfile -t list < <( [[ $key == gradient ]] && echo none; [[ $key == wsActiveColor || $key == nihil* ]] && echo default; [[ $args == '#'* ]] && echo "$args"; color_roles)
      next=$(cycle "$(tweak_value "$key" "$args")" "$dir" "${list[@]}")
    fi
    if [[ $next == none || $next == default ]]; then
      skin_edit --arg k "$key" 'del(.[$k])'
    else
      skin_edit --arg k "$key" --arg v "$next" '.[$k] = $v'
    fi
    ;;
  esac
}

# Параметр бара, который при текущей форме / compact ничего не меняет, — подсказка вместо
# «по умолчанию», чтобы не казалось, что настройка «не применяется».
bar_tweak_note() {
  local key=$1 shape=$2 compact=$3 need=""
  case "$key" in
  gap) need="floating pill islands" ;;
  margin) need="floating pill islands notch" ;;
  width) need="floating pill notch" ;;
  radius) need="floating islands notch hug frame" ;;
  frameWidth) need="frame" ;;
  islandGap) need="islands" ;;
  shadow | glow) need="floating pill islands notch underline" ;;
  compact) return 0 ;;
  compact*) [[ $compact == off ]] && t "only works when “Compact: when to shrink” is on" ; return 0 ;;
  esac
  [[ -z $need || " $need " == *" $shape "* ]] && return 0
  t "no effect for shape %s — needs: %s" "$shape" "$need"
}

# dash/osd/notify: свой фон, альфа, радиус и рамка не действуют, пока включено «следовать бару».
follow_bar_note() {
  local key=$1 prefix
  [[ $key =~ ^(dash|osd|notify)(Background|Alpha|Radius|Border)$ ]] || return 0
  prefix=${BASH_REMATCH[1]}
  [[ $(tweak_value "${prefix}FollowBar" true) == false ]] && return 0
  t "no effect while “Follow the bar style” is on"
}

# Ручной ввод (i в overlay или `customizer.sh tweak <key> set <value>`): значение проверяется по
# спецификации; неверное не записывается — код 2 и причина на stderr (на языке интерфейса).
tweak_set() {
  local key=$1 value=$2 spec kind args lo hi
  fail() { printf '%s\n' "$1" >&2; exit 2; }
  spec=$(tweak_spec "$key") || fail "$(t "Unknown setting: %s" "$key")"
  TW_FILE=$(tweak_file "$key")
  IFS='|' read -r _ kind args _ <<<"$spec"
  value=$(sed -E 's/^[[:space:]]+|[[:space:]]+$//g' <<<"$value")
  case "$kind" in
  num)
    read -r lo hi _ _ <<<"$args"
    [[ $value =~ ^-?[0-9]+([.][0-9]+)?$ ]] || fail "$(t "%s is not a number" "$value")"
    awk -v v="$value" -v lo="$lo" -v hi="$hi" 'BEGIN { exit !(v + 0 >= lo + 0 && v + 0 <= hi + 0) }' ||
      fail "$(t "%s is out of range %s … %s — not applied" "$value" "$lo" "$hi")"
    value=$(awk -v v="$value" 'BEGIN { printf "%g", v + 0 }')
    skin_edit --arg k "$key" --argjson v "$value" '.[$k] = $v'
    ;;
  enum)
    [[ " $args " == *" $value "* ]] || fail "$(t "%s is not one of: %s" "$value" "$args")"
    skin_edit --arg k "$key" --arg v "$value" '.[$k] = $v'
    ;;
  bool)
    case "${value,,}" in
    true | on | yes | 1 | вкл | да) value=true ;;
    false | off | no | 0 | выкл | нет) value=false ;;
    *) fail "$(t "%s is not on/off" "$value")" ;;
    esac
    [[ $key == transparent ]] && set_transparent "$value"
    skin_edit --arg k "$key" --argjson v "$value" '.[$k] = $v'
    ;;
  color)
    if [[ ($key == gradient && $value == none) || (($key == wsActiveColor || $key == nihil*) && $value == default) ]]; then
      skin_edit --arg k "$key" 'del(.[$k])'
    elif [[ $value =~ ^#[0-9A-Fa-f]{6}$ ]] || color_roles | grep -qxF -- "$value"; then
      skin_edit --arg k "$key" --arg v "$value" '.[$k] = $v'
    else
      fail "$(t "%s is not #rrggbb or a theme colour role" "$value")"
    fi
    ;;
  font)
    [[ -z $value ]] || font_list | grep -qxF -- "$value" || fail "$(t "Font not found: %s" "$value")"
    if [[ -z $value ]]; then skin_edit --arg k "$key" 'del(.[$k])'; else skin_edit --arg k "$key" --arg v "$value" '.[$k] = $v'; fi
    ;;
  text | file)
    if [[ -z $value ]]; then skin_edit --arg k "$key" 'del(.[$k])'; else skin_edit --arg k "$key" --arg v "$value" '.[$k] = $v'; fi
    ;;
  esac
}

# Строки Bar Tweaks / Lock Tweaks: $1 — имя массива параметров, $2 — файл настроек.
list_tweaks() {
  local -n table=$1
  TW_FILE=$2
  local t key kind args label def v hint mark long deflong sub shape compact
  if [[ $1 == TWEAKS ]]; then
    shape=$(tweak_value shape full)
    compact=$(tweak_value compact off)
  fi
  for t in "${table[@]}"; do
    # "#Раздел" — заголовок раздела: overlay рисует его линией и не выделяет.
    if [[ $t == '#'* ]]; then
      printf '%s\t%s\t\t0\t\theader\n' "$(t "${t#\#}")" "section:${t#\#}"
      continue
    fi
    IFS='|' read -r key kind args label <<<"$t"
    case "$kind" in
    num) def=${args##* } hint=$(t "h/l or −/+ — step %s, range %s" "$(awk '{print $3}' <<<"$args")" "$(awk '{print $1 " … " $2}' <<<"$args")") ;;
    enum) def=${args%% *} hint=$(t "h/l — cycle: %s" "$args") ;;
    color) def=$args hint=$(t "h/l — theme roles (bar = stock bar colour) · ⏎ — your own colour") ;;
    bool) def=$args hint=$(t "h/l or ⏎ — on/off") ;;
    font) def="" hint=$(t "h/l — Nerd fonts from fc-list; empty = system") ;;
    text) def="" hint=$(t "⏎ — enter text") ;;
    file) def="" hint=$(t "⏎ — pick an image") ;;
    esac
    v=$(tweak_value "$key" "$def")
    mark=""
    [[ $v != "$def" ]] && mark="●  "
    long=$(default_label "$key" "$v")
    deflong=$(default_label "$key" "$def")
    # В строке списка — короткое значение (до скобки), полностью — в превью.
    # Заметка: литеральные \n, overlay превращает их в переводы строк.
    # 6-е поле — подпись под строкой в списке (по умолчанию).
    sub=$(t "default: %s" "${deflong%% (*}")
    local na=""
    [[ $1 == TWEAKS ]] && na=$(bar_tweak_note "$key" "$shape" "$compact")
    [[ $1 != TWEAKS ]] && na=$(follow_bar_note "$key")
    [[ -n $na ]] && sub="○ $na"
    printf '%s\t%s\t%s\t0\t%s\t%s\n' "$mark$(t "$label"):  ${long%% (*}" "$key" "$TW_FILE" \
      "$(t "Now: %s" "$long")"'\n'"$(t "Default: %s" "$deflong")${na:+\\n$na}"'\n\n'"$hint · $(t "x — reset to default")" \
      "$sub"
  done
}

lock_current() { jq -r '.design // "classic"' "$LOCK_CFG" 2>/dev/null || echo classic; }

# Имя файла превью: "my:Foo.qml" -> "my-Foo.qml".
lock_thumb_name() { tr -c 'A-Za-z0-9._\n-' '-' <<<"$1"; }

lock_edit() {
  TW_FILE="$LOCK_CFG"
  skin_edit "$@"
}

# Снимает каждый дизайн через превью экрана блокировки (без блокировки).
lock_thumbs() {
  mkdir -p "$LOCK_THUMBS"
  notify-send -t 3000 "Lock" "$(t "Capturing design previews…")"
  local id
  {
    jq -r '.[].id' "$LOCK_PLUGIN/designs/designs.json"
    for f in "$LOCK_USER_DIR"/*.qml; do [[ -f $f ]] && echo "my:$(basename "$f")"; done
  } | while read -r id; do
    omarchy-shell lock previewDesign "$id" >/dev/null
    sleep 1.5
    grim -s 1 -t jpeg -q 90 "$LOCK_THUMBS/$(lock_thumb_name "$id").jpg"
  done
  omarchy-shell lock hidePreview >/dev/null
  notify-send -t 3000 "Lock" "$(t "Previews updated")"
}

# Миниатюры пикеров заранее: theme switcher (все темы) и обои текущей темы.
# Каталоги — ровно те же, что передают omarchy-theme-switcher / omarchy-theme-bg-switcher:
# ключ кэша строк omarchy-menu-images — md5 списка каталогов.
picker_cache() {
  local start before after theme
  start=$(date +%s)
  before=$(find "$PICKER_CACHE" -maxdepth 1 -name '*.jpg' 2>/dev/null | wc -l)
  notify-send -t 3000 "Theme Switcher" "$(t "Caching thumbnails…")"
  # --preload готовит previews/ (по превью на тему) и прогревает overlay.
  omarchy-theme-switcher --preload >/dev/null 2>&1
  omarchy-menu-images --cache-only "${XDG_CACHE_HOME:-$HOME/.cache}/omarchy/theme-selector/previews" >/dev/null 2>&1
  theme=$(theme_name)
  omarchy-menu-images --cache-only "$HOME/.local/state/omarchy/current/theme/backgrounds" \
    "$HOME/.config/omarchy/backgrounds/$theme" >/dev/null 2>&1
  after=$(find "$PICKER_CACHE" -maxdepth 1 -name '*.jpg' 2>/dev/null | wc -l)
  notify-send -t 4000 "Theme Switcher" "$(t "Done in %s s: %s new thumbnails" "$(($(date +%s) - start))" "$((after - before))")"
}

# Миниатюры, чей исходник исчез или изменился (размер:mtime не совпадает с index.tsv),
# удаляются; индекс переписывается. --dry-run только считает. Работает строго внутри
# $PICKER_CACHE (realpath-проверка).
picker_prune() {
  python3 - "$PICKER_CACHE" "${1:-}" "$(t "Can delete: %s thumbnails, %s GB; %s stay")" "$(t "Deleted: %s thumbnails, %s GB; %s stay")" <<'PRUNE'
import os, sys
cache = os.path.realpath(sys.argv[1])
dry = sys.argv[2] == "--dry-run"
msg_dry, msg_done = sys.argv[3], sys.argv[4]
index = os.path.join(cache, "index.tsv")
keep, lines = set(), []
try:
    for line in open(index, encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 3:
            continue
        path, sig, h = parts
        try:
            st = os.stat(path)
        except OSError:
            continue
        if f"{st.st_size}:{int(st.st_mtime)}" == sig:
            keep.add(h + ".jpg")
            lines.append(line if line.endswith("\n") else line + "\n")
except FileNotFoundError:
    pass
# Всё, на что ссылаются кэши строк (*.rows), тоже оставляем.
for name in os.listdir(cache):
    if name.endswith(".rows"):
        for row in open(os.path.join(cache, name), encoding="utf-8", errors="replace"):
            cols = row.rstrip("\n").split("\t")
            if len(cols) == 2:
                keep.add(os.path.basename(cols[1]))
count = size = 0
for name in os.listdir(cache):
    if not name.endswith(".jpg") or name in keep:
        continue
    full = os.path.join(cache, name)
    if not os.path.realpath(full).startswith(cache + os.sep) or not os.path.isfile(full):
        continue
    count += 1
    size += os.path.getsize(full)
    if not dry:
        os.remove(full)
if not dry:
    tmp = index + ".prune.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(dict.fromkeys(lines))
    os.replace(tmp, index)
print((msg_dry if dry else msg_done).replace("%s", "{}").format(count, f"{size / 1024**3:.1f}", len(keep)))
PRUNE
}

bar_skin_preview() {
  # Строка «Сохранить текущий» — показать то, что было на баре до превью.
  if [[ $1 == save ]]; then set -- "$SKIN_BACKUP"; fi
  [[ -f $1 ]] || return 0
  cp "$1" "$BAR_SKIN"
  set_transparent "$(jq -r '.transparent // false' "$1")"
}

# Сохранить скин, который был на баре до превью (снимок SKIN_BACKUP), в $USER_SKINS/<имя>.json.
save_user_skin() {
  local name file note
  name=$(zenity --entry --title="$(t "Save the bar skin")" --text="$(t "Skin name (latin letters, digits, - and _):")" \
    --entry-text="my-skin" 2>/dev/null) || return 0
  name=$(tr '[:upper:] ' '[:lower:]-' <<<"$name" | tr -cd 'a-z0-9_-')
  [[ -n $name ]] || { notify-send -u critical "Bar Skin" "$(t "Empty skin name")"; return 1; }
  file="$USER_SKINS/$name.json"
  if [[ -e $file ]]; then
    zenity --question --title="$(t "Save the bar skin")" --text="$(t "Skin %s already exists. Overwrite?" "$name")" 2>/dev/null || return 0
  fi
  note=$(zenity --entry --title="$(t "Save the bar skin")" --text="$(t "Description (optional):")" 2>/dev/null) || note=""
  mkdir -p "$USER_SKINS"
  { [[ -s $SKIN_BACKUP ]] && cat "$SKIN_BACKUP" || echo '{}'; } |
    jq --arg n "$note" 'with_entries(select(.key | test("^note(_[a-z]+)?$") | not)) | if $n == "" then . else {note: $n} + . end' >"$file.tmp" &&
    mv "$file.tmp" "$file"
  cp "$SKIN_BACKUP" "$BAR_SKIN" 2>/dev/null
  notify-send -t 3000 "Bar Skin" "$(t "Saved %s" "$name")"
}

# Сохранить раскладку из shell.json в $USER_LAYOUTS/<имя>.json.
save_user_layout() {
  local name file
  name=$(zenity --entry --title="$(t "Save the bar layout")" --text="$(t "Layout name (latin letters, digits, - and _):")" \
    --entry-text="my-layout" 2>/dev/null) || return 0
  name=$(tr '[:upper:] ' '[:lower:]-' <<<"$name" | tr -cd 'a-z0-9_-')
  [[ -n $name ]] || { notify-send -u critical "Bar Layout" "$(t "Empty layout name")"; return 1; }
  file="$USER_LAYOUTS/$name.json"
  if [[ -e $file ]]; then
    zenity --question --title="$(t "Save the bar layout")" --text="$(t "Layout %s already exists. Overwrite?" "$name")" 2>/dev/null || return 0
  fi
  mkdir -p "$USER_LAYOUTS"
  jq --arg n "$(t "Saved %s" "$(date +%F)")" '.bar | {note: $n, position, centerAnchor, layout}' "$SHELL_JSON" >"$file.tmp" &&
    mv "$file.tmp" "$file"
  notify-send -t 3000 "Bar Layout" "$(t "Saved: %s" "$name")"
}

# Удалить свою раскладку (только из $USER_LAYOUTS) после подтверждения; файл уходит в корзину.
delete_user_layout() {
  local file=$1 name
  [[ -f $file && $(dirname "$(realpath "$file")") == "$(realpath "$USER_LAYOUTS")" && $file == *.json ]] || {
    notify-send -u critical "Bar Layout" "$(t "Only your own layouts (★) can be deleted")"; return 1; }
  name=$(basename "$file" .json)
  zenity --question --title="$(t "Delete the bar layout")" \
    --text="$(t "Delete your layout %s? The file goes to the trash." "$name")" 2>/dev/null || return 0
  gio trash "$file" && notify-send -t 3000 "Bar Layout" "$(t "Deleted %s" "$name")"
}

# Удалить свой скин (только из $USER_SKINS) после подтверждения; файл уходит в корзину (gio trash).
delete_user_skin() {
  local file=$1 name
  [[ -f $file && $(dirname "$(realpath "$file")") == "$(realpath "$USER_SKINS")" && $file == *.json ]] || {
    notify-send -u critical "Bar Skin" "$(t "Only your own skins (★) can be deleted")"; return 1; }
  name=$(basename "$file" .json)
  zenity --question --title="$(t "Delete the bar skin")" \
    --text="$(t "Delete your skin %s? The file goes to the trash." "$name")" 2>/dev/null || return 0
  gio trash "$file" && notify-send -t 3000 "Bar Skin" "$(t "Deleted %s" "$name")"
}

bar_skin_restore() {
  # Overlay зовёт это только после превью, так что снимок свежий.
  [[ -f $SKIN_BACKUP ]] && cp "$SKIN_BACKUP" "$BAR_SKIN"
  [[ -f $TRANSPARENT_BACKUP ]] && set_transparent "$(command cat "$TRANSPARENT_BACKUP")"
}

# ── Виджеты бара: включение, порядок, параметры (shell.json .bar.layout) ──
# Строки категории bar-widgets — твики с ключами w:<id> (h/l — сдвиг, ⏎/x — вкл/выкл) и
# wset:<id>:<key> (параметр виджета). Перемещение и добавление делает сам шелл
# (moveBarWidget / putBarWidget); убранный виджет вместе с настройками и местом
# запоминается в bar-hidden.json, чтобы вернуться туда же.
BAR_HIDDEN="$HOME/.config/omarchy/customizer/bar-hidden.json"

# Человеческие имена qml-модулей бара (у плагинов имя — из манифеста).
widget_label() {
  case "$1" in
  nihil-mark) t "Nihil logo" ;;
  active-app) t "Active app" ;;
  battery-gauge) t "Battery (LED)" ;;
  dot-clock) t "Clock (Doto)" ;;
  privacy-led) t "Microphone LED" ;;
  *) jq -r --arg id "$1" 'map(select(.id == $id))[0] | .barWidget.displayName // .name // $id' <<<"$WIDGET_CATALOG" 2>/dev/null || echo "$1" ;;
  esac
}

widget_location() {
  jq -r --arg id "$1" '.bar.layout as $l | [("left", "center", "right") as $s
    | (($l[$s] // []) | map(if type == "object" then .id else . end) | index($id)) as $i
    | select($i != null) | "\($s) \($i)"] | first // ""' "$SHELL_JSON"
}

widget_hide() {
  local id=$1 sec=$2 idx=$3 entry
  entry=$(jq -c --arg s "$sec" --argjson i "$idx" '.bar.layout[$s][$i]' "$SHELL_JSON")
  mkdir -p "$(dirname "$BAR_HIDDEN")"
  { [[ -s $BAR_HIDDEN ]] && cat "$BAR_HIDDEN" || echo '{}'; } |
    jq --arg id "$id" --argjson e "$entry" --arg s "$sec" --argjson i "$idx" \
      '.[$id] = {entry: $e, section: $s, index: $i}' >"$RUN_DIR/bar-hidden.tmp" && cp "$RUN_DIR/bar-hidden.tmp" "$BAR_HIDDEN"
  shell_edit --arg s "$sec" --argjson i "$idx" '.bar.layout[$s] |= (.[0:$i] + .[$i + 1:])'
}

widget_show() {
  local id=$1 stash
  stash=$(jq -c --arg id "$id" '.[$id] // empty' "$BAR_HIDDEN" 2>/dev/null)
  if [[ -n $stash ]]; then
    shell_edit --argjson h "$stash" '.bar.layout[$h.section] = ((.bar.layout[$h.section] // [])
      | ([$h.index, length] | min) as $i | .[0:$i] + [$h.entry] + .[$i:])'
    jq --arg id "$id" 'del(.[$id])' "$BAR_HIDDEN" >"$RUN_DIR/bar-hidden.tmp" && cp "$RUN_DIR/bar-hidden.tmp" "$BAR_HIDDEN"
  else
    omarchy-shell shell putBarWidget "$id" '{}' >/dev/null
  fi
}

# $1 = id, $2 = - | + | toggle | reset | pick
widget_step() {
  local id=$1 how=$2 loc sec idx n si place
  local -a secs=(left center right)
  loc=$(widget_location "$id")
  [[ $how == set ]] && return 0
  if [[ $how != - && $how != + ]]; then
    if [[ -n $loc ]]; then widget_hide "$id" $loc; else widget_show "$id"; fi
    return
  fi
  [[ -n $loc ]] || return 0
  read -r sec idx <<<"$loc"
  n=$(jq --arg s "$sec" '.bar.layout[$s] | length' "$SHELL_JSON")
  for si in 0 1 2; do [[ ${secs[si]} == "$sec" ]] && break; done
  # Через край секции виджет переходит в соседнюю: в конец предыдущей или в начало следующей.
  if [[ $how == - ]]; then
    if ((idx > 0)); then place=$(jq -cn --arg s "$sec" --argjson i $((idx - 1)) '{section: $s, index: $i}')
    elif ((si > 0)); then place=$(jq -cn --arg s "${secs[si - 1]}" --argjson i "$(jq --arg s "${secs[si - 1]}" '.bar.layout[$s] // [] | length' "$SHELL_JSON")" '{section: $s, index: $i}')
    else return 0; fi
  else
    if ((idx < n - 1)); then place=$(jq -cn --arg s "$sec" --argjson i $((idx + 1)) '{section: $s, index: $i}')
    elif ((si < 2)); then place=$(jq -cn --arg s "${secs[si + 1]}" '{section: $s, index: 0}')
    else return 0; fi
  fi
  omarchy-shell shell moveBarWidget "$id" "$place" >/dev/null
}

# Шрифты системы: omarchy-font-profile (dotfiles) — терминалы, fontconfig, GTK, VS Code, браузер, Nihil.
font_profile_step() {
  command -v omarchy-font-profile >/dev/null || return 0
  local -a list
  mapfile -t list < <(omarchy-font-profile list | cut -f1)
  local cur next dir=1
  [[ $1 == - ]] && dir=-1
  cur=$(omarchy-font-profile)
  if [[ $1 == reset ]]; then next=stock; else next=$(cycle "$cur" "$dir" "${list[@]}"); fi
  omarchy-font-profile "$next" >/dev/null 2>&1 || true
}

# Звуковые пакеты: theme (звуки темы) и каталоги sounds/<пакет> плагина.
sound_packs() {
  local d
  echo theme
  for d in "$CUSTOMIZER_DIR"/sounds/*/; do basename "$d"; done
}

sound_pack_desc() {
  case "$1" in
  theme) t "Sounds of the current Omarchy theme (apps/sounds), then the freedesktop theme" ;;
  nihil) t "NIHIL: tactile hardware clicks and LED blips" ;;
  classic) t "Classic: soft neutral system sounds" ;;
  flat) t "Flat: short clean sine ticks" ;;
  glass) t "Glass: glassy inharmonic bells with a long ring" ;;
  fluent) t "Fluent: soft marimba notes" ;;
  paper) t "Paper: rustle of a sheet, pencil ticks and taps on the desk" ;;
  neumorph) t "Neumorphism: muted soft thuds" ;;
  brutal) t "Brutalism: hard clicks and low thumps" ;;
  retro) t "Retro 9x: 8-bit square-wave chiptune motifs" ;;
  neon) t "Neon: synth saw with a filter sweep" ;;
  *) t "Sound pack: %s" "$1" ;;
  esac
}

SOUND_EVENTS=(open close switch menu notify critical lock power volume)

font_group_title() {
  case "$1" in
  base) echo "Without a style" ;;
  nihil) echo "NIHIL" ;;
  paper) echo "Paper" ;;
  retro) echo "Retro" ;;
  *) echo "$1" ;;
  esac
}

list_font_profile() {
  command -v omarchy-font-profile >/dev/null || return 0
  local cur desc
  cur=$(omarchy-font-profile)
  desc=$(omarchy-font-profile list | awk -F'\t' -v c="$cur" '$1 == c { print $2 }')
  printf '%s\t%s\t\t0\t\theader\n' "$(t "System fonts")" "section:System fonts"
  printf '%s\t%s\t\t0\t%s\t%s\n' "$(t "Font profile"):  $cur" "fontProfile" \
    "$(t "$desc")"'\n\n'"$(t "h/l — stock · nothing · dot · pixel. Applies to terminals, GTK, VS Code, browser (Dark Reader, Stylus) and the Nihil shell. x — back to stock.")" \
    "$(t "$desc")"
}

# Параметры виджетов (bool): id|key|default|label
WIDGET_SETTINGS=(
  "kamradsmeshnyavy.tray|collapse|false|Tray: collapse into a drawer (opens on hover)"
  "kamradsmeshnyavy.tray|monochrome|true|Tray: monochrome icons (colour on hover)"
)

widget_setting_value() { # id key default
  jq -r --arg id "$1" --arg k "$2" --arg d "$3" '[.bar.layout[][] | select(type == "object" and .id == $id)][0]
    | if . != null and has($k) and .[$k] != null then .[$k] | tostring else $d end' "$SHELL_JSON"
}

widget_setting() { # "<id>:<key>"
  local id=${1%:*} key=${1##*:} t def cur
  for t in "${WIDGET_SETTINGS[@]}"; do
    IFS='|' read -r tid tkey def _ <<<"$t"
    [[ $tid == "$id" && $tkey == "$key" ]] && break
  done
  cur=$(widget_setting_value "$id" "$key" "$def")
  omarchy-shell shell setBarWidget "$id" "$key" "$([[ $cur == true ]] && echo false || echo true)" '{}' >/dev/null
}

list_bar_widgets() {
  WIDGET_CATALOG=$(omarchy plugin list --json 2>/dev/null || echo '[]')
  local sec id on t tid tkey def label v
  local -A seen=()
  for sec in left center right; do
    case $sec in left) label=$(t "Left / top") ;; center) label=$(t "Center") ;; right) label=$(t "Right / bottom") ;; esac
    printf '%s\t%s\t\t0\t\theader\n' "$label" "section:$sec"
    while read -r id; do
      [[ -n $id ]] || continue
      seen[$id]=1
      printf '%s\t%s\t\t0\t%s\t%s\n' "● $(widget_label "$id")" "tweak:w:$id" \
        "$(t "On the bar · %s" "$id")"'\n\n'"$(t "h/l — move earlier / later (across sections at the edge) · ⏎ — remove from the bar")" "$id"
    done < <(jq -r --arg s "$sec" '.bar.layout[$s] // [] | .[] | if type == "object" then .id else . end' "$SHELL_JSON")
  done
  # Не на баре: убранные (с запомненным местом) и установленные виджеты-плагины. Стоковый
  # виджет, у которого есть свой клон, не предлагаем — его включение сняло бы клон.
  printf '%s\t%s\t\t0\t\theader\n' "$(t "Not on the bar")" "section:off"
  { jq -r 'keys[]' "$BAR_HIDDEN" 2>/dev/null
    jq -r --argjson cloned "$(cat "$HOME"/.config/omarchy/plugins/*/manifest.json 2>/dev/null | jq -s '[.[].omarchy.clonedFrom // empty]')" \
      '.[] | select((.kinds // []) | index("bar-widget")) | select(.id as $i | $cloned | index($i) | not) | .id' <<<"$WIDGET_CATALOG"
  } | awk '!s[$0]++' | while read -r id; do
    [[ -n $id && -z ${seen[$id]:-} ]] || continue
    printf '%s\t%s\t\t0\t%s\t%s\n' "○ $(widget_label "$id")" "tweak:w:$id" \
      "$(t "Not on the bar · %s" "$id")"'\n\n'"$(t "⏎ — put on the bar (back to its old place if it was removed here)")" "$id"
  done
  printf '%s\t%s\t\t0\t\theader\n' "$(t "Widget settings")" "section:settings"
  for t in "${WIDGET_SETTINGS[@]}"; do
    IFS='|' read -r tid tkey def label <<<"$t"
    v=$(widget_setting_value "$tid" "$tkey" "$def")
    printf '%s\t%s\t\t0\t%s\t%s\n' "$(t "$label"):  $v" "tweak:wset:$tid:$tkey" \
      "$(t "Now: %s" "$v")"'\n'"$(t "Default: %s" "$def")"'\n\n'"$(t "h/l or ⏎ — on/off")" "$(t "default: %s" "$def")"
  done
}

# ── Глобальные пресеты, Glyph и Лаунчер ───────────────────────────────

preset_name_of() {
  local base
  base=$(basename "$1" .json)
  jq -r --arg l "$UI_LANG" --arg d "$base" '.["name_" + $l] // .name // $d' "$1" 2>/dev/null || echo "$base"
}

preset_summary() {
  jq -r '[
    (if .theme then "theme: " + .theme else empty end),
    (if .style then "style: " + .style else empty end),
    (if .barSkin then "bar: " + .barSkin elif .barSkinData then "bar: custom" else empty end),
    (if .barLayout then "layout: " + .barLayout elif .barLayoutData then "layout: custom" else empty end),
    (if .lock.design then "lock: " + .lock.design else empty end),
    (if .launcher.skin then "launcher: " + .launcher.skin else empty end),
    (if .anims and .anims != "" then "anims: " + .anims else empty end),
    (if .glyph.glyphEnabled == true then "glyph: on" else empty end)
  ] | join("  ·  ")' "$1" 2>/dev/null
}

# Включён ли раздел: $1 — файл (preset-apply.json / style-apply.json), $2 — ключ; по умолчанию да.
section_on() {
  [[ $(jq -r --arg k "$2" 'if has($k) then .[$k] | tostring else "true" end' "$1" 2>/dev/null || echo true) != false ]]
}
preset_on() { section_on "$PRESET_CFG" "$1"; }
style_on() { section_on "$STYLE_CFG" "$1"; }

# Сравниваются только разделы, которые пресет применяет.
preset_matches() {
  local f=$1 p_theme p_skin p_lock
  if preset_on presetTheme; then
    p_theme=$(jq -r '.theme // ""' "$f" 2>/dev/null)
    [[ -n $p_theme && $p_theme != "$(theme_name)" ]] && return 1
  fi
  if preset_on presetBar; then
    p_skin=$(jq -r '.barSkin // ""' "$f" 2>/dev/null)
    [[ -n $p_skin && -f $BAR_DIR/manifest.json && $p_skin != "$(current_skin)" ]] && return 1
  fi
  if preset_on presetLock; then
    p_lock=$(jq -r '.lock.design // ""' "$f" 2>/dev/null)
    [[ -n $p_lock && -f $LOCK_PLUGIN/manifest.json && $p_lock != "$(lock_current)" ]] && return 1
  fi
  return 0
}

# Геометрия окон из пресета: ~/.local/state/hypr/geometry, читает hypr/customizer.lua.
geometry_summary() {
  local f="${XDG_STATE_HOME:-$HOME/.local/state}/hypr/geometry" _n gi go bs r shd
  [[ -s $f ]] || { t "Hyprland config"; return; }
  read -r _n gi go bs r shd <"$f" || true
  t "gaps %s/%s · border %s · rounding %s · shadow %s" "$gi" "$go" "$bs" "$r" "$([[ ${shd:-0} != 0 ]] && echo on || echo off)"
}

geometry_reset() {
  local f="${XDG_STATE_HOME:-$HOME/.local/state}/hypr/geometry"
  [[ -s $f ]] && : >"$f"
  hyprctl reload >/dev/null 2>&1 || true
  restore
  notify-send -t 2000 "Presets" "$(t "Window geometry: Hyprland config")"
}

theme_exists() {
  [[ -n $1 && ( -d $HOME/.config/omarchy/themes/$1 || -d ${OMARCHY_PATH:-/usr/share/omarchy}/themes/$1 ) ]]
}

current_preset_stem() {
  local saved f stem
  if [[ -s $ACTIVE_PRESET ]]; then
    saved=$(<"$ACTIVE_PRESET")
    for f in "$USER_PRESETS/$saved.json" "$PRESET_DIR/$saved.json"; do
      if [[ -f $f ]] && preset_matches "$f"; then
        echo "$saved"
        return
      fi
    done
  fi
  for f in "$USER_PRESETS"/*.json "$PRESET_DIR"/*.json; do
    [[ -f $f ]] || continue
    if preset_matches "$f"; then
      basename "$f" .json
      return
    fi
  done
  echo custom
}

current_preset_label() {
  local stem f
  stem=$(current_preset_stem)
  [[ $stem == custom ]] && { echo custom; return; }
  for f in "$USER_PRESETS/$stem.json" "$PRESET_DIR/$stem.json"; do
    [[ -f $f ]] && { preset_name_of "$f"; return; }
  done
  echo "$stem"
}

write_json_inplace() {
  local target=$1 json=$2 tmp="$RUN_DIR/preset-write.tmp"
  mkdir -p "$(dirname "$target")"
  printf '%s\n' "$json" >"$tmp" && cp "$tmp" "$target"
}

read_json_or_empty() {
  if [[ -s $1 ]]; then jq -c '.' "$1" 2>/dev/null || echo '{}'; else echo '{}'; fi
}

snapshot_preset() {
  local out=$1 title=${2:-} note=${3:-}
  local hypr_state="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
  local theme wp anim="" f op bl sh geom_json="null" skin_name layout_name skin_data="null" layout_data="null" bar_tr
  theme=$(theme_name)
  wp=$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true)
  [[ -n $wp ]] && wp=${wp/#"$HOME/"/"~/"}
  if [[ -s $ANIM_ACTIVE ]]; then
    while read -r f; do
      cmp -s "$f" "$ANIM_ACTIVE" && { anim=$(basename "$f" .lua); break; }
    done < <(anim_files)
  fi
  op=$("$OPACITY" current 2>/dev/null || echo subtle)
  bl=$("$BLUR" current 2>/dev/null || echo medium)
  sh=$(current_shader)
  if [[ -s $hypr_state/geometry ]]; then
    local _gn gi go bs r shd
    read -r _gn gi go bs r shd <"$hypr_state/geometry" || true
    if [[ -n ${shd:-} ]]; then
      geom_json=$(jq -cn --argjson gi "$gi" --argjson go "$go" --argjson bs "$bs" --argjson r "$r" --argjson s "$((shd > 0 ? 1 : 0))" \
        '{gapsIn: $gi, gapsOut: $go, borderSize: $bs, rounding: $r, shadow: ($s == 1)}')
      [[ -f ${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/toggles/hypr/window-no-gaps.lua ]] \
        && geom_json=$(jq -c '. + {noGaps: true}' <<<"$geom_json")
    fi
  fi
  skin_name=$(current_skin)
  if [[ $skin_name == custom || $skin_name == stock ]]; then
    skin_name=""
    skin_data=$(read_json_or_empty "$BAR_SKIN")
  fi
  layout_name=$(current_layout)
  if [[ $layout_name == custom ]]; then
    layout_name=""
    layout_data=$(jq -c '.bar | {position, centerAnchor, layout}' "$SHELL_JSON" 2>/dev/null || echo 'null')
  fi
  bar_tr=$(jq -r '.bar.transparent // false' "$SHELL_JSON" 2>/dev/null || echo false)
  local style_id
  style_id=$(current_style_stem)
  [[ $style_id == custom ]] && style_id=""

  mkdir -p "$(dirname "$out")"
  jq -n \
    --arg name "$title" \
    --arg note "$note" \
    --arg theme "$theme" \
    --arg style "$style_id" \
    --arg wallpaper "$wp" \
    --arg anims "$anim" \
    --arg opacity "$op" \
    --arg blur "$bl" \
    --arg shader "$sh" \
    --argjson hyprGeometry "$geom_json" \
    --arg barSkin "$skin_name" \
    --argjson barSkinData "$skin_data" \
    --arg barLayout "$layout_name" \
    --argjson barLayoutData "$layout_data" \
    --argjson barTransparent "$bar_tr" \
    --argjson lock "$(read_json_or_empty "$LOCK_CFG")" \
    --argjson launcher "$(read_json_or_empty "$MENU_CFG")" \
    --argjson wallpaperFx "$(read_json_or_empty "$FX_CFG")" \
    --argjson imagePicker "$(read_json_or_empty "$PICKER_CFG")" \
    --argjson widgets "$(read_json_or_empty "$WIDGET_CFG")" \
    --argjson osd "$(read_json_or_empty "$OSD_CFG")" \
    --argjson notifications "$(read_json_or_empty "$NOTIFY_CFG")" \
    --argjson sounds "$(read_json_or_empty "$SOUND_CFG")" \
    --argjson glyph "$(read_json_or_empty "$GLYPH_CFG")" \
    --argjson look "$(read_json_or_empty "$LOOK_CFG")" \
    '(if $name != "" then {name: $name} else {} end)
     + (if $note != "" then {note: $note} else {} end)
     + {theme: $theme}
     + (if $style != "" then {style: $style} else {} end)
     + {
       wallpaper: $wallpaper,
       anims: $anims,
       opacity: $opacity,
       blur: $blur,
       shader: $shader,
       hyprGeometry: $hyprGeometry
     }
     + (if $barSkin != "" then {barSkin: $barSkin} else {barSkinData: $barSkinData} end)
     + (if $barLayout != "" then {barLayout: $barLayout} else {barLayoutData: $barLayoutData} end)
     + {
       barTransparent: $barTransparent,
       lock: $lock,
       launcher: $launcher,
       wallpaperFx: $wallpaperFx,
       imagePicker: $imagePicker,
       widgets: $widgets,
       osd: $osd,
       notifications: $notifications,
       sounds: $sounds,
       glyph: $glyph,
       look: $look
     }' >"$out.tmp" && cp "$out.tmp" "$out"
}

apply_preset() {
  local file=$1 label
  [[ -f $file ]] || { notify-send -u critical "Presets" "$(t "Preset not found: %s" "$file")"; exit 1; }
  label=$(preset_name_of "$file")
  local is_backup=false
  [[ $(realpath "$file") == "$(realpath -m "$LAST_PRESET")" ]] && is_backup=true

  # Тему проверяем до записи чего-либо: иначе пресет применится наполовину.
  local theme wp
  theme=$(jq -r '.theme // ""' "$file")
  if $is_backup || preset_on presetTheme; then
    if [[ -n $theme ]] && ! theme_exists "$theme"; then
      notify-send -u critical "Presets" "$(t "Theme %s is not installed — preset not applied. Turn off \"Apply theme\" to use it without the theme." "$theme")"
      exit 1
    fi
  else
    theme=""
  fi
  notify-send -t 3000 "Presets" "$(t "Applying preset %s…" "$label")"

  # Резервная копия — только с «своего» состояния. Поверх уже применённого пресета она
  # не перезаписывается, чтобы «Восстановить прежнюю настройку» вела к исходному виду.
  if ! $is_backup && { [[ ! -s $LAST_PRESET ]] || [[ $(current_preset_stem) == custom ]]; }; then
    snapshot_preset "$LAST_PRESET" "$(t "Previous setup")" \
      "$(t "Automatic backup before applying %s (%s)" "$label" "$(date '+%F %H:%M')")"
  fi

  # Пресет со ссылкой на стиль: сначала стиль (вливается), затем собственные поля пресета поверх.
  local style_ref style_file
  style_ref=$(jq -r '.style // ""' "$file")
  if [[ -n $style_ref ]] && style_file=$(style_file_of "$style_ref"); then
    apply_form_sections "$style_file" "$PRESET_CFG" preset "$is_backup" merge
    # id стиля для панелей: у пресета префикс preset, поэтому id дописываем здесь.
    if [[ -s $LOOK_CFG ]] && { $is_backup || preset_on presetLook; }; then
      write_json_inplace "$LOOK_CFG" "$(jq --arg id "$style_ref" '. + {id: $id}' "$LOOK_CFG")"
    fi
    if $is_backup || preset_on presetFonts; then apply_style_fonts "$style_file"; fi
  fi
  FORM_KEEP_LOOK=false
  [[ -n $style_ref ]] && FORM_KEEP_LOOK=true
  apply_form_sections "$file" "$PRESET_CFG" preset "$is_backup" replace

  # Theme & wallpaper (тема уже проверена и отфильтрована выше)
  wp=""
  { $is_backup || preset_on presetWallpaper; } && wp=$(jq -r '.wallpaper // ""' "$file")
  [[ $wp == "~/"* ]] && wp="$HOME/${wp#"~/"}"
  if [[ -n $theme && $theme != "$(theme_name)" ]]; then
    if [[ -n $wp && -f $wp ]]; then
      OMARCHY_THEME_SKIP_BACKGROUND=1 omarchy theme set "$theme"
      omarchy theme bg set "$wp"
    else
      omarchy theme set "$theme"
    fi
  elif [[ -n $wp && -f $wp ]]; then
    omarchy theme bg set "$wp"
  fi

  hyprctl reload >/dev/null 2>&1 || true
  restore
  { $is_backup || preset_on presetLook; } && refresh_app_looks

  if $is_backup; then
    : >"$ACTIVE_PRESET"
  else
    basename "$file" .json >"$ACTIVE_PRESET"
  fi
  if [[ -n $style_ref ]]; then printf '%s\n' "$style_ref" >"$ACTIVE_STYLE"; else : >"$ACTIVE_STYLE"; fi
  notify-send -t 3000 "Presets" "$(t "Applied preset: %s" "$label")"
}

# Разделы «формы» из файла пресета или стиля: скины, конфиги плагинов, геометрия, анимации,
# прозрачность, блюр, шейдер. $1 — файл, $2 — файл переключателей, $3 — префикс ключей (preset/style),
# $4 — true для резервной копии (применяется целиком), $5 — replace (раздел заменяет файл, как у
# пресетов) или merge (ключи раздела вливаются в текущий файл — стиль не трогает твои прочие настройки).
apply_form_sections() {
  local file=$1 cfg=$2 prefix=$3 is_backup=$4 mode=$5
  _form_on() { $is_backup || section_on "$cfg" "$prefix$1"; }

  local pair key flag target json
  for pair in \
    "lock|Lock|$LOCK_CFG" \
    "launcher|Launcher|$MENU_CFG" \
    "wallpaperFx|WallpaperFx|$FX_CFG" \
    "imagePicker|WallpaperFx|$PICKER_CFG" \
    "widgets|Widgets|$WIDGET_CFG" \
    "osd|Osd|$OSD_CFG" \
    "notifications|Notifications|$NOTIFY_CFG" \
    "sounds|Sounds|$SOUND_CFG" \
    "glyph|Glyph|$GLYPH_CFG"; do
    IFS='|' read -r key flag target <<<"$pair"
    _form_on "$flag" || continue
    jq -e --arg k "$key" 'has($k) and .[$k] != null' "$file" >/dev/null 2>&1 || continue
    if [[ $mode == merge ]]; then
      json=$(jq --arg k "$key" --argjson cur "$(read_json_or_empty "$target")" '$cur * .[$k]' "$file")
    else
      json=$(jq --arg k "$key" '.[$k]' "$file")
    fi
    write_json_inplace "$target" "$json"
  done

  # Bar skin & layout
  local bs bl sfile lfile btr
  if _form_on Bar; then
    if jq -e '.barSkinData != null and (.barSkinData | type == "object")' "$file" >/dev/null 2>&1; then
      write_json_inplace "$BAR_SKIN" "$(jq '.barSkinData' "$file")"
    else
      bs=$(jq -r '.barSkin // ""' "$file")
      if [[ -n $bs ]]; then
        for sfile in "$USER_SKINS/$bs.json" "$BAR_DIR/skins/$bs.json"; do
          [[ -f $sfile ]] && { cp "$sfile" "$BAR_SKIN"; break; }
        done
      fi
    fi
    if jq -e '.barLayoutData != null and (.barLayoutData | type == "object")' "$file" >/dev/null 2>&1; then
      local ltmp="$RUN_DIR/preset-layout.tmp"
      jq '.barLayoutData' "$file" >"$ltmp"
      shell_apply_layout "$ltmp"
    else
      bl=$(jq -r '.barLayout // ""' "$file")
      if [[ -n $bl ]]; then
        for lfile in "$USER_LAYOUTS/$bl.json" "$BAR_DIR/layouts/$bl.json"; do
          [[ -f $lfile ]] && { shell_apply_layout "$lfile"; break; }
        done
      fi
    fi
    if jq -e 'has("barTransparent")' "$file" >/dev/null 2>&1; then
      btr=$(jq -r '.barTransparent // false' "$file")
      set_transparent "$btr"
    fi
  fi

  # Hyprland state (geometry, animations, opacity, blur, shader)
  local hypr_state="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
  mkdir -p "$hypr_state"
  if _form_on Geometry; then
    if jq -e '.hyprGeometry != null and (.hyprGeometry | type == "object")' "$file" >/dev/null 2>&1; then
      jq -r '.hyprGeometry | "preset \(.gapsIn // 4) \(.gapsOut // 8) \(.borderSize // 1) \(.rounding // 12) \(if .shadow == true then 1 else 0 end)"' \
        "$file" >"$hypr_state/geometry"
      # «Без отступов» Omarchy (Super+Shift+Backspace) снимает и рамки окон: включён только там, где
      # геометрия просит noGaps (рамка-бортик Nihil — окна вплотную к ней), иначе рамки возвращаются.
      set_no_gaps "$(jq -r '.hyprGeometry.noGaps // false' "$file")"
    elif [[ $mode == replace ]] && jq -e 'has("hyprGeometry")' "$file" >/dev/null 2>&1; then
      : >"$hypr_state/geometry"
      set_no_gaps false
    fi
  fi

  local anim afile op blr sh
  if _form_on Anims && jq -e 'has("anims")' "$file" >/dev/null 2>&1; then
    anim=$(jq -r '.anims // ""' "$file")
    if [[ -z $anim ]]; then
      : >"$ANIM_ACTIVE"
    else
      for afile in "$ANIM_USER_DIR/$anim.lua" "$ANIM_DIR/$anim.lua"; do
        [[ -f $afile ]] && { cp "$afile" "$ANIM_ACTIVE"; cp "$afile" "$ANIM_BACKUP" 2>/dev/null || true; break; }
      done
    fi
  fi
  if _form_on Opacity; then
    op=$(jq -r '.opacity // ""' "$file")
    [[ -n $op ]] && "$OPACITY" set "$op" >/dev/null 2>&1 || true
    blr=$(jq -r '.blur // ""' "$file")
    [[ -n $blr ]] && "$BLUR" set "$blr" >/dev/null 2>&1 || true
  fi
  sh=""
  _form_on Shader && sh=$(jq -r '.shader // ""' "$file")
  if [[ $sh == off ]]; then
    "$TOGGLE" off >/dev/null 2>&1 || true
  elif [[ -n $sh ]]; then
    "$TOGGLE" on "$sh" >/dev/null 2>&1 || true
  fi
  # Токены панелей: стиль пишет свой блок look с id стиля; пресет без look и без стиля — вид по умолчанию.
  if _form_on Look; then
    if jq -e '.look | type == "object"' "$file" >/dev/null 2>&1; then
      local look_id=""
      [[ $prefix == style ]] && look_id=$(basename "$file" .json)
      write_json_inplace "$LOOK_CFG" "$(jq --arg id "$look_id" '.look + (if $id != "" then {id: $id} else {} end)' "$file")"
    elif [[ $mode == replace && ${FORM_KEEP_LOOK:-false} != true ]]; then
      write_json_inplace "$LOOK_CFG" '{}'
    fi
  fi
  unset -f _form_on
}

# Тоггл Omarchy «без отступов»: true / false; reload сделает вызывающий.
set_no_gaps() {
  local flag="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/toggles/hypr/window-no-gaps.lua" want=$1
  if [[ $want == true && ! -f $flag ]]; then
    omarchy-hyprland-toggle window-no-gaps on >/dev/null 2>&1 || true
  elif [[ $want != true && -f $flag ]]; then
    omarchy-hyprland-toggle window-no-gaps off >/dev/null 2>&1 || true
  fi
}

# ── Стили ─────────────────────────────────────────────────────────────

# Файл стиля по id: свой (~/.config/omarchy/customizer/styles) важнее встроенного.
style_file_of() {
  local f
  for f in "$USER_STYLES/$1.json" "$STYLE_DIR/$1.json"; do
    [[ -f $f ]] && { echo "$f"; return 0; }
  done
  return 1
}

# Профиль шрифтов стиля (omarchy-font-profile из dotfiles): терминалы, fontconfig, GTK, браузер, Nihil.
apply_style_fonts() {
  local fonts
  fonts=$(jq -r '.fonts // ""' "$1" 2>/dev/null)
  [[ -n $fonts ]] && command -v omarchy-font-profile >/dev/null || return 0
  [[ $(omarchy-font-profile 2>/dev/null) == "$fonts" ]] && return 0
  omarchy-font-profile "$fonts" >/dev/null 2>&1 || true
}

# Вид приложений под стиль: GTK, терминалы (omarchy-app-themes) и Firefox (omarchy-firefox-chrome) читают
# ~/.config/omarchy/style.json. Скрипты — из dotfiles (omarchy-themes/scripts) или из PATH; нет — шаг пропускается.
refresh_app_looks() {
  local name path
  for name in omarchy-app-themes omarchy-firefox-chrome; do
    path=$(command -v "$name" 2>/dev/null || true)
    [[ -n $path ]] || path="$HOME/dotfiles/omarchy-themes/scripts/$name"
    [[ -x $path ]] && "$path" >/dev/null 2>&1 &
  done
  wait
}

# Светлая ли тема: luma фона из colors.toml (как theme_palette.py: > 0.5 — светлая).
theme_is_light() {
  local d bg
  for d in "$HOME/.config/omarchy/themes/$1" "${OMARCHY_PATH:-/usr/share/omarchy}/themes/$1"; do
    [[ -f $d/colors.toml ]] || continue
    bg=$(grep -m1 -E '^\s*background\s*=' "$d/colors.toml" | grep -oE '#[0-9a-fA-F]{6}')
    [[ -n $bg ]] || return 1
    (( (299 * 16#${bg:1:2} + 587 * 16#${bg:3:2} + 114 * 16#${bg:5:2}) / 1000 > 128 ))
    return
  done
  return 1
}

# Тема стиля по переключателю styleTheme: off — пусто; dark / light — своя из пары (нет светлой — тёмная);
# current — вариант той же яркости, что у темы сейчас.
style_theme_for() {
  local file=$1 mode dark light
  mode=$(jq -r '.styleTheme // "current"' "$STYLE_CFG" 2>/dev/null || echo current)
  dark=$(jq -r '.theme.dark // ""' "$file" 2>/dev/null)
  light=$(jq -r '.theme.light // ""' "$file" 2>/dev/null)
  [[ -n $light ]] || light=$dark
  case "$mode" in
  dark) echo "$dark" ;;
  light) echo "$light" ;;
  current) if theme_is_light "$(theme_name)"; then echo "$light"; else echo "$dark"; fi ;;
  esac
}

style_summary() {
  jq -r '[
    (if .hyprGeometry then "corners " + (.hyprGeometry.rounding | tostring) + (if .hyprGeometry.shadow then " · shadow" else "" end) else empty end),
    (if .barSkin then "bar: " + .barSkin elif .barSkinData then "bar: custom" else empty end),
    (if .lock.design then "lock: " + .lock.design else empty end),
    (if .launcher.skin then "launcher: " + .launcher.skin else empty end),
    (if .opacity then "opacity: " + .opacity else empty end),
    (if .blur then "blur: " + .blur else empty end),
    (if .anims and .anims != "" then "anims: " + .anims else empty end),
    (if .fonts then "fonts: " + .fonts else empty end),
    (if (.theme | type) == "object" then "themes: " + .theme.dark + " / " + (.theme.light // .theme.dark) else empty end)
  ] | join("  ·  ")' "$1" 2>/dev/null
}

# Совпадает ли стиль с текущим видом — по разделам, которые он применяет.
style_matches() {
  local f=$1 v checked=false
  if style_on styleBar; then
    v=$(jq -r '.barSkin // ""' "$f" 2>/dev/null)
    if [[ -n $v && -f $BAR_DIR/manifest.json ]]; then [[ $v == "$(current_skin)" ]] || return 1; checked=true; fi
    if jq -e '.barSkinData | type == "object"' "$f" >/dev/null 2>&1; then
      [[ $(jq -S '.barSkinData | with_entries(select(.key | test("^note(_[a-z]+)?$") | not))' "$f") == "$(skin_canon "$BAR_SKIN")" ]] || return 1
      checked=true
    fi
  fi
  if style_on styleLock; then
    v=$(jq -r '.lock.design // ""' "$f" 2>/dev/null)
    if [[ -n $v && -f $LOCK_PLUGIN/manifest.json ]]; then [[ $v == "$(lock_current)" ]] || return 1; checked=true; fi
  fi
  if style_on styleOpacity; then
    v=$(jq -r '.opacity // ""' "$f" 2>/dev/null)
    if [[ -n $v ]]; then [[ $v == "$("$OPACITY" current 2>/dev/null)" ]] || return 1; checked=true; fi
  fi
  $checked
}

current_style_stem() {
  local saved f
  if [[ -s $ACTIVE_STYLE ]]; then
    saved=$(<"$ACTIVE_STYLE")
    if f=$(style_file_of "$saved") && style_matches "$f"; then
      echo "$saved"
      return
    fi
  fi
  for f in "$USER_STYLES"/*.json "$STYLE_DIR"/*.json; do
    [[ -f $f ]] || continue
    if style_matches "$f"; then
      basename "$f" .json
      return
    fi
  done
  echo custom
}

current_style_label() {
  local stem f
  stem=$(current_style_stem)
  if [[ $stem != custom ]] && f=$(style_file_of "$stem"); then preset_name_of "$f"; else echo custom; fi
}

apply_style() {
  local file=$1 label
  [[ -f $file ]] || { notify-send -u critical "Styles" "$(t "Style not found: %s" "$file")"; exit 1; }
  label=$(preset_name_of "$file")
  notify-send -t 3000 "Styles" "$(t "Applying style %s…" "$label")"
  # Та же резервная копия, что у пресетов: Presets → «Восстановить прежнюю настройку».
  if [[ ! -s $LAST_PRESET ]] || [[ $(current_preset_stem) == custom && $(current_style_stem) == custom ]]; then
    snapshot_preset "$LAST_PRESET" "$(t "Previous setup")" \
      "$(t "Automatic backup before applying %s (%s)" "$label" "$(date '+%F %H:%M')")"
  fi
  # Тема — первой: её хуки пересобирают GTK / Firefox / терминалы, форма стиля ложится поверх.
  local theme
  theme=$(style_theme_for "$file")
  if [[ -n $theme && $theme != "$(theme_name)" ]]; then
    if theme_exists "$theme"; then
      omarchy theme set "$theme"
    else
      notify-send -u critical "Styles" "$(t "Theme %s is not installed — the style is applied without it." "$theme")"
    fi
  fi
  apply_form_sections "$file" "$STYLE_CFG" style false merge
  style_on styleFonts && apply_style_fonts "$file"
  style_on styleLook && refresh_app_looks
  hyprctl reload >/dev/null 2>&1 || true
  restore
  basename "$file" .json >"$ACTIVE_STYLE"
  notify-send -t 3000 "Styles" "$(t "Applied style: %s" "$label")"
}

save_user_style() {
  local raw slug file note tmp="$RUN_DIR/style-snapshot.json" fonts=""
  raw=$(zenity --entry --title="$(t "Save style")" --text="$(t "Style name:")" \
    --entry-text="My Style" 2>/dev/null) || return 0
  slug=$(tr '[:upper:] ' '[:lower:]-' <<<"$raw" | tr -cd 'a-z0-9_-')
  [[ -n $slug ]] || slug="style-$(date +%Y%m%d-%H%M%S)"
  file="$USER_STYLES/$slug.json"
  if [[ -e $file ]]; then
    zenity --question --title="$(t "Save style")" --text="$(t "Style %s already exists. Overwrite?" "$slug")" 2>/dev/null || return 0
  fi
  note=$(zenity --entry --title="$(t "Save style")" --text="$(t "Description (optional):")" 2>/dev/null) || note=""
  command -v omarchy-font-profile >/dev/null && fonts=$(omarchy-font-profile 2>/dev/null)
  snapshot_preset "$tmp" "$raw" "$note"
  mkdir -p "$USER_STYLES"
  # Стиль — только форма: без темы, обоев и «содержимого» (какие виджеты видны, формат часов, громкость).
  jq --arg fonts "$fonts" 'del(.theme, .wallpaper, .style,
      .widgets.clock, .widgets.media, .widgets.visualizer, .widgets.sysinfo, .widgets.edgeHover,
      .widgets.dashMedia, .widgets.dashCalendar, .widgets.dashWeather, .widgets.dashStats,
      .lock.clock24, .lock.showSeconds, .lock.showDate, .sounds.sounds, .sounds.soundVolume,
      .imagePicker.autoCache, .glyph.glyphCharger, .glyph.glyphCriticalRed, .osd.osdShowValue, .look.id)
    + (if $fonts != "" then {fonts: $fonts} else {} end)' "$tmp" >"$tmp.out" \
    && cp "$tmp.out" "$file"
  basename "$file" .json >"$ACTIVE_STYLE"
  notify-send -t 3000 "Styles" "$(t "Saved %s" "$raw")"
}

delete_user_style() {
  local file=$1 name
  [[ -f $file && $(dirname "$(realpath "$file")") == "$(realpath -m "$USER_STYLES")" && $file == *.json ]] || {
    notify-send -u critical "Styles" "$(t "Only your own styles (★) can be deleted")"; return 1; }
  name=$(preset_name_of "$file")
  zenity --question --title="$(t "Delete style")" \
    --text="$(t "Delete your style %s? The file goes to the trash." "$name")" 2>/dev/null || return 0
  gio trash "$file" && notify-send -t 3000 "Styles" "$(t "Deleted %s" "$name")"
}

save_user_preset() {
  local raw slug file note
  raw=$(zenity --entry --title="$(t "Save preset")" --text="$(t "Preset name:")" \
    --entry-text="My Preset" 2>/dev/null) || return 0
  slug=$(tr '[:upper:] ' '[:lower:]-' <<<"$raw" | tr -cd 'a-z0-9_-')
  [[ -n $slug ]] || slug="preset-$(date +%Y%m%d-%H%M%S)"
  file="$USER_PRESETS/$slug.json"
  if [[ -e $file ]]; then
    zenity --question --title="$(t "Save preset")" --text="$(t "Preset %s already exists. Overwrite?" "$slug")" 2>/dev/null || return 0
  fi
  note=$(zenity --entry --title="$(t "Save preset")" --text="$(t "Description (optional):")" 2>/dev/null) || note=""
  mkdir -p "$USER_PRESETS"
  snapshot_preset "$file" "$raw" "$note"
  basename "$file" .json >"$ACTIVE_PRESET"
  notify-send -t 3000 "Presets" "$(t "Saved %s" "$raw")"
}

delete_user_preset() {
  local file=$1 name
  [[ -f $file && $(dirname "$(realpath "$file")") == "$(realpath "$USER_PRESETS")" && $file == *.json && $(basename "$file") != "my-settings.json" ]] || {
    notify-send -u critical "Presets" "$(t "Only your own presets (★) can be deleted")"; return 1; }
  name=$(preset_name_of "$file")
  zenity --question --title="$(t "Delete preset")" \
    --text="$(t "Delete your preset %s? The file goes to the trash." "$name")" 2>/dev/null || return 0
  gio trash "$file" && notify-send -t 3000 "Presets" "$(t "Deleted %s" "$name")"
}

launcher_current() { jq -r '.skin // "constellation"' "$MENU_CFG" 2>/dev/null || echo constellation; }

launcher_skins() {
  [[ -f $MENU_PLUGIN/SkinConfig.qml ]] || return 0
  # "list" — стоковый список меню, файла скина у него нет; остальные — ключи files в SkinConfig.qml.
  echo "list"
  awk -F'"' '/^    "[a-z0-9-]+":/ { print $2 }' "$MENU_PLUGIN/SkinConfig.qml"
}

launcher_skin_desc() {
  case "$1" in
  nihil) t "NIHIL hardware bump with concave fillets, monochrome app grid, > actions and = LED calculator" ;;
  paper) t "Sketchbook page: polaroid cards on a ruled sheet, pencil circle, tape and a sticky note" ;;
  list) t "Stock Omarchy compact list card" ;;
  board) t "Tactile keycap board grid" ;;
  constellation) t "Starfield constellation launcher" ;;
  terminal) t "Minimalist terminal prompt launcher" ;;
  *-hack) t "Minimalist terminal-style hack variant of %s" "${1%-hack}" ;;
  *-term) t "Terminal-palette variant of %s" "${1%-term}" ;;
  *) t "Launcher skin: %s" "$1" ;;
  esac
}

glyph_status() {
  [[ $(jq -r '.glyphEnabled // false' "$GLYPH_CFG" 2>/dev/null) == true ]] && echo on || echo off
}

list() {
  case "$1" in
  presets)
    local f cur stem label
    cur=$(current_preset_stem)
    printf '%s\t%s\t\t0\t%s\n' "$(t "💾 Save current setup as a preset…")" "save" \
      "$(t "Snapshot your active theme, wallpaper, bar, animations, opacity, blur, lock screen, launcher, widgets, OSD, notifications, sounds and Glyph into %s." "${USER_PRESETS/#$HOME/\~}")"
    if [[ -s $LAST_PRESET ]]; then
      printf '%s\t%s\t%s\t0\t%s\t%s\n' "$(t "↩ Restore previous setup")" "$LAST_PRESET" "$LAST_PRESET" \
        "$(note_of "$LAST_PRESET")" "$(preset_summary "$LAST_PRESET")"
    fi
    for f in "$USER_PRESETS"/*.json; do
      [[ -f $f ]] || continue
      stem=$(basename "$f" .json)
      label=$(preset_name_of "$f")
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "★ $label" "$f" "$f" \
        "$([[ $stem == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")"'\n\n'"$(preset_summary "$f")"'\n\n'"$(t "Your preset: %s" "${f/#$HOME/\~}")" \
        "$(preset_summary "$f")"
    done
    for f in "$PRESET_DIR"/*.json; do
      [[ -f $f ]] || continue
      stem=$(basename "$f" .json)
      label=$(preset_name_of "$f")
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$label" "$f" "$f" \
        "$([[ $stem == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")"'\n\n'"$(preset_summary "$f")" \
        "$(preset_summary "$f")"
    done
    list_tweaks PRESET_TWEAKS "$PRESET_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    list_tweaks WINDOW_TWEAKS "$WINDOW_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    printf '%s\t%s\t\t0\t%s\n' "$(t "↺ Reset window geometry")" "geometry-reset" \
      "$(t "Drop gaps, borders, rounding and shadow set by a preset and return to your Hyprland config. Now: %s" "$(geometry_summary)")"
    ;;
  sounds)
    # Пакеты (⏎ — выбрать, p — послушать), переключатели sounds.json, проверка событий текущим пакетом.
    local pack cur ev
    cur=$(jq -r '.soundPack // "theme"' "$SOUND_CFG" 2>/dev/null || echo theme)
    printf '%s\t%s\t\t0\t\theader\n' "$(t "Sound packs")" "section:Sound packs"
    while read -r pack; do
      printf '%s\t%s\t\t%s\t%s\t%s\n' "$pack" "pack:$pack" "$([[ $pack == "$cur" ]] && echo 1 || echo 0)" \
        "$(sound_pack_desc "$pack")"'\n\n'"$(t "⏎ — use this pack · p — listen without switching")" "$(sound_pack_desc "$pack")"
    done < <(sound_packs)
    list_tweaks SOUND_TWEAKS "$SOUND_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } $2 != "soundPack" { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    printf '%s\t%s\t\t0\t\theader\n' "$(t "Test events")" "section:Test events"
    for ev in "${SOUND_EVENTS[@]}"; do
      printf '%s\t%s\t\t0\t%s\n' "▶ $ev" "test:$ev" "$(t "⏎ or p — play «%s» with the current pack" "$ev")"
    done
    ;;
  fonts)
    # Профили omarchy-font-profile, сгруппированные по стилям. sub — «sans · mono · title» (по нему
    # сцена шрифтов рисует образцы).
    command -v omarchy-font-profile >/dev/null || return 0
    local cur name desc group sans mono title last=""
    cur=$(omarchy-font-profile)
    while IFS=$'\t' read -r name desc group sans mono title; do
      if [[ $group != "$last" ]]; then
        printf '%s\t%s\t\t0\t\theader\n' "$(t "$(font_group_title "$group")")" "section:$group"
        last=$group
      fi
      printf '%s\t%s\t\t%s\t%s\t%s\n' "$name" "$name" "$([[ $name == "$cur" ]] && echo 1 || echo 0)" \
        "$(t "$desc")" "$sans · $mono · ${title:-$sans}"
    done < <(omarchy-font-profile list)
    ;;
  styles)
    local f cur stem label
    cur=$(current_style_stem)
    printf '%s\t%s\t\t0\t%s\n' "$(t "💾 Save current look as a style…")" "save" \
      "$(t "Snapshot the form of your desktop without colours — window geometry, bar, lock screen, launcher, widgets, OSD, notifications, animations, opacity, blur, sounds, Glyph and fonts — into %s. It works on any theme." "${USER_STYLES/#$HOME/\~}")"
    for f in "$USER_STYLES"/*.json; do
      [[ -f $f ]] || continue
      stem=$(basename "$f" .json)
      label=$(preset_name_of "$f")
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "★ $label" "$f" "$f" \
        "$([[ $stem == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")"'\n\n'"$(style_summary "$f")"'\n\n'"$(t "Your style: %s" "${f/#$HOME/\~}")" \
        "$(style_summary "$f")"
    done
    for f in "$STYLE_DIR"/*.json; do
      [[ -f $f ]] || continue
      stem=$(basename "$f" .json)
      label=$(preset_name_of "$f")
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$label" "$f" "$f" \
        "$([[ $stem == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")"'\n\n'"$(style_summary "$f")" \
        "$(style_summary "$f")"
    done
    list_tweaks STYLE_TWEAKS "$STYLE_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    ;;
  dotify)
    local dir cur_bg
    dir=$(walls_dir)
    cur_bg=$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true)
    printf '%s\t%s\t%s\t0\t%s\n' "$(t "⚡ Dotify current wallpaper")" "current" "$cur_bg" \
      "$(t "Convert the active wallpaper into an LED dot-matrix wallpaper at your monitor's native resolution and apply it.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "󰣇 Generate Arch Linux LED wallpaper")" "arch" \
      "$(t "Render the Arch Linux glyph on an LED dot-matrix grid for your monitor resolution and apply it.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "📂 Dotify a whole folder…  (O)")" "pick-dir" \
      "$(t "Pick a folder; every image directly in it is converted into an LED dot-matrix wallpaper for the current theme.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "🖼 Dotify image(s) from anywhere…  (o)")" "pick-files" \
      "$(t "Pick one or more images (Ctrl/Shift-click) from any folder to convert into LED dot-matrix wallpapers.")"
    list_tweaks DOTIFY_TWEAKS "$DOTIFY_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    printf '%s\t%s\t\t0\t\theader\n' "$(t "Source images")" "section:Source images"
    images_in "$dir" 10 | while read -r f; do
      printf '%s\t%s\t%s\t0\n' "${f#"$dir"/}" "$f" "$f"
    done
    ;;
  glyph)
    printf '%s\t%s\t\t0\t%s\n' "$(t "⚡ Test notification sweep  (p)")" "test:normal" \
      "$(t "Run a single perimeter Glyph light sweep around the screen.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "🔴 Test critical alert sweep")" "test:critical" \
      "$(t "Run a double signal-red perimeter Glyph sweep around the screen.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "🔋 Test charger rising beams")" "test:charge" \
      "$(t "Run dual rising light beams from the bottom corners.")"
    list_tweaks GLYPH_TWEAKS "$GLYPH_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    ;;
  launcher)
    local cur sk
    cur=$(launcher_current)
    printf '%s\t%s\t\t0\t%s\n' "$(t "🚀 Open launcher  (p)")" "open" \
      "$(t "Open the application launcher with the active skin.")"
    list_tweaks LAUNCHER_TWEAKS "$MENU_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    printf '%s\t%s\t\t0\t\theader\n' "$(t "Skins")" "section:Skins"
    launcher_skins | awk '!seen[$0]++' | while read -r sk; do
      [[ -n $sk ]] || continue
      printf '%s\t%s\t\t%s\t%s\n' "$sk" "skin:$sk" "$([[ $sk == "$cur" ]] && echo 1 || echo 0)" \
        "$(launcher_skin_desc "$sk")"'\n\n'"$(t "⏎ — select · p — open launcher")"
    done
    ;;
  anims)
    # Snapshot what is in use (empty file = nothing picked yet, Hyprland's own config);
    # previews overwrite it until anim-restore.
    if [[ -f $ANIM_ACTIVE ]]; then cp "$ANIM_ACTIVE" "$ANIM_BACKUP"; else : >"$ANIM_BACKUP"; fi
    anim_files | while read -r f; do
      local cur=0
      cmp -s "$f" "$ANIM_ACTIVE" && cur=1
      printf '%s\t%s\t%s\t%s\n' "$(basename "$f" .lua)" "$f" "$f" "$cur"
    done
    ;;
  bar-layouts)
    local f cur
    cur=$(current_layout)
    printf '%s\t%s\t\t0\t%s\n' "$(t "💾 Save the current one as a preset…")" "save" \
      "$(t "Save the layout from shell.json as your own in %s — it shows up here with a ★." "${USER_LAYOUTS/#$HOME/\~}")"
    for f in "$USER_LAYOUTS"/*.json; do
      [[ -f $f ]] || continue
      printf '%s\t%s\t%s\t%s\t%s\n' "★ $(basename "$f" .json)" "$f" "$f" \
        "$([[ $(basename "$f" .json) == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")  ·  $(layout_summary "$f")"'\n\n'"$(t "Your layout: %s" "${f/#$HOME/\~}")"
    done
    for f in "$BAR_DIR"/layouts/*.json; do
      [[ -f $f ]] || continue
      printf '%s\t%s\t%s\t%s\t%s\n' "$(basename "$f" .json)" "$f" "$f" \
        "$([[ $(basename "$f" .json) == "$cur" ]] && echo 1 || echo 0)" \
        "$(note_of "$f")  ·  $(layout_summary "$f")"
    done
    ;;
  bar-skins)
    # Снимок того, что сейчас на баре; превью перезаписывают его до bar-skins-restore.
    if [[ -s $BAR_SKIN ]]; then cp "$BAR_SKIN" "$SKIN_BACKUP"; else echo '{}' >"$SKIN_BACKUP"; fi
    jq -r '.bar.transparent // false' "$SHELL_JSON" >"$TRANSPARENT_BACKUP"
    local f cur
    cur=$(current_skin)
    printf '%s\t%s\t%s\t0\t%s\n' "$(t "💾 Save the current skin…")" "save" "$SKIN_BACKUP" \
      "$(t "Save what is on the bar now as your own skin in %s — it shows up here with a ★." "${USER_SKINS/#$HOME/\~}")"
    for f in "$USER_SKINS"/*.json; do
      [[ -f $f ]] || continue
      printf '%s\t%s\t%s\t%s\t%s\n' "★ $(basename "$f" .json)" "$f" "$f" \
        "$([[ $(basename "$f" .json) == "$cur" ]] && echo 1 || echo 0)" "$(note_of "$f")"'\n\n'"$(t "Your skin: %s" "${f/#$HOME/\~}")"
    done
    for f in "$BAR_DIR"/skins/*.json; do
      [[ -f $f ]] || continue
      printf '%s\t%s\t%s\t%s\t%s\n' "$(basename "$f" .json)" "$f" "$f" \
        "$([[ $(basename "$f" .json) == "$cur" ]] && echo 1 || echo 0)" "$(note_of "$f")"
    done
    ;;
  bar-tweaks) list_tweaks TWEAKS "$BAR_SKIN" ;;
  bar-widgets) list_bar_widgets ;;
  lock-tweaks) list_tweaks LOCK_TWEAKS "$LOCK_CFG" ;;
  widgets)
    list_tweaks WIDGET_TWEAKS "$WIDGET_CFG"
    list_tweaks NIHIL_TWEAKS "$NIHIL_CFG"
    ;;
  dashboard) list_tweaks DASH_TWEAKS "$WIDGET_CFG" ;;
  osd) list_tweaks OSD_TWEAKS "$OSD_CFG" ;;
  notifications)
    list_tweaks NOTIFY_TWEAKS "$NOTIFY_CFG"
    return 0
    ;;
  wallpaper-fx)
    # Сначала настройки (строки tweak:<key>), потом эффекты.
    list_tweaks FX_TWEAKS "$FX_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    local cur e desc
    cur=$(jq -r '.type // "slant"' "$FX_CFG" 2>/dev/null || echo slant)
    while IFS='|' read -r e desc; do
      printf '%s\t%s\t\t%s\t%s\n' "$e" "$e" "$([[ $e == "$cur" ]] && echo 1 || echo 0)" "$(t "$desc")"'\n\n'"$(t "⏎ — select · p — play it on the desktop")"
    done <<'EFFECTS'
slant|Slanted wipe from the centre — stock Omarchy
fade|Smooth cross-fade
wipe|Wipe along the “Angle”
wave|Wipe with a wavy edge
grow|A circle grows from a point (center / cursor / random)
outer|A circle shrinks to a point — the new wallpaper comes from the edges
diamond|A diamond from a point
clock|Radial sweep, like a clock hand
blinds|Blinds
doors|Doors opening from the middle
mosaic|Squares in random order
dissolve|Pixel noise
pixelize|Pixels grow and shrink back
ripple|Ripples on water
swirl|Swirl into the centre
crosszoom|Radial blur with zoom
slide|The new wallpaper pushes the old one out (along the “Angle”)
zoom|The old one flies forward, the new one fades in
glitch|Torn stripes and channel split
burn|Burns through in spots with a glowing edge
waterdrop|A drop: waves from a point, fading out
hexagon|Honeycomb opening from the centre
random|A random effect every time
none|No animation
EFFECTS
    ;;
  theme-switcher)
    printf '%s\t%s\t\t0\t%s\n' "$(t "⚡ Cache thumbnails")" "cache" \
      "$(t "Make thumbnails for the theme switcher (all themes) and for the current theme's wallpapers ahead of time, so the pickers open instantly.")"'\n\n'"$(t "Cache: %s" "$PICKER_CACHE ($(command du -sh "$PICKER_CACHE" 2>/dev/null | cut -f1))")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "🧹 Clean up unused thumbnails")" "prune" \
      "$(t "Delete thumbnails of images that are gone or have changed. Thumbnails of existing images stay.")"'\n\n'"$(picker_prune --dry-run 2>/dev/null)"
    list_tweaks PICKER_TWEAKS "$PICKER_CFG" | awk -F'\t' 'BEGIN { OFS = "\t" } { if ($2 !~ /^section:/) $2 = "tweak:" $2; print }'
    local cur st desc
    cur=$(jq -r '.style // "slices"' "$PICKER_CFG" 2>/dev/null || echo slices)
    while IFS='|' read -r st desc; do
      printf '%s\t%s\t\t%s\t%s\n' "$st" "style:$st" "$([[ $st == "$cur" ]] && echo 1 || echo 0)" "$(t "$desc")"'\n\n'"$(t "⏎ — select · p — open the theme switcher")"
    done <<'STYLES'
slices|Slanted slices — stock Omarchy
cards|Even rounded cards
coverflow|Neighbours turned in 3D, like iTunes
strip|A strip of equal cards, the selected one bigger
wide|A huge preview and thin slices
polaroid|Cards in a white frame with a caption
STYLES
    ;;
  lock)
    local cur id name file thumb
    cur=$(lock_current)
    printf '%s\t%s\t\t0\t%s\n' "$(t "🔄 Refresh previews of all designs  (T)")" "regen-thumbs" \
      "$(t "Each design shows on screen in turn (≈1.5 s each) and is captured in the current theme's colours.")"
    jq -r --arg l "$UI_LANG" '.[] | [.id, .name, (.["description_" + $l] // .description), (.tags | join(" · "))] | @tsv' "$LOCK_PLUGIN/designs/designs.json" |
      while IFS=$'\t' read -r id name desc tags; do
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$id" "$LOCK_THUMBS/$(lock_thumb_name "$id").jpg" \
          "$([[ $id == "$cur" ]] && echo 1 || echo 0)" "$desc"'\n\n'"$(t "p — show it live · ⏎ — select")" "$tags"
      done
    # Свои дизайны: ~/.config/omarchy/lock-designs/*.qml, id my:<файл>.
    for file in "$LOCK_USER_DIR"/*.qml; do
      [[ -f $file ]] || continue
      name=$(basename "$file")
      id="my:$name"
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "${name%.qml}" "$id" "$LOCK_THUMBS/$(lock_thumb_name "$id").jpg" \
        "$([[ $id == "$cur" ]] && echo 1 || echo 0)" "$(t "Your design: %s" "$file")"'\n\n'"$(t "p — show it live · ⏎ — select")" "custom"
    done
    ;;
  themes)
    local current dir slug label
    current=$(theme_name)
    # Тема «dynamic» из текущих обоев — если установлен omarchy-wallpaper-theme (matugen)
    if command -v omarchy-wallpaper-theme >/dev/null; then
      local scheme
      for scheme in tonal-spot vibrant expressive fruit-salad monochrome light; do
        printf '%s\t%s\t\t0\t%s\n' "$(t "🎨 Theme from wallpaper: %s" "$scheme")" "dynamic:$scheme" \
          "$(t "Build the “dynamic” theme from the current wallpaper with matugen (Material You) and apply it.")"
      done
    fi
    {
      find -L "$HOME/.config/omarchy/themes" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null
      find "$OMARCHY_PATH/themes" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null
    } | sort -u | while read -r slug; do
      dir="$HOME/.config/omarchy/themes/$slug"
      [[ -d $dir ]] || dir="$OMARCHY_PATH/themes/$slug"
      label=$(sed -E 's/(^|-)([a-z])/\1\u\2/g; s/-/ /g' <<<"$slug")
      printf '%s\t%s\t%s\t%s\t%s\n' "$label" "$slug" "$(theme_preview "$dir")" "$([[ $slug == "$current" ]] && echo 1 || echo 0)" "$(theme_palette "$dir")"
    done
    ;;
  theme-walls)
    # Как omarchy-bg-browser (SUPER+CTRL+SPACE): категории — подпапки
    # ~/.config/omarchy/backgrounds/<тема>. $2 — путь внутри неё ("" — корень).
    # Строки папок: value "dir:<путь>", превью — первая картинка папки.
    local rel=${2:-} root dir bg cur_bg sub n first name cur parent
    [[ $rel == *..* || $rel == /* ]] && rel=""
    root="$HOME/.config/omarchy/backgrounds/$(theme_name)"
    dir="$root${rel:+/$rel}"
    cur_bg=$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null)
    if [[ -n $rel ]]; then
      parent=${rel%/*}
      [[ $parent == "$rel" ]] && parent=""
      printf '%s\t%s\t\t0\t%s\t%s\n' "󰁝  .." "dir:$parent" "$(t "Back: %s" "${parent:-$(t "all categories")}")" "$rel"
    fi
    if [[ -d $dir ]]; then
      while IFS= read -r -d '' sub; do
        n=$(find -L "$sub" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.gif' -o -iname '*.bmp' \) \
          -not -name '.*' 2>/dev/null | wc -l)
        ((n > 0)) || continue
        name=${sub##*/}
        first=$(images_in "$sub" 10 | head -n 1)
        cur=0
        [[ $cur_bg == "$(readlink -f "$sub")"/* ]] && cur=1
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "󰉋  $name" "dir:${rel:+$rel/}$name" "$first" "$cur" \
          "$(t "Category — wallpapers: %s" "$n")"'\n\n'"$(t "⏎ — open · h — back")" "$(t "wallpapers: %s" "$n")"
      done < <(find -L "$dir" -mindepth 1 -maxdepth 1 -type d -not -name '.*' -print0 2>/dev/null | sort -z)
      images_in "$dir" 1 | while read -r f; do
        printf '%s\t%s\t%s\t%s\n' "$(basename "$f")" "$f" "$f" "$([[ $(readlink -f "$f") == "$cur_bg" ]] && echo 1 || echo 0)"
      done
    fi
    # В корне — ещё и собственные обои темы, как в стоковом switcher.
    if [[ -z $rel ]]; then
      bg="$HOME/.config/omarchy/themes/$(theme_name)/backgrounds"
      [[ -d $bg ]] || bg="$HOME/.local/state/omarchy/current/theme/backgrounds"
      images_in "$bg" 1 | while read -r f; do
        printf '%s\t%s\t%s\t%s\n' "$(basename "$f")" "$f" "$f" "$([[ $(readlink -f "$f") == "$cur_bg" ]] && echo 1 || echo 0)"
      done
    fi
    ;;
  walls)
    local dir
    dir=$(walls_dir)
    printf '%s\t%s\t\t0\t%s\n' "$(t "📂 Recolor a whole folder…  (O)")" "pick-dir" \
      "$(t "Pick a folder; every image directly in it is recolored into the theme's backgrounds.")"
    printf '%s\t%s\t\t0\t%s\n' "$(t "🖼 Recolor image(s) from anywhere…  (o)")" "pick-files" \
      "$(t "Pick one or more images (Ctrl/Shift-click) from any folder.")"
    images_in "$dir" 10 | while read -r f; do
      printf '%s\t%s\t%s\t0\n' "${f#"$dir"/}" "$f" "$f"
    done
    ;;
  shaders)
    local cur
    cur=$(current_shader)
    printf '%s\t%s\t\t0\n' "$(t "⏻ Toggle shader (now: %s)" "$cur")" "toggle"
    printf '%s\t%s\t\t0\n' "$(t "⏭ Next shader")" "next"
    "$TOGGLE" list | while read -r f; do
      local n
      n=$(basename "$f" .frag)
      printf '%s\t%s\t%s\t%s\n' "$n" "$n" "$f" "$([[ $n == "$cur" ]] && echo 1 || echo 0)"
    done
    ;;
  opacity)
    local n a i cur
    "$OPACITY" list | while read -r n a i cur; do
      printf '%s\t%s\t\t%s\t%s\n' "$n  ($a / $i)" "$n" "$cur" \
        "active_opacity = $a · inactive_opacity = $i"
    done
    ;;
  blur)
    local n sz ps v no cur
    "$BLUR" list | while read -r n sz ps v no cur; do
      if ((sz == 0)); then
        printf '%s\t%s\t\t%s\t%s\n' "$n  ($(t "no blur"))" "$n" "$cur" "size 0 passes 0 vibrancy 0 noise 0"
      else
        printf '%s\t%s\t\t%s\t%s\n' "$n  ($sz × $ps)" "$n" "$cur" "size $sz passes $ps vibrancy $v noise $no"
      fi
    done
    ;;
  esac
}

apply() {
  local category=$1 value=$2
  case "$category" in
  presets)
    case "$value" in
    save) save_user_preset ;;
    tweak:window*) tweak "${value#tweak:}" pick; hyprctl reload >/dev/null 2>&1 ;;
    tweak:*) tweak "${value#tweak:}" pick ;;
    geometry-reset) geometry_reset ;;
    *) apply_preset "$value" ;;
    esac
    ;;
  fonts)
    [[ $value == section:* ]] || omarchy-font-profile "$value" >/dev/null 2>&1 || true
    ;;
  sounds)
    case "$value" in
    pack:*)
      write_json_inplace "$SOUND_CFG" "$(jq --arg p "${value#pack:}" '.soundPack = $p' <<<"$(read_json_or_empty "$SOUND_CFG")")"
      "$PLAY_SOUND" notify --force
      ;;
    test:*) "$PLAY_SOUND" "${value#test:}" --force ;;
    tweak:*) tweak "${value#tweak:}" pick ;;
    esac
    ;;
  styles)
    case "$value" in
    save) save_user_style ;;
    tweak:*) tweak "${value#tweak:}" pick ;;
    *) apply_style "$value" ;;
    esac
    ;;
  dotify)
    local picked
    case "$value" in
    tweak:*) tweak "${value#tweak:}" pick ;;
    current)
      picked=$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true)
      [[ -f $picked ]] || { notify-send -u critical "Dotify" "$(t "No active wallpaper found")"; exit 1; }
      dotify_files "$picked"
      ;;
    arch) dotify_glyph "󰣇" "arch" ;;
    pick-dir)
      picked=$(zenity --file-selection --directory --title="$(t "Folder to dotify")" \
        --filename="$(walls_dir)/" 2>/dev/null) || exit 0
      local -a dfiles
      mapfile -t dfiles < <(images_in "$picked" 1)
      dotify_files "${dfiles[@]}"
      ;;
    pick-files)
      picked=$(zenity --file-selection --multiple --separator=$'\n' --title="$(t "Image(s) to dotify")" \
        --filename="$(walls_dir)/" \
        --file-filter="Images | *.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP" 2>/dev/null) || exit 0
      local -a list
      mapfile -t list <<<"$picked"
      dotify_files "${list[@]}"
      ;;
    *) dotify_files "$value" ;;
    esac
    ;;
  glyph)
    case "$value" in
    tweak:*) tweak "${value#tweak:}" pick ;;
    test:normal) omarchy-shell -q glyph test false >/dev/null 2>&1 ;;
    test:critical) omarchy-shell -q glyph test true >/dev/null 2>&1 ;;
    test:charge) omarchy-shell -q glyph charge >/dev/null 2>&1 ;;
    esac
    ;;
  launcher)
    case "$value" in
    tweak:*) tweak "${value#tweak:}" pick ;;
    open) setsid -f omarchy-menu toggle apps >/dev/null 2>&1 ;;
    skin:*)
      mkdir -p "$(dirname "$MENU_CFG")"
      TW_FILE="$MENU_CFG"
      skin_edit --arg s "${value#skin:}" '.skin = $s'
      notify-send -t 2000 "Launcher" "$(t "Skin: %s" "${value#skin:}")"
      ;;
    esac
    ;;
  anims)
    cp "$value" "$ANIM_ACTIVE"
    cp "$value" "$ANIM_BACKUP"
    hyprctl reload >/dev/null 2>&1
    notify-send -t 2000 "Animations" "$(t "Loaded: %s" "$(basename "$value" .lua)")"
    ;;
  bar-layouts)
    if [[ $value == save ]]; then save_user_layout; exit 0; fi
    # shell.json перечитывается на лету, рестарт шелла не нужен (он убил бы и overlay).
    # Остальное (idle, bar.id, transparent) не трогаем; клоны страхуем в .plugins.
    shell_apply_layout "$value"
    notify-send -t 2000 "Bar Layout" "$(t "Applied %s" "$(basename "$value" .json)")"
    ;;
  bar-skins)
    if [[ $value == save ]]; then save_user_skin; exit 0; fi
    bar_skin_preview "$value"
    cp "$BAR_SKIN" "$SKIN_BACKUP"
    notify-send -t 2000 "Bar Skin" "$(t "Applied %s" "$(basename "$value" .json)")"
    ;;
  bar-tweaks | lock-tweaks | widgets | dashboard | osd | notifications) tweak "$value" pick ;;
  wallpaper-fx)
    if [[ $value == tweak:* ]]; then tweak "${value#tweak:}" pick; exit 0; fi
    TW_FILE="$FX_CFG"
    skin_edit --arg t "$value" '.type = $t'
    notify-send -t 2000 "Wallpaper FX" "$(t "Transition: %s" "$value")"
    ;;
  theme-switcher)
    case "$value" in
    tweak:*) tweak "${value#tweak:}" pick ;;
    cache) picker_cache ;;
    prune)
      local info
      info=$(picker_prune --dry-run)
      zenity --question --title="$(t "Thumbnail cache")" --text="$info\n\n$(t "Delete?")" 2>/dev/null || exit 0
      notify-send -t 4000 "Theme Switcher" "$(picker_prune)"
      ;;
    style:*)
      TW_FILE="$PICKER_CFG"
      skin_edit --arg s "${value#style:}" '.style = $s'
      notify-send -t 2000 "Theme Switcher" "$(t "Style: %s" "${value#style:}")"
      ;;
    esac
    ;;
  lock)
    if [[ $value == regen-thumbs ]]; then lock_thumbs; exit 0; fi
    lock_edit --arg d "$value" '.design = $d'
    notify-send -t 2000 "Lock" "$(t "Design: %s" "$value")"
    ;;
  themes)
    if [[ $value == dynamic:* ]]; then
      local -a opts=(--scheme "${value#dynamic:}")
      [[ $value == dynamic:light ]] && opts=(--mode light)
      notify-send -t 3000 "Theme" "$(t "Building a theme from the wallpaper…")"
      omarchy-wallpaper-theme "${opts[@]}" || { notify-send -u critical "Theme" "$(t "matugen failed")"; exit 1; }
      notify-send -t 3000 "Theme" "$(t "Applied %s" dynamic)"
      exit 0
    fi
    notify-send -t 3000 "Theme" "$(t "Applying %s…" "$value")"
    omarchy theme set "$value"
    notify-send -t 3000 "Theme" "$(t "Applied %s" "$value")"
    ;;
  theme-walls)
    omarchy theme bg set "$value"
    notify-send -t 3000 "Wallpaper" "$(t "Applied %s" "$(basename "$value")")"
    ;;
  walls)
    local picked
    case "$value" in
    pick-dir)
      picked=$(zenity --file-selection --directory --title="$(t "Folder to recolor")" \
        --filename="$(walls_dir)/" 2>/dev/null) || exit 0
      recolor "$picked"
      ;;
    pick-files)
      picked=$(zenity --file-selection --multiple --separator=$'\n' --title="$(t "Image(s) to recolor")" \
        --filename="$(walls_dir)/" \
        --file-filter="Images | *.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP" 2>/dev/null) || exit 0
      local -a list
      mapfile -t list <<<"$picked"
      recolor_files "${list[@]}"
      ;;
    *) recolor_files "$value" ;;
    esac
    ;;
  shaders)
    case "$value" in
    toggle) "$TOGGLE" ;;
    next) "$TOGGLE" next ;;
    *) "$TOGGLE" on "$value" ;;
    esac
    ;;
  opacity) "$OPACITY" set "$value" ;;
  blur) "$BLUR" set "$value" ;;
  esac
}

# One worker per source: $1 = image path. Skips thumbs newer than the source.
thumb_one() {
  local t
  t="$THUMB_DIR/$(printf %s "$1" | md5sum | cut -d' ' -f1).jpg"
  [[ -f $t && ! $1 -nt $t ]] && return 0
  vipsthumbnail "$1" --size 320x200 -o "$t[Q=82]" 2>/dev/null
}

thumbs() {
  mkdir -p "$THUMB_DIR"
  export THUMB_DIR
  export -f thumb_one
  list "$1" "${2:-}" | awk -F'\t' '$2 !~ /^(tweak:|section:)/ && $3 != "" { print $3 }' | xargs -d '\n' -P "$(nproc)" -I{} bash -c 'thumb_one "$1"' _ {}
}

status() {
  local anim=custom f
  [[ -s $ANIM_ACTIVE ]] || anim=default
  while read -r f; do
    cmp -s "$f" "$ANIM_ACTIVE" && { anim=$(basename "$f" .lua); break; }
  done < <(anim_files)
  printf 'preset\t%s\n' "$(current_preset_label)"
  printf 'style\t%s\n' "$(current_style_label)"
  command -v omarchy-font-profile >/dev/null && printf 'fonts\t%s\n' "$(omarchy-font-profile)"
  printf 'sound\t%s\n' "$(jq -r 'if .sounds == false then "off" else (.soundPack // "theme") end' "$SOUND_CFG" 2>/dev/null || echo theme)"
  printf 'theme\t%s\n' "$(theme_name)"
  printf 'wallpaper\t%s\n' "$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null)"
  printf 'anims\t%s\n' "$anim"
  printf 'shader\t%s\n' "$(current_shader)"
  printf 'opacity\t%s\n' "$("$OPACITY" current 2>/dev/null)"
  printf 'blur\t%s\n' "$("$BLUR" current 2>/dev/null)"
  printf 'glyph\t%s\n' "$(glyph_status)"
  printf 'bar-skin\t%s\n' "$(current_skin)"
  printf 'bar-layout\t%s\n' "$(current_layout)"
  printf 'lock\t%s\n' "$(lock_current)"
  printf 'fx\t%s\n' "$(jq -r '.type // "slant"' "$FX_CFG" 2>/dev/null || echo slant)"
  printf 'picker\t%s\n' "$(jq -r '.style // "slices"' "$PICKER_CFG" 2>/dev/null || echo slices)"
  printf 'launcher\t%s\n' "$(launcher_current)"
  # Для макетов в превью: вторые обои темы и 7 превью тем вокруг текущей.
  local cur_bg
  cur_bg=$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null)
  printf 'wallpaper-next\t%s\n' "$(images_in "$(dirname "$cur_bg")" 1 | grep -vxF "$cur_bg" | head -n 1)"
  printf 'picker-previews\t%s\n' "$(find -L "${XDG_CACHE_HOME:-$HOME/.cache}/omarchy/theme-selector/previews" -maxdepth 1 -type f 2>/dev/null |
    sort | awk -v cur="$(theme_name)" '{ a[NR] = $0; n = $0; sub(/.*\//, "", n); sub(/\.[^.]+$/, "", n); if (n == cur) c = NR }
      END { if (!c) c = 4; s = c - 3; if (s < 1) s = 1; e = s + 6; if (e > NR) e = NR
            for (i = s; i <= e; i++) printf "%s%s", (i > s ? "|" : ""), a[i] }')"
  # Numbers for the preview stage: "active inactive" / "size passes vibrancy noise".
  printf 'opacity-values\t%s\n' "$("$OPACITY" list 2>/dev/null | awk '$4 == 1 { print $2, $3 }')"
  printf 'blur-values\t%s\n' "$("$BLUR" list 2>/dev/null | awk '$6 == 1 { print $2, $3, $4, $5 }')"
}

# Вернуть сохранённое после `hyprctl reload` (Customizer зовёт это на configreloaded и при старте
# шелла): анимации, прозрачность, блюр, шейдер. Без сохранённого выбора ничего не трогаем.
restore() {
  local hypr_state="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
  [[ -s $ANIM_ACTIVE ]] && hyprctl eval "$(<"$ANIM_ACTIVE")" >/dev/null
  [[ -s $hypr_state/opacity ]] && "$OPACITY" restore
  [[ -s $hypr_state/blur ]] && "$BLUR" restore
  # Omarchy's "no gaps" toggle (omarchy-hyprland-window-gaps-toggle) wins while it is on.
  if [[ -s $hypr_state/geometry && ! -f ${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/toggles/hypr/window-no-gaps.lua ]]; then
    local _gn gi go bs r shd
    read -r _gn gi go bs r shd <"$hypr_state/geometry" || true
    if [[ -n ${shd:-} ]]; then
      hyprctl eval "hl.config({ general = { gaps_in = $gi, gaps_out = $go, border_size = $bs }, decoration = { rounding = $r, shadow = { enabled = $([[ $shd -gt 0 ]] && echo true || echo false) } } })" >/dev/null
    fi
  fi
  "$TOGGLE" restore
  # Блюр под самим оверлеем.
  hyprctl eval 'hl.layer_rule({ match = { namespace = "omarchy-customizer" }, blur = true, ignore_alpha = 0.6 })' >/dev/null
  date +%s >"$RUN_DIR/restored"
}

# Что есть на этой машине: категории, которым нужны плагины-компаньоны или программы, без них скрыты.
available() {
  local plugins="$HOME/.config/omarchy/plugins"
  echo presets
  echo styles
  command -v omarchy-font-profile >/dev/null && echo fonts
  command -v pw-play >/dev/null && echo sounds
  echo themes
  echo theme-walls
  command -v lutgen >/dev/null && command -v zenity >/dev/null && echo walls
  python3 -c 'import numpy, PIL' 2>/dev/null && echo dotify
  echo anims
  echo opacity
  echo blur
  echo glyph
  echo shaders
  if [[ -f $BAR_DIR/manifest.json ]]; then printf '%s\n' bar-skins bar-layouts bar-tweaks; fi
  # Виджеты бара правят shell.json — работает и со стоковым баром.
  echo bar-widgets
  if [[ -f $LOCK_PLUGIN/manifest.json ]]; then printf '%s\n' lock lock-tweaks; fi
  [[ -f $plugins/kamradsmeshnyavy.background/manifest.json ]] && echo wallpaper-fx
  [[ -f $plugins/kamradsmeshnyavy.widgets/manifest.json ]] && printf '%s\n' widgets dashboard
  [[ -f $plugins/kamradsmeshnyavy.osd/manifest.json ]] && echo osd
  [[ -f $plugins/kamradsmeshnyavy.notifications/manifest.json ]] && echo notifications
  [[ -f $plugins/kamradsmeshnyavy.image-picker/manifest.json ]] && echo theme-switcher
  [[ -f $MENU_PLUGIN/manifest.json ]] && echo launcher
  command -v zenity >/dev/null && echo has:zenity
  return 0
}

mkdir -p "$RUN_DIR" "$STATE_DIR"
case "${1:-}" in
list) list "${2:-}" "${3:-}" ;;
status) status ;;
available) available ;;
restore) restore ;;
lang) echo "$UI_LANG" ;;
thumbs) thumbs "${2:-}" "${3:-}" ;;
opacity-preview) "$OPACITY" preview "$2" ;;
opacity-restore) "$OPACITY" restore ;;
blur-preview) "$BLUR" preview "$2" ;;
blur-restore) "$BLUR" restore ;;
bar-skins-preview) bar_skin_preview "$2" ;;
bar-skins-restore) bar_skin_restore ;;
tweak)
  if [[ ${3:-} == set ]]; then tweak_set "$2" "${4-}"; else tweak "$2" "${3:-+}"; fi
  # Углы окон — правило окон: снять старое можно только перезагрузкой конфига (hypr/customizer.lua).
  [[ $2 == window* ]] && hyprctl reload >/dev/null 2>&1
  ;;
lock-preview) omarchy-shell lock previewDesign "${2:-}" >/dev/null ;;
skin-delete) delete_user_skin "${2:-}" ;;
layout-delete) delete_user_layout "${2:-}" ;;
preset-delete) delete_user_preset "${2:-}" ;;
# Послушать пакет, не выбирая его: sound-preview <пакет> [событие].
sound-preview) OMARCHY_SOUND_PACK="${2:-theme}" "$PLAY_SOUND" "${3:-notify}" --force ;;
style-delete) delete_user_style "${2:-}" ;;
lock-thumbs) lock_thumbs ;;
fx-replay) omarchy-shell background replay >/dev/null ;;
picker-cache) picker_cache ;;
picker-open) setsid -f omarchy-theme-switcher >/dev/null 2>&1 ;;
launcher-open) setsid -f omarchy-menu toggle apps >/dev/null 2>&1 ;;
glyph-test) omarchy-shell -q glyph test "${2:-false}" >/dev/null 2>&1 ;;
anim-preview)
  cp "$2" "$ANIM_ACTIVE"
  hyprctl reload >/dev/null 2>&1
  ;;
anim-restore)
  # The overlay only calls this after a preview, so the backup is fresh.
  if [[ -f $ANIM_BACKUP ]] && ! cmp -s "$ANIM_BACKUP" "${ANIM_ACTIVE}"; then
    cp "$ANIM_BACKUP" "$ANIM_ACTIVE"
    hyprctl reload >/dev/null 2>&1
  fi
  ;;
apply) apply "$2" "$3" ;;
*)
  echo "usage: $0 list|status|available|restore|lang|thumbs|anim-preview|anim-restore|opacity-preview|opacity-restore|blur-preview|blur-restore|bar-skins-preview|bar-skins-restore|tweak|apply ..." >&2
  exit 1
  ;;
esac
