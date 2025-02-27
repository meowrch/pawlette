#!/usr/bin/env python3
import traceback
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

import constants as cnst
from errors.themes import ThemeNotFound

from .merge_copy import MergeCopyHandler


@dataclass
class Theme:
    name: str
    path: Path


class ThemeManager:
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
                return Theme(name=theme_name, path=path)

        return None

    @staticmethod
    def apply_theme(theme_name: str) -> None:
        """Applying the theme

        Args:
            theme_name (str): Theme name

        Raises:
            ThemeNotFound: Theme not found
        """
        theme: Theme | None = ThemeManager.get_theme(theme_name)

        if theme is None:
            logger.warning("theme not found")
            raise ThemeNotFound(theme_name)

        handler = MergeCopyHandler(theme_name=theme_name)

        for app in (theme.path / "configs").iterdir():
            app_name = app.stem
            reload_cmd = cnst.RELOAD_COMMANDS.get(app_name, None)

            try:
                logger.info(
                    f'Applying theme for "{app_name}" application. {app} -> {cnst.XDG_CONFIG_HOME / app_name}'
                )

                handler.apply(
                    src=app, dst=cnst.XDG_CONFIG_HOME / app_name, reload_cmd=reload_cmd
                )
            except Exception:
                logger.warning(
                    f'Theme application error for the "{app_name}" application: {traceback.format_exc()}'
                )
