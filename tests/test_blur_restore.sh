#!/usr/bin/env bash
# Regression test for issue #14: `blur.sh restore` / `opacity.sh restore` with
# no saved preset must keep the live values, not fall back to the Hyprland
# config default. No compositor needed: a fake hyprctl answers getoption from
# a live-state file, applies evals to it, and snaps it to the config default
# on reload (blur 4/2 dotmatrix-sized, opacity solid) — exactly the old bug.
#
#   /usr/bin/bash tests/test_blur_restore.sh
set -euo pipefail

PLUGIN="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
fails=0
check() { # $1 = name, $2.. = test command
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "ok    $name"; else echo "FAIL  $name"; fails=$((fails + 1)); fi
}

# Run a restore, capturing its exit code without tripping `set -e`.
# Usage: restore <script> <root> — sets $code.
restore() {
    local script="$1" root="$2"
    code=0
    env -i PATH="$root/stubs:/usr/bin:/bin" HOME="$root/home" XDG_STATE_HOME="$root/state" FAKE_STATE="$root/state" FAKE_HYPRCTL_MODE=ok \
        bash "$PLUGIN/scripts/$script" restore || code=$?
}

# Fake hyprctl: live.txt holds "enabled size passes vibrancy noise active inactive".
write_stub() {
    local dir="$1" mode="$2"
    cat >"$dir/hyprctl" <<'STUB'
#!/usr/bin/env bash
live="$FAKE_STATE/live.txt"
echo "hyprctl $*" >>"$FAKE_STATE/calls.log"
if [[ $FAKE_HYPRCTL_MODE == fail ]]; then exit 1; fi
read -r en s p v n a i <"$live"
case "$1" in
  getoption)
    case "$2" in
      decoration:blur:enabled) echo "{\"option\": \"$2\", \"bool\": $en, \"set\": true }" ;;
      decoration:blur:size) echo "{\"option\": \"$2\", \"int\": $s, \"set\": true }" ;;
      decoration:blur:passes) echo "{\"option\": \"$2\", \"int\": $p, \"set\": true }" ;;
      decoration:blur:vibrancy) echo "{\"option\": \"$2\", \"float\": $v, \"set\": true }" ;;
      decoration:blur:noise) echo "{\"option\": \"$2\", \"float\": $n, \"set\": true }" ;;
      decoration:active_opacity) echo "{\"option\": \"$2\", \"float\": $a, \"set\": true }" ;;
      decoration:inactive_opacity) echo "{\"option\": \"$2\", \"float\": $i, \"set\": true }" ;;
    esac
    ;;
  eval)
    arg="$2"
    if [[ $arg == *blur* ]]; then
      en="$(sed -n -E 's/.*enabled = (true|false).*/\1/p' <<<"$arg")"
      s="$(sed -n -E 's/.*size = ([0-9]+).*/\1/p' <<<"$arg")"
      p="$(sed -n -E 's/.*passes = ([0-9]+).*/\1/p' <<<"$arg")"
      v="$(sed -n -E 's/.*vibrancy = ([0-9.]+).*/\1/p' <<<"$arg")"
      n="$(sed -n -E 's/.*noise = ([0-9.]+).*/\1/p' <<<"$arg")"
    elif [[ $arg == *opacity* ]]; then
      a="$(sed -n -E 's/.*[^a-z]active_opacity = ([0-9.]+).*/\1/p' <<<"$arg")"
      i="$(sed -n -E 's/.*inactive_opacity = ([0-9.]+).*/\1/p' <<<"$arg")"
    fi
    echo "$en $s $p $v $n $a $i" >"$live"
    ;;
  reload)
    # Hyprland config default: blur dotmatrix-sized, opacity solid.
    echo "true 4 2 0.00 0.000 1.00 1.00" >"$live"
    ;;
esac
STUB
    chmod +x "$dir/hyprctl"
}

setup() { # $1 = live line, $2 = hyprctl mode (ok|fail) -> prints sandbox dir
    local root
    root="$(mktemp -d)"
    mkdir -p "$root/home" "$root/state" "$root/stubs"
    echo "$1" >"$root/state/live.txt"
    : >"$root/state/calls.log"
    write_stub "$root/stubs" "$2"
    echo "$root"
}

live_field() { # $1 = root, $2.. = field numbers -> values
    local root="$1"; shift
    cut -d' ' -f"$*" "$root/state/live.txt"
}

