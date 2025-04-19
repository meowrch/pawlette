#!/usr/bin/env python3
import os
from pathlib import Path

from pawlette.enums.session_type import LinuxSessionType
from pawlette.schemas.commands import CommandInfo

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
APP_STATE_DIR = XDG_STATE_HOME / APPLICATION_NAME

APP_BACKUP_DIR = APP_STATE_DIR / "backups"
APP_CONFIG_FILE = APP_CONFIG_DIR / (APPLICATION_NAME + ".json")
VERSIONS_FILE = APP_STATE_DIR / "installed_themes.json"
THEMES_FOLDER = APP_DATA_DIR / "themes"
SYS_THEMES_FOLDER = Path(f"/usr/share/{APPLICATION_NAME}")

##==> Application paths
##############################################################
DEFAULT_THEME_LOGO = APP_FOLDER / "assets" / "default-theme-logo.png"
THEME_WALLPAPERS_SYMLINK = APP_DATA_DIR / "theme_wallpapers"
GTK_THEME_SYMLINK_DIR = (Path.home() / ".themes").absolute()
ICON_THEME_SYMLINK_DIR = (Path.home() / ".icons").absolute()

##==> Ссылка на список официальных тем
THEMES_LIST_URL = (
    "https://raw.githubusercontent.com/meowrch/meowrch-themes/main/themes.list"
)


##==> Команды перезагрузки для приложений
RELOAD_COMMANDS = {
    "hypr": CommandInfo(command="hyprctl reload", check_command_exists="hyprctl"),
    "waybar": CommandInfo(command="killall -SIGUSR2 waybar", check_process="waybar"),
    "kitty": CommandInfo(command="killall -SIGUSR1 kitty", check_process="kitty"),
    "cava": CommandInfo(command="killall -USR1 cava", check_process="cava"),
    "dunst": CommandInfo(command="killall -HUP dunst", check_process="dunst"),
    "tmux": CommandInfo(
        command="tmux source ~/.config/tmux/tmux.conf", check_process="tmux"
    ),
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
