import json
import shutil
import subprocess
import traceback
from pathlib import Path

from loguru import logger

import pawlette.constants as cnst
from pawlette.schemas.commands import CommandInfo
from pawlette.schemas.themes import Theme

from .patch_engine import PatchEngine
from pawlette.schemas.config_struct import Config


class MergeCopyHandler:
    __slots__ = "theme", "config"

    def __init__(self, theme: Theme, config: Config) -> None:
        self.theme: Theme = theme
        self.config: Config = config

    def apply_for_all_configs(self):
        for app in (self.theme.path / "configs").iterdir():
            app_name = app.stem
            command = cnst.RELOAD_COMMANDS.get(app_name, None)

            try:
                logger.info(
                    f'Applying theme for "{app_name}" application. {app} -> {cnst.XDG_CONFIG_HOME / app_name}'
                )

                self.apply(
                    src=app, dst=cnst.XDG_CONFIG_HOME / app_name, command=command
                )
            except Exception:
                logger.warning(
                    f'Theme application error for the "{app_name}" application: {traceback.format_exc()}'
                )

    def apply(
        self,
        src: Path,
        dst: Path,
        command: CommandInfo = None,
    ):
        if not src.exists():
            return

        # Создаем целевую папку, если её нет
        dst.mkdir(parents=True, exist_ok=True)

        # Объединение и патчинг конфигурационных файлов
        self._merge_and_patch(src, dst)

        if command:
            if command.check_command_exists:
                if not shutil.which(command.check_command_exists):
                    return
            if command.check_process:
                result = subprocess.run(
                    ["pgrep", command.check_process], capture_output=True
                )
                if result.returncode != 0:
                    return
            self.run_command(command.command)

    def _merge_dicts(self, base: dict, override: dict) -> dict:
        """Глубокое слияние словарей с приоритетом override"""
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_dicts(result[k], v)
            else:
                result[k] = v
        return result

    def _merge_and_patch(self, src: Path, dst: Path):
        """Рекурсивное копирование с обработкой патчей"""
        patching = {}

        for item in src.iterdir():
            dest_path = dst / item.name

            if item.is_dir():
                # Обработка поддиректорий
                dest_path.mkdir(exist_ok=True)
                self._merge_and_patch(item, dest_path)
            elif item.suffix == ".prepaw":
                with open(item) as f:
                    content = f.read()

                patch_name = item.with_suffix("").name
                if patch_name in patching:
                    patching[patch_name]["pre"] = content
                else:
                    patching[patch_name] = {
                        "dst": dest_path.with_suffix(""),
                        "pre": content,
                        "post": None,
                        "merge": None,
                    }
            elif item.suffix == ".postpaw":
                with open(item) as f:
                    content = f.read()

                patch_name = item.with_suffix("").name
                if patch_name in patching:
                    patching[patch_name]["post"] = content
                else:
                    patching[patch_name] = {
                        "dst": dest_path.with_suffix(""),
                        "pre": None,
                        "post": content,
                        "merge": None,
                    }
            elif item.suffix == ".jsonpaw":
                # JSON merge-патч
                try:
                    with open(item) as f:
                        merge_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Invalid JSON in merge patch {item}: {e}")
                    continue

                patch_name = item.with_suffix("").name
                if patch_name in patching:
                    patching[patch_name]["merge"] = merge_data
                else:
                    patching[patch_name] = {
                        "dst": dest_path.with_suffix(""),
                        "pre": None,
                        "post": None,
                        "merge": merge_data,
                    }
            else:
                self._smart_copy(item, dest_path)

        for p in patching.values():
            dst_file: Path = p["dst"]
            if not dst_file.exists():
                logger.info(f"There is no original file for the patch {dst_file}")
                continue

            # Сначала применяем JSON merge (если есть)
            if p.get("merge") is not None:
                try:
                    with open(dst_file) as f:
                        current = json.load(f)
                    if not isinstance(current, dict):
                        raise ValueError("Target JSON is not an object")
                except Exception as e:
                    logger.warning(
                        f"Cannot read/parse target JSON {dst_file}: {e}. Skipping merge for this file"
                    )
                else:
                    if isinstance(p["merge"], dict):
                        merged = self._merge_dicts(current, p["merge"])
                        with open(dst_file, "w", encoding="utf-8") as f:
                            json.dump(merged, f, ensure_ascii=False, indent=2)
                            f.write("\n")
                        logger.info(f"Merged JSON into: {dst_file}")
                    else:
                        logger.warning(
                            f"Merge patch for {dst_file} is not a JSON object, skipping"
                        )

            # Затем применяем PRE/POST патчи
            if p.get("pre") or p.get("post"):
                logger.info(f"Patching file: {dst_file}")
                PatchEngine.apply_to_file(
                    theme_name=self.theme.name,
                    target_file=dst_file,
                    config=self.config,
                    pre_content=p.get("pre"),
                    post_content=p.get("post"),
                )

    def _smart_copy(self, src: Path, dst: Path):
        """Интеллектуальное копирование с проверкой хэшей"""
        if not dst.exists() or self._files_differ(src, dst):
            shutil.copy2(src, dst)

    def _files_differ(self, file1: Path, file2: Path) -> bool:
        """Сравнение файлов по хэшу"""
        return (
            file1.stat().st_mtime != file2.stat().st_mtime
            or file1.read_bytes() != file2.read_bytes()
        )

    def run_command(self, command: str) -> None:
        try:
            subprocess.run(
                command.split(),
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            print(f"Error executing command: {traceback.format_exc()}")
