#!/usr/bin/env bash
# Regression test for install.sh: the fork's repo is what gets added, bad flags print usage and exit 2,
# --with validates its list, a run without a terminal installs the Customizer alone without the
# "/dev/tty" noise, and a second run leaves a single Super+Shift+T bind. Everything runs in a temp HOME
# with `omarchy`, `hyprctl` and `fc-cache` stubbed on PATH, so the real desktop is never touched.
#
#   /usr/bin/bash tests/test_install.sh
set -euo pipefail

PLUGIN="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
fails=0
check() { # $1 = name, $2.. = test command
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "ok    $name"; else echo "FAIL  $name"; fails=$((fails + 1)); fi
}

root="$(mktemp -d "${TMPDIR:-/tmp}/install-test.XXXXXX")"
trap 'rm -rf "$root"' EXIT
mkdir -p "$root/bin" "$root/home/.config/hypr"
LOG="$root/calls.log"
printf -- '-- user binding\no.bind("SUPER + RETURN", "Terminal", "xdg-terminal")\n' >"$root/home/.config/hypr/bindings.lua"

# `omarchy plugin add URL …` records the URL and fakes the install: the Customizer is the plugin
# checkout itself (fonts/ must exist for the DOT-MATRIX link), companions get a bare manifest.
cat >"$root/bin/omarchy" <<STUB
#!/usr/bin/env bash
echo "omarchy \$*" >>"$LOG"
if [[ \$1 == plugin && \$2 == add ]]; then
  name=\${3##*/}
  case \$name in
    omarchy-customizer|omtopia-personalizer) id=kamradsmeshnyavy.customizer ;;
    omarchy-bar-skins) id=kamradsmeshnyavy.bar ;;
    omarchy-lock-designs) id=kamradsmeshnyavy.lock ;;
    omarchy-wallpaper-fx) id=kamradsmeshnyavy.background ;;
    omarchy-image-picker-styles) id=kamradsmeshnyavy.image-picker ;;
    omarchy-launcher-skins) id=kamradsmeshnyavy.menu ;;
    *) id=unknown.\$name ;;
  esac
  mkdir -p "\$HOME/.config/omarchy/plugins"
  if [[ \$id == kamradsmeshnyavy.customizer ]]; then
    ln -sfn "$PLUGIN" "\$HOME/.config/omarchy/plugins/\$id"
  else
    mkdir -p "\$HOME/.config/omarchy/plugins/\$id"; echo '{}' >"\$HOME/.config/omarchy/plugins/\$id/manifest.json"
  fi
fi
STUB
printf '#!/usr/bin/env bash\necho "hyprctl $*" >>"%s"\n' "$LOG" >"$root/bin/hyprctl"
printf '#!/usr/bin/env bash\necho "fc-cache $*" >>"%s"\n' "$LOG" >"$root/bin/fc-cache"
chmod +x "$root/bin/"*

# Run install.sh in the sandbox; sets $code (exit status) and $out (stdout+stderr).
install() {
    code=0
    out="$(env -i HOME="$root/home" PATH="$root/bin:/usr/bin:/bin" bash "$PLUGIN/install.sh" "$@" 2>&1)" || code=$?
}
# Same, but with no controlling terminal (as under `curl … | bash` in a cron-like shell).
install_notty() {
    code=0
    out="$(env -i HOME="$root/home" PATH="$root/bin:/usr/bin:/bin" setsid -w bash "$PLUGIN/install.sh" </dev/null 2>&1)" || code=$?
}
added() { grep -c '^omarchy plugin add ' "$LOG" || true; }
has() { [[ $out == *"$1"* ]]; } # $out holds the last run's stdout+stderr
reset() { rm -rf "$root/home/.config/omarchy" "$root/home/.local" "$LOG"; : >"$LOG"; }

# --all: the Customizer from this fork, then every companion from its own repo.
reset; install --all
check "--all: exits 0" test "$code" = "0"
check "--all: six plugins added" test "$(added)" = "6"
check "--all: the Customizer comes from the fork, not the upstream repo" \
    grep -q '^omarchy plugin add https://github.com/AventurineDream/omtopia-personalizer --enable --yes$' "$LOG"
check "--all: companions come from KamradSmeshnyavy" \
    test "$(grep -c '^omarchy plugin add https://github.com/KamradSmeshnyavy/omarchy-' "$LOG")" = "5"
check "--all: DOT-MATRIX fonts linked into ~/.local/share/fonts" \
    test "$(readlink "$root/home/.local/share/fonts/dotmatrix")" = "$root/home/.config/omarchy/plugins/kamradsmeshnyavy.customizer/fonts"
check "--all: shell restart requested" grep -q '^omarchy restart shell$' "$LOG"

# --with: only the listed companions, the Customizer always.
reset; install --with bar,lock
check "--with bar,lock: exits 0" test "$code" = "0"
check "--with bar,lock: customizer + bar + lock only" test "$(added)" = "3"
check "--with bar,lock: no wallpaper-fx" bash -c "! grep -q omarchy-wallpaper-fx '$LOG'"
reset; install --with=fx
check "--with=fx: customizer + fx" test "$(added)" = "2"

# --none and a second run: one bind line, no duplicate plugin adds.
reset; install --none
check "--none: only the Customizer" test "$(added)" = "1"
check "--none: bind added" grep -q 'o.bind("SUPER + SHIFT + T"' "$root/home/.config/hypr/bindings.lua"
install --none
check "second run: exits 0" test "$code" = "0"
check "second run: still one Super+Shift+T bind" test "$(grep -c 'SUPER + SHIFT + T' "$root/home/.config/hypr/bindings.lua")" = "1"
check "second run: existing bind line kept" grep -q 'SUPER + RETURN' "$root/home/.config/hypr/bindings.lua"
check "second run: no second plugin add" test "$(added)" = "1"

# Bad input: usage on stderr, nothing installed, nonzero exit.
reset; install --bogus
check "unknown flag: exit 2" test "$code" = "2"
check "unknown flag: usage printed" has "usage:"
check "unknown flag: nothing added" test "$(added)" = "0"
reset; install --with
check "--with without a list: exit 2" test "$code" = "2"
reset; install --with bar,nope
check "--with unknown companion: exit 2 and named" test "$code" = "2"
check "--with unknown companion: message names it" has "unknown companion: nope"
check "--with unknown companion: nothing added" test "$(added)" = "0"
# A glob in the list is a name to reject, not a pattern for the files in the current directory.
mkdir -p "$root/globdir" && touch "$root/globdir/bar" "$root/globdir/lock"
pushd "$root/globdir" >/dev/null
reset; install --with '*'
popd >/dev/null
check "--with '*' from a directory with files: exit 2" test "$code" = "2"
check "--with '*': message names the glob, not a file" has "unknown companion: *"
reset; install --with 'bar, lock'
check "--with 'bar, lock': blanks trimmed, three plugins" test "$(added)" = "3"
reset; install -h
check "-h: exit 0" test "$code" = "0"
check "-h: usage printed" has "usage:"

# No terminal to ask on: the Customizer alone, with one notice and no /dev/tty errors.
if command -v setsid >/dev/null; then
    reset; install_notty
    check "no terminal: exits 0" test "$code" = "0"
    check "no terminal: only the Customizer added" test "$(added)" = "1"
    check "no terminal: notice names the way to add companions" has "--all or --with bar,lock"
    check "no terminal: no /dev/tty error" bash -c '! grep -q /dev/tty <<<"$1"' _ "$out"
else
    echo "skip  no terminal: setsid not installed"
fi

echo "$fails failure(s)"
exit "$fails"
