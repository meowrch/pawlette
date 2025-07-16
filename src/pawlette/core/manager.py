#!/usr/bin/env python3
import json

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.utils import create_symlink_dir
from pawlette.errors.themes import ThemeNotFound
from pawlette.schemas.config_struct import Config
from pawlette.schemas.themes import Theme

from .installer import Installer
from .selective_manager import SelectiveThemeManager
from .system_theme_appliers import GTKThemeApplier
from .system_theme_appliers import IconThemeApplier


class ThemeManager:
    installer: Installer

    def __init__(self, config: Config, use_selective: bool = True) -> None:
        self.installer = Installer()
        self.use_selective = use_selective
        self.config = config

        self.selective_manager = SelectiveThemeManager(config)

    @staticmethod
    def get_all_themes() -> list[Theme]:
        """Gives all found themes in the system and local directory.
        If a theme with the same name is found in both directories,
        it will be taken from the system directory.

        Returns:
            list[Theme]: List of themes with name and path
        """
        themes: dict[str, Theme] = {}

        for i in [cnst.SYS_THEMES_FOLDER, cnst.THEMES_FOLDER]:
            if not i.exists() or not i.is_dir():
                continue

            for p in i.iterdir():
                if p.exists() and p.is_dir():
                    themes[p.stem] = Theme(name=p.stem, path=p)

        return list(themes.values())

    @staticmethod
    def get_all_themes_info() -> str:
        """This method returns JSON with the paths to the theme itself,
        logo, wallpaper and theme gtk for each theme

        Returns:
            str: JSON with the params of theme
        """
        themes = ThemeManager.get_all_themes()
        return json.dumps(
            {
                i.name: {
                    "path": str(i.path),
                    "logo": str(i.theme_logo),
                    "wallpapers": str(i.wallpapers_folder),
                    "gtk-folder": str(i.gtk_folder),
                }
                for i in themes
            }
        )

    @staticmethod
    def get_theme(theme_name: str) -> Theme | None:
        """
        Gives the theme if it is found in the system or local catalog.
        If a theme with the same name is found in both directories,
        it will be taken from the system directory.

        Args:
            theme_name (str): Theme name

        Returns:
            Theme: Theme dataclass with name and path.
                   If the theme is not found, None is returned
        """
        path = cnst.THEMES_FOLDER / theme_name
        sys_path = cnst.SYS_THEMES_FOLDER / theme_name

        for p in [sys_path, path]:
            if p.exists() and p.is_dir():
                return Theme(name=theme_name, path=p)

        return None

    def apply_theme(self, theme_name: str) -> None:
        """Applying the theme with selective manager

        Args:
            theme_name (str): Theme name

        Raises:
            ThemeNotFound: Theme not found
        """
        # Используем селективный менеджер
        self.selective_manager.apply_theme(theme_name)

        # Применяем системные темы (GTK, иконки, обои)
        theme = ThemeManager.get_theme(theme_name)
        if theme:
            self._apply_system_themes(theme)

            # Коммитим изменения от системных тем (если есть)
            if self.selective_manager.has_uncommitted_changes():
                logger.info("Committing system theme changes")
                self.selective_manager._run_git("add", "-A")
                self.selective_manager._run_git("commit", "-m", f"Apply system themes for: {theme_name}")
        else:
            logger.warning("theme not found")
            raise ThemeNotFound(theme_name)

    def _apply_system_themes(self, theme: Theme):
        """Применяем системные темы (GTK, иконки, обои)"""
        logger.info("Applying system themes (GTK, icons, wallpapers)")

        ##==> Apply GTK theme
        ##################################
        GTKThemeApplier().apply(theme)

        ##==> Apply Icon theme
        ##################################
        IconThemeApplier().apply(theme)

        ##==> Apply wallpapers
        ##################################
        theme.wallpapers_folder.mkdir(parents=True, exist_ok=True)
        create_symlink_dir(
            target=theme.wallpapers_folder, link=cnst.THEME_WALLPAPERS_SYMLINK
        )

    def restore_original(self) -> None:
        """Возврат к базовому состоянию с сохранением пользовательских изменений"""
        logger.debug("=== RESTORE ORIGINAL ===")

        # Используем селективный менеджер для восстановления
        self.selective_manager.restore_original()

    def get_current_theme_name(self) -> str | None:
        """Get current theme name from selective manager"""
        try:
            return self.selective_manager.get_current_theme()
        except Exception as e:
            logger.error(f"Error getting current theme: {e}")
            return None
