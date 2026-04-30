from __future__ import annotations

import colorsys
from pathlib import Path

from .palette import Palette

ANALOGOUS_STEP = 30.0
MIN_ACCENT_SAT = 0.45
MIN_SEMANTIC_SAT = 0.50
ANSI_DARK_L = 0.45
ANSI_BRIGHT_L = 0.65
ANSI_MIN_HUE_DIST = 25.0  # closer than this → merge into one slot


# ---------------------------------------------------------------------------
# Colour math
# ---------------------------------------------------------------------------

RGB = tuple[int, int, int]


def _to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h * 360, s, l


def _hsl_to_rgb(h: float, s: float, l: float) -> RGB:
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return round(r * 255), round(g * 255), round(b * 255)


def _hsl_hex(h: float, s: float, l: float) -> str:
    return _to_hex(*_hsl_to_rgb(h, s, l))


def _lum(r: int, g: int, b: int) -> float:
    def _c(v: int) -> float:
        v_ = v / 255
        return v_ / 12.92 if v_ <= 0.04045 else ((v_ + 0.055) / 1.055) ** 2.4

    return 0.2126 * _c(r) + 0.7152 * _c(g) + 0.0722 * _c(b)


def _hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _shift_l(h: float, s: float, l: float, delta: float) -> str:
    return _hsl_hex(h, s, max(0.0, min(1.0, l + delta)))


# ---------------------------------------------------------------------------
# ANSI hue ring builder
# ---------------------------------------------------------------------------


def _build_ansi_hues(
    cluster_hsl: list[tuple[float, float, float]], primary_hue: float, n: int = 6
) -> list[float]:
    """Return `n` maximally-diverse hues for the ANSI colour ring.

    Strategy:
    1. Take cluster hues sorted by saturation (most vivid first).
    2. Greedily add hues that are at least ANSI_MIN_HUE_DIST from all
       already-selected ones (similar to accent picking).
    3. If fewer than `n` distinct hues remain, fill the missing slots
       by evenly spacing from primary_hue around the 360° wheel.
       This guarantees diversity even on monochrome wallpapers.
    """
    # Sort by saturation descending
    by_sat = sorted(cluster_hsl, key=lambda x: -x[1])

    selected: list[float] = []
    for h, s, l in by_sat:
        if all(_hue_dist(h, sh) >= ANSI_MIN_HUE_DIST for sh in selected):
            selected.append(h)
        if len(selected) == n:
            break

    # Fill remaining slots with evenly-spaced hues from primary
    if len(selected) < n:
        step = 360.0 / n
        for i in range(n):
            candidate = (primary_hue + i * step) % 360
            if all(_hue_dist(candidate, sh) >= ANSI_MIN_HUE_DIST for sh in selected):
                selected.append(candidate)
            if len(selected) == n:
                break

    # Last resort: just evenly space from primary regardless
    while len(selected) < n:
        step = 360.0 / n
        selected.append((primary_hue + len(selected) * step) % 360)

    return selected[:n]


# ---------------------------------------------------------------------------
# Pixel extraction
# ---------------------------------------------------------------------------


def _get_palette_colours(image_path: str | Path, n: int = 16) -> list[RGB]:
    from PIL import Image

    img = Image.open(image_path).convert("RGB").resize((192, 192), Image.LANCZOS)
    quantized = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=0)
    palette_raw = quantized.getpalette()
    colours: list[RGB] = [
        (palette_raw[i * 3], palette_raw[i * 3 + 1], palette_raw[i * 3 + 2])
        for i in range(n)
    ]
    hist = quantized.histogram()[:n]
    colours = [c for _, c in sorted(zip(hist, colours), reverse=True)]
    return colours


# ---------------------------------------------------------------------------
# Palette builder
# ---------------------------------------------------------------------------


