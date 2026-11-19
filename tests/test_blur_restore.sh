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
# Все песочницы кейсов лежат в одном каталоге: /tmp здесь tmpfs (RAM), а trap удаляет его
# после зелёного прогона; при провале каталог остаётся, путь печатается.
BASE="$(mktemp -d)"
cleanup() {
    local rc=$?
    if ((rc == 0)); then rm -rf -- "$BASE"; else echo "песочницы сохранены: $BASE" >&2; fi
}
trap cleanup EXIT
check() { # $1 = name, $2.. = test command
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "ok    $name"; else echo "FAIL  $name"; fails=$((fails + 1)); fi
}

# Run any subcommand, capturing its exit code without tripping `set -e`.
# Usage: run_script <script> <root> <args...> — sets $code.
run_script() {
    local script="$1" root="$2"; shift 2
    code=0
    env -i PATH="$root/stubs:/usr/bin:/bin" HOME="$root/home" XDG_STATE_HOME="$root/state" XDG_RUNTIME_DIR="$root/run" FAKE_STATE="$root/state" FAKE_HYPRCTL_MODE=ok \
        bash "$PLUGIN/scripts/$script" "$@" || code=$?
}

# Run a restore, capturing its exit code without tripping `set -e`.
# Usage: restore <script> <root> — sets $code.
restore() {
    run_script "$1" "$2" restore
}

# Run a preview, capturing its exit code without tripping `set -e`.
# Usage: preview <script> <root> <name> — sets $code.
preview() {
    run_script "$1" "$2" preview "$3"
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
    root="$(mktemp -d "$BASE/case.XXXXXX")"
    mkdir -p "$root/home" "$root/state" "$root/stubs" "$root/run"
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
check "blur restore, no state, live medium: no state file written" test ! -e "$r/state/hypr/blur"
check "blur restore, no state, live medium: no reload" test "$(grep -c "hyprctl reload" "$r/state/calls.log")" = "0"

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
check "blur restore, no state, live off: no state file written" test ! -e "$r/state/hypr/blur"

# 4. blur, no state, compositor unreadable: nothing happens, exit 0.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" fail)"
code=0
env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" XDG_RUNTIME_DIR="$r/run" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=fail \
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
check "opacity restore, no state, live frosted: no state file written" test ! -e "$r/state/hypr/opacity"

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

# 9. Fresh system (no state file): no preset is in use, as opacity.sh. `current` and `list` mark none, and the
#    first next or prev applies the default (medium). A blur named by `set` (styles, presets) is in use afterwards.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
err="$(env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" XDG_RUNTIME_DIR="$r/run" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=ok \
    bash "$PLUGIN/scripts/blur.sh" current 2>&1 >/dev/null)"
check "blur current, no state: no stderr noise" test -z "$err"
check "blur current, no state: prints nothing (no preset in use)" test -z "$(run_script blur.sh "$r" current)"
check "blur list, no state: no row is marked in use" test -z "$(run_script blur.sh "$r" list | awk '$6 == 1')"
err="$(env -i PATH="$r/stubs:/usr/bin:/bin" HOME="$r/home" XDG_STATE_HOME="$r/state" XDG_RUNTIME_DIR="$r/run" FAKE_STATE="$r/state" FAKE_HYPRCTL_MODE=ok \
    bash "$PLUGIN/scripts/opacity.sh" current 2>&1 >/dev/null)"
check "opacity current, no state: no stderr noise" test -z "$err"

r="$(setup "true 4 2 0.00 0.000 0.85 0.70" ok)"
run_script blur.sh "$r" next
check "blur next, fresh: exits 0" test "$code" = "0"
check "blur next, fresh: applies the default medium" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur next, fresh: medium is now in use" test "$(run_script blur.sh "$r" current)" = "medium"
check "blur next, fresh: state file is medium" test "$(cat "$r/state/hypr/blur")" = "medium 6 3 0.17 0.012"

r="$(setup "true 4 2 0.00 0.000 0.85 0.70" ok)"
run_script blur.sh "$r" prev
check "blur prev, fresh: exits 0" test "$code" = "0"
check "blur prev, fresh: applies the default medium too" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur prev, fresh: medium is now in use" test "$(run_script blur.sh "$r" current)" = "medium"

r="$(setup "true 4 2 0.00 0.000 0.85 0.70" ok)"
run_script blur.sh "$r" set strong
check "blur set strong, fresh: exits 0" test "$code" = "0"
check "blur set strong, fresh: strong is live" test "$(live_field "$r" 1-5)" = "true 10 4 0.20 0.015"
check "blur set strong, fresh: strong is in use" test "$(run_script blur.sh "$r" current)" = "strong"
run_script blur.sh "$r" next
check "blur next after set strong: continues from strong to frosted" test "$(run_script blur.sh "$r" current)" = "frosted"

