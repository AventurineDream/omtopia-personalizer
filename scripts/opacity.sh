#!/usr/bin/env bash
# System-wide window transparency presets (decoration active/inactive_opacity).
# The choice is saved to $STATE as "<name> <active> <inactive>" and
# the Customizer re-applies it after every config reload (customizer.sh restore,
# or hypr/customizer.lua when it is loaded from the Hyprland config).
#
#   opacity.sh               # next preset (same as `next`)
#   opacity.sh next | prev   # cycle through PRESETS
#   opacity.sh set <name>    # apply a preset by name (used by the customizer)
#   opacity.sh preview <name>  # apply without saving or notifying (customizer hover); snapshots the pre-preview live values once
#   opacity.sh restore       # re-apply the saved preset silently (none saved: restore the pre-preview snapshot, else keep the live opacity)
#   opacity.sh list          # "<name> <active> <inactive> <current 0/1>" per line
#   opacity.sh current       # name of the preset in use
#
# Bind it if you like, e.g. SUPER+ALT+O (next), SUPER+ALT+SHIFT+O (prev).
set -euo pipefail
# shellcheck source=i18n.sh
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/i18n.sh"

# name active inactive
PRESETS=(
    "solid   1.00 1.00"
    "subtle  1.00 0.90"
    "dotmatrix   1.00 0.85"
    "soft    0.95 0.85"
    "glass   0.90 0.80"
    "frosted 0.85 0.70"
)
DEFAULT=subtle

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hypr"
STATE="$STATE_DIR/opacity"
mkdir -p "$STATE_DIR"

# Pre-preview snapshot (issue #14): see blur.sh — same lifecycle.
SNAPSHOT_DIR="${XDG_RUNTIME_DIR:-/tmp}/omarchy-customizer"
SNAPSHOT="$SNAPSHOT_DIR/opacity-preview"

names() { local p; for p in "${PRESETS[@]}"; do echo "${p%% *}"; done; }

lookup() { # $1 = name -> "active inactive", fails when unknown
    local p n a i
    for p in "${PRESETS[@]}"; do
        read -r n a i <<<"$p"
        [[ $n == "$1" ]] && { echo "$a $i"; return 0; }
    done
    return 1
}

current() {
    local c
    { read -r c _ <"$STATE"; } 2>/dev/null || true
    lookup "${c:-}" >/dev/null 2>&1 && echo "$c" || echo "$DEFAULT"
}

notify() { # $1 = title, $2 = body
    # Replace the previous toast by id so repeated presses update one toast.
    local idf="$STATE_DIR/opacity-notify-id" id
    id="$(cat "$idf" 2>/dev/null || echo 0)"
    omarchy notification send -p -r "$id" -t 1500 -g 󰂵 --app-name "Opacity" \
        "$1" "$2" >"$idf" 2>/dev/null || true
}

set_opacity() { # $1 = name; fails when unknown
    local a i
    read -r a i < <(lookup "$1") || return 1
    hyprctl eval "hl.config({ decoration = { active_opacity = $a, inactive_opacity = $i } })" >/dev/null
}

live_opacity() { # -> "active inactive", fails when unreadable
    local a i
    a="$(hyprctl getoption decoration:active_opacity -j 2>/dev/null | jq -r '.float // empty' 2>/dev/null)" || return 1
    i="$(hyprctl getoption decoration:inactive_opacity -j 2>/dev/null | jq -r '.float // empty' 2>/dev/null)" || return 1
    [[ -n $a && -n $i ]] || return 1
    echo "$a $i"
}

match_preset() { # $1..$2 = active inactive -> preset name, fails when none matches
    local a="$1" i="$2" row name ra ri
    for row in "${PRESETS[@]}"; do
        read -r name ra ri <<<"$row"
        if awk -v x="$ra" -v y="$a" -v u="$ri" -v w="$i" 'BEGIN { p = x - y; if (p < 0) p = -p; q = u - w; if (q < 0) q = -q; exit !(p < 0.001 && q < 0.001) }'; then
            echo "$name"
            return 0
        fi
    done
    return 1
}

set_opacity_raw() { # $1..$2 = active inactive; re-applies exact live values, no state write
    local a="$1" i="$2"
    hyprctl eval "hl.config({ decoration = { active_opacity = $a, inactive_opacity = $i } })" >/dev/null
}

restore_live() {
    # No saved preset. Prefer the pre-preview snapshot (taken by preview):
    # it holds the values from before the hover, while live is now the
    # previewed preset. Without a snapshot, keep whatever is live now
    # instead of letting the reload snap it to the Hyprland config default
    # (same bug class as blur.sh, issue #14). Never write state here — a
    # hover must not persist — and never reload: the reload would re-fire
    # configreloaded and clobber the other script's restore. When the
    # compositor cannot be read at all, do nothing.
    local live a i name
    if [[ -s $SNAPSHOT ]]; then
        read -r a i <"$SNAPSHOT"
        rm -f "$SNAPSHOT"
    else
        live="$(live_opacity)" || return 0
        read -r a i <<<"$live"
    fi
    if name="$(match_preset "$a" "$i")"; then
        set_opacity "$name"
    else
        set_opacity_raw "$a" "$i"
    fi
}

preview() { # $1 = name; snapshot the pre-preview live values once, then apply without saving
    local live
    lookup "$1" >/dev/null 2>&1 || return 1
    if [[ ! -s $SNAPSHOT ]]; then
        if live="$(live_opacity 2>/dev/null)"; then
            mkdir -p "$SNAPSHOT_DIR"
            echo "$live" >"$SNAPSHOT"
        fi
    fi
    set_opacity "$1"
}

apply() { # $1 = name
    local a i
    set_opacity "$1" || { notify "$(t "No such preset")" "$1"; exit 1; }
    read -r a i < <(lookup "$1")
    echo "$1 $a $i" >"$STATE"
    rm -f "$SNAPSHOT" # the preview session (if any) is over; don't let a stale snapshot linger
    notify "$(t "Transparency: %s" "$1")" "$(t "active window %s · inactive %s" "$a" "$i")"
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
restore) if [[ -s $STATE ]]; then set_opacity "$(current)"; else restore_live; fi ;;
current) current ;;
list)
    cur="$(current)"
    for p in "${PRESETS[@]}"; do
        read -r n a i <<<"$p"
        echo "$n $a $i $([[ $n == "$cur" ]] && echo 1 || echo 0)"
    done
    ;;
*) echo "usage: $0 [next|prev|set <name>|preview <name>|restore|list|current]" >&2; exit 1 ;;
esac
