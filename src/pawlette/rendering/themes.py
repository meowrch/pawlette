from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from pawlette.extraction import Palette

log = logging.getLogger(__name__)

# All Palette field names — used to validate colors.toml
_PALETTE_FIELDS = set(Palette.__dataclass_fields__.keys())


def _parse_tomllib(data: str) -> dict:
    """Parse TOML string, handling both tomllib (3.11+) and tomli fallback."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError as exc:
            raise ImportError(
                "tomllib is not available. Install 'tomli' for Python < 3.11."
            ) from exc
    return tomllib.loads(data)


def load_theme(name: str, themes_dir: Path, variant: str | None = None) -> Palette:
    """Load a static theme by name from *themes_dir*.

    Parameters
    ----------
    name:
        Theme directory name.
    themes_dir:
        Root directory containing theme folders.
    variant:
        Optional variant name to merge overrides from
        [variants.<variant>] section in colors.toml.

    Raises
    ------
    FileNotFoundError:
        If the theme directory or colors.toml does not exist.
    ValueError:
        If colors.toml is missing required palette fields,
        or if the requested variant does not exist,
        or if the variant overrides an unknown palette field.
    """
    theme_dir = themes_dir / name
    colors_file = theme_dir / "colors.toml"

    if not colors_file.exists():
        raise FileNotFoundError(f"Theme {name!r} not found. Expected: {colors_file}")

    data = _parse_tomllib(colors_file.read_text(encoding="utf-8"))

    # Base palette — support [colors] section or flat dict
    colors: dict[str, str] = data.get("colors", data)

    # Apply variant overrides if requested
    if variant is not None:
        variants = data.get("variants", {})
        if variant not in variants:
            raise ValueError(
                f"Theme {name!r} has no variant {variant!r}. "
                f"Available: {', '.join(sorted(variants.keys())) or 'none'}"
            )
        override = variants[variant]
        unknown_override = set(override.keys()) - _PALETTE_FIELDS
        if unknown_override:
            raise ValueError(
                f"Variant {variant!r} of theme {name!r} "
                f"overrides unknown fields: {', '.join(sorted(unknown_override))}"
            )
        colors = {**colors, **override}

    missing = _PALETTE_FIELDS - set(colors.keys())
    if missing:
        raise ValueError(
            f"Theme {name!r} is missing required fields: {', '.join(sorted(missing))}"
        )

    return Palette(**{k: colors[k] for k in _PALETTE_FIELDS})


def list_themes(themes_dir: Path) -> list[str]:
    """Return names of all installed themes (directories with colors.toml)."""
    if not themes_dir.exists():
        return []
    return sorted(
        d.name
        for d in themes_dir.iterdir()
        if d.is_dir() and (d / "colors.toml").exists()
    )


def list_theme_variants(name: str, themes_dir: Path) -> list[str]:
    """Return variant names for a given theme, or empty list if none.

    Raises
    ------
    FileNotFoundError:
        If the theme directory or colors.toml does not exist.
    """
    colors_file = themes_dir / name / "colors.toml"
    if not colors_file.exists():
        raise FileNotFoundError(f"Theme {name!r} not found. Expected: {colors_file}")

    data = _parse_tomllib(colors_file.read_text(encoding="utf-8"))
    variants = data.get("variants", {})
    return sorted(variants.keys())


def theme_meta(name: str, themes_dir: Path) -> dict[str, str]:
    """Read optional meta.toml for display info. Returns empty dict if absent."""
    meta_file = themes_dir / name / "meta.toml"
    if not meta_file.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    return tomllib.loads(meta_file.read_text(encoding="utf-8"))
