from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load pawlette.toml configuration.

    Parameters
    ----------
    config_path:
        Path to pawlette.toml. If None, uses ~/.config/pawlette/pawlette.toml

    Returns
    -------
    Dict with configuration, or empty dict if file doesn't exist or can't be parsed.
    """
    if config_path is None:
        from pawlette.core import xdg

        config_path = xdg.config_dir() / "pawlette.toml"

    if not config_path.exists():
        log.debug("Config file not found: %s", config_path)
        return {}

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            log.warning("tomllib/tomli not available — cannot load config")
            return {}

    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not parse config %s: %s", config_path, exc)
        return {}


def get_backend_config(config: dict[str, Any], backend: str) -> dict[str, Any]:
    """Extract backend-specific configuration.

    Parameters
    ----------
    config:
        Full config dict from load_config()
    backend:
        Backend name (e.g., "native", "matugen")

    Returns
    -------
    Dict with backend options, or empty dict if not configured.
    """
    return config.get("backends", {}).get(backend, {})


def get_default_backend(config: dict[str, Any]) -> str | None:
    """Get the default backend from config.

    Returns None if not configured (caller should use hardcoded default).
    """
    return config.get("backend")


def get_default_mode(config: dict[str, Any]) -> str | None:
    """Get the default mode (dark/light) from config.

    Returns None if not configured (caller should use hardcoded default).
    """
    return config.get("mode")
