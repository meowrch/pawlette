#!/usr/bin/env python3
from pathlib import Path
from typing import List


def create_dirs(paths: List[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
