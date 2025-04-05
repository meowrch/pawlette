import re
import shutil
import subprocess
from pathlib import Path
from typing import List

from loguru import logger

import constants as cnst
from common.utils import create_symlink_dir
from enums.session_type import LinuxSessionType
from schemas.themes import Theme


class GTKThemeApplier:
    """A class to handle GTK theme application on Linux systems."""

    @staticmethod
    def _update_gtk_config(config_path: Path, theme_name: str) -> bool:
        """
        Updates a GTK config file with the specified theme name.

        Args:
            config_path: Path to the GTK config file
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

            theme_entry = f"gtk-theme-name={theme_name}"
            if theme_entry in content:
                return False

            if "gtk-theme-name=" in content:
                new_content = re.sub(r"gtk-theme-name=.*", theme_entry, content)
                config_path.write_text(new_content)
            else:
                with config_path.open("a") as f:
                    f.write(f"{theme_entry}\n")

            return True
        except Exception as e:
            logger.error(f"Failed to update GTK config at {config_path}: {e}")
            return False

    @staticmethod
    def _is_command_available(command: str) -> bool:
        """Check if a command is available in the system."""
        return shutil.which(command) is not None

    @staticmethod
    def _apply_wayland_theme(theme_name: str) -> bool:
        """Apply theme for Wayland sessions using gsettings."""
        if not GTKThemeApplier._is_command_available("gsettings"):
            logger.warning("gsettings command not found - cannot apply theme")
            return False

        try:
            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.interface",
                    "gtk-theme",
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
    def _apply_x11_theme(theme_name: str) -> bool:
        """Apply theme for X11 sessions using xsettingsd."""
        if not GTKThemeApplier._is_command_available("xsettingsd"):
            logger.warning("xsettingsd not found - cannot apply theme")
            return False

        if not cnst.XSETTINGSD_CONFIG.exists():
            logger.warning(f"xsettingsd config not found at {cnst.XSETTINGSD_CONFIG}")
            return False

        try:
            content = cnst.XSETTINGSD_CONFIG.read_text()
            theme_line = f'Net/ThemeName "{theme_name}"'

            if theme_line in content:
                return True

            if "Net/ThemeName" in content:
                new_content = re.sub(r"Net/ThemeName .*", theme_line, content)
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

    @staticmethod
    def apply_gtk_themes(gtk_configs: List[Path], gtk_theme_name: str) -> None:
        """
        Applies the GTK theme to all specified config files and live session.

        Args:
            gtk_configs: List of GTK config files to update
            gtk_theme_name: Name of the theme to apply
        """
        for config in gtk_configs:
            GTKThemeApplier._update_gtk_config(config, gtk_theme_name)

        if cnst.SESSION_TYPE == LinuxSessionType.WAYLAND:
            GTKThemeApplier._apply_wayland_theme(gtk_theme_name)
        elif cnst.SESSION_TYPE == LinuxSessionType.X11:
            GTKThemeApplier._apply_x11_theme(gtk_theme_name)

    @staticmethod
    def apply(theme: Theme) -> None:
        """
        Applies the GTK theme by creating symlinks and updating configs.

        Args:
            theme: Theme object containing theme information
        """
        if not theme.gtk_folder.exists():
            logger.warning(f"GTK theme folder not found: {theme.gtk_folder}")
            return

        gtk_theme_name = "pawlette-" + theme.name
        gtk_theme_link = cnst.GTK_THEME_SYMLINK_DIR / gtk_theme_name

        if not create_symlink_dir(
            target=theme.gtk_folder.absolute(),
            link=gtk_theme_link,
        ):
            return

        GTKThemeApplier.apply_gtk_themes(
            gtk_configs=[cnst.GTK2_CFG, cnst.GTK3_CFG, cnst.GTK4_CFG],
            gtk_theme_name=gtk_theme_name,
        )
