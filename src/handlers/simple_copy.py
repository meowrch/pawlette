#!/usr/bin/env python3
import shutil
from pathlib import Path

from .base import BaseHandler


class SimpleCopyHandler(BaseHandler):
    def apply(self, src: Path, dst: Path):
        if not src.exists():
            return

        if dst.exists():
            shutil.rmtree(dst)

        shutil.copytree(src, dst)
        if self.reload_cmd:
            self.run_command(self.reload_cmd)
