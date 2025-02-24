#!/usr/bin/env python3
import os
from pathlib import Path

APPLICATION_NAME = "pawlette"

# Получаем пути в соответствии с XDG стандартами
XDG_DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CACHE_HOME = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))

APP_FOLDER = Path(__file__).resolve().parent

# Пути для данных, кэша и конфигураций приложения
APP_DATA_DIR = XDG_DATA_HOME / APPLICATION_NAME
APP_CACHE_DIR = XDG_CACHE_HOME / APPLICATION_NAME
APP_CONFIG_DIR = XDG_CONFIG_HOME / APPLICATION_NAME

# Путь к темам (системный каталог)
THEMES_FOLDER = APP_DATA_DIR
SYS_THEMES_FOLDER = Path(f"/usr/share/{APPLICATION_NAME}")
