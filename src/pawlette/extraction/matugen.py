from __future__ import annotations

import colorsys
import json
import logging
import subprocess
from typing import Any

from .palette import Mode
from .palette import Palette

log = logging.getLogger(__name__)


def extract_matugen(
    source_type: str,
    *args: str,
    mode: Mode = "dark",
    matugen_config: dict[str, Any] | None = None,
) -> Palette:
    """Extract palette using matugen backend.

    Parameters
    ----------
    source_type:
        "image" or "color"
    *args:
        Additional arguments (e.g., path for image, "hex", "#color" for color)
    mode:
        "dark" or "light"
    matugen_config:
        Optional backend-specific configuration dict
    """
    raw = _run_matugen(source_type, *args, matugen_config=matugen_config)
    return _map_matugen_to_palette(raw, mode=mode)


def _run_matugen(
    *args: str, matugen_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run matugen with optional config overrides.

    Parameters
    ----------
    *args:
        Positional arguments for matugen (e.g., "image", "/path/to/file")
    matugen_config:
        Optional dict with matugen settings from config file.
        Supported keys: "prefer" (darkness/lightness/saturation/etc.), "fallback_color" (hex color for closest-to-fallback)
    """
    if matugen_config is None:
        matugen_config = {}

    # Build command with config options
    cmd = ["matugen", *args, "--json", "hex"]

    # Add --prefer if configured
    prefer = matugen_config.get("prefer", "darkness")  # default to darkness
    if prefer:
        cmd.extend(["--prefer", prefer])

        # If prefer is closest-to-fallback, add --fallback-color
        if prefer == "closest-to-fallback":
            fallback = matugen_config.get("fallback_color", "#cba6f7")  # default purple
            cmd.extend(["--fallback-color", fallback])

    log.debug("Running matugen: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "matugen is not installed or not in PATH. "
            "Install it from https://github.com/InioX/matugen"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"matugen failed (exit {exc.returncode}):\n{exc.stderr.strip()}"
        ) from exc
    return json.loads(result.stdout)


def _pick(colors: dict[str, Any], *keys: str, mode: Mode) -> str:
    opposite: Mode = "light" if mode == "dark" else "dark"
    for k in keys:
        if k not in colors:
            continue
        entry = colors[k]
        if isinstance(entry, str):
            return entry
        # Try mode, opposite, default, or first available
        value = (
            entry.get(mode)
            or entry.get(opposite)
            or entry.get("default")
            or next(iter(entry.values()))
        )
        # Extract "color" field if value is a dict
        if isinstance(value, dict) and "color" in value:
            return value["color"]
        if isinstance(value, str):
            return value
        # Fallback: convert to string
        return str(value)
    raise KeyError(f"None of {keys} found in matugen output")


def _map_matugen_to_palette(raw: dict[str, Any], mode: Mode = "dark") -> Palette:
    colors: dict[str, Any] = raw.get("colors", {})

    def p(*keys: str) -> str:
        return _pick(colors, *keys, mode=mode)

    bg = p("background", "surface")
    fg = p("on_background", "on_surface")
    primary = p("primary")

    # Derive semantic from primary hue (same as native backend logic)
    def _hex_to_hsl(h: str) -> tuple[float, float, float]:
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        hh, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        return hh * 360, s, l

    def _sem(target_hue: float, l_off: float = 0.0) -> str:
        ph, ps, _ = _hex_to_hsl(primary)
        tl = (0.65 if mode == "dark" else 0.40) + l_off
        r, g, b = colorsys.hls_to_rgb(
            target_hue / 360, max(0.0, min(1.0, tl)), max(ps, 0.50)
        )
        return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"

    # Build a minimal ANSI ring from matugen accents
    _ring_keys = [
        ("error", "tertiary"),
        ("tertiary", "secondary"),
        ("secondary", "primary"),
        ("primary", "secondary"),
        ("secondary", "tertiary"),
        ("tertiary", "error"),
    ]

    def _ring(i: int) -> str:
        return p(*_ring_keys[i % 6])

    def _brighten(hex_c: str, delta: float = 0.12) -> str:
        # Ensure hex_c is a string (handle dict values from matugen)
        if not isinstance(hex_c, str):
            hex_c = str(hex_c)
        # Strip quotes and whitespace
        hex_c = hex_c.strip().strip("'\"")
        # Ensure it starts with #
        if not hex_c.startswith("#"):
            hex_c = "#" + hex_c
        r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        r2, g2, b2 = colorsys.hls_to_rgb(h, min(1.0, l + delta), s)
        return f"#{round(r2 * 255):02x}{round(g2 * 255):02x}{round(b2 * 255):02x}"

    return Palette(
        # UI
        color_bg=bg,
        color_bg_alt=p("surface_dim", "surface_container_low", "surface"),
        color_surface=p("surface_container", "surface_container_high"),
        color_surface_alt=p("surface_container_highest", "surface_container_high"),
        color_text=fg,
        color_text_muted=p("on_surface_variant", "outline"),
        color_text_subtle=p("outline", "outline_variant"),
        color_primary=primary,
        color_secondary=p("secondary"),
        color_border_active=primary,
        color_border_inactive=p("outline_variant", "surface_container_highest"),
        color_cursor=fg,
        color_selection_bg=primary,
        # ANSI
        ansi_color0=bg,
        ansi_color1=_ring(0),
        ansi_color2=_ring(1),
        ansi_color3=_ring(2),
        ansi_color4=_ring(3),
        ansi_color5=_ring(4),
        ansi_color6=_ring(5),
        ansi_color7=fg,
        ansi_color8=p("surface_dim", "surface_container_low"),
        ansi_color9=_brighten(_ring(0)),
        ansi_color10=_brighten(_ring(1)),
        ansi_color11=_brighten(_ring(2)),
        ansi_color12=_brighten(_ring(3)),
        ansi_color13=_brighten(_ring(4)),
        ansi_color14=_brighten(_ring(5)),
        ansi_color15=_brighten(fg),
        # Semantic (always true hues)
        color_red=_sem(0.0),
        color_green=_sem(120.0),
        color_yellow=_sem(60.0),
        color_blue=_sem(225.0, l_off=-0.04),
        color_cyan=_sem(185.0, l_off=+0.04),
        color_magenta=_sem(300.0),
    )
