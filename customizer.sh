#!/usr/bin/env bash
# Точка входа бэкенда Customizer. Сам бэкенд — на Python: backend/ (CLI и постоянный режим
# `serve` для overlay), описания настроек — settings.json. Этот скрипт оставлен, потому что его
# зовут overlay, хук смены темы, меню и fzf-скрипт: customizer.sh <команда> … как раньше.
# Прежний bash-бэкенд — tests/legacy/customizer.sh (эталон для tests/compare_*.py).
exec /usr/bin/python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/backend/run.py" "$@"
