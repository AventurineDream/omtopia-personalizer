#!/usr/bin/env bash
# Reading mode: the desktop turns into a printed page for long reading.
#   - screen shader shaders/reading.frag (ink on paper, grain, fibres, dither, vignette);
#   - flat windows: no gaps, 1px black border, square corners, no blur / shadow / dimming / animations;
#   - screen brightness and, optionally, a light theme for the time of reading.
# Turning it off reloads Hyprland: hypr/customizer.lua re-applies the saved style, windows tab and
# screen shader, so nothing has to be remembered and restored by hand (only brightness and theme).
#
#   reading-mode.sh [toggle|on|off|status|restore|look]
#
# Settings — Customizer → Windows → Shader → Reading mode, file ~/.config/omarchy/customizer/reading-mode.json:
#   readingPage        auto | paper | invert — how a dark theme becomes a page: auto inverts brightness in
#                      the shader when the theme is dark (instant, photos look like negatives), paper never
#                      inverts (use with readingTheme), invert always does
#   readingShader      reading | paper | film | gameboy | none
#   readingTexture     0..2 — strength of the paper texture (grain, fibres, dither)
#   readingBrightness  0..100 — screen brightness while reading, 0 = don't touch (default 40)
#   readingTheme       Omarchy theme for reading, empty = keep the current one
#   readingFlat        true — flat windows;   readingAnimations  false — animations off
#
# State: ~/.local/state/hypr/reading-mode (exists = on) holds what has to come back:
#   brightness=<raw value>  theme=<name>
# The reading shader is written with the chosen INVERT / TEXTURE to ~/.local/state/hypr/reading-page.frag;
# hypr/customizer.lua re-applies the look while the state file exists, so a config reload keeps the page.
set -euo pipefail
# shellcheck source=i18n.sh
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/i18n.sh"

CFG="$HOME/.config/omarchy/customizer/reading-mode.json"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
STATE="$STATE_DIR/reading-mode"
PAGE="$STATE_DIR/reading-page.frag"
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

theme_is_light() { [[ -f $HOME/.config/omarchy/current/theme/light.mode ]]; }

# The shader for the page: the reading shader gets INVERT / TEXTURE baked into a copy, any other
# shader is used as is. Prints the path, or nothing for "none".
page_shader() {
    local name src invert=0.0 tex
    name="$(cfg readingShader reading)"
    [[ $name != none && -n $name ]] || return 0
    src="$("$CUSTOMIZER_DIR/scripts/crt-toggle.sh" list | grep -m1 "/$name\.frag$" || true)"
    [[ -n $src ]] || return 0
    if [[ $name != reading ]]; then
        echo "$src"
        return
    fi
    case "$(cfg readingPage auto)" in
    invert) invert=1.0 ;;
    paper) invert=0.0 ;;
    *) theme_is_light || invert=1.0 ;;
    esac
    tex="$(cfg readingTexture 1)"
    [[ $tex =~ ^[0-9]+(\.[0-9]+)?$ ]] || tex=1
    [[ $tex == *.* ]] || tex="$tex.0"
    sed -e "s/^const float INVERT  = .*;/const float INVERT  = $invert;/" \
        -e "s/^const float TEXTURE = .*;/const float TEXTURE = $tex;/" "$src" >"$PAGE.tmp"
    mv -f "$PAGE.tmp" "$PAGE"
    echo "$PAGE"
}

# The flat look + page shader by `hyprctl eval`, no reload. The same values live in the reading block of
# hypr/customizer.lua (while the config loads) and the Customizer's restore after `configreloaded` calls
# `reading-mode.sh look` last — otherwise its opacity / blur / geometry restore would undo the page.
look() {
    [[ -f $STATE ]] || return 0
    local lua="" path
    if [[ $(cfg readingFlat true) == true ]]; then
        lua+='hl.config({ general = { gaps_in = 0, gaps_out = 0, border_size = 1,'
        lua+=' col = { active_border = "rgba(000000ff)", inactive_border = "rgba(000000ff)" } },'
        lua+=' decoration = { rounding = 0, dim_inactive = false, blur = { enabled = false }, shadow = { enabled = false } } })'
        lua+=' hl.window_rule({ match = { class = ".*" }, rounding = 0 })'
    fi
    [[ $(cfg readingAnimations false) == true ]] || lua+=' hl.config({ animations = { enabled = false } })'
    path="$(page_shader)"
    lua+=" hl.config({ decoration = { screen_shader = \"$path\" }, debug = { damage_tracking = 2 } })"
    hyprctl eval "$lua" >/dev/null
}

# After a settings change: re-bake the shader and reload, so switching e.g. flat windows off takes effect;
# the reload ends in the Customizer's restore → look.
apply_look() {
    page_shader >/dev/null
    hyprctl reload >/dev/null
    sleep 0.3
    look
}

has_backlight() { brightnessctl -l -c backlight 2>/dev/null | grep -q backlight; }

on() {
    [[ -f $STATE ]] && { apply_look; return; }
    local saved="" b theme cur
    b="$(cfg readingBrightness 40)"
    if [[ $b =~ ^[0-9]+$ ]] && ((b > 0)) && has_backlight; then
        saved+="brightness=$(brightnessctl -c backlight get)"$'\n'
        brightnessctl -q -c backlight set "${b}%"
    fi
    theme="$(cfg readingTheme "")"
    if [[ -n $theme ]]; then
        cur="$(omarchy-theme-current 2>/dev/null || true)"
        if [[ -n $cur && $cur != "$theme" ]]; then
            saved+="theme=$cur"$'\n'
            omarchy-theme-set "$theme" >/dev/null 2>&1 || true
        fi
    fi
    printf '%s' "$saved" >"$STATE"
    look
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
look) look ;;
status) [[ -f $STATE ]] && echo on || echo off ;;
*) echo "usage: ${0##*/} [toggle|on|off|status|restore]" >&2; exit 2 ;;
esac
