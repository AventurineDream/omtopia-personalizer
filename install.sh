#!/usr/bin/env bash
# Install the Omarchy Customizer and, optionally, its companion plugins.
#
#   curl -fsSL https://raw.githubusercontent.com/KamradSmeshnyavy/omarchy-customizer/main/install.sh | bash
#   … | bash -s -- --all                 # Customizer + every companion
#   … | bash -s -- --with bar,lock       # Customizer + the listed ones
#   … | bash -s -- --none                # Customizer only
#
# Each plugin is a separate repo added with `omarchy plugin add`, so `omarchy plugin update`
# and `omarchy plugin remove` keep working. Already installed plugins are skipped.
set -euo pipefail

BASE=https://github.com/KamradSmeshnyavy
PLUGINS="$HOME/.config/omarchy/plugins"
BINDINGS="$HOME/.config/hypr/bindings.lua"

# key | repo | plugin id | what it adds
COMPANIONS=(
  "bar|omarchy-bar-skins|kamradsmeshnyavy.bar|top bar with 18 skins, layouts and a compact mode"
  "lock|omarchy-lock-designs|kamradsmeshnyavy.lock|22 lock screen designs"
  "fx|omarchy-wallpaper-fx|kamradsmeshnyavy.background|24 wallpaper transitions"
  "picker|omarchy-image-picker-styles|kamradsmeshnyavy.image-picker|six theme/wallpaper picker styles"
  "launcher|omarchy-launcher-skins|kamradsmeshnyavy.menu|full-screen launcher skins"
)

mode=ask
with=""
while (($#)); do
  case $1 in
  --all) mode=all ;;
  --none) mode=none ;;
  --with) mode=with with=${2:?--with needs a list, e.g. bar,lock}; shift ;;
  --with=*) mode=with with=${1#--with=} ;;
  -h | --help) sed -n '2,10p' "$0" 2>/dev/null || true; exit 0 ;;
  *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

command -v omarchy >/dev/null || { echo "Omarchy not found: this installs Omarchy shell plugins." >&2; exit 1; }

add() { # repo id
  if [[ -e $PLUGINS/$2/manifest.json ]]; then
    echo "• $2 is already installed — skipping (update it with: omarchy plugin update $2)"
    return
  fi
  echo "• adding $2 …"
  omarchy plugin add "$BASE/$1" --enable --yes
}

# Questions go to the terminal even when the script itself comes from a pipe.
ask() { # prompt -> 0 for yes
  local reply=""
  if [[ -r /dev/tty ]]; then
    read -r -p "$1 [y/N] " reply </dev/tty || true
  fi
  [[ $reply == [yY]* ]]
}

add omarchy-customizer kamradsmeshnyavy.customizer

# Fonts of the Nihil (dot-matrix) style — Doto, Space Grotesk, Space Mono (SIL OFL 1.1).
# Without them the Nihil skins fall back to the Omarchy font.
fonts_src="$PLUGINS/kamradsmeshnyavy.customizer/fonts"
fonts_dst="$HOME/.local/share/fonts/nihil"
if [[ -d $fonts_src && ! -e $fonts_dst ]]; then
  mkdir -p "$(dirname "$fonts_dst")"
  ln -s "$fonts_src" "$fonts_dst"
  command -v fc-cache >/dev/null && fc-cache -f "$fonts_dst" >/dev/null 2>&1 || true
fi

for c in "${COMPANIONS[@]}"; do
  IFS='|' read -r key repo id what <<<"$c"
  case $mode in
  all) add "$repo" "$id" ;;
  with) [[ ",$with," == *",$key,"* ]] && add "$repo" "$id" ;;
  ask) ask "Also install $repo — $what?" && add "$repo" "$id" ;;
  none) ;;
  esac
done

if [[ -f $BINDINGS ]] && ! grep -q "kamradsmeshnyavy.customizer" "$BINDINGS"; then
  cat >>"$BINDINGS" <<'BIND'

-- Omarchy Customizer (https://github.com/KamradSmeshnyavy/omarchy-customizer)
o.bind("SUPER + SHIFT + T", "Omarchy Customizer", "omarchy-shell shell toggle kamradsmeshnyavy.customizer")
BIND
  echo "• bound Super+Shift+T in $BINDINGS"
fi

hyprctl reload >/dev/null 2>&1 || true
omarchy restart shell >/dev/null 2>&1 || true
echo "Done. Open the Customizer with Super+Shift+T."
