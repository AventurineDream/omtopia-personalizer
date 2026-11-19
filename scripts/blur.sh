#!/usr/bin/env bash
# System-wide background blur presets (decoration.blur). Works on every
# translucent window, so it shows together with the opacity.sh presets.
# The choice is saved to $STATE as "<name> <size> <passes> <vibrancy> <noise>"
# and the Customizer re-applies it after every config reload (customizer.sh restore,
# or hypr/customizer.lua when it is loaded from the Hyprland config).
#
#   blur.sh                  # next preset (same as `next`)
#   blur.sh next | prev      # cycle through PRESETS
#   blur.sh set <name>       # apply a preset by name (used by the customizer)
#   blur.sh preview <name>   # apply without saving or notifying (customizer hover); snapshots the pre-preview live values once
#   blur.sh restore          # re-apply the saved preset silently (none saved: restore the pre-preview snapshot, else keep the live blur)
#                              a saved name that is no longer in PRESETS also keeps the live blur (exit 0).
#   blur.sh list             # "<name> <size> <passes> <vibrancy> <noise> <current 0/1>"
#   blur.sh current          # name of the preset in use; empty when none was applied
#   blur.sh live             # "enabled size passes vibrancy noise" of the live blur; fails when the compositor cannot be read
#   blur.sh set-live "<enabled size passes vibrancy noise>"  # restore exact live values with no preset in use (rollback snapshots)
#
# Bind it if you like, e.g. SUPER+ALT+U (next), SUPER+ALT+SHIFT+U (prev).
set -euo pipefail
# shellcheck source=i18n.sh
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/i18n.sh"

# name size passes vibrancy noise   (size 0 = blur off)
PRESETS=(
    "off      0  1 0.00 0.000"
    "light    3  2 0.10 0.010"
    "dotmatrix    4  2 0.00 0.000"
    "medium   6  3 0.17 0.012"
    "strong  10  4 0.20 0.015"
    "frosted 14  4 0.30 0.030"
    "liquid  12  3 0.45 0.008"
)
DEFAULT=medium # what next/prev apply when no preset is in use; never reported as in use (see current)

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
STATE="$STATE_DIR/blur"
mkdir -p "$STATE_DIR"

# Pre-preview snapshot (issue #14): preview saves the live values here on the
# first hover so restore can put them back; it lives in the runtime dir (gone
# on logout) and is consumed by restore / cleared by an explicit apply.
SNAPSHOT_DIR="${XDG_RUNTIME_DIR:-/tmp}/omarchy-customizer"
SNAPSHOT="$SNAPSHOT_DIR/blur-preview"

names() { local p; for p in "${PRESETS[@]}"; do echo "${p%% *}"; done; }

lookup() { # $1 = name -> "size passes vibrancy noise", fails when unknown
    local p n rest
    for p in "${PRESETS[@]}"; do
        read -r n rest <<<"$p"
        [[ $n == "$1" ]] && { echo "$rest"; return 0; }
    done
    return 1
}

# Name of the saved preset, or nothing when none was applied. A fresh system is not "medium": the
# lists, status and Home card must not mark a preset the compositor is not using.
current() {
    local c=""
    { read -r c _ <"$STATE"; } 2>/dev/null || true
    if lookup "$c" >/dev/null 2>&1; then echo "$c"; fi
}

notify() { # $1 = title, $2 = body
    # Replace the previous toast by id so repeated presses update one toast.
    local idf="$STATE_DIR/blur-notify-id" id
    id="$(cat "$idf" 2>/dev/null || echo 0)"
    omarchy notification send -p -r "$id" -t 1500 -g 󰂷 --app-name "Blur" \
        "$1" "$2" >"$idf" 2>/dev/null || true
}

set_blur() { # $1 = name; fails when unknown
    local s p v n on=true
    read -r s p v n < <(lookup "$1") || return 1
    ((s == 0)) && on=false
    hyprctl eval "hl.config({ decoration = { blur = { enabled = $on, size = $((s > 0 ? s : 1)), passes = $p, vibrancy = $v, noise = $n } } })" >/dev/null
}

live_blur() { # -> "enabled size passes vibrancy noise" (enabled: true/false), fails when unreadable
    local on s p v n
    # NB: `.bool // empty` would swallow `false` (jq `//` treats false as empty),
    # so read .bool bare and validate it below.
    on="$(hyprctl getoption decoration:blur:enabled -j 2>/dev/null | jq -r '.bool' 2>/dev/null)" || return 1
    s="$(hyprctl getoption decoration:blur:size -j 2>/dev/null | jq -r '.int // empty' 2>/dev/null)" || return 1
    p="$(hyprctl getoption decoration:blur:passes -j 2>/dev/null | jq -r '.int // empty' 2>/dev/null)" || return 1
    v="$(hyprctl getoption decoration:blur:vibrancy -j 2>/dev/null | jq -r '.float // empty' 2>/dev/null)" || return 1
    n="$(hyprctl getoption decoration:blur:noise -j 2>/dev/null | jq -r '.float // empty' 2>/dev/null)" || return 1
    [[ ($on == true || $on == false) && -n $s && -n $p && -n $v && -n $n ]] || return 1
    echo "$on $s $p $v $n"
}

