"""Core utilities — config and XDG paths."""

from .config import load_config
from .xdg import cache_dir, config_dir, plugins_dir, state_dir, themes_dir

__all__ = ["load_config", "config_dir", "plugins_dir", "themes_dir", "state_dir", "cache_dir"]
