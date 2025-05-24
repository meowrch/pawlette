#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.setup_loguru import setup_loguru
from pawlette.config import generate_default_config
from pawlette.core.manager import ThemeManager

##==> Настраиваем loguru
################################
setup_loguru()


def configure_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Theme manager for Meowrch OS", prog="pawlette"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, title="subcommands", description="valid commands"
    )

    # generate config
    subparsers.add_parser("generate-config", help="Generate default configuration")

    # get themes
    subparsers.add_parser("get-themes", help="List all installed themes")

    # get available themes
    subparsers.add_parser(
        "get-available-themes",
        help="JSON with all available themes with url for download",
    )

    # get themes info
    subparsers.add_parser(
        "get-themes-info", help="JSON with all installed themes + params"
    )

    # Install theme
    install_theme_parser = subparsers.add_parser(
        "install-theme", help="Install theme from official repository pawlette-themes"
    )
    install_theme_parser.add_argument(
        "theme_name", type=str, help="Name of theme to install"
    )

    # Update theme
    update_theme_parser = subparsers.add_parser(
        "update-theme", help="Update theme from official repository pawlette-themes"
    )
    update_theme_parser.add_argument(
        "theme_name", type=str, help="Name of theme to update"
    )

    # Update all themes
    subparsers.add_parser(
        "update-all-themes",
        help="Update all themes from official repository pawlette-themes",
    )

    # Apply theme
    apply_theme_parser = subparsers.add_parser(
        "set-theme", help="Apply specified theme"
    )
    apply_theme_parser.add_argument(
        "theme_name", type=str, help="Name of theme to apply"
    )

    # Restore
    subparsers.add_parser("restore", help="Restore the original look")

    return parser


def validate_file_path(input_path: str) -> Path:
    """Helper to resolve and validate file path"""
    path = Path(input_path).expanduser().absolute()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"File not found: {path}")
    return path


def print_backups(backups: List[dict], original_path: Path) -> None:
    """Pretty print backup list"""
    if not backups:
        print(f"No backups available for {original_path}")
        return

    print(f"Available backups for {original_path}:")
    print("-" * 80)
    for backup in backups:
        print(f"Hash: {backup['hash']}")
        print(f"Timestamp: {backup['timestamp']}")
        print(f"Location: {backup['path']}")
        print("-" * 80)


def main() -> None:
    manager = ThemeManager()

    ##==> Создание каталогов, если их нет.
    ##########################################
    dirs_to_create = [
        cnst.APP_DATA_DIR,
        cnst.APP_CACHE_DIR,
        cnst.APP_CONFIG_DIR,
        cnst.THEMES_FOLDER,
        cnst.APP_BACKUP_DIR,
    ]

    for p in dirs_to_create:
        p.mkdir(parents=True, exist_ok=True)

    ##==> Обработка аргументов
    ##########################################
    parser = configure_argparser()
    args = parser.parse_args()

    match args.command:
        case "generate-config":
            generate_default_config()
        case "get-themes":
            themes = manager.get_all_themes()
            print("\n".join([i.name for i in themes]))
        case "get-available-themes":
            print(manager.installer.fetch_available_themes())
        case "get-themes-info":
            info = manager.get_all_themes_info()
            print(info)
        case "install-theme":
            if args.theme_name:
                manager.installer.install_theme(args.theme_name)
        case "update-theme":
            if args.theme_name:
                manager.installer.update_theme(args.theme_name)
        case "update-all-themes":
            manager.installer.update_all_themes()
        case "set-theme":
            if args.theme_name:
                manager.apply_theme(args.theme_name)
        case "restore":
            manager.restore_original()
        case _:
            logger.warning(f'Command "{args.command}" not found!')


if __name__ == "__main__":
    main()
