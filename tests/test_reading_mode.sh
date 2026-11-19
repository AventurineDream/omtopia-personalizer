#!/usr/bin/env bash
# Sandbox test for scripts/reading-mode.sh and the reading_after() dispatch in backend/customizer/tweak_ops.py.
# Covers: a failing brightnessctl (no backlight, or no session bus) must not abort `on`, and `off` must not put
# back a brightness that was never saved; readingBrightness / readingTheme changes apply at once while reading
# (`live`, which must not run the restore path), and do nothing while reading is off.
# brightnessctl, hyprctl, omarchy-theme-* and omarchy are stubs that log their calls; nothing real changes.
#
#   /usr/bin/bash tests/test_reading_mode.sh
set -euo pipefail

PLUGIN="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
fails=0
check() { # $1 = name, $2.. = test command
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "ok    $name"; else echo "FAIL  $name"; fails=$((fails + 1)); fi
}

root="$(mktemp -d)"
trap 'rm -rf "$root"' EXIT
mkdir -p "$root/stubs" "$root/home/.config/omarchy/customizer" "$root/state" "$root/run"
LOG="$root/calls"
BRIGHT="$root/bright"
THEME="$root/theme"
CFG="$root/home/.config/omarchy/customizer/reading-mode.json"
STATE="$root/state/hypr/reading-mode"
: >"$LOG"
echo 40 >"$BRIGHT"
echo take3 >"$THEME"

stub() { # $1 = command name; the body comes from stdin
    { echo '#!/usr/bin/env bash'; cat; } >"$root/stubs/$1"
    chmod +x "$root/stubs/$1"
}
# The backlight is listed, but get and set fail when FAKE_BRIGHTNESS is not ok: a session without a bus.
stub brightnessctl <<'EOF'
echo "brightnessctl $*" >>"$FAKE_LOG"
if [[ $1 == -l ]]; then echo "Device 'intel_backlight' of class 'backlight'"; exit 0; fi
if [[ ${FAKE_BRIGHTNESS:-ok} != ok ]]; then echo "Can't connect to system bus" >&2; exit 1; fi
case "$*" in
*" get") cat "$FAKE_BRIGHT" ;;
*" set "*) v="${*: -1}"; echo "${v%\%}" >"$FAKE_BRIGHT" ;;
esac
EOF
stub hyprctl <<'EOF'
echo "hyprctl $*" >>"$FAKE_LOG"
EOF
stub omarchy-theme-current <<'EOF'
cat "$FAKE_THEME"
EOF
stub omarchy-theme-set <<'EOF'
echo "omarchy-theme-set $*" >>"$FAKE_LOG"
echo "$1" >"$FAKE_THEME"
EOF
stub omarchy <<'EOF'
echo "omarchy $*" >>"$FAKE_LOG"
EOF

# Runs reading-mode.sh with the brightnessctl mode (ok | fail) and the subcommand; sets $code.
rm_run() {
    code=0
    env -i PATH="$root/stubs:/usr/bin:/bin" HOME="$root/home" XDG_STATE_HOME="$root/state" \
        XDG_RUNTIME_DIR="$root/run" FAKE_LOG="$LOG" FAKE_BRIGHT="$BRIGHT" FAKE_THEME="$THEME" \
        FAKE_BRIGHTNESS="$1" bash "$PLUGIN/scripts/reading-mode.sh" "${@:2}" >/dev/null 2>&1 || code=$?
}
write_cfg() { printf '%s\n' "$1" >"$CFG"; }
# Prints what reading_after() runs for a key: "live", "restore", or nothing while reading is off.
dispatch() {
    env -i PATH=/usr/bin:/bin HOME="$root/home" XDG_STATE_HOME="$root/state" python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
from customizer import tweak_ops
tweak_ops._quiet = lambda args: print(" ".join(args[1:]))
tweak_ops.reading_after(sys.argv[2])' "$PLUGIN/backend" "$1"
}