match_preset() { # $1..$5 = enabled(true/false) size passes vibrancy noise -> preset name, fails when none matches
    local on="$1" s="$2" p="$3" v="$4" n="$5" row name rs rp rv rn
    [[ $on == false ]] && { echo off; return 0; }
    for row in "${PRESETS[@]}"; do
        read -r name rs rp rv rn <<<"$row"
        [[ $name == off ]] && continue
        [[ $rs == "$s" && $rp == "$p" ]] || continue
        if awk -v a="$rv" -v b="$v" -v c="$rn" -v d="$n" 'BEGIN { x = a - b; if (x < 0) x = -x; y = c - d; if (y < 0) y = -y; exit !(x < 0.001 && y < 0.001) }'; then
            echo "$name"
            return 0
        fi
    done
    return 1
}

set_blur_raw() { # $1..$5 = enabled size passes vibrancy noise; re-applies exact live values, no state write
    local on="$1" s="$2" p="$3" v="$4" n="$5"
    hyprctl eval "hl.config({ decoration = { blur = { enabled = $on, size = $((s > 0 ? s : 1)), passes = $p, vibrancy = $v, noise = $n } } })" >/dev/null
}

# Rollback of a snapshot taken while no preset was in use: re-applies the exact live values it recorded and
# leaves no preset in use (the state file goes, so current and list mark none). Hyprland evals the value, so
# only the five live fields, exactly, are accepted; anything else changes nothing.
set_live() { # $1 = "enabled size passes vibrancy noise", as `live` prints it
    local re='^(true|false) [0-9]+ [0-9]+ [0-9.]+ [0-9.]+$' on s p v n
    [[ ${1:-} =~ $re ]] || { echo "blur.sh: not live blur values: ${1:-}" >&2; return 1; }
    read -r on s p v n <<<"$1"
    set_blur_raw "$on" "$s" "$p" "$v" "$n"
    rm -f "$STATE" "$SNAPSHOT"
}

restore_live() {
    # No saved preset. Prefer the pre-preview snapshot (taken by preview):
    # it holds the values from before the hover, while live is now the
    # previewed preset — restoring live would keep the hover AND anchor it.
    # Without a snapshot, keep whatever is live now instead of letting the
    # reload snap it to the Hyprland config default (issue #14). Never write
    # state here — a hover must not persist — and never reload: the reload
    # would re-fire configreloaded and clobber the other script's restore.
    # When the compositor cannot be read at all, do nothing.
    local live on s p v n name
    if [[ -s $SNAPSHOT ]]; then
        read -r on s p v n <"$SNAPSHOT"
        rm -f "$SNAPSHOT"
    else
        live="$(live_blur)" || return 0
        read -r on s p v n <<<"$live"
    fi
    if name="$(match_preset "$on" "$s" "$p" "$v" "$n")"; then
        set_blur "$name"
    else
        set_blur_raw "$on" "$s" "$p" "$v" "$n"
    fi
}

preview() { # $1 = name; snapshot the pre-preview live values once, then apply without saving
    local live
    lookup "$1" >/dev/null 2>&1 || return 1
    if [[ ! -s $SNAPSHOT ]]; then
        if live="$(live_blur 2>/dev/null)"; then
            mkdir -p "$SNAPSHOT_DIR"
            echo "$live" >"$SNAPSHOT"
        fi
    fi
    set_blur "$1"
}

apply() { # $1 = name
    local s p v n
    set_blur "$1" || { notify "$(t "No such preset")" "$1"; exit 1; }
    read -r s p v n < <(lookup "$1")
    echo "$1 $s $p $v $n" >"$STATE"
    rm -f "$SNAPSHOT" # the preview session (if any) is over; don't let a stale snapshot linger
    if ((s == 0)); then
        notify "$(t "Blur: off")" "$(t "windows show through without blur")"
    else
        notify "$(t "Blur: %s" "$1")" "size $s · passes $p · vibrancy $v"
    fi
}

step() { # $1 = +1 / -1
    local -a list
    mapfile -t list < <(names)
    local cur n=${#list[@]} k
    cur="$(current)"
    for k in "${!list[@]}"; do
        [[ ${list[$k]} == "$cur" ]] && { apply "${list[$(( (k + $1 + n) % n ))]}"; return; }
    done
    apply "$DEFAULT"
}

case "${1:-next}" in
next) step 1 ;;
prev) step -1 ;;
set) apply "${2:?preset name}" ;;
preview) preview "${2:?preset name}" ;;
# A saved name that no longer exists (renamed or removed preset) keeps the live blur, not an exit 1.
restore) if [[ -n $(current) ]]; then set_blur "$(current)"; else restore_live; fi ;;
current) current ;;
live) live_blur ;;
set-live) set_live "${2:-}" ;;
list)
    cur="$(current)"
    for p in "${PRESETS[@]}"; do
        read -r n s ps v no <<<"$p"
        echo "$n $s $ps $v $no $([[ $n == "$cur" ]] && echo 1 || echo 0)"
    done
    ;;
*) echo "usage: $0 [next|prev|set <name>|preview <name>|restore|list|current|live|set-live <values>]" >&2; exit 1 ;;
esac
