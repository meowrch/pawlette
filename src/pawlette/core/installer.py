#!/usr/bin/env python3
import json
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path

import requests
from loguru import logger
from packaging import version
from tqdm import tqdm

from pawlette import constants as cnst
from pawlette.schemas.themes import InstalledThemeInfo
from pawlette.schemas.themes import RemoteTheme
from pawlette.schemas.themes import ThemeSource


class Installer:
    def __init__(self):
        # Кэш установленных тем
        self.installed_themes: dict[str, InstalledThemeInfo] = (
            self._load_installed_themes()
        )

    def _load_installed_themes(self) -> dict[str, InstalledThemeInfo]:
        """Загружает информацию об установленных темах из кэша"""
        if not cnst.VERSIONS_FILE.exists():
            return {}

        with open(cnst.VERSIONS_FILE) as f:
            data = json.load(f)

        themes: dict[str, InstalledThemeInfo] = {}
        for name, info in data.items():
            # Поддержка старого формата без поля source
            source_raw = info.get("source")
            try:
                source = ThemeSource(source_raw) if source_raw is not None else None
            except ValueError:
                source = None

            themes[name] = InstalledThemeInfo(
                name=name,
                version=info["version"],
                source_url=info["source_url"],
                installed_path=Path(info["installed_path"]),
                source=source,
            )

        return themes

    def _save_installed_themes(self):
        """Сохраняет информацию об установленных темах в кэш"""
        data = {}
        for name, theme in self.installed_themes.items():
            source_value = None
            if getattr(theme, "source", None) is not None:
                # Enum -> строка
                try:
                    source_value = theme.source.value  # type: ignore[assignment]
                except AttributeError:
                    source_value = str(theme.source)

            data[name] = {
                "version": theme.version,
                "source_url": theme.source_url,
                "installed_path": str(theme.installed_path),
                "source": source_value,
            }

        with open(cnst.VERSIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _convert_github_url(self, url: str) -> str:
        """Преобразует GitHub URL из blob в raw"""
        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    def _load_themes(
        self, url: str, source_type: ThemeSource
    ) -> dict[str, RemoteTheme]:
        """Загружает и парсит список тем с указанного URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.error(
                f"Error fetching {source_type.value} themes list from {url}: {e}"
            )
            return {}

        themes: dict[str, RemoteTheme] = {}
        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=2)
            if len(parts) >= 2:
                name = parts[0]
                raw_url = parts[1]
                url_converted = self._convert_github_url(raw_url)
                themes[name] = RemoteTheme(
                    name=name,
                    url=url_converted,
                    source=source_type,
                )
        return themes

    def fetch_remote_themes(self) -> dict[str, RemoteTheme]:
        """Получает все доступные темы (официальные и комьюнити) с пометкой источника."""
        themes: dict[str, RemoteTheme] = {}

        sources: list[tuple[str, ThemeSource]] = [
            (cnst.OFFICIAL_THEMES_LIST_URL, ThemeSource.OFFICIAL),
            (cnst.COMMUNITY_THEMES_LIST_URL, ThemeSource.COMMUNITY),
        ]

        for url, source_type in sources:
            loaded = self._load_themes(url, source_type)
            for name, remote in loaded.items():
                # Официальные темы имеют приоритет над комьюнити при конфликте имён
                if name not in themes or remote.source == ThemeSource.OFFICIAL:
                    themes[name] = remote

        return themes

    def fetch_available_themes(self) -> dict[str, str]:
        """Получает список доступных тем из репозитория (в старом формате name -> url)."""
        try:
            remote_themes = self.fetch_remote_themes()
            return {name: theme.url for name, theme in remote_themes.items()}
        except Exception as e:
            logger.error(f"Error fetching themes list: {e}")
            return {}

    def _extract_version_from_filename(self, filename: str) -> str:
        """Извлекает версию из имени файла темы"""
        # Ожидаемый формат: theme-name-vX.Y.Z.tar.gz
        matches = re.findall(r"v(\d+(?:\.\d+)*)(?:[-_.]|$)", filename)
        return matches[-1] if matches else "1.0"

    def install_theme(self, theme_name: str, skip_warning: bool = False):
        """Устанавливает указанную тему (официальную или из комьюнити)."""
        themes = self.fetch_remote_themes()
        if not themes:
            print("Failed to fetch themes list.")
            return

        if theme_name not in themes:
            print(f"Theme '{theme_name}' not found.")
            return

        remote_theme = themes[theme_name]
        theme_url = remote_theme.url

        if remote_theme.source == ThemeSource.COMMUNITY and not skip_warning:
            if not self._show_community_warning(
                remote_theme.name, remote_theme.url, action="installation"
            ):
                print("Installation cancelled.")
                return

        self._install_theme_from_url(remote_theme.name, theme_url, remote_theme.source)

    @staticmethod
    def _visible_width(text: str) -> int:
        """Возвращает приблизительную ширину строки в терминале с учётом юникод-символов.

        Учитывает полноширинные символы и emoji, а также нулевую ширину у
        вариационных селекторов и комбинируемых символов.
        """
        import unicodedata

        width = 0
        i = 0
        while i < len(text):
            ch = text[i]

            # Вариационные селекторы и zero-width joiner не занимают места
            codepoint = ord(ch)
            if 0xFE00 <= codepoint <= 0xFE0F or codepoint == 0x200D:
                i += 1
                continue

            if unicodedata.combining(ch):
                i += 1
                continue

            eaw = unicodedata.east_asian_width(ch)
            if eaw in ("F", "W"):
                width += 2
            else:
                width += 1

            i += 1

        return width

    def _print_warning_box(self, title: str, lines: list[str]) -> None:
        """Печатает красивый блок-предупреждение с рамкой с учётом ширины emoji."""
        if not lines:
            lines = []

        content_lines = [title] + [""] + lines
        padding = 2

        max_width = 0
        for line in content_lines:
            w = self._visible_width(line)
            if w > max_width:
                max_width = w

        inner_width = max_width + padding * 2

        top = "╔" + "═" * inner_width + "╗"
        bottom = "╚" + "═" * inner_width + "╝"

        print()
        print(top)
        for line in content_lines:
            line_width = self._visible_width(line)
            spaces_needed = max_width - line_width
            padded = " " * padding + line + " " * spaces_needed + " " * padding
            print(f"║{padded}║")
        print(bottom)

    def _show_community_warning(
        self, theme_name: str, url: str, action: str = "installation"
    ) -> bool:
        """Показывает предупреждение перед установкой/обновлением комьюнити-темы."""
        lines = [
            f"Theme: {theme_name}",
            f"Source: {url}",
            "",
            "This theme is not reviewed by Pawlette maintainers.",
            "Please check the source repository before proceeding.",
            "Use at your own risk.",
        ]
        self._print_warning_box("⚠️  COMMUNITY THEME", lines)
        answer = input(f"Continue {action}? [y/N]: ").strip().lower()
        return answer in ("y", "yes")

    def _install_theme_from_url(
        self, theme_name: str, theme_url: str, source: ThemeSource | None = None
    ):
        """Скачивает архив темы и устанавливает её."""
        print(f"Installing theme '{theme_name}' from {theme_url}...")

        try:
            # Получаем размер файла для прогресс-бара
            response = requests.head(theme_url, allow_redirects=True)
            total_size = int(response.headers.get("content-length", 0))

            # Определяем версию из URL
            theme_version = self._extract_version_from_filename(
                theme_url.split("/")[-1]
            )

            # Создание временного файла с прогресс-баром
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".tar.gz"
            ) as tmp_file:
                # Загрузка с прогресс-баром
                with requests.get(theme_url, stream=True) as r:
                    r.raise_for_status()
                    with tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Downloading {theme_name}",
                        ncols=80,
                    ) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            tmp_file.write(chunk)
                            pbar.update(len(chunk))

                tmp_path = tmp_file.name

            # Целевая директория для темы
            theme_target_dir = cnst.THEMES_FOLDER / theme_name

            # Полностью удаляем старую папку темы для чистого обновления
            if theme_target_dir.exists():
                logger.info(f"Removing old theme directory: {theme_target_dir}")
                shutil.rmtree(theme_target_dir)

            # Создаём новую чистую папку
            theme_target_dir.mkdir(exist_ok=True, parents=True)

            # Распаковка архива с обработкой структуры
            print(f"Extracting {theme_name}...")
            with tarfile.open(tmp_path, "r:gz") as tar:
                members = tar.getmembers()

                # Определяем общую директорию в архиве
                if members:
                    members_names = [m.name for m in members]
                    common_dir = os.path.commonpath(members_names)

                    # Проверяем нужно ли обрезать путь
                    strip_length = (
                        len(common_dir) + 1
                        if all(name.startswith(common_dir) for name in members_names)
                        else 0
                    )
                else:
                    strip_length = 0

                # Фильтруем и корректируем пути
                extracted_members = []
                for member in members:
                    if strip_length:
                        new_name = member.name[strip_length:]
                        if not new_name:  # Пропускаем корневую директорию
                            continue
                        member.name = new_name

                    # Пропускаем элементы вне целевой директории
                    target_path = os.path.join(theme_target_dir, member.name)
                    if not os.path.abspath(target_path).startswith(
                        os.path.abspath(theme_target_dir)
                    ):
                        continue

                    extracted_members.append(member)

                # Извлекаем с прогресс-баром
                with tqdm(
                    total=len(extracted_members), desc="Extracting files", ncols=80
                ) as pbar:
                    for member in extracted_members:
                        tar.extract(member, theme_target_dir)
                        pbar.update(1)

            # Обновляем информацию об установленной теме
            self.installed_themes[theme_name] = InstalledThemeInfo(
                name=theme_name,
                version=theme_version,
                source_url=theme_url,
                installed_path=theme_target_dir,
                source=source,
            )
            self._save_installed_themes()
            print(
                f"\nTheme '{theme_name}' (v{theme_version}) successfully installed to {theme_target_dir}"
            )
        except Exception as e:
            logger.error(f"Error installing theme: {e}")
            raise
        finally:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def update_theme(self, theme_name: str):
        """Обновляет указанную тему до последней версии."""
        if theme_name not in self.installed_themes:
            print(f"Theme '{theme_name}' is not installed.")
            return

        current_version = self.installed_themes[theme_name].version
        remote_themes = self.fetch_remote_themes()

        if theme_name not in remote_themes:
            print(f"Theme '{theme_name}' not found in available themes.")
            return

        remote = remote_themes[theme_name]
        theme_url = remote.url
        new_version = self._extract_version_from_filename(theme_url.split("/")[-1])

        if version.parse(new_version) <= version.parse(current_version):
            print(f"Theme '{theme_name}' is already up to date (v{current_version}).")
            return

        if remote.source == ThemeSource.COMMUNITY:
            if not self._show_community_warning(theme_name, theme_url, action="update"):
                print("Update cancelled.")
                return

        print(
            f"Updating theme '{theme_name}' from v{current_version} to v{new_version}..."
        )
        self._install_theme_from_url(theme_name, theme_url, remote.source)

    def update_all_themes(self):
        """Обновляет все установленные темы до последних версий.

        Перед обновлением показывает список тем и спрашивает подтверждение.
        Если есть комьюнити-темы, выводит предупреждающий баннер.
        """
        if not self.installed_themes:
            print("No themes installed to update.")
            return

        print("Checking for theme updates...")

        remote_themes = self.fetch_remote_themes()
        if not remote_themes:
            print("Failed to fetch themes list.")
            return

        themes_to_update: list[tuple[str, RemoteTheme, str, str]] = []
        community_to_update: list[str] = []

        for theme_name, installed in self.installed_themes.items():
            if theme_name not in remote_themes:
                continue

            remote = remote_themes[theme_name]
            theme_url = remote.url
            new_version = self._extract_version_from_filename(
                theme_url.split("/")[-1]
            )
            current_version = installed.version

            if version.parse(new_version) <= version.parse(current_version):
                continue

            themes_to_update.append((theme_name, remote, current_version, new_version))
            if remote.source == ThemeSource.COMMUNITY:
                community_to_update.append(theme_name)

        if not themes_to_update:
            print("All themes are already up to date.")
            return

        # Если есть комьюнити-темы, показываем предупреждение
        if community_to_update:
            lines = [
                "The update includes community themes:",
                "",
            ] + [f"  - {name}" for name in sorted(community_to_update)] + [
                "",
                "These themes are not reviewed by Pawlette maintainers.",
                "Please check their source repositories before updating.",
                "Update at your own risk.",
            ]
            self._print_warning_box("⚠️  COMMUNITY THEMES", lines)

        # Показываем полный список обновляемых тем с версиями и источником
        print("The following themes will be updated:\n")
        for theme_name, remote, current_version, new_version in themes_to_update:
            if remote.source == ThemeSource.COMMUNITY:
                icon = "🌍"
                label = "community"
            else:
                icon = "📦"
                label = "official"
            print(
                f"  {icon} [{label}] {theme_name}: v{current_version} -> v{new_version}"
            )
        print()

        # Глобальное подтверждение перед обновлением (для любых тем)
        answer = input(
            "Do you want to proceed with updating these themes? [y/N]: "
        ).strip().lower()
        if answer not in ("y", "yes"):
            print("Update cancelled.")
            return

        for theme_name, remote, current_version, new_version in themes_to_update:
            print(
                f"Updating theme '{theme_name}' from v{current_version} to v{new_version}..."
            )
            self._install_theme_from_url(theme_name, remote.url, remote.source)
