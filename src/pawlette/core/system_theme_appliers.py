import re
import shutil
import subprocess
from pathlib import Path

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.utils import create_symlink_dir
from pawlette.enums.session_type import LinuxSessionType
from pawlette.schemas.themes import Theme


class BaseThemeApplier:
    """Базовый класс для применения тем с параметризацией"""

    def __init__(
        self,
        config_key: str,
        gsettings_key: str,
        xsettings_key: str,
        symlink_dir: Path,
        theme_folder_attr: str,
        qt_configs: list[Path] | None = None,
    ):
        self.config_key = config_key
        self.gsettings_key = gsettings_key
        self.xsettings_key = xsettings_key
        self.symlink_dir = symlink_dir
        self.theme_folder_attr = theme_folder_attr
        self.qt_configs = qt_configs or []

    def _is_command_available(self, command: str) -> bool:
        """Проверяет доступность команды в системе"""
        return shutil.which(command) is not None

    def _update_gtk_config(self, config_path: Path, theme_name: str) -> bool:
        """
        Обновляет конфиг GTK с указанным именем темы.
        Возвращает True если файл был изменен.
        """
        if not config_path.parent.exists():
            logger.warning(f"Директория конфига не существует: {config_path.parent}")
            return False

        try:
            config_path.touch(exist_ok=True)
            content = config_path.read_text()

            theme_entry = f"{self.config_key}={theme_name}"
            if theme_entry in content:
                return False

            if f"{self.config_key}=" in content:
                new_content = re.sub(rf"{self.config_key}=.*", theme_entry, content)
                config_path.write_text(new_content)
            else:
                with config_path.open("a") as f:
                    f.write(f"{theme_entry}\n")

            return True
        except Exception as e:
            logger.error(f"Ошибка обновления GTK конфига {config_path}: {e}")
            return False

    def _update_qt_config(self, config_path: Path, theme_name: str) -> bool:
        """
        Обновляет конфиг QT с указанным именем темы.
        Возвращает True если файл был изменен.
        """
        if not config_path.exists():
            logger.warning(f"QT конфиг не существует: {config_path}")
            return False

        try:
            content = config_path.read_text()
            theme_entry = f"icon_theme={theme_name}"

            if theme_entry in content:
                return False

            if "[Appearance]" in content:
                if "icon_theme=" in content:
                    new_content = re.sub(r"icon_theme=.*", theme_entry, content)
                else:
                    new_content = content.replace(
                        "[Appearance]", f"[Appearance]\n{theme_entry}", 1
                    )
            else:
                new_content = content + f"\n[Appearance]\n{theme_entry}\n"

            config_path.write_text(new_content)
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления QT конфига {config_path}: {e}")
            return False

    def _apply_wayland_theme(self, theme_name: str) -> bool:
        """Применяет тему для Wayland через gsettings"""
        if not self._is_command_available("gsettings"):
            logger.warning("gsettings не найден")
            return False

        try:
            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.interface",
                    self.gsettings_key,
                    theme_name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка gsettings: {e.stderr}")
            return False

    def _apply_x11_theme(self, theme_name: str) -> bool:
        """Применяет тему для X11 через xsettingsd"""
        if not self._is_command_available("xsettingsd"):
            logger.warning("xsettingsd не найден")
            return False

        if not cnst.XSETTINGSD_CONFIG.exists():
            logger.warning(f"Конфиг xsettingsd не найден: {cnst.XSETTINGSD_CONFIG}")
            return False

        try:
            content = cnst.XSETTINGSD_CONFIG.read_text()
            theme_line = f'{self.xsettings_key} "{theme_name}"'

            if theme_line in content:
                return True

            if self.xsettings_key in content:
                new_content = re.sub(rf"{self.xsettings_key} .*", theme_line, content)
            else:
                new_content = content + f"\n{theme_line}\n"

            cnst.XSETTINGSD_CONFIG.write_text(new_content)
            subprocess.run(["killall", "-HUP", "xsettingsd"], check=True)
            return True
        except Exception as e:
            logger.error(f"Ошибка применения X11 темы: {e}")
            return False

    def _apply_theme_configs(self, theme_name: str) -> None:
        """Обновляет все связанные конфиги"""
        # GTK конфиги
        for config in [cnst.GTK2_CFG, cnst.GTK3_CFG, cnst.GTK4_CFG]:
            self._update_gtk_config(config, theme_name)

        # QT конфиги
        for config in self.qt_configs:
            self._update_qt_config(config, theme_name)

        # Live session
        if cnst.SESSION_TYPE == LinuxSessionType.WAYLAND:
            self._apply_wayland_theme(theme_name)
        elif cnst.SESSION_TYPE == LinuxSessionType.X11:
            self._apply_x11_theme(theme_name)

    def _setup_symlink(self, theme: Theme) -> Path | None:
        """Создает симлинк темы и возвращает путь к теме"""
        theme_folder = getattr(theme, self.theme_folder_attr)
        if not theme_folder.exists():
            logger.warning(f"Папка темы не найдена: {theme_folder}")
            return None

        theme_name = f"pawlette-{theme.name}"
        theme_link = self.symlink_dir / theme_name

        if create_symlink_dir(theme_folder.absolute(), theme_link):
            return theme_folder
        return None

    def cleanup(self, theme_name: str) -> None:
        """Очищает симлинки темы"""
        theme_link = self.symlink_dir / f"pawlette-{theme_name}"
        if theme_link.exists():
            logger.debug(f"Removing symlink: {theme_link}")
            if theme_link.is_symlink():
                theme_link.unlink()
            elif theme_link.is_dir():
                shutil.rmtree(theme_link)

    def apply(self, theme: Theme) -> None:
        """Основной метод применения темы"""
        # Очищаем старые симлинки перед применением новых
        self.cleanup(theme.name)

        if self._setup_symlink(theme):
            theme_name = f"pawlette-{theme.name}"
            self._apply_theme_configs(theme_name)


