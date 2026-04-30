from __future__ import annotations

import colorsys
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pawlette.color_extractor import Palette

log = logging.getLogger(__name__)

# Matches the whole {{ ... }} token, captures everything inside
_TOKEN_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")

# Splits a single filter segment like "darken 15" or "strip"
_FILTER_RE = re.compile(r"([a-z]+)(?:\s+(\d+(?:\.\d+)?))?")


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) not in (6, 8):
        raise ValueError(f"Invalid hex colour: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    )


def _apply_alpha(hex_color: str, percent: float) -> str:
    alpha = round(percent / 100 * 255)
    return hex_color.rstrip()[:7] + f"{alpha:02x}"


def _lighten(hex_color: str, amount: float) -> str:
    # strip alpha before operating, re-append after
    base = hex_color[:7]
    suffix = hex_color[7:]
    r, g, b = _hex_to_rgb(base)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = min(1.0, l + amount / 100)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(round(r2 * 255), round(g2 * 255), round(b2 * 255)) + suffix


def _darken(hex_color: str, amount: float) -> str:
    base = hex_color[:7]
    suffix = hex_color[7:]
    r, g, b = _hex_to_rgb(base)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = max(0.0, l - amount / 100)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(round(r2 * 255), round(g2 * 255), round(b2 * 255)) + suffix


def _apply_single_filter(value: str, filter_name: str, filter_arg: str | None) -> str:
    """Apply one filter to *value* (which may already be non-hex after strip/rgb)."""
    arg = float(filter_arg) if filter_arg is not None else None

    match filter_name:
        case "alpha":
            return _apply_alpha(value, arg or 100)
        case "lighten":
            return _lighten(value, arg or 10)
        case "darken":
            return _darken(value, arg or 10)
        case "strip":
            return value.lstrip("#")
        case "rgb":
            r, g, b = _hex_to_rgb(value)
            return f"{r},{g},{b}"
        case "uppercase":
            return value.upper()
        case _:
            log.warning("Unknown filter %r — skipping", filter_name)
            return value


def _apply_filter_chain(hex_color: str, raw_chain: str) -> str:
    """Parse and apply a `|`-separated filter chain to *hex_color*.

    Each segment is "filtername [arg]", e.g. "darken 15" or "strip".
    Filters are applied left-to-right.
    """
    value = hex_color
    for segment in raw_chain.split("|"):
        segment = segment.strip()
        if not segment:
            continue
        m = _FILTER_RE.fullmatch(segment)
        if not m:
            log.warning("Cannot parse filter segment %r — skipping", segment)
            continue
        value = _apply_single_filter(value, m.group(1), m.group(2))
    return value


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render_template(template: str, palette_dict: dict[str, str]) -> str:
    """Replace all {{token}} occurrences in *template* with palette values."""

    def replacer(match: re.Match) -> str:
        inner = match.group(1).strip()

        # Split on the first `|` to get role name and the rest (filter chain)
        if "|" in inner:
            role, chain = inner.split("|", 1)
            role = role.strip()
        else:
            role = inner
            chain = ""

        hex_color = palette_dict.get(role)
        if hex_color is None:
            log.warning("Unknown palette role %r — leaving token as-is", role)
            return match.group(0)

        if not chain.strip():
            return hex_color

        return _apply_filter_chain(hex_color, chain)

    return _TOKEN_RE.sub(replacer, template)


# ---------------------------------------------------------------------------
# File system scan & apply
# ---------------------------------------------------------------------------


def apply_templates(
    palette: "Palette",
    config_root: str | Path | None = None,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Scan *config_root* for .pawlette files and render them in-place.

    Parameters
    ----------
    palette:
        Active Palette instance to use for substitution.
    config_root:
        Root directory to scan. Defaults to ~/.config.
    dry_run:
        If True, do not write any files — only return the list of targets.

    Returns
    -------
    List of Path objects that were (or would be) written.
    """
    if config_root is None:
        config_root = Path.home() / ".config"
    else:
        config_root = Path(config_root)

    palette_dict = palette.to_dict()
    written: list[Path] = []

    for template_path in sorted(config_root.rglob("*.pawlette")):
        target_path = template_path.with_suffix("")  # strip .pawlette

        try:
            raw = template_path.read_text(encoding="utf-8")
        except OSError as exc:
            log.error("Cannot read template %s: %s", template_path, exc)
            continue

        rendered = _render_template(raw, palette_dict)

        if not dry_run:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(rendered, encoding="utf-8")
                log.info("Rendered %s → %s", template_path.name, target_path)
            except OSError as exc:
                log.error("Cannot write %s: %s", target_path, exc)
                continue

        written.append(target_path)

    return written
