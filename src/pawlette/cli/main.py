from __future__ import annotations

import argparse
import json
import logging
import sys

from pawlette.cli.migration import migrate_from_v1
from pawlette.core import xdg
from pawlette.extraction import DEFAULT_BACKEND
from pawlette.extraction import DEFAULT_MODE
from pawlette.extraction import Palette
from pawlette.extraction import extract_from_hex
from pawlette.extraction import extract_from_image
from pawlette.plugins import run_plugins
from pawlette.rendering import apply_templates


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)-8s %(message)s", level=level)


# ---------------------------------------------------------------------------
# Palette persistence
# ---------------------------------------------------------------------------


def _save_palette(palette: Palette) -> None:
    path = xdg.active_palette_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(palette.to_dict(), indent=2), encoding="utf-8")


def _load_palette() -> Palette | None:
    path = xdg.active_palette_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Palette(**data)
    except Exception as exc:
        logging.warning("Could not load cached palette: %s", exc)
        return None


def _print_palette(palette: Palette, mode: str = "", backend: str = "") -> None:
    groups = [
        (
            "Surfaces",
            ["color_bg", "color_bg_alt", "color_surface", "color_surface_alt"],
        ),
        ("Text", ["color_text", "color_text_muted", "color_text_subtle"]),
        ("Accents", ["color_primary", "color_secondary"]),
        ("Borders", ["color_border_active", "color_border_inactive"]),
        ("Cursor", ["color_cursor", "color_selection_bg"]),
        (
            "Semantic",
            [
                "color_red",
                "color_green",
                "color_yellow",
                "color_blue",
                "color_cyan",
                "color_magenta",
            ],
        ),
        ("ANSI dark", [f"ansi_color{i}" for i in range(8)]),
        ("ANSI bright", [f"ansi_color{i}" for i in range(8, 16)]),
    ]
    meta = " ".join(
        filter(
            None,
            [
                f"mode={mode}" if mode else "",
                f"backend={backend}" if backend else "",
            ],
        )
    )
    if meta:
        print(f"\n  [{meta}]")
    d = palette.to_dict()
    for group_name, fields in groups:
        print(f"\n  {group_name}")
        for f in fields:
            hex_val = d.get(f, "?")
            if len(hex_val) == 7 and hex_val.startswith("#"):
                r, g, b = (
                    int(hex_val[1:3], 16),
                    int(hex_val[3:5], 16),
                    int(hex_val[5:7], 16),
                )
                swatch = f"\x1b[48;2;{r};{g};{b}m  \x1b[0m"
            else:
                swatch = "  "
            print(f"    {swatch} {f:<28} {hex_val}")
    print()


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_apply(args: argparse.Namespace) -> int:
    log = logging.getLogger(__name__)

    # Load config
    from pawlette.core import config as cfg

    user_config = cfg.load_config()

    # Priority: CLI args > config file > hardcoded defaults
    mode = (
        args.mode if args.mode else (cfg.get_default_mode(user_config) or DEFAULT_MODE)
    )
    backend = (
        args.backend
        if args.backend
        else (cfg.get_default_backend(user_config) or DEFAULT_BACKEND)
    )

    # Build backend config: start with config file, override with CLI args
    backend_config = cfg.get_backend_config(user_config, backend).copy()

    # Override with CLI args if provided
    if backend == "matugen":
        if args.matugen_prefer:
            backend_config["prefer"] = args.matugen_prefer
        if args.matugen_fallback_color:
            backend_config["fallback_color"] = args.matugen_fallback_color

    if args.source == "image":
        log.info(
            "Extracting palette [backend=%s, mode=%s]: %s", backend, mode, args.value
        )
        palette = extract_from_image(
            args.value, mode=mode, backend=backend, backend_config=backend_config
        )
    elif args.source == "hex":
        log.info("Extracting palette from hex [mode=%s]: %s", mode, args.value)
        palette = extract_from_hex(
            args.value, mode=mode, backend=backend, backend_config=backend_config
        )
    elif args.source == "theme":
        palette = _load_theme_palette(args.value)
        if palette is None:
            log.error("Theme %r not found in %s", args.value, xdg.themes_dir())
            return 1
    else:
        log.error("Unknown source: %s", args.source)
        return 1

    if args.print_palette or args.dry_run:
        _print_palette(palette, mode=mode, backend=backend)

    _save_palette(palette)
    log.debug("Palette saved to %s", xdg.active_palette_file())

    if not args.skip_templates:
        written = apply_templates(
            palette,
            config_root=xdg.templates_root(),
            dry_run=args.dry_run,
        )
        log.info("Rendered %d template(s)", len(written))
        if args.dry_run and written:
            log.info("(dry-run) Would write:")
            for p in written:
                log.info("  %s", p)

    if not args.skip_plugins and not args.dry_run:
        results = run_plugins(palette, plugins_dir=xdg.plugins_dir())
        failed = [name for name, ok in results.items() if not ok]
        if failed:
            log.warning("Failed plugins: %s", ", ".join(failed))

    return 0


