"""Unit tests for the matugen → Palette mapping logic."""

from pawlette.extraction.matugen import _map_matugen_to_palette


FAKE_MATUGEN_OUTPUT = {
    "colors": {
        "background":                  {"hex": "#1e1e2e"},
        "surface_dim":                 {"hex": "#181825"},
        "surface_container":           {"hex": "#313244"},
        "surface_container_highest":   {"hex": "#45475a"},
        "on_background":               {"hex": "#cdd6f4"},
        "on_surface_variant":          {"hex": "#a6adc8"},
        "outline":                     {"hex": "#585b70"},
        "outline_variant":             {"hex": "#45475a"},
        "primary":                     {"hex": "#cba6f7"},
        "secondary":                   {"hex": "#89b4fa"},
        "tertiary":                    {"hex": "#94e2d5"},
        "error":                       {"hex": "#f38ba8"},
        "surface":                     {"hex": "#1e1e2e"},
        "surface_variant":             {"hex": "#181825"},
        "on_surface":                  {"hex": "#cdd6f4"},
        "surface_container_high":      {"hex": "#313244"},
    }
}


def _lightness(hex_c: str) -> float:
    """HSL lightness in [0, 1] of a #rrggbb string."""
    import colorsys

    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    _, lightness, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return lightness


def _matugen_with(**overrides: dict) -> dict:
    """Deep copy of FAKE_MATUGEN_OUTPUT with color *overrides* applied."""
    import copy

    out = copy.deepcopy(FAKE_MATUGEN_OUTPUT)
    out["colors"].update(overrides)
    return out


def test_palette_fields_populated():
    palette = _map_matugen_to_palette(FAKE_MATUGEN_OUTPUT)
    assert palette.color_bg == "#1e1e2e"
    assert palette.color_primary == "#cba6f7"
    assert palette.color_red.startswith("#")  # Semantic colors are derived, not from matugen
    assert palette.color_border_inactive == "#45475a"


def test_to_env_keys():
    palette = _map_matugen_to_palette(FAKE_MATUGEN_OUTPUT)
    env = palette.to_env()
    assert "PAWLETTE_COLOR_BG" in env
    assert "PAWLETTE_COLOR_PRIMARY" in env
    assert env["PAWLETTE_COLOR_TEXT"] == "#cdd6f4"


def test_to_dict_roundtrip():
    palette = _map_matugen_to_palette(FAKE_MATUGEN_OUTPUT)
    d = palette.to_dict()
    assert d["color_secondary"] == "#89b4fa"


def test_bg_alt_is_lighter_than_bg_dark_mode():
    """bg_alt must be one step lighter than bg (dark mode)."""
    palette = _map_matugen_to_palette(FAKE_MATUGEN_OUTPUT, mode="dark")
    assert _lightness(palette.color_bg_alt) > _lightness(palette.color_bg)


def test_bg_alt_prefers_surface_container_low_over_surface_dim():
    """When surface_dim == background (common matugen output), bg_alt must pick
    the lighter surface_container_low instead of collapsing back to bg."""
    raw = _matugen_with(
        background={"hex": "#151218"},
        surface={"hex": "#151218"},
        surface_dim={"hex": "#151218"},
        surface_container_low={"hex": "#1d1a20"},
    )
    palette = _map_matugen_to_palette(raw, mode="dark")
    assert palette.color_bg == "#151218"
    assert palette.color_bg_alt == "#1d1a20"
    assert _lightness(palette.color_bg_alt) > _lightness(palette.color_bg)


def test_bg_alt_is_darker_than_bg_light_mode():
    """In light mode the step direction reverses: bg_alt is darker than bg.
    (FAKE_MATUGEN_OUTPUT is mode-agnostic, so bg stays the same hex in both
    modes — this only exercises the sign of the derived step.)"""
    palette = _map_matugen_to_palette(FAKE_MATUGEN_OUTPUT, mode="light")
    assert _lightness(palette.color_bg_alt) < _lightness(palette.color_bg)
