#!/usr/bin/env python3
import os
from pathlib import Path

APPLICATION_NAME = "pawlette"

# Получаем пути в соответствии с XDG стандартами
XDG_DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CACHE_HOME = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_STATE_HOME = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))

APP_FOLDER = Path(__file__).resolve().parent

# Пути для данных, кэша и конфигураций приложения
APP_CONFIG_DIR = XDG_CONFIG_HOME / APPLICATION_NAME
APP_DATA_DIR = XDG_DATA_HOME / APPLICATION_NAME
APP_CACHE_DIR = XDG_CACHE_HOME / APPLICATION_NAME
APP_BACKUP_DIR = XDG_STATE_HOME / APPLICATION_NAME / "backups"

APP_CONFIG_FILE = APP_CONFIG_DIR / (APPLICATION_NAME + ".json")

THEMES_FOLDER = APP_DATA_DIR / "themes"
SYS_THEMES_FOLDER = Path(f"/usr/share/{APPLICATION_NAME}")


# Форматы комментариев для разных расширений
COMMENT_FORMATS = {
    ".json": "//",
    ".conf": "#",
    ".yaml": "#",
    ".toml": "#",
}


DEFAULT_CONFIG = {
    "max_backups": 5,
    "comment_styles": COMMENT_FORMATS,
}
