#!/usr/bin/env bash
# Install the Omarchy Customizer and, optionally, its companion plugins.
#
#   bash install.sh                      # Customizer, then a question per companion
#   bash install.sh --all                # Customizer + every companion
#   bash install.sh --with bar,lock      # Customizer + the listed ones
#   bash install.sh --none               # Customizer only
#
# Each plugin is a separate repo added with `omarchy plugin add`, so `omarchy plugin update`
# and `omarchy plugin remove` keep working. Already installed plugins are skipped.
set -euo pipefail

BASE=https://github.com/KamradSmeshnyavy
# This fork ships as Omtopia Personalizer; the upstream plugin of the same id is a different repo.
CUSTOMIZER_URL=https://github.com/AventurineDream/omtopia-personalizer
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

usage() { # the help text; a bad flag prints it to stderr and exits 2
  cat <<'USAGE'
usage: bash install.sh [--all | --with KEY[,KEY…] | --none]
  (no flag)    the Customizer, then a question per companion plugin
  --all        the Customizer and every companion plugin
  --with LIST  the Customizer and the listed companions
  --none       the Customizer only
companions: bar (bar skins), lock (lock designs), fx (wallpaper transitions),
            picker (image picker styles), launcher (launcher skins)
USAGE
}

while (($#)); do
  case $1 in
  --all) mode=all ;;
  --none) mode=none ;;
  --with) mode=with with=${2-}; if (($# >= 2)); then shift; fi ;;
  --with=*) mode=with with=${1#--with=} ;;
  -h | --help) usage; exit 0 ;;
  *) usage >&2; echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ $mode == with ]]; then
  [[ -n ${with//[, ]/} ]] || { usage >&2; echo "--with needs a list, e.g. --with bar,lock" >&2; exit 2; }
  for k in ${with//,/ }; do
    [[ " bar lock fx picker launcher " == *" $k "* ]] || { usage >&2; echo "unknown companion: $k" >&2; exit 2; }
  done
fi

command -v omarchy >/dev/null || { echo "Omarchy not found: this installs Omarchy shell plugins." >&2; exit 1; }
# With no terminal there is nobody to answer the questions: say so and install the Customizer alone,
# instead of skipping each companion silently.
if [[ $mode == ask ]] && ! { : </dev/tty; } 2>/dev/null; then
  echo "• no terminal to ask on — installing the Customizer only; add companions with --all or --with bar,lock" >&2
  mode=none
fi

add() { # url id: skips a plugin whose manifest is already in place
  if [[ -e $PLUGINS/$2/manifest.json ]]; then
    echo "• $2 is already installed — skipping (update it with: omarchy plugin update $2)"
    return
  fi
  echo "• adding $2 …"
  omarchy plugin add "$1" --enable --yes
}

# Questions go to the terminal even when the script itself comes from a pipe.
ask() { # prompt -> 0 for yes
  local reply=""
  read -r -p "$1 [y/N] " reply </dev/tty || true
  [[ $reply == [yY]* ]]
}

add "$CUSTOMIZER_URL" kamradsmeshnyavy.customizer

# Fonts of the DOT-MATRIX (dot-matrix) style — Doto, Space Grotesk, Space Mono (SIL OFL 1.1).
# Without them the DOT-MATRIX skins fall back to the Omarchy font.
fonts_src="$PLUGINS/kamradsmeshnyavy.customizer/fonts"
fonts_dst="$HOME/.local/share/fonts/dotmatrix"
if [[ -d $fonts_src && ! -e $fonts_dst ]]; then
  mkdir -p "$(dirname "$fonts_dst")"
  ln -s "$fonts_src" "$fonts_dst"
  command -v fc-cache >/dev/null && fc-cache -f "$fonts_dst" >/dev/null 2>&1 || true
fi

for c in "${COMPANIONS[@]}"; do
  IFS='|' read -r key repo id what <<<"$c"
  case $mode in
  all) add "$BASE/$repo" "$id" ;;
  with) [[ ",$with," == *",$key,"* ]] && add "$BASE/$repo" "$id" ;;
  ask) ask "Also install $repo — $what?" && add "$BASE/$repo" "$id" ;;
  none) ;;
  esac
done

if [[ -f $BINDINGS ]] && ! grep -q "kamradsmeshnyavy.customizer" "$BINDINGS"; then
  cat >>"$BINDINGS" <<'BIND'

-- Omtopia Personalizer (https://github.com/AventurineDream/omtopia-personalizer)
o.bind("SUPER + SHIFT + T", "Omarchy Customizer", "omarchy-shell shell toggle kamradsmeshnyavy.customizer")
BIND
  echo "• bound Super+Shift+T in $BINDINGS"
fi

hyprctl reload >/dev/null 2>&1 || true
omarchy restart shell >/dev/null 2>&1 || true
echo "Done. Open the Customizer with Super+Shift+T."