def _build_palette(colours: list[RGB], mode: str = "dark") -> Palette:
    hsl_all = [_rgb_to_hsl(*c) for c in colours]
    pairs = list(zip(colours, hsl_all))

    # --- BG / FG ---
    by_lum = sorted(pairs, key=lambda x: _lum(*x[0]))
    if mode == "dark":
        bg_rgb, bg_hsl = by_lum[0]
        fg_rgb, fg_hsl = by_lum[-1]
    else:
        bg_rgb, bg_hsl = by_lum[-1]
        fg_rgb, fg_hsl = by_lum[0]

    bh, bs, bl = bg_hsl
    fh, fs, fl = fg_hsl

    bg_lum = _lum(*bg_rgb)
    fg_lum = _lum(*fg_rgb)
    contrast = (max(bg_lum, fg_lum) + 0.05) / (min(bg_lum, fg_lum) + 0.05)
    if contrast < 4.5:
        push = 0.35 if mode == "dark" else -0.35
        fh, fs, fl = _rgb_to_hsl(*_hsl_to_rgb(fh, fs, max(0.0, min(1.0, fl + push))))

    # --- UI surfaces ---
    step = 0.05 if mode == "dark" else -0.05
    bg_hex = _to_hex(*bg_rgb)
    bg_alt_hex = _shift_l(bh, bs, bl, step * 0.8)
    surface_hex = _shift_l(bh, bs, bl, step * 1.8)
    surf_alt_hex = _shift_l(bh, bs, bl, step * 2.8)

    # --- Text ---
    text_hex = _hsl_hex(fh, fs, fl)
    text_muted_hex = _shift_l(fh, fs, fl, -0.18 if mode == "dark" else 0.18)
    text_subtle_hex = _shift_l(fh, fs, fl, -0.34 if mode == "dark" else 0.34)

    # --- Accents ---
    excluded = {bg_rgb, fg_rgb}
    cands = sorted(
        [(rgb, h, s, l) for (rgb, (h, s, l)) in pairs if rgb not in excluded],
        key=lambda x: -x[2],
    )

    def _pick_cluster(
        used_hues: list[float], min_dist: float = 40.0
    ) -> tuple[float, float] | None:
        for _, h, s, l in cands:
            if all(_hue_dist(h, uh) >= min_dist for uh in used_hues):
                return h, s
        return None

    res = _pick_cluster([])
    ph, ps = res if res else ((cands[0][1], cands[0][2]) if cands else (bh, 0.6))
    primary_hex = _hsl_hex(
        ph, max(ps, MIN_ACCENT_SAT), 0.68 if mode == "dark" else 0.42
    )

    res2 = _pick_cluster([ph])
    if res2:
        sh, ss = res2
    else:
        sh, ss = (ph + ANALOGOUS_STEP) % 360, ps
    secondary_hex = _hsl_hex(
        sh, max(ss, MIN_ACCENT_SAT), 0.63 if mode == "dark" else 0.47
    )

    # --- ANSI 16 ---
    # Get 6 diverse hues: real clusters where possible, evenly-spaced fill otherwise
    cluster_hsl_excl = [hsl for rgb, hsl in pairs if rgb not in excluded]
    ansi_hues = _build_ansi_hues(cluster_hsl_excl, primary_hue=ph, n=6)

    # Saturation for ANSI: use primary saturation as baseline, minimum 0.40
    ansi_sat = max(ps, 0.40)

    dark_l = ANSI_DARK_L if mode == "dark" else (1.0 - ANSI_BRIGHT_L)
    bright_l = ANSI_BRIGHT_L if mode == "dark" else (1.0 - ANSI_DARK_L)

    dark_ring = [_hsl_hex(h, ansi_sat, dark_l) for h in ansi_hues]
    bright_ring = [_hsl_hex(h, ansi_sat, bright_l) for h in ansi_hues]

    ansi_bg_dim = _shift_l(bh, bs, bl, step * 1.2)
    ansi_fg_br = _shift_l(fh, fs, fl, 0.08 if mode == "dark" else -0.08)

    # --- Semantic ---
    def _sem(target_hue: float, l_off: float = 0.0) -> str:
        tl = (0.65 if mode == "dark" else 0.40) + l_off
        return _hsl_hex(target_hue, max(ps, MIN_SEMANTIC_SAT), max(0.0, min(1.0, tl)))

    cursor_hex = primary_hex
    selection_hex = _hsl_hex(
        ph, max(ps, MIN_ACCENT_SAT), 0.35 if mode == "dark" else 0.75
    )

    return Palette(
        color_bg=bg_hex,
        color_bg_alt=bg_alt_hex,
        color_surface=surface_hex,
        color_surface_alt=surf_alt_hex,
        color_text=text_hex,
        color_text_muted=text_muted_hex,
        color_text_subtle=text_subtle_hex,
        color_primary=primary_hex,
        color_secondary=secondary_hex,
        color_border_active=primary_hex,
        color_border_inactive=_shift_l(bh, bs, bl, step * 4.0),
        color_cursor=cursor_hex,
        color_selection_bg=selection_hex,
        ansi_color0=bg_hex,
        ansi_color1=dark_ring[0],
        ansi_color2=dark_ring[1],
        ansi_color3=dark_ring[2],
        ansi_color4=dark_ring[3],
        ansi_color5=dark_ring[4],
        ansi_color6=dark_ring[5],
        ansi_color7=text_hex,
        ansi_color8=ansi_bg_dim,
        ansi_color9=bright_ring[0],
        ansi_color10=bright_ring[1],
        ansi_color11=bright_ring[2],
        ansi_color12=bright_ring[3],
        ansi_color13=bright_ring[4],
        ansi_color14=bright_ring[5],
        ansi_color15=ansi_fg_br,
        color_red=_sem(0.0),
        color_green=_sem(120.0),
        color_yellow=_sem(60.0),
        color_blue=_sem(225.0, l_off=-0.04),
        color_cyan=_sem(185.0, l_off=+0.04),
        color_magenta=_sem(300.0),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_native(image_path: str | Path, mode: str = "dark", k: int = 16) -> Palette:
    """Extract a full Palette from a wallpaper image."""
    colours = _get_palette_colours(image_path, n=k)
    return _build_palette(colours, mode=mode)
