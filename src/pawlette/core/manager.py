#!/usr/bin/env python3
import json
import shutil

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.utils import create_symlink_dir
from pawlette.errors.themes import ThemeNotFound
from pawlette.schemas.config_struct import Config
from pawlette.schemas.themes import Theme

from .installer import Installer
from .selective_manager import SelectiveThemeManager
from .system_theme_appliers import CursorThemeApplier
from .system_theme_appliers import GTKThemeApplier
from .system_theme_appliers import IconThemeApplier
from .wm_reloader import WMReloader


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

    def get_all_themes_info(self) -> str:
        """Возвращает JSON с информацией по всем найденным темам.

        Включает пути к теме, пометку источника (official/community/local)
        и установленную версию (если известна).
        """
        themes = ThemeManager.get_all_themes()

        installed_info = self.installer.installed_themes

        result: dict[str, dict[str, str | None]] = {}
        for theme in themes:
            if theme.name in installed_info and installed_info[theme.name].source:
                source = installed_info[theme.name].source.value  # type: ignore[union-attr]
            else:
                source = "local"

            version = (
                installed_info[theme.name].version
                if theme.name in installed_info
                else None
            )

            result[theme.name] = {
                "path": str(theme.path),
                "logo": str(theme.theme_logo),
                "wallpapers": str(theme.wallpapers_folder),
                "gtk-folder": str(theme.gtk_folder),
                "source": source,
                "version": version,
            }

        return json.dumps(result, indent=2, ensure_ascii=False)

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

        # Получаем тему
        theme = ThemeManager.get_theme(theme_name)
        if theme:
            # Применяем системные темы (GTK, иконки, обои)
            self._apply_system_themes(theme)

            # Коммитим изменения от системных тем (если есть)
            if self.selective_manager.has_uncommitted_changes():
                logger.info("Committing system theme changes")
                self.selective_manager._run_git("add", "-A")
                self.selective_manager._run_git(
                    "commit", "-m", f"Apply system themes for: {theme_name}"
                )

            # Перезагружаем WM для применения изменений
            WMReloader.reload_current_wm()
        else:
            logger.warning("theme not found")
            raise ThemeNotFound(theme_name)

    def _apply_system_themes(self, theme: Theme):
        """Применяем системные темы (GTK, иконки, обои)"""
        logger.info("Applying system themes (GTK, icons, wallpapers)")

        ##==> Apply GTK theme (только если существует)
        ##################################
        if theme.gtk_folder.exists():
            logger.info("Applying GTK theme")
            GTKThemeApplier().apply(theme)
        else:
            logger.info("GTK theme not found in this version, skipping")

        ##==> Apply Icon theme (только если существует)
        ##################################
        if theme.icons_folder.exists():
            logger.info("Applying icon theme")
            IconThemeApplier().apply(theme)
        else:
            logger.info("Icon theme not found in this version, skipping")

        ##==> Apply Cursor theme (если присутствует)
        ##################################
        if theme.icons_folder.exists() and (theme.icons_folder / "cursors").exists():
            logger.info("Applying cursor theme")
            CursorThemeApplier().apply(theme)
        else:
            logger.info("Cursor theme not found in this version, skipping")

        ##==> Apply wallpapers
        ##################################
        if theme.wallpapers_folder.exists():
            theme.wallpapers_folder.mkdir(parents=True, exist_ok=True)
            create_symlink_dir(
                target=theme.wallpapers_folder, link=cnst.THEME_WALLPAPERS_SYMLINK
            )
        else:
            if cnst.THEME_WALLPAPERS_SYMLINK.exists():
                if cnst.THEME_WALLPAPERS_SYMLINK.is_symlink():
                    cnst.THEME_WALLPAPERS_SYMLINK.unlink()
                elif cnst.THEME_WALLPAPERS_SYMLINK.is_dir():
                    shutil.rmtree(cnst.THEME_WALLPAPERS_SYMLINK)

    def restore_original(self) -> None:
        """Возврат к базовому состоянию с сохранением пользовательских изменений"""
        logger.debug("=== RESTORE ORIGINAL ===")

        # Используем селективный менеджер для восстановления
        self.selective_manager.restore_original()

    def reset_theme_to_clean(self, theme_name: str) -> None:
        """Сбрасывает тему к чистому состоянию, удаляя пользовательские изменения.

        Работает только в селективном режиме: откатывает ТОЛЬКО файлы этой темы
        к состоянию последнего применения (HEAD), не трогая другие конфиги.
        """
        if not self.use_selective:
            logger.warning("reset-theme is only available in selective mode")
            return

        # Проверяем, что тема существует
        theme = ThemeManager.get_theme(theme_name)
        if not theme:
            logger.warning("theme not found")
            raise ThemeNotFound(theme_name)

        # Переключаемся на ветку темы (создастся если нужно)
        self.selective_manager._create_or_switch_branch(theme_name)

        # Получаем список затронутых файлов этой темы в ~/.config
        theme_files = self.selective_manager._get_theme_files(theme)

        # Откатываем изменения только для файлов этой темы
        for file_path in theme_files:
            try:
                rel = file_path.relative_to(self.selective_manager.config_dir)
            except ValueError:
                # Вне рабочей директории git — пропускаем
                continue

            # Пытаемся использовать современную команду restore; если не поддерживается — fallback на checkout
            ok = self.selective_manager._run_git(
                "restore", "--worktree", "--staged", "--source=HEAD", str(rel)
            )
            if not ok:
                self.selective_manager._run_git("checkout", "--", str(rel))

        logger.info(f"Theme '{theme_name}' reset to clean state")

    def get_current_theme_name(self) -> str | None:
        """Get current theme name from selective manager"""
        try:
            return self.selective_manager.get_current_theme()
        except Exception as e:
            logger.error(f"Error getting current theme: {e}")
            return None

    def uninstall_theme(self, theme_name: str) -> None:
        """Полностью удаляет тему: файлы, кэш, git‑ветку и системные симлинки."""
        # 1. Удаляем саму тему и её кэш (каталог, installed_themes.json, .version)
        self.installer.uninstall_theme(theme_name)

        # 2. Удаляем git‑ветку темы в селективном менеджере (если включен)
        if self.use_selective:
            try:
                deleted = self.selective_manager.delete_theme_branch(theme_name)
                if deleted:
                    logger.info(f"Deleted git branch for theme '{theme_name}'")
            except Exception as e:
                logger.error(f"Failed to delete git branch for theme '{theme_name}': {e}")

        # 3. Очищаем системные симлинки GTK/иконок/курсора
        try:
            GTKThemeApplier().cleanup(theme_name)
            IconThemeApplier().cleanup(theme_name)
            CursorThemeApplier().cleanup(theme_name)
            logger.info(f"Cleaned up GTK/icon/cursor symlinks for theme '{theme_name}'")
        except Exception as e:
            logger.error(
                f"Failed to cleanup system theme symlinks for '{theme_name}': {e}"
            )
