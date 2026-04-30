from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Mode = Literal["dark", "light"]

DEFAULT_MODE: Mode = "dark"


@dataclass
class Palette:
    """Role-based palette used across pawlette.

    UI roles
    --------
    color_bg            Deepest background
    color_bg_alt        Panels, sidebars (one step up)
    color_surface       Buttons, inputs
    color_surface_alt   Hover / elevated surface
    color_text          Primary readable text
    color_text_muted    Secondary text, placeholders
    color_text_subtle   Disabled, captions
    color_primary       Main accent — active tabs, selection highlight
    color_secondary     Secondary accent
    color_border_active   Active window border
    color_border_inactive Inactive window border
    color_cursor        Terminal / editor cursor
    color_selection_bg  Text selection background

    ANSI 16 (terminal palette)
    --------------------------
    ansi_color0..ansi_color15
    All 16 colours come from the wallpaper directly.
    color0  = darkest (terminal background)
    color7  = lightest (terminal foreground)
    color8  = dim background variant
    color15 = bright foreground variant
    color1-6   dark accent ring
    color9-14  bright accent ring

    Semantic (always true colours, never ANSI aliases)
    --------------------------------------------------
    color_red / color_green / color_yellow
    color_blue / color_cyan / color_magenta
    Derived at fixed target hues using primary saturation.
    """

    # --- UI roles ---
    color_bg: str = "#000000"
    color_bg_alt: str = "#000000"
    color_surface: str = "#000000"
    color_surface_alt: str = "#000000"
    color_text: str = "#ffffff"
    color_text_muted: str = "#ffffff"
    color_text_subtle: str = "#ffffff"
    color_primary: str = "#ffffff"
    color_secondary: str = "#ffffff"
    color_border_active: str = "#ffffff"
    color_border_inactive: str = "#ffffff"
    color_cursor: str = "#ffffff"
    color_selection_bg: str = "#ffffff"

    # --- ANSI 16 ---
    ansi_color0: str = "#000000"
    ansi_color1: str = "#000000"
    ansi_color2: str = "#000000"
    ansi_color3: str = "#000000"
    ansi_color4: str = "#000000"
    ansi_color5: str = "#000000"
    ansi_color6: str = "#000000"
    ansi_color7: str = "#ffffff"
    ansi_color8: str = "#000000"
    ansi_color9: str = "#000000"
    ansi_color10: str = "#000000"
    ansi_color11: str = "#000000"
    ansi_color12: str = "#000000"
    ansi_color13: str = "#000000"
    ansi_color14: str = "#000000"
    ansi_color15: str = "#ffffff"

    # --- Semantic (true colours) ---
    color_red: str = "#ff0000"
    color_green: str = "#00ff00"
    color_yellow: str = "#ffff00"
    color_blue: str = "#0000ff"
    color_cyan: str = "#00ffff"
    color_magenta: str = "#ff00ff"

    # -----------------------------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()

    def to_env(self) -> dict[str, str]:
        """Flat env-var mapping for plugins/scripts."""
        d = self.to_dict()
        return {f"PAWLETTE_{k.upper()}": v for k, v in d.items()}

    def ansi_dict(self) -> dict[str, str]:
        """Only the 16 ANSI colours as {color0: hex, ...}."""
        return {
            k.replace("ansi_", ""): v
            for k, v in self.to_dict().items()
            if k.startswith("ansi_")
        }
