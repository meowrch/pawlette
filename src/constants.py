#!/usr/bin/env python3
import os
from pathlib import Path

from enums.session_type import LinuxSessionType

##==> BASE
##############################################################
APPLICATION_NAME = "pawlette"
APP_FOLDER = Path(__file__).resolve().parent

##==> Получаем пути в соответствии с XDG стандартами
##############################################################
XDG_DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CACHE_HOME = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_STATE_HOME = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))

##==> Пути для данных, кэша и конфигураций приложения
##############################################################
APP_CONFIG_DIR = XDG_CONFIG_HOME / APPLICATION_NAME
APP_DATA_DIR = XDG_DATA_HOME / APPLICATION_NAME
APP_CACHE_DIR = XDG_CACHE_HOME / APPLICATION_NAME
APP_BACKUP_DIR = XDG_STATE_HOME / APPLICATION_NAME / "backups"

APP_CONFIG_FILE = APP_CONFIG_DIR / (APPLICATION_NAME + ".json")

THEMES_FOLDER = APP_DATA_DIR / "themes"
SYS_THEMES_FOLDER = Path(f"/usr/share/{APPLICATION_NAME}")

##==> Application paths
##############################################################
DEFAULT_THEME_LOGO = APP_FOLDER / "assets" / "default-theme-logo.png"
THEME_WALLPAPERS_SYMLINK = APP_DATA_DIR / "theme_wallpapers"
GTK_THEME_SYMLINK_DIR = (Path.home() / ".themes").absolute()

##==> Команды перезагрузки для приложений
RELOAD_COMMANDS = {
    "hypr": "hyprctl reload",
    "waybar": "killall -SIGUSR2 waybar",
    "qt5ct": None,
    "qt6ct": None,
    "kitty": "killall -SIGUSR1 kitty",
    "fish": None,
    "starship": None,
}

##==> Форматы комментариев для разных расширений
COMMENT_FORMATS = {
    ".json": "//",
    ".conf": "#",
    ".yaml": "#",
    ".toml": "#",
}

##==> Стандартная конфигурация
DEFAULT_CONFIG = {
    "max_backups": 5,
    "comment_styles": COMMENT_FORMATS,
}


##==> Разное
##############################################################
XSETTINGSD_CONFIG = Path.home() / ".config" / "xsettingsd" / "xsettingsd.conf"
GTK2_CFG: Path = Path.home() / ".config" / "gtk-2.0" / "gtkrc"
GTK3_CFG: Path = Path.home() / ".config" / "gtk-3.0" / "settings.ini"
GTK4_CFG: Path = Path.home() / ".config" / "gtk-4.0" / "settings.ini"
SESSION_TYPE = LinuxSessionType.detect()