class GTKThemeApplier(BaseThemeApplier):
    """Обработчик GTK тем с симлинками для GTK4"""

    def __init__(self):
        super().__init__(
            config_key="gtk-theme-name",
            gsettings_key="gtk-theme",
            xsettings_key="Net/ThemeName",
            symlink_dir=cnst.GTK_THEME_SYMLINK_DIR,
            theme_folder_attr="gtk_folder",
        )

    def _link_gtk4_styles(self, theme_folder: Path) -> None:
        """Создает симлинки для GTK4 ассетов и стилей"""
        gtk4_dir = theme_folder / "gtk-4.0"
        if not gtk4_dir.exists():
            return

        target_dir = Path.home() / ".config" / "gtk-4.0"
        target_dir.mkdir(parents=True, exist_ok=True)

        for css_file in ["gtk.css", "gtk-dark.css"]:
            source = gtk4_dir / css_file
            if not source.exists():
                continue

            dest = target_dir / css_file
            self._create_symlink(source, dest)

        assets_source = gtk4_dir / "assets"
        if assets_source.exists() and assets_source.is_dir():
            assets_dest = target_dir / "assets"
            self._create_symlink(assets_source, assets_dest, is_directory=True)

    def _create_symlink(
        self, source: Path, dest: Path, is_directory: bool = False
    ) -> None:
        """Утилита для создания символических ссылок"""
        try:
            if dest.exists() or dest.is_symlink():
                dest.unlink()

            dest.symlink_to(source, target_is_directory=is_directory)
        except Exception as e:
            logger.error(f"Ошибка создания ссылки {dest.name}: {e}")

    def cleanup(self, theme_name: str) -> None:
        """Переопределенная очистка с обработкой GTK4"""
        # Очищаем основной симлинк
        super().cleanup(theme_name)

        # Очищаем GTK4 симлинки
        self._cleanup_gtk4_symlinks()

    def _cleanup_gtk4_symlinks(self) -> None:
        """Очищает GTK4 симлинки в .config/gtk-4.0"""
        gtk4_dir = Path.home() / ".config" / "gtk-4.0"
        for item in ["gtk.css", "gtk-dark.css", "assets"]:
            symlink_path = gtk4_dir / item
            if symlink_path.exists():
                logger.debug(f"Removing GTK4 symlink: {symlink_path}")
                if symlink_path.is_symlink():
                    symlink_path.unlink()
                elif symlink_path.is_dir():
                    shutil.rmtree(symlink_path)

    def apply(self, theme: Theme) -> None:
        """Переопределенный метод с обработкой GTK4"""
        # Очищаем старые симлинки перед применением новых
        self.cleanup(theme.name)

        theme_folder = self._setup_symlink(theme)
        if theme_folder:
            self._link_gtk4_styles(theme_folder)
            theme_name = f"pawlette-{theme.name}"
            self._apply_theme_configs(theme_name)


class IconThemeApplier(BaseThemeApplier):
    """Обработчик иконок с обновлением QT конфигов"""

    def __init__(self):
        super().__init__(
            config_key="gtk-icon-theme-name",
            gsettings_key="icon-theme",
            xsettings_key="Net/IconThemeName",
            symlink_dir=cnst.ICON_THEME_SYMLINK_DIR,
            theme_folder_attr="icons_folder",
            qt_configs=[
                Path.home() / ".config" / "qt5ct" / "qt5ct.conf",
                Path.home() / ".config" / "qt6ct" / "qt6ct.conf",
            ],
        )
