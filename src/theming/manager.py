#!/usr/bin/env python3
from loguru import logger

import constants as cnst
from errors.themes import ThemeNotFound
from schemas.themes import Theme

from .merge_copy import MergeCopyHandler


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

        ##==> Apply all configs
        ##################################
        merge = MergeCopyHandler(theme=theme)
        merge.apply_for_all_configs()
