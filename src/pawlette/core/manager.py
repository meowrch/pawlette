#!/usr/bin/env python3
import json
import subprocess

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.utils import create_symlink_dir
from pawlette.errors.themes import ThemeNotFound
from pawlette.schemas.themes import Theme

from .git_manager import GitManager
from .installer import Installer
from .merge_copy import MergeCopyHandler
from .system_theme_appliers import GTKThemeApplier
from .system_theme_appliers import IconThemeApplier


class ThemeManager:
    BASE_BRANCH = "base"
    THEME_PREFIX = "theme/"
    installer: Installer

    def __init__(self) -> None:
        self.installer = Installer()
        self.git = GitManager(
            repo_path=cnst.APP_STATE_DIR / ".config.git",
            config_path=cnst.XDG_CONFIG_HOME,
        )
        self._init_base_state()

    def _init_base_state(self):
        if not self.git.checkout(self.BASE_BRANCH):
            self.git.create_branch(self.BASE_BRANCH)
            self.git.checkout(self.BASE_BRANCH)
            self.git.commit("Initial base state")

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
                return Theme(name=theme_name, path=path)

        return None

    def apply_theme(self, theme_name: str) -> None:
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

        user_changes_exist = self._has_uncommitted_changes()

        # Сохраняем пользовательские изменения
        if user_changes_exist:
            self.git.stash()

        try:
            # Возвращаемся к базовому состоянию
            self.git.checkout(self.BASE_BRANCH)

            # Создаем ветку для темы
            theme_branch = f"{self.THEME_PREFIX}{theme_name}"

            if self.git.branch_exists(theme_branch):
                self.git.checkout(theme_branch)
            else:
                self.git.create_branch(theme_branch)
                self.git.checkout(theme_branch)

            # Применяем изменения темы
            self._apply_theme_changes(theme)
            self.git.commit(f"Applied theme: {theme_name}")

            # Возвращаем пользовательские изменения
            if user_changes_exist:
                self.git.stash_pop()

        except Exception:
            self.git.reset_hard("HEAD^")
            raise

    def restore_original(self) -> None:
        """Возврат к базовому состоянию с сохранением пользовательских изменений"""
        if self._has_uncommitted_changes():
            self.git.stash()
            self.git.checkout(self.BASE_BRANCH)
            self.git.stash_pop()
        else:
            self.git.checkout(self.BASE_BRANCH)

    def _apply_theme_changes(self, theme: Theme):
        ##==> Apply all configs
        ##################################
        merge = MergeCopyHandler(theme=theme)
        merge.apply_for_all_configs()

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

    def _get_current_theme(self) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(self.git.repo_path), "branch", "--show-current"],
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip()
        return branch.split("/")[-1] if self.THEME_PREFIX in branch else None

    def _has_uncommitted_changes(self) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.git.repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