# 1) brightnessctl fails: on still turns the page on; off does not try to put back a brightness it never saved.
write_cfg '{"readingBrightness": 35, "readingTheme": "", "readingShader": "none"}'
: >"$LOG"
rm_run fail on
check "R1 on exits 0 when brightnessctl fails" [ "$code" -eq 0 ]
check "R1 on turns the page on" [ -f "$STATE" ]
check "R1 on remembers no brightness it did not change" bash -c "! grep -q '^brightness=' '$STATE'"
: >"$LOG"
rm_run fail off
check "R1 off exits 0 when brightnessctl fails" [ "$code" -eq 0 ]
check "R1 off turns the page off" [ ! -e "$STATE" ]
check "R1 off calls no brightnessctl when nothing was saved" bash -c "! grep -q '^brightnessctl' '$LOG'"

# 2) brightnessctl works: on remembers the raw value and sets the reading one; off puts the raw value back.
echo 40 >"$BRIGHT"
rm -f "$STATE"
rm_run ok on
check "on remembers the raw brightness" grep -q '^brightness=40$' "$STATE"
check "on sets the reading brightness" [ "$(cat "$BRIGHT")" = 35 ]
rm_run ok off
check "off puts the raw brightness back" [ "$(cat "$BRIGHT")" = 40 ]

# 3) readingBrightness changed while reading: applied at once, the raw value saved at on is kept, no reload.
echo 40 >"$BRIGHT"
rm -f "$STATE"
write_cfg '{"readingBrightness": 35, "readingTheme": "", "readingShader": "none"}'
rm_run ok on
write_cfg '{"readingBrightness": 25, "readingTheme": "", "readingShader": "none"}'
: >"$LOG"
rm_run ok live
check "R2 live applies a changed readingBrightness" [ "$(cat "$BRIGHT")" = 25 ]
check "R2 live keeps the raw brightness saved at on" grep -q '^brightness=40$' "$STATE"
check "R2 live does not reload Hyprland" bash -c "! grep -q '^hyprctl reload' '$LOG'"

# 4) readingTheme changed while reading: applied at once; the theme in use at on is remembered once; off switches back.
rm -f "$STATE"
echo take3 >"$THEME"
write_cfg '{"readingBrightness": 0, "readingTheme": "", "readingShader": "none"}'
rm_run ok on
check "on with an empty readingTheme keeps the theme" [ "$(cat "$THEME")" = take3 ]
write_cfg '{"readingBrightness": 0, "readingTheme": "tokyo-night", "readingShader": "none"}'
: >"$LOG"
rm_run ok live
check "R2 live applies a changed readingTheme" [ "$(cat "$THEME")" = tokyo-night ]
check "R2 live remembers the theme in use" grep -q '^theme=take3$' "$STATE"
check "R2 live does not reload Hyprland itself" bash -c "! grep -q '^hyprctl reload' '$LOG'"
write_cfg '{"readingBrightness": 0, "readingTheme": "catppuccin", "readingShader": "none"}'
rm_run ok live
check "a second theme change applies" [ "$(cat "$THEME")" = catppuccin ]
check "a second theme change keeps the first remembered theme" grep -q '^theme=take3$' "$STATE"
rm_run ok off
check "off switches back to the theme in use before reading" [ "$(cat "$THEME")" = take3 ]

# 5) live while reading is off: nothing runs.
rm -f "$STATE"
echo take3 >"$THEME"
write_cfg '{"readingBrightness": 25, "readingTheme": "tokyo-night", "readingShader": "none"}'
: >"$LOG"
rm_run ok live
check "live does nothing while reading is off (theme)" [ "$(cat "$THEME")" = take3 ]
check "live does nothing while reading is off (no calls)" [ ! -s "$LOG" ]

# 6) dispatch: readingTheme / readingBrightness run live while reading; other reading keys still run restore.
mkdir -p "$(dirname "$STATE")"
: >"$STATE"
check "dispatch readingTheme runs live while reading" [ "$(dispatch readingTheme)" = live ]
check "dispatch readingBrightness runs live while reading" [ "$(dispatch readingBrightness)" = live ]
check "dispatch readingPage still runs restore" [ "$(dispatch readingPage)" = restore ]
rm -f "$STATE"
check "dispatch runs nothing while reading is off" [ -z "$(dispatch readingTheme)" ]

echo
if ((fails)); then echo "FAIL: $fails"; exit 1; fi
echo "all passed"
