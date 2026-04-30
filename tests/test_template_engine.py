"""Unit tests for the template rendering engine."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

from pawlette.rendering.templates import _render_template, apply_templates


FAKE_PALETTE_DICT = {
    "color_bg":              "#1e1e2e",
    "color_bg_alt":          "#181825",
    "color_surface":         "#313244",
    "color_surface_alt":     "#45475a",
    "color_text":            "#cdd6f4",
    "color_text_muted":      "#a6adc8",
    "color_text_subtle":     "#585b70",
    "color_primary":         "#cba6f7",
    "color_secondary":       "#89b4fa",
    "color_tertiary":        "#94e2d5",
    "color_red":             "#f38ba8",
    "color_green":           "#a6e3a1",
    "color_yellow":          "#f9e2af",
    "color_blue":            "#89b4fa",
    "color_magenta":         "#cba6f7",
    "color_cyan":            "#94e2d5",
    "color_border_active":   "#cba6f7",
    "color_border_inactive": "#45475a",
}


def test_simple_substitution():
    tpl = "background = {{color_bg}}"
    assert _render_template(tpl, FAKE_PALETTE_DICT) == "background = #1e1e2e"


def test_alpha_filter():
    tpl = "color = {{color_primary | alpha 80}}"
    result = _render_template(tpl, FAKE_PALETTE_DICT)
    # alpha 80% of 255 = 204 = 0xcc
    assert result == "color = #cba6f7cc"


def test_strip_filter():
    tpl = "color = {{color_primary | strip}}"
    assert _render_template(tpl, FAKE_PALETTE_DICT) == "color = cba6f7"


def test_rgb_filter():
    tpl = "rgb({{color_primary | rgb}})"
    assert _render_template(tpl, FAKE_PALETTE_DICT) == "rgb(203,166,247)"


def test_lighten_filter():
    tpl = "{{color_bg | lighten 20}}"
    result = _render_template(tpl, FAKE_PALETTE_DICT)
    # Should produce a lightened hex, not the original
    assert result != "#1e1e2e"
    assert result.startswith("#")
    assert len(result) == 7


def test_unknown_role_preserved():
    tpl = "x = {{nonexistent_role}}"
    result = _render_template(tpl, FAKE_PALETTE_DICT)
    assert result == "x = {{nonexistent_role}}"


def test_apply_templates_dry_run(tmp_path: Path):
    # Create a fake .pawlette template
    tpl_dir = tmp_path / "waybar"
    tpl_dir.mkdir()
    tpl_file = tpl_dir / "style.css.pawlette"
    tpl_file.write_text("background: {{color_bg}};")

    palette = MagicMock()
    palette.to_dict.return_value = FAKE_PALETTE_DICT

    written = apply_templates(palette, config_root=tmp_path, dry_run=True)
    assert len(written) == 1
    # In dry_run mode the target should NOT be created
    assert not (tpl_dir / "style.css").exists()


def test_apply_templates_writes_file(tmp_path: Path):
    tpl_dir = tmp_path / "polybar"
    tpl_dir.mkdir()
    tpl_file = tpl_dir / "config.ini.pawlette"
    tpl_file.write_text("[colors]\nbg = {{color_bg}}\n")

    palette = MagicMock()
    palette.to_dict.return_value = FAKE_PALETTE_DICT

    written = apply_templates(palette, config_root=tmp_path)
    target = tpl_dir / "config.ini"
    assert target.exists()
    assert "#1e1e2e" in target.read_text()
