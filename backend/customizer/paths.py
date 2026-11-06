"""Пути к конфигам и состоянию — те же, что в начале customizer.sh."""
import os
from pathlib import Path

HOME = Path(os.environ.get("HOME", str(Path.home())))
PLUGIN = Path(__file__).resolve().parent.parent.parent      # каталог плагина
CONFIG = HOME / ".config/omarchy"
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state") / "omarchy-customizer"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache")
RUN = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / "omarchy-customizer"

SETTINGS_JSON = PLUGIN / "settings.json"
I18N_DIR = PLUGIN / "i18n"
LEGACY = PLUGIN / "customizer.sh"

SHELL_JSON = CONFIG / "shell.json"
BAR_SKIN = CONFIG / "bar-skin.json"
CUSTOMIZER_JSON = CONFIG / "customizer.json"
THEME_COLORS = HOME / ".local/state/omarchy/current/theme/colors.toml"
THEME_NAME = HOME / ".local/state/omarchy/current/theme.name"
CURRENT_BG = HOME / ".local/state/omarchy/current/background"


def expand(path: str) -> Path:
    """«~/…» из settings.json → абсолютный путь."""
    return HOME / path[2:] if path.startswith("~/") else Path(path)


def tilde(path) -> str:
    """Абсолютный путь → «~/…» для подписей (как ${f/#$HOME/\\~})."""
    s, h = str(path), str(HOME)
    return "~" + s[len(h):] if s.startswith(h) else s
