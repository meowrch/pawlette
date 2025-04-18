#!/usr/bin/env python3
import json
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Dict

import requests
from loguru import logger
from packaging import version
from tqdm import tqdm

from pawlette import constants as cnst
from pawlette.schemas.themes import InstalledThemeInfo


class Installer:
    def __init__(self):
        # Кэш установленных тем
        self.installed_themes: Dict[str, InstalledThemeInfo] = (
            self._load_installed_themes()
        )

    def _load_installed_themes(self) -> Dict[str, InstalledThemeInfo]:
        """Загружает информацию об установленных темах из кэша"""
        if not cnst.VERSIONS_FILE.exists():
            return {}

        with open(cnst.VERSIONS_FILE, "r") as f:
            data = json.load(f)
            return {
                name: InstalledThemeInfo(
                    name=name,
                    version=info["version"],
                    source_url=info["source_url"],
                    installed_path=Path(info["installed_path"]),
                )
                for name, info in data.items()
            }

    def _save_installed_themes(self):
        """Сохраняет информацию об установленных темах в кэш"""
        data = {
            name: {
                "version": theme.version,
                "source_url": theme.source_url,
                "installed_path": str(theme.installed_path),
            }
            for name, theme in self.installed_themes.items()
        }

        with open(cnst.VERSIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _convert_github_url(self, url: str) -> str:
        """Преобразует GitHub URL из blob в raw"""
        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    def fetch_available_themes(self) -> Dict[str, str]:
        """Получает список доступных тем из репозитория"""
        try:
            response = requests.get(cnst.THEMES_LIST_URL)
            response.raise_for_status()
            themes = {}
            for line in response.text.splitlines():
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split(maxsplit=2)
                    if len(parts) >= 2:
                        name = parts[0]
                        url = self._convert_github_url(parts[1])
                        themes[name] = url
            return themes
        except Exception as e:
            logger.error(f"Error fetching themes list: {e}")
            return {}

    def _extract_version_from_filename(self, filename: str) -> str:
        """Извлекает версию из имени файла темы"""
        # Ожидаемый формат: theme-name-vX.Y.Z.tar.gz
        parts = filename.split("-")
        for part in reversed(parts):
            if part.startswith("v") and part[1:].replace(".", "").isdigit():
                return part[1:]
        return "1.0"  # Версия по умолчанию

    def install_theme(self, theme_name: str):
        """Устанавливает указанную тему"""
        themes = self.fetch_available_themes()
        if not themes:
            print("Failed to fetch themes list.")
            return

        if theme_name not in themes:
            print(f"Theme '{theme_name}' not found.")
            return

        theme_url = themes[theme_name]
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
                        ncols=80,  # Ширина прогресс-бара
                    ) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            tmp_file.write(chunk)
                            pbar.update(len(chunk))

                tmp_path = tmp_file.name

            # Целевая директория для темы
            theme_target_dir = cnst.THEMES_FOLDER / theme_name
            theme_target_dir.mkdir(exist_ok=True)

            # Распаковка архива с прогресс-баром
            print(f"Extracting {theme_name}...")
            with tarfile.open(tmp_path, "r:gz") as tar:
                # Получаем список файлов для прогресс-бара
                members = tar.getmembers()
                with tqdm(
                    total=len(members), desc="Extracting files", ncols=80
                ) as pbar:
                    for member in members:
                        tar.extract(member, path=theme_target_dir)
                        pbar.update(1)

            # Обновляем информацию об установленной теме
            self.installed_themes[theme_name] = InstalledThemeInfo(
                name=theme_name,
                version=theme_version,
                source_url=theme_url,
                installed_path=theme_target_dir,
            )
            self._save_installed_themes()
            print(
                f"\nTheme '{theme_name}' (v{theme_version}) successfully installed to {theme_target_dir}"
            )
        except Exception as e:
            logger.error(f"Error installing theme: {e}")
        finally:
            # Удаление временного файла
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def update_theme(self, theme_name: str):
        """Обновляет указанную тему до последней версии"""
        if theme_name not in self.installed_themes:
            print(f"Theme '{theme_name}' is not installed.")
            return

        current_version = self.installed_themes[theme_name].version
        available_themes = self.fetch_available_themes()

        if theme_name not in available_themes:
            print(f"Theme '{theme_name}' not found in available themes.")
            return

        theme_url = available_themes[theme_name]
        new_version = self._extract_version_from_filename(theme_url.split("/")[-1])

        if version.parse(new_version) <= version.parse(current_version):
            print(f"Theme '{theme_name}' is already up to date (v{current_version}).")
            return

        print(
            f"Updating theme '{theme_name}' from v{current_version} to v{new_version}..."
        )
        self.install_theme(theme_name)

    def update_all_themes(self):
        """Обновляет все установленные темы до последних версий"""
        if not self.installed_themes:
            print("No themes installed to update.")
            return

        print("Checking for theme updates...")
        for theme_name in list(self.installed_themes.keys()):
            self.update_theme(theme_name)