# 9b. A stale saved name (renamed or removed preset): no preset is in use, and restore keeps the live blur.
r="$(setup "true 5 2 0.13 0.007 0.85 0.70" ok)"
mkdir -p "$r/state/hypr" && echo "frosty 1 1 0.00 0.000" >"$r/state/hypr/blur"
check "blur current, stale saved name: prints nothing" test -z "$(run_script blur.sh "$r" current)"
restore blur.sh "$r"
check "blur restore, stale saved name: exits 0" test "$code" = "0"
check "blur restore, stale saved name: live blur kept verbatim, not medium" test "$(live_field "$r" 1-5)" = "true 5 2 0.13 0.007"

# 10. blur preview then restore: the hover does not persist.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
preview blur.sh "$r" strong
check "blur preview strong: exits 0" test "$code" = "0"
check "blur preview strong: live blur becomes strong" test "$(live_field "$r" 1-5)" = "true 10 4 0.20 0.015"
check "blur preview strong: snapshot holds the pre-preview medium" test "$(cat "$r/run/omarchy-customizer/blur-preview")" = "true 6 3 0.17 0.012"
check "blur preview strong: no state file written" test ! -e "$r/state/hypr/blur"
restore blur.sh "$r"
check "blur preview->restore: exits 0" test "$code" = "0"
check "blur preview->restore: live blur back to medium" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur preview->restore: no state file written" test ! -e "$r/state/hypr/blur"
check "blur preview->restore: snapshot consumed" test ! -e "$r/run/omarchy-customizer/blur-preview"
check "blur preview->restore: no reload" test "$(grep -c "hyprctl reload" "$r/state/calls.log")" = "0"

# 11. blur preview twice: the second preview keeps the original snapshot.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
preview blur.sh "$r" strong
preview blur.sh "$r" light
check "blur preview strong then light: live blur becomes light" test "$(live_field "$r" 1-5)" = "true 3 2 0.10 0.010"
check "blur preview strong then light: snapshot still the pre-preview medium" test "$(cat "$r/run/omarchy-customizer/blur-preview")" = "true 6 3 0.17 0.012"
restore blur.sh "$r"
check "blur preview x2->restore: live blur back to medium" test "$(live_field "$r" 1-5)" = "true 6 3 0.17 0.012"
check "blur preview x2->restore: no state file written" test ! -e "$r/state/hypr/blur"

# 12. opacity preview then restore: the hover does not persist.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
preview opacity.sh "$r" glass
check "opacity preview glass: exits 0" test "$code" = "0"
check "opacity preview glass: live opacity becomes glass" test "$(live_field "$r" 6-7)" = "0.90 0.80"
check "opacity preview glass: snapshot holds the pre-preview frosted" test "$(cat "$r/run/omarchy-customizer/opacity-preview")" = "0.85 0.70"
check "opacity preview glass: no state file written" test ! -e "$r/state/hypr/opacity"
restore opacity.sh "$r"
check "opacity preview->restore: exits 0" test "$code" = "0"
check "opacity preview->restore: live opacity back to frosted" test "$(live_field "$r" 6-7)" = "0.85 0.70"
check "opacity preview->restore: no state file written" test ! -e "$r/state/hypr/opacity"
check "opacity preview->restore: snapshot consumed" test ! -e "$r/run/omarchy-customizer/opacity-preview"

# 13. blur preview then an explicit set: the snapshot is cleared, the set wins.
r="$(setup "true 6 3 0.17 0.012 0.85 0.70" ok)"
preview blur.sh "$r" strong
run_script blur.sh "$r" set light
check "blur preview then set light: exits 0" test "$code" = "0"
check "blur preview then set light: live blur becomes light" test "$(live_field "$r" 1-5)" = "true 3 2 0.10 0.010"
check "blur preview then set light: state file is light" test "$(cat "$r/state/hypr/blur")" = "light 3 2 0.10 0.010"
check "blur preview then set light: snapshot cleared" test ! -e "$r/run/omarchy-customizer/blur-preview"

# 14. rollback values: `live` reads the compositor, `set-live` re-applies exact values with no preset in use.
r="$(setup "true 4 2 0.00 0.000 0.85 0.70" ok)"
check "blur live: prints the five live fields" test "$(run_script blur.sh "$r" live)" = "true 4 2 0.00 0.000"
echo "frosty 1 1 0.00 0.000" >"$r/state/hypr/blur"
run_script blur.sh "$r" set-live "true 5 2 0.13 0.007"
check "blur set-live: exits 0" test "$code" = "0"
check "blur set-live: live blur becomes the exact values" test "$(live_field "$r" 1-5)" = "true 5 2 0.13 0.007"
check "blur set-live: state file removed (no preset in use)" test ! -e "$r/state/hypr/blur"
check "blur set-live: current is empty" test -z "$(run_script blur.sh "$r" current)"
check "blur set-live: no snapshot left behind" test ! -e "$r/run/omarchy-customizer/blur-preview"
run_script blur.sh "$r" set-live "true 4 2 0.00 0.000; os.exit()"
check "blur set-live, garbage: exits non-zero" test "$code" != "0"
check "blur set-live, garbage: live blur untouched" test "$(live_field "$r" 1-5)" = "true 5 2 0.13 0.007"
run_script blur.sh "$r" set-live "false 4 2 0.00 0.000"
check "blur set-live, off: live blur off" test "$(live_field "$r" 1)" = "false"

echo "$fails failure(s)"
exit "$fails"