def cmd_render(args: argparse.Namespace) -> int:
    log = logging.getLogger(__name__)
    palette = _load_palette()
    if palette is None:
        log.error(
            "No cached palette at %s. Run 'pawlette apply' first.",
            xdg.active_palette_file(),
        )
        return 1

    if getattr(args, "print_palette", False):
        _print_palette(palette)

    written = apply_templates(
        palette,
        config_root=xdg.templates_root(),
        dry_run=args.dry_run,
    )
    log.info("Rendered %d template(s)", len(written))

    if not args.skip_plugins and not args.dry_run:
        run_plugins(palette, plugins_dir=xdg.plugins_dir())

    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    themes_path = xdg.themes_dir()
    if not themes_path.exists():
        print(f"No themes directory found at {themes_path}")
        return 1

    themes = sorted(
        [
            d.name
            for d in themes_path.iterdir()
            if d.is_dir() and (d / "colors.toml").exists()
        ]
    )

    if not themes:
        print(f"No themes found in {themes_path}")
        return 0

    for theme in themes:
        print(theme)

    return 0


# ---------------------------------------------------------------------------
# Theme loader
# ---------------------------------------------------------------------------


def _load_theme_palette(theme_name: str) -> Palette | None:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            logging.error("tomllib/tomli not available.")
            return None

    theme_file = xdg.themes_dir() / theme_name / "colors.toml"
    if not theme_file.exists():
        return None

    data = tomllib.loads(theme_file.read_text(encoding="utf-8"))
    colors = data.get("colors", {})
    try:
        return Palette(
            **{k: v for k, v in colors.items() if k in Palette.__dataclass_fields__}
        )
    except TypeError as exc:
        logging.error("Theme %r is missing fields: %s", theme_name, exc)
        return None


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose", action="store_true", default=False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pawlette", description="Theme management utility for Linux desktops."
    )
    _add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    apply_p = sub.add_parser("apply", help="Apply a palette from a source")
    apply_p.add_argument("source", choices=["image", "hex", "theme"])
    apply_p.add_argument("value", help="Path / hex colour / theme name")
    apply_p.add_argument(
        "--mode",
        choices=["dark", "light"],
        default=None,
        help="Color scheme mode (default: from config or 'dark')",
    )
    apply_p.add_argument(
        "--backend",
        choices=["native", "matugen"],
        default=None,
        help="Extraction backend (default: from config or 'native'). native = fast PIL k-means, matugen = Material You",
    )

    # Backend-specific options
    apply_p.add_argument(
        "--matugen-prefer",
        choices=[
            "darkness",
            "lightness",
            "saturation",
            "less-saturation",
            "value",
            "closest-to-fallback",
        ],
        default=None,
        help="Matugen color preference (default: from config or 'darkness'). "
        "darkness=darkest, lightness=lightest, saturation=most saturated (recommended), "
        "less-saturation=least saturated, value=highest brightness, closest-to-fallback=closest to fallback",
    )
    apply_p.add_argument(
        "--matugen-fallback-color",
        default=None,
        help="Fallback color for matugen when using --matugen-prefer closest-to-fallback (default: from config or '#cba6f7')",
    )

    apply_p.add_argument("--dry-run", action="store_true")
    apply_p.add_argument("--skip-templates", action="store_true")
    apply_p.add_argument("--skip-plugins", action="store_true")
    apply_p.add_argument("--print-palette", action="store_true")
    _add_common(apply_p)

    render_p = sub.add_parser("render", help="Re-render templates from cached palette")
    render_p.add_argument("--dry-run", action="store_true")
    render_p.add_argument("--skip-plugins", action="store_true")
    render_p.add_argument("--print-palette", action="store_true")
    _add_common(render_p)

    list_p = sub.add_parser("list", help="List available themes")
    _add_common(list_p)

    migrate_p = sub.add_parser(
        "migrate-from-v1",
        help="Migrating pawlette from v1 to the current version",
    )
    _add_common(migrate_p)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _setup_logging(args.verbose)
    handlers = {
        "apply": cmd_apply,
        "render": cmd_render,
        "list": cmd_list,
        "migrate-from-v1": migrate_from_v1,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
