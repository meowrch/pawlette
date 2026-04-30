"""Tests for the static theme loader."""

from pathlib import Path

import pytest

from pawlette.rendering.themes import list_themes, load_theme


MINIMAL_COLORS = {
    "color_bg":              "#1e1e2e",
    "color_bg_alt":          "#181825",
    "color_surface":         "#313244",
    "color_surface_alt":     "#45475a",
    "color_text":            "#cdd6f4",
    "color_text_muted":      "#a6adc8",
    "color_text_subtle":     "#585b70",
    "color_primary":         "#cba6f7",
    "color_secondary":       "#89b4fa",
    "color_border_active":   "#cba6f7",
    "color_border_inactive": "#45475a",
    "color_cursor":          "#cdd6f4",
    "color_selection_bg":    "#cba6f7",
    "color_red":             "#f38ba8",
    "color_green":           "#a6e3a1",
    "color_yellow":          "#f9e2af",
    "color_blue":            "#89b4fa",
    "color_magenta":         "#cba6f7",
    "color_cyan":            "#94e2d5",
    "ansi_color0":           "#1e1e2e",
    "ansi_color1":           "#f38ba8",
    "ansi_color2":           "#a6e3a1",
    "ansi_color3":           "#f9e2af",
    "ansi_color4":           "#89b4fa",
    "ansi_color5":           "#cba6f7",
    "ansi_color6":           "#94e2d5",
    "ansi_color7":           "#cdd6f4",
    "ansi_color8":           "#313244",
    "ansi_color9":           "#f38ba8",
    "ansi_color10":          "#a6e3a1",
    "ansi_color11":          "#f9e2af",
    "ansi_color12":          "#89b4fa",
    "ansi_color13":          "#cba6f7",
    "ansi_color14":          "#94e2d5",
    "ansi_color15":          "#cdd6f4",
}


def _write_theme(themes_dir: Path, name: str, colors: dict) -> None:
    theme_dir = themes_dir / name
    theme_dir.mkdir(parents=True)
    lines = ["[colors]\n"] + [f'{k} = "{v}"\n' for k, v in colors.items()]
    (theme_dir / "colors.toml").write_text("".join(lines))


def test_load_valid_theme(tmp_path):
    _write_theme(tmp_path, "test-theme", MINIMAL_COLORS)
    palette = load_theme("test-theme", tmp_path)
    assert palette.color_bg == "#1e1e2e"
    assert palette.color_primary == "#cba6f7"


def test_load_missing_theme(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_theme("nonexistent", tmp_path)


def test_load_incomplete_theme(tmp_path):
    incomplete = {"color_bg": "#1e1e2e"}  # missing most fields
    _write_theme(tmp_path, "bad-theme", incomplete)
    with pytest.raises(ValueError, match="missing required fields"):
        load_theme("bad-theme", tmp_path)


def test_list_themes(tmp_path):
    _write_theme(tmp_path, "alpha", MINIMAL_COLORS)
    _write_theme(tmp_path, "beta", MINIMAL_COLORS)
    # directory without colors.toml should be ignored
    (tmp_path / "empty-dir").mkdir()
    themes = list_themes(tmp_path)
    assert themes == ["alpha", "beta"]


def test_list_themes_empty_dir(tmp_path):
    assert list_themes(tmp_path) == []


def test_list_themes_nonexistent_dir(tmp_path):
    assert list_themes(tmp_path / "no-such-dir") == []
