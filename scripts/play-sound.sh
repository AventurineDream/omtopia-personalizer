#!/usr/bin/env bash
# Interface sound player for Omarchy Customizer.
# Supports sound packs in ~/.config/omarchy/sounds.json:
#   {"sounds": true, "soundPack": "theme|dotmatrix|<каталог в sounds/>", "soundVolume": 0.6, "windowSounds": false}
#
# Events: open close switch special fullscreen lock power menu notify critical volume charge
#         (plus freedesktop aliases: message-new-instant, dialog-warning, audio-volume-change,
#          service-login, battery-low, screen-capture)
set -u

event=${1:-}
force=${2:-}
[[ $event =~ ^[a-z0-9-]+$ ]] || exit 0

CUSTOMIZER_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)
conf=$HOME/.config/omarchy/sounds.json
enabled=true volume=0.6 pack=theme
if [[ -f $conf ]]; then
  enabled=$(jq -r 'if .sounds == false then "false" else "true" end' "$conf" 2>/dev/null || echo true)
  volume=$(jq -r '.soundVolume // 0.6' "$conf" 2>/dev/null || echo 0.6)
  pack=$(jq -r '.soundPack // "theme"' "$conf" 2>/dev/null || echo theme)
fi
# Прослушивание пакета без смены настройки (Customizer → Звуки, p): OMARCHY_SOUND_PACK=<пакет>.
[[ -n ${OMARCHY_SOUND_PACK:-} ]] && pack=$OMARCHY_SOUND_PACK
[[ $force == --force || $enabled == true ]] || exit 0

# Throttle rapid events (held volume keys or window/workspace bursts).
case "$event" in
audio-volume-change | volume | open | close | switch | special | fullscreen)
  stamp=${XDG_RUNTIME_DIR:-/tmp}/omarchy-sound-$event
  now=$(date +%s%3N)
  last=0
  [[ -f $stamp ]] && last=$(<"$stamp")
  ((now - ${last:-0} < 75)) && exit 0
  echo "$now" >"$stamp"
  ;;
esac

# Map between DOT-MATRIX short names and freedesktop sound-theme names.
declare -A DOTMATRIX_MAP=(
  [message-new-instant]=notify
  [dialog-warning]=critical
  [battery-low]=critical
  [audio-volume-change]=volume
  [service-login]=power
  [screen-capture]=open
  [power-plug]=charge
)
declare -A FDO_MAP=(
  [notify]=message-new-instant
  [critical]=dialog-warning
  [battery-low]=dialog-warning
  [volume]=audio-volume-change
  [power]=service-login
  [charge]=power-plug
)
# Чего нет в пакете — ближайший звук (зарядка → power, как было до charge.ogg).
declare -A FALLBACK_MAP=(
  [charge]=power
)

short=${DOTMATRIX_MAP[$event]:-$event}
fdo=${FDO_MAP[$event]:-$event}
alt=${FALLBACK_MAP[$short]:-}

case "$pack" in
dotmatrix)
  dirs=(
    "$CUSTOMIZER_DIR/sounds/dotmatrix"
    "$HOME/.local/state/omarchy/current/theme/apps/sounds"
    /usr/share/sounds/freedesktop/stereo
  )
  names=("$short" "$event" "$fdo" "$alt")
  ;;
*)
  if [[ $pack != theme && $pack =~ ^[a-z0-9-]+$ && -d $CUSTOMIZER_DIR/sounds/$pack ]]; then
    # Пакет стиля (classic, flat, glass, paper, …): чего в нём нет — из dotmatrix, потом freedesktop.
    dirs=(
      "$CUSTOMIZER_DIR/sounds/$pack"
      "$CUSTOMIZER_DIR/sounds/dotmatrix"
      /usr/share/sounds/freedesktop/stereo
    )
    names=("$short" "$event" "$fdo" "$alt")
  else
    dirs=(
      "$HOME/.local/state/omarchy/current/theme/apps/sounds"
      /usr/share/sounds/freedesktop/stereo
    )
    names=("$event" "$fdo" "$short")
  fi
  ;;
esac

file=
for dir in "${dirs[@]}"; do
  [[ -d $dir ]] || continue
  for name in "${names[@]}"; do
    [[ -n $name ]] || continue
    for ext in oga ogg wav flac; do
      [[ -f $dir/$name.$ext ]] && { file=$dir/$name.$ext; break 3; }
    done
  done
done
[[ -n $file ]] || exit 0

setsid -f pw-play --volume "$volume" "$file" >/dev/null 2>&1
