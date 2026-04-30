from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# XDG roots
# ---------------------------------------------------------------------------


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))


def _xdg_cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))


# ---------------------------------------------------------------------------
# Pawlette-specific paths
# ---------------------------------------------------------------------------


def config_dir() -> Path:
    """~/.config/pawlette  — user config, themes (static palettes)."""
    return _xdg_config_home() / "pawlette"


def templates_root() -> Path:
    """~/.config  — root directory scanned for *.pawlette templates."""
    return _xdg_config_home()


def plugins_dir() -> Path:
    """~/.local/share/pawlette/plugins  — executable plugin files."""
    return _xdg_data_home() / "pawlette" / "plugins"


def themes_dir() -> Path:
    """~/.local/share/pawlette/themes  — bundled / user-installed themes."""
    return _xdg_data_home() / "pawlette" / "themes"


def state_dir() -> Path:
    """~/.local/state/pawlette  — runtime state (active palette cache, etc.)."""
    return _xdg_state_home() / "pawlette"


def cache_dir() -> Path:
    """~/.cache/pawlette  — ephemeral cache (matugen JSON output, etc.)."""
    return _xdg_cache_home() / "pawlette"


def active_palette_file() -> Path:
    """Path to the last-applied palette JSON (used for quick re-render)."""
    return state_dir() / "active_palette.json"


def matugen_cache_file() -> Path:
    """Cached raw matugen JSON output."""
    return cache_dir() / "matugen_output.json"


def ensure_dirs() -> None:
    """Create all XDG directories that pawlette needs."""
    for d in (config_dir(), plugins_dir(), themes_dir(), state_dir(), cache_dir()):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Debug helper
# ---------------------------------------------------------------------------


def dump() -> dict[str, Path]:
    """Return a mapping of all pawlette XDG paths (useful for --debug)."""
    return {
        "config_dir": config_dir(),
        "templates_root": templates_root(),
        "plugins_dir": plugins_dir(),
        "themes_dir": themes_dir(),
        "state_dir": state_dir(),
        "cache_dir": cache_dir(),
        "active_palette_file": active_palette_file(),
        "matugen_cache_file": matugen_cache_file(),
    }
