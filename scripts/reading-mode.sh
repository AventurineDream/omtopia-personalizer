#!/usr/bin/env bash
# Reading mode: the desktop turns into a printed page for long reading.
#   - screen shader shaders/reading.frag (ink on paper, grain, dither);
#   - flat windows: no gaps, 1px border, square corners, no blur / shadow / animations;
#   - optional: screen brightness and a light theme for the time of reading.
# Turning it off reloads Hyprland: hypr/customizer.lua re-applies the saved style, windows tab and
# screen shader, so nothing has to be remembered and restored by hand.
#
#   reading-mode.sh [toggle|on|off|status|restore]
#
# Settings (all optional) — ~/.config/omarchy/customizer/reading-mode.json:
#   { "shader": "reading",   // any name from crt-toggle.sh list, "" = no shader
#     "flat": true,          // gaps 0, border 1, rounding 0, no blur / shadow
#     "animations": false,   // false = animations off while reading
#     "brightness": 0,       // 1..100 = set this % while reading, 0 = don't touch
#     "theme": "" }          // Omarchy theme for reading, "" = keep the current one
#
# State: ~/.local/state/hypr/reading-mode (exists = on) holds what has to come back:
#   brightness=<raw value>  theme=<name>
# `restore` is run by hypr/customizer.lua indirectly: it re-applies the flat look itself while the
# state file exists, so a config reload during reading keeps the page.
set -euo pipefail
# shellcheck source=i18n.sh
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/i18n.sh"

CFG="$HOME/.config/omarchy/customizer/reading-mode.json"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
STATE="$STATE_DIR/reading-mode"
mkdir -p "$STATE_DIR"

cfg() { # $1 = key, $2 = default
    local v
    v="$(jq -r --arg k "$1" 'if has($k) then .[$k] | tostring else empty end' "$CFG" 2>/dev/null || true)"
    echo "${v:-$2}"
}

notify() {
    local idf="$STATE_DIR/reading-mode-notify-id" id
    id="$(command cat "$idf" 2>/dev/null || echo 0)"
    omarchy notification send -p -r "$id" -t 2000 -g 󰂺 --app-name "Reading mode" \
        "$1" "${2:-}" >"$idf" 2>/dev/null || true
}

shader_path() { # $1 = name -> path or ""
    [[ -n $1 ]] || return 0
    "$CUSTOMIZER_DIR/scripts/crt-toggle.sh" list | grep -m1 "/$1\.frag$" || true
}

# Flat look + shader. Same values as the reading block in hypr/customizer.lua.
apply_look() {
    local lua="" path
    if [[ $(cfg flat true) == true ]]; then
        lua+='hl.config({ general = { gaps_in = 0, gaps_out = 0, border_size = 1 },'
        lua+=' decoration = { rounding = 0, blur = { enabled = false }, shadow = { enabled = false } } })'
        lua+=' hl.window_rule({ match = { class = ".*" }, rounding = 0 })'
    fi
    if [[ $(cfg animations false) != true ]]; then
        lua+=' hl.config({ animations = { enabled = false } })'
    fi
    path="$(shader_path "$(cfg shader reading)")"
    if [[ -n $path ]]; then
        lua+=" hl.config({ decoration = { screen_shader = \"$path\" }, debug = { damage_tracking = 2 } })"
    fi
    [[ -z $lua ]] || hyprctl eval "$lua" >/dev/null
}

has_backlight() { brightnessctl -l -c backlight 2>/dev/null | grep -q backlight; }

on() {
    [[ -f $STATE ]] && { apply_look; return; }
    local saved="" b theme
    b="$(cfg brightness 0)"
    if [[ $b =~ ^[0-9]+$ ]] && ((b > 0)) && has_backlight; then
        saved+="brightness=$(brightnessctl -c backlight get)"$'\n'
        brightnessctl -q -c backlight set "${b}%"
    fi
    theme="$(cfg theme "")"
    if [[ -n $theme ]]; then
        local cur
        cur="$(omarchy-theme-current 2>/dev/null || true)"
        if [[ -n $cur && $cur != "$theme" ]]; then
            saved+="theme=$cur"$'\n'
            omarchy-theme-set "$theme" >/dev/null 2>&1 || true
        fi
    fi
    printf '%s' "$saved" >"$STATE"
    apply_look
    notify "$(t "Reading mode on")" "$(t "Press again to return to the desktop")"
}

off() {
    [[ -f $STATE ]] || return 0
    local b theme
    b="$(sed -n 's/^brightness=//p' "$STATE")"
    theme="$(sed -n 's/^theme=//p' "$STATE")"
    mv -f "$STATE" "$STATE.last"
    hyprctl reload >/dev/null
    [[ -n $b ]] && brightnessctl -q -c backlight set "$b" || true
    [[ -n $theme ]] && { omarchy-theme-set "$theme" >/dev/null 2>&1 || true; }
    notify "$(t "Reading mode off")"
}

case "${1:-toggle}" in
toggle) if [[ -f $STATE ]]; then off; else on; fi ;;
on) on ;;
off) off ;;
restore) [[ -f $STATE ]] && apply_look || true ;;
status) [[ -f $STATE ]] && echo on || echo off ;;
*) echo "usage: ${0##*/} [toggle|on|off|status|restore]" >&2; exit 2 ;;
esac
