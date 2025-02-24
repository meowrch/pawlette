import shutil
from pathlib import Path

from .base import BaseHandler


class MergeCopyHandler(BaseHandler):
    def apply(self, src: Path, dst: Path):
        if not src.exists():
            return

        # Создаем целевую папку, если её нет
        dst.mkdir(parents=True, exist_ok=True)

        # Копируем с объединением
        for item in dst.iterdir():
            dest = src / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        if self.reload_cmd:
            self.run_command(self.reload_cmd)
