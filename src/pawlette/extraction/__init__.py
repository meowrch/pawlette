"""Colour extraction facade.

Backends
--------
  native   (default)
      PIL median-cut quantize + HSL role mapping.
      Only requires Pillow. Fast, no external binaries.

  matugen
      Calls the external `matugen` binary (Material You).
      Requires matugen to be installed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from .matugen import extract_matugen
from .native import extract_native
from .palette import Mode, Palette

Backend = Literal["native", "matugen"]

DEFAULT_MODE: Mode = "dark"
DEFAULT_BACKEND: Backend = "native"

log = logging.getLogger(__name__)

__all__ = ["Palette", "Mode", "Backend", "extract_from_image", "extract_from_hex", "extract_native", "extract_matugen"]


def extract_from_image(
    wallpaper: str | Path,
    mode: Mode = DEFAULT_MODE,
    backend: Backend = DEFAULT_BACKEND,
    backend_config: dict[str, Any] | None = None,
) -> Palette:
    """Extract palette from an image file.

    Parameters
    ----------
    wallpaper:
        Path to wallpaper image (symlinks are resolved automatically)
    mode:
        "dark" or "light"
    backend:
        "native" or "matugen"
    backend_config:
        Optional backend-specific configuration dict
    """
    # Resolve symlinks to get the actual image path
    wallpaper_path = Path(wallpaper).resolve()

    if backend == "native":
        return extract_native(wallpaper_path, mode=mode)
    return extract_matugen("image", str(wallpaper_path), mode=mode, matugen_config=backend_config)


def extract_from_hex(
    hex_color: str,
    mode: Mode = DEFAULT_MODE,
    backend: Backend = DEFAULT_BACKEND,
    backend_config: dict[str, Any] | None = None,
) -> Palette:
    """Extract palette from a seed hex colour (matugen only).

    Parameters
    ----------
    hex_color:
        Seed color in hex format (e.g., "#cba6f7")
    mode:
        "dark" or "light"
    backend:
        "native" or "matugen" (native will fallback to matugen)
    backend_config:
        Optional backend-specific configuration dict
    """
    if backend == "native":
        log.warning(
            "Native backend does not support hex seed — falling back to matugen."
        )
    return extract_matugen("color", "hex", hex_color, mode=mode, matugen_config=backend_config)
