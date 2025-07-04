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
    USER_PREFIX = "user/"
    installer: Installer

    def __init__(self, use_selective: bool = True) -> None:
        self.installer = Installer()
        self.use_selective = use_selective
        
        if use_selective:
            from .selective_manager import SelectiveThemeManager
            self.selective_manager = SelectiveThemeManager()
        else:
            # Fallback to old git-based system
            self.git = GitManager(
                repo_path=cnst.APP_STATE_DIR / ".config.git",
                config_path=cnst.XDG_CONFIG_HOME,
            )
            # Only init base state if repository was just created
            if not self.git.branch_exists(self.BASE_BRANCH):
                self._init_base_state()

    def _init_base_state(self):
        # Only create base branch if it doesn't exist, don't checkout unnecessarily
        if not self.git.branch_exists(self.BASE_BRANCH):
            current_branch = self.git.get_current_branch()
            self.git.create_branch(self.BASE_BRANCH)
            self.git.checkout(self.BASE_BRANCH)
            self.git.commit("Initial base state")
            # Return to previous branch if we had one
            if current_branch and current_branch != self.BASE_BRANCH:
                self.git.checkout(current_branch, force=True)

    def _log_repo_state(self):
        logger.debug("Current Git state:")
        logger.debug("Branches:\n" + "\n".join(self.git.get_branches()))
        logger.debug("Last commits:\n" + self.git.get_log(5))
        logger.debug("Status:\n" + self.git.get_status())
        logger.debug("Current commit: " + self.git.get_current_commit())

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
        """Applying the theme with user branch system or selective manager

        Args:
            theme_name (str): Theme name

        Raises:
            ThemeNotFound: Theme not found
        """
        if self.use_selective:
            # Используем новый селективный менеджер
            self.selective_manager.apply_theme(theme_name)
            
            # Применяем системные темы (GTK, иконки, обои)
            theme = ThemeManager.get_theme(theme_name)
            if theme:
                self._apply_system_themes(theme)
            return
            
        # Fallback to old git-based system
        logger.debug(f"=== BEFORE APPLY {theme_name} ===")
        self._log_repo_state()

        theme: Theme | None = ThemeManager.get_theme(theme_name)

        if theme is None:
            logger.warning("theme not found")
            raise ThemeNotFound(theme_name)

        current_branch = self.git.get_current_branch()
        
        # Сохраняем текущие пользовательские изменения если есть
        if self.git.has_uncommitted_changes():
            self._save_current_user_changes()

        # Переключаемся на пользовательскую ветку или создаем ее
        user_branch = f"{self.USER_PREFIX}{theme_name}"
        theme_branch = f"{self.THEME_PREFIX}{theme_name}"
        
        if self.git.branch_exists(user_branch):
            # Пользовательская ветка уже существует - используем ее состояние
            logger.info(f"Switching to existing user branch: {user_branch}")
            self._switch_to_user_branch_safe(user_branch)
        else:
            # Создаем новую тему если нужно
            self._ensure_theme_branch(theme_name, theme)
            
            # Применяем тему поверх текущего состояния
            logger.info(f"Applying theme {theme_name} over current config")
            self._apply_theme_changes(theme)
            
            # Создаем пользовательскую ветку с текущим состоянием
            logger.info(f"Creating new user branch: {user_branch}")
            self.git.create_branch(user_branch)
            self.git.checkout(user_branch, force=True)
            self.git.commit(f"Initial user state for theme: {theme_name}")

        logger.debug(f"=== AFTER APPLY {theme_name} ===")
        self._log_repo_state()
        
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
        logger.debug("=== BEFORE RESTORE ===")
        self._log_repo_state()

        if self._has_uncommitted_changes():
            self.git.stash()
            self.git.checkout(self.BASE_BRANCH)
            self.git.stash_pop()
        else:
            self.git.checkout(self.BASE_BRANCH)

        logger.debug("=== AFTER RESTORE ===")
        self._log_repo_state()

        logger.debug("=== BEFORE RESTORE ===")
        self._log_repo_state()

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

    def _save_current_user_changes(self) -> None:
        """Save current user changes to the current branch"""
        current_branch = self.git.get_current_branch()
        logger.info(f"Saving user changes in branch: {current_branch}")
        self.git.commit(f"Save user changes - {current_branch}")

    def _ensure_theme_branch(self, theme_name: str, theme: Theme) -> None:
        """Ensure theme branch exists and is up to date"""
        theme_branch = f"{self.THEME_PREFIX}{theme_name}"

        if not self.git.branch_exists(theme_branch):
            # Create theme branch from base
            logger.info(f"Creating theme branch: {theme_branch}")
            self.git.checkout(self.BASE_BRANCH)
            self.git.create_branch(theme_branch)
            self.git.checkout(theme_branch)

            # Apply theme changes
            self._apply_theme_changes(theme)
            self.git.commit(f"Applied clean theme: {theme_name}")
        else:
            logger.info(f"Theme branch already exists: {theme_branch}")

    def reset_theme_to_clean(self, theme_name: str) -> None:
        """Reset user branch to clean theme state"""
        user_branch = f"{self.USER_PREFIX}{theme_name}"
        theme_branch = f"{self.THEME_PREFIX}{theme_name}"
        if not self.git.branch_exists(user_branch):
            logger.warning(f"User branch {user_branch} does not exist")
            return

        if not self.git.branch_exists(theme_branch):
            logger.warning(f"Theme branch {theme_branch} does not exist")
            return

        current_branch = self.git.get_current_branch()

        # If we're on the user branch we want to reset, switch to theme branch first
        if current_branch == user_branch:
            self.git.checkout(theme_branch, force=True)

        # Force delete user branch and recreate from theme branch
        self.git._run_git("branch", "-D", user_branch)  # Force delete user branch
        self.git.create_branch_from(user_branch, theme_branch)

        # Switch back to the reset user branch
        self.git.checkout(user_branch, force=True)

        logger.info(f"Reset {theme_name} to clean state")

    def _switch_to_user_branch_safe(self, user_branch: str) -> None:
        """Safely switch to user branch - just change HEAD pointer without checkout"""
        logger.info(f"Switching to user branch: {user_branch}")
        
        # Simply change the branch pointer without affecting working directory
        subprocess.run(
            ["git", "-C", str(self.git.repo_path), "symbolic-ref", "HEAD", f"refs/heads/{user_branch}"],
            capture_output=True
        )

    def get_current_theme_name(self) -> str | None:
        """Get current theme name from branch or selective manager"""
        try:
            if self.use_selective:
                return self.selective_manager.get_current_theme()
            else:
                current_branch = self.git.get_current_branch()

                if current_branch.startswith(self.USER_PREFIX):
                    return current_branch[len(self.USER_PREFIX) :]
                elif current_branch.startswith(self.THEME_PREFIX):
                    return current_branch[len(self.THEME_PREFIX) :]
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting current theme: {e}")
            return None
