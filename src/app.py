#!/usr/bin/env python3
import argparse

from loguru import logger

import constants as cnst
from theming.manager import ThemeManager


def configure_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Theme manager for Meowrch OS", prog="pawlette"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, title="subcommands", description="valid commands"
    )

    # get themes
    subparsers.add_parser("get-themes", help="List all available themes")

    # Apply theme
    theme_parser = subparsers.add_parser("set-theme", help="Apply specified theme")
    theme_parser.add_argument("theme_name", type=str, help="Name of theme to apply")
    return parser


def main() -> None:
    manager = ThemeManager()

    ##==> Создание каталогов, если их нет.
    ##########################################
    dirs_to_create = [
        cnst.APP_DATA_DIR,
        cnst.APP_CACHE_DIR,
        cnst.APP_CONFIG_DIR,
        cnst.THEMES_FOLDER,
    ]

    for p in dirs_to_create:
        p.mkdir(parents=True, exist_ok=True)

    ##==> Обработка аргументов
    ##########################################
    parser = configure_argparser()
    args = parser.parse_args()

    match args.command:
        case "get-themes":
            themes = manager.get_all_themes()
            print("\n".join([i.name for i in themes]))
        case "set-theme":
            if args.theme_name:
                manager.apply_theme(args.theme_name)
        case _:
            logger.warning(f'Command "{args.command}" not found!')


if __name__ == "__main__":
    main()
