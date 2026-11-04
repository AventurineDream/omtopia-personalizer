#!/usr/bin/env bash
# Один раз после переименования стиля NIHIL → DOT-MATRIX: переносит настройки и состояние пользователя.
#   - ~/.config/omarchy/nihil.json → dotmatrix.json (ключи nihilBg… → dotmatrixBg…);
#   - значения в ~/.config/omarchy/**/*.json и в состоянии Customizer: nihil → dotmatrix, NIHIL → DOT-MATRIX,
#     шрифты «Nihil Dot/Mono/Pixel» → «DotMatrix …», тема nihil → dot-matrix;
#   - шрифты: ссылка ~/.local/share/fonts/nihil → dotmatrix, сборка nihil-build — в корзину, Mono/Pixel пересобираются;
#   - тема: ссылка ~/.config/omarchy/themes/nihil → dot-matrix (если тема из dotfiles), активная тема nihil → dot-matrix.
# Повторный запуск ничего не ломает.
set -uo pipefail

CUSTOMIZER_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)
OMARCHY=$HOME/.config/omarchy
STATE=${XDG_STATE_HOME:-$HOME/.local/state}
FONTS=$HOME/.local/share/fonts

# Те же правила, что у переименования в коде (атрибуция исходного NIHIL / Nihil-Shell не трогается).
migrate_text() {
  python3 -I -c '
import re, sys
text = sys.stdin.read()
keep = {}
def hide(m):
    k = "\x00%d\x00" % len(keep); keep[k] = m.group(0); return k
for p in (r"(?i)nihil-shell", r"(?i)nihilshell", r"(?i)nihilo", r"poligle"):
    text = re.sub(p, hide, text)
text = text.replace("nihil-boot", "dot-matrix-boot")
text = re.sub(r"themes/nihil\b", "themes/dot-matrix", text)
text = re.sub(r"(\"theme\"\s*:\s*\")nihil(\")", r"\1dot-matrix\2", text)
text = re.sub(r"Nihil (Dot|Mono|Pixel)", r"DotMatrix \1", text)
text = text.replace("NIHIL_", "DOTMATRIX_")
text = re.sub(r"NIHIL(?![A-Za-z0-9_])", "DOT-MATRIX", text)
text = re.sub(r"Nihil(?=[A-Za-z0-9_.])", "DotMatrix", text)
text = text.replace("Nihil", "DOT-MATRIX").replace("nihil", "dotmatrix")
for k, v in keep.items(): text = text.replace(k, v)
sys.stdout.write(text)'
}

migrate_file() {
  local f=$1 tmp
  [[ -f $f && ! -L $f ]] || return 0
  grep -qi nihil "$f" 2>/dev/null || return 0
  tmp=$(mktemp "$f.XXXXXX") || return 0
  if migrate_text <"$f" >"$tmp"; then
    chmod --reference="$f" "$tmp" 2>/dev/null
    mv -f "$tmp" "$f"
    echo "migrated: ${f/#$HOME/\~}"
  else
    mv -f "$tmp" "$f.failed"
  fi
}

# 1. Палитра стиля
if [[ -f $OMARCHY/nihil.json && ! -e $OMARCHY/dotmatrix.json ]]; then
  migrate_text <"$OMARCHY/nihil.json" >"$OMARCHY/dotmatrix.json" && gio trash "$OMARCHY/nihil.json" && echo "nihil.json → dotmatrix.json"
fi

# 2. Настройки и состояние
while IFS= read -r -d '' f; do migrate_file "$f"; done < <(
  find "$OMARCHY" -maxdepth 3 \( -path "$OMARCHY/themes" -o -path "$OMARCHY/backgrounds" -o -path "$OMARCHY/plugins" \) -prune \
    -o -type f \( -name '*.json' -o -name '*.toml' \) -print0 2>/dev/null
  find "$STATE/omarchy-customizer" -maxdepth 1 -type f -print0 2>/dev/null
  # активные пресеты прозрачности / блюра («nihil 1.00 0.85»)
  find "$STATE/hypr" -maxdepth 1 -type f \( -name opacity -o -name blur \) -print0 2>/dev/null
)
[[ -f $STATE/omarchy/current/theme.name && $(<"$STATE/omarchy/current/theme.name") == nihil ]] && NEED_THEME=1

# 3. Шрифты: ссылка на fonts/ плагина и пересборка DotMatrix Mono / Pixel
if [[ -L $FONTS/nihil ]]; then
  ln -sfn "$CUSTOMIZER_DIR/fonts" "$FONTS/dotmatrix" && unlink "$FONTS/nihil" && echo "fonts: nihil → dotmatrix"
fi
[[ -e $FONTS/dotmatrix ]] || ln -sfn "$CUSTOMIZER_DIR/fonts" "$FONTS/dotmatrix"
if [[ -d $FONTS/nihil-build ]]; then
  gio trash "$FONTS/nihil-build" && echo "fonts: nihil-build → trash"
fi
# Старое правило fontconfig «sans-serif → шрифт профиля»: идёт по алфавиту после 60-dotmatrix-fonts.conf и
# перебивало текущий профиль (сайты, Arial, интерфейсы расширений получали шрифт прежнего профиля).
FC_OLD="$HOME/.config/fontconfig/conf.d/60-nihil-fonts.conf"
if [[ -f $FC_OLD ]]; then
  gio trash "$FC_OLD" && echo "fontconfig: 60-nihil-fonts.conf → trash"
fi
[[ -d $HOME/.cache/nihil-fonts ]] && gio trash "$HOME/.cache/nihil-fonts"
fc-cache -f "$FONTS" >/dev/null 2>&1 || true
if command -v omarchy-font-profile >/dev/null; then
  omarchy-font-profile build-fonts >/dev/null 2>&1 && echo "fonts: DotMatrix Mono / Pixel built"
  omarchy-font-profile apply >/dev/null 2>&1 || true
fi

# 4. Тема из dotfiles: ссылка в ~/.config/omarchy/themes
if [[ -L $OMARCHY/themes/nihil ]]; then
  target=$(readlink "$OMARCHY/themes/nihil")
  new=${target%/nihil}/dot-matrix
  if [[ -d $new ]]; then
    ln -sfn "$new" "$OMARCHY/themes/dot-matrix" && unlink "$OMARCHY/themes/nihil" && echo "theme link: nihil → dot-matrix"
  fi
fi
if [[ ${NEED_THEME:-} == 1 ]] && command -v omarchy >/dev/null; then
  omarchy theme set dot-matrix && echo "theme: dot-matrix"
fi
echo "done"
