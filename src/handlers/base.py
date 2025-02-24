#!/usr/bin/env python3
import subprocess
from abc import ABC
from abc import abstractmethod
from pathlib import Path


class BaseHandler(ABC):
    """Base class for theme handlers"""

    reload_cmd: str

    def __init__(self, reload_cmd: str = None):
        """Initialize the theme handler

        Args:
            reload_cmd (str, optional): Command to reload the app after applying the theme. Defaults to None.
        """
        self.reload_cmd = reload_cmd

    @abstractmethod
    def apply(self, src: Path, dst: Path):
        """Applies the given theme

        Args:
            src (Path): Path to the theme
            dst (Path): Path to the app configuration
        """
        ...

    def run_command(self, command: str) -> None:
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e.cmd}")