# 1. blur, no state, live medium: restore keeps medium and anchors it.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
restore blur.sh "$r"
check "blur restore, no state, live medium: exits 0" test "$code" = "0"
check "blur restore, no state, live medium: live blur stays medium" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur restore, no state, live medium: state file anchored" test "$(cat "$r/state/hypr/blur")" = "medium 6 3 0.17 0.012"
check "blur restore, no state, live medium: reload happened" grep -q "hyprctl reload" "$r/state/calls.log"

# 2. blur, no state, live hand-tuned (no preset matches): raw values kept, no state file.
r="$(setup "true 5 2 0.13 0.007 0.85 0.70" ok)"
restore blur.sh "$r"
check "blur restore, no state, live hand-tuned: exits 0" test "$code" = "0"
check "blur restore, no state, live hand-tuned: live blur kept verbatim" test "$(live_field "$r" 1-5)" = "true 5 2 0.13 0.007"
check "blur restore, no state, live hand-tuned: no state file written" test ! -e "$r/state/hypr/blur"

# 3. blur, no state, live off: stays off, anchored as off.
r="$(setup "false 1 1 0.00 0.000 0.85 0.70" ok)"
restore blur.sh "$r"
check "blur restore, no state, live off: exits 0" test "$code" = "0"
check "blur restore, no state, live off: stays off" test "$(live_field "$r" 1)" = "false"
check "blur restore, no state, live off: state file anchored" test "$(cat "$r/state/hypr/blur")" = "off 0 1 0.00 0.000"

# 4. blur, no state, compositor unreadable: nothing happens, exit 0.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" fail)"
code=0
env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=fail \
    bash "$PLUGIN/scripts/blur.sh" restore || code=$?
check "blur restore, no state, hyprctl down: exits 0" test "$code" = "0"
check "blur restore, no state, hyprctl down: live blur untouched" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur restore, no state, hyprctl down: no reload attempted" test "$(grep -c "hyprctl reload" "$r/state/calls.log")" = "0"
check "blur restore, no state, hyprctl down: no state file written" test ! -e "$r/state/hypr/blur"

# 5. blur, state file present: old behaviour — saved preset wins, no reload.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
mkdir -p "$r/state/hypr" && echo "light 3 2 0.10 0.010" >"$r/state/hypr/blur"
restore blur.sh "$r"
check "blur restore, state light: exits 0" test "$code" = "0"
check "blur restore, state light: live blur becomes light" test "$(live_field "$r" 1-5)" = "true 3 2 0.10 0.010"
check "blur restore, state light: no reload" test "$(grep -c "hyprctl reload" "$r/state/calls.log")" = "0"

# 6. opacity, no state, live frosted: restore keeps frosted and anchors it.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
restore opacity.sh "$r"
check "opacity restore, no state, live frosted: exits 0" test "$code" = "0"
check "opacity restore, no state, live frosted: live opacity stays frosted" test "$(live_field "$r" 6-7)" = "0.85 0.70"
check "opacity restore, no state, live frosted: state file anchored" test "$(cat "$r/state/hypr/opacity")" = "frosted 0.85 0.70"

# 7. opacity, no state, live hand-tuned: raw values kept, no state file.
r="$(setup "true 6 3 0.17 0.012 0.93 0.77" ok)"
restore opacity.sh "$r"
check "opacity restore, no state, live hand-tuned: exits 0" test "$code" = "0"
check "opacity restore, no state, live hand-tuned: live opacity kept verbatim" test "$(live_field "$r" 6-7)" = "0.93 0.77"
check "opacity restore, no state, live hand-tuned: no state file written" test ! -e "$r/state/hypr/opacity"

# 8. opacity, state file present: old behaviour.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
mkdir -p "$r/state/hypr" && echo "glass 0.90 0.80" >"$r/state/hypr/opacity"
restore opacity.sh "$r"
check "opacity restore, state glass: exits 0" test "$code" = "0"
check "opacity restore, state glass: live opacity becomes glass" test "$(live_field "$r" 6-7)" = "0.90 0.80"

# 9. `current` with no state file: prints the default with no stderr noise.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
err="$(env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=ok \
    bash "$PLUGIN/scripts/blur.sh" current 2>&1 >/dev/null)"
check "blur current, no state: no stderr noise" test -z "$err"
err="$(env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=ok \
    bash "$PLUGIN/scripts/opacity.sh" current 2>&1 >/dev/null)"
check "opacity current, no state: no stderr noise" test -z "$err"

echo "$fails failure(s)"
exit "$fails"
