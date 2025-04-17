import re
import shutil
import subprocess
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import List

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.utils import create_symlink_dir
from pawlette.enums.session_type import LinuxSessionType
from pawlette.schemas.themes import Theme


class BaseThemeApplier(ABC):
    """Base class for theme appliers with common functionality."""

    @staticmethod
    def _is_command_available(command: str) -> bool:
        """Check if a command is available in the system."""
        return shutil.which(command) is not None

    @staticmethod
    def _update_gtk_config(config_path: Path, config_key: str, theme_name: str) -> bool:
        """
        Updates a GTK config file with the specified theme name.

        Args:
            config_path: Path to the GTK config file
            config_key: The config key to update (e.g. "gtk-theme-name")
            theme_name: Name of the theme to apply

        Returns:
            bool: True if the file was updated, False otherwise
        """
        if not config_path.parent.exists():
            logger.warning(f"Config directory doesn't exist: {config_path.parent}")
            return False

        try:
            config_path.touch(exist_ok=True)
            content = config_path.read_text()

            theme_entry = f"{config_key}={theme_name}"
            if theme_entry in content:
                return False

            if f"{config_key}=" in content:
                new_content = re.sub(rf"{config_key}=.*", theme_entry, content)
                config_path.write_text(new_content)
            else:
                with config_path.open("a") as f:
                    f.write(f"{theme_entry}\n")

            return True
        except Exception as e:
            logger.error(f"Failed to update GTK config at {config_path}: {e}")
            return False

    @staticmethod
    def _update_qt_config(config_path: Path, theme_name: str) -> bool:
        """
        Updates a QT config file with the specified icon theme name.

        Args:
            config_path: Path to the QT config file (qt5ct.conf or qt6ct.conf)
            theme_name: Name of the icon theme to apply

        Returns:
            bool: True if the file was updated, False otherwise
        """
        if not config_path.exists():
            logger.warning(f"QT config file doesn't exist: {config_path}")
            return False

        try:
            content = config_path.read_text()
            theme_entry = f"icon_theme={theme_name}"

            # Если строка уже существует с правильным значением
            if theme_entry in content:
                return False

            if "[Appearance]" in content:
                # Если строка icon_theme уже существует
                if "icon_theme=" in content:
                    new_content = re.sub(r"icon_theme=.*", theme_entry, content)
                    config_path.write_text(new_content)
                else:  # Если её не было
                    new_content = content.replace(
                        "[Appearance]", f"[Appearance]\n{theme_entry}", 1
                    )
                    config_path.write_text(new_content)
            else:
                # Если секции Appearance нет
                with config_path.open("a") as f:
                    f.write(f"\n[Appearance]\n{theme_entry}\n")

            return True
        except Exception as e:
            logger.error(f"Failed to update QT config at {config_path}: {e}")
            return False

    @staticmethod
    def _apply_wayland_theme(theme_name: str, gsettings_key: str) -> bool:
        """Apply theme for Wayland sessions using gsettings."""
        if not BaseThemeApplier._is_command_available("gsettings"):
            logger.warning("gsettings command not found - cannot apply theme")
            return False

        try:
            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.interface",
                    gsettings_key,
                    theme_name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"gsettings failed: {e.stderr}")
            return False

    @staticmethod
    def _apply_x11_theme(theme_name: str, xsettings_key: str) -> bool:
        """Apply theme for X11 sessions using xsettingsd."""
        if not BaseThemeApplier._is_command_available("xsettingsd"):
            logger.warning("xsettingsd not found - cannot apply theme")
            return False

        if not cnst.XSETTINGSD_CONFIG.exists():
            logger.warning(f"xsettingsd config not found at {cnst.XSETTINGSD_CONFIG}")
            return False

        try:
            content = cnst.XSETTINGSD_CONFIG.read_text()
            theme_line = f'{xsettings_key} "{theme_name}"'

            if theme_line in content:
                return True

            if xsettings_key in content:
                new_content = re.sub(rf"{xsettings_key} .*", theme_line, content)
                cnst.XSETTINGSD_CONFIG.write_text(new_content)
            else:
                with cnst.XSETTINGSD_CONFIG.open("a") as f:
                    f.write(f"{theme_line}\n")

            subprocess.run(
                ["killall", "-HUP", "xsettingsd"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to apply X11 theme: {e}")
            return False

    @abstractmethod
    def get_config_key(self) -> str:
        """Returns the config key used in GTK config files."""
        pass

    @abstractmethod
    def get_gsettings_key(self) -> str:
        """Returns the key used in gsettings."""
        pass

    @abstractmethod
    def get_xsettings_key(self) -> str:
        """Returns the key used in xsettingsd."""
        pass

    @abstractmethod
    def get_theme_folder(self, theme: Theme) -> Path:
        """Returns the theme folder path from the theme object."""
        pass

    @abstractmethod
    def get_symlink_dir(self) -> Path:
        """Returns the symlink directory for this theme type."""
        pass

    def apply_theme(self, gtk_configs: List[Path], theme_name: str) -> None:
        """
        Applies the theme to all specified config files and live session.

        Args:
            gtk_configs: List of GTK config files to update
            theme_name: Name of the theme to apply
        """
        for config in gtk_configs:
            self._update_gtk_config(config, self.get_config_key(), theme_name)

        if cnst.SESSION_TYPE == LinuxSessionType.WAYLAND:
            self._apply_wayland_theme(theme_name, self.get_gsettings_key())
        elif cnst.SESSION_TYPE == LinuxSessionType.X11:
            self._apply_x11_theme(theme_name, self.get_xsettings_key())

    def _apply(self, theme: Theme) -> None:
        """
        Applies the theme by creating symlinks and updating configs.

        Args:
            theme: Theme object containing theme information
        """
        theme_folder = self.get_theme_folder(theme)
        if not theme_folder.exists():
            logger.warning(f"Theme folder not found: {theme_folder}")
            return

        theme_name = "pawlette-" + theme.name
        theme_link = self.get_symlink_dir() / theme_name

        if not create_symlink_dir(
            target=theme_folder.absolute(),
            link=theme_link,
        ):
            return

        self.apply_theme(
            gtk_configs=[cnst.GTK2_CFG, cnst.GTK3_CFG, cnst.GTK4_CFG],
            theme_name=theme_name,
        )


class GTKThemeApplier(BaseThemeApplier):
    """A class to handle GTK theme application on Linux systems."""

    def get_config_key(self) -> str:
        return "gtk-theme-name"

    def get_gsettings_key(self) -> str:
        return "gtk-theme"

    def get_xsettings_key(self) -> str:
        return "Net/ThemeName"

    def get_theme_folder(self, theme: Theme) -> Path:
        return theme.gtk_folder

    def get_symlink_dir(self) -> Path:
        return cnst.GTK_THEME_SYMLINK_DIR

    def apply(self, theme: Theme) -> None:
        self._apply(theme)


class IconThemeApplier(BaseThemeApplier):
    """A class to handle Icon theme application on Linux systems."""

    def get_config_key(self) -> str:
        return "gtk-icon-theme-name"

    def get_gsettings_key(self) -> str:
        return "icon-theme"

    def get_xsettings_key(self) -> str:
        return "Net/IconThemeName"

    def get_theme_folder(self, theme: Theme) -> Path:
        return theme.icons_folder

    def get_symlink_dir(self) -> Path:
        return cnst.ICON_THEME_SYMLINK_DIR

    def apply(self, theme: Theme) -> None:
        self._apply(theme)

        # Обновляем конфиги QT
        qt5_config = Path.home() / ".config" / "qt5ct" / "qt5ct.conf"
        qt6_config = Path.home() / ".config" / "qt6ct" / "qt6ct.conf"
        self._update_qt_config(qt5_config, theme.name)
        self._update_qt_config(qt6_config, theme.name)
