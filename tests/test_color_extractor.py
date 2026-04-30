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
