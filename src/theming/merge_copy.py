import shutil
import subprocess
from pathlib import Path

from loguru import logger

from .patch_engine import PatchEngine


class MergeCopyHandler:
    __slots__ = "theme_name"

    def __init__(self, theme_name: str) -> None:
        self.theme_name = theme_name

    def apply(self, src: Path, dst: Path, reload_cmd: str = None):
        if not src.exists():
            return

        # Создаем целевую папку, если её нет
        dst.mkdir(parents=True, exist_ok=True)

        # Объединение и патчинг конфигурационных файлов
        self._merge_and_patch(src, dst)

        if reload_cmd:
            self.run_command(reload_cmd)

    def _merge_and_patch(self, src: Path, dst: Path):
        """Рекурсивное копирование с обработкой патчей"""
        patching = {}

        for item in src.iterdir():
            dest_path = dst / item.name

            if item.is_dir():
                # Обработка поддиректорий
                dest_path.mkdir(exist_ok=True)
                self._merge_and_patch(item, dest_path)
            elif item.suffix == ".pre_pawlette":
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
                    }
            elif item.suffix == ".post_pawlette":
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
                    }
            else:
                self._smart_copy(item, dest_path)

        for p in patching.values():
            dst: Path = p["dst"]
            if dst.exists():
                logger.info(f"Patching file: {dst}")
                PatchEngine.apply_to_file(
                    theme_name=self.theme_name,
                    target_file=dst,
                    pre_content=p["pre"],
                    post_content=p["post"],
                )
            else:
                logger.info(f"There is no original file for the patch {dst}")

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
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e.cmd}")
