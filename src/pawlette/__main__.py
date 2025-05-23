#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.setup_loguru import setup_loguru
from pawlette.config import generate_default_config
from pawlette.core.backup import BackupSystem
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

    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers = backup_parser.add_subparsers(
        dest="backup_command", required=True
    )

    # List backups
    list_parser = backup_subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument(
        "file_path",
        type=str,
        help="Original file path to list backups for (from home dir)",
    )

    # Restore backup
    restore_parser = backup_subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument(
        "file_path", type=str, help="Original file path to restore (from home dir)"
    )
    restore_parser.add_argument(
        "--hash",
        type=str,
        help="Specific backup hash to restore (latest if not specified)",
    )

    # Cleanup backups
    backup_subparsers.add_parser("cleanup", help="Clean up old backups")

    # System backup commands
    sys_backup_parser = subparsers.add_parser(
        "system-backup", help="System backup operations"
    )
    sys_backup_subparsers = sys_backup_parser.add_subparsers(
        dest="sys_backup_command", required=True
    )

    # Create system backup
    create_parser = sys_backup_subparsers.add_parser(
        "create", help="Create full system backup"
    )
    create_parser.add_argument(
        "--comment", type=str, help="Backup description", default=""
    )

    # Restore system backup
    restore_parser = sys_backup_subparsers.add_parser(
        "restore", help="Restore system from backup"
    )
    restore_parser.add_argument("backup_id", type=str, help="Backup ID to restore")

    # List system backups
    sys_backup_subparsers.add_parser("list", help="List all system backups")

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


def backup_command(args) -> None:
    """Handle backup subcommands"""
    match args.backup_command:
        case "list":
            original_path = validate_file_path(args.file_path)
            backups = BackupSystem.get_backups(original_path)
            print_backups(backups, original_path)

        case "restore":
            original_path = validate_file_path(args.file_path)
            if BackupSystem.restore_backup(original_path, args.hash):
                print(f"Successfully restored {original_path}")
            else:
                print(f"Failed to restore {original_path}")

        case "cleanup":
            BackupSystem.cleanup_old_backups()
            print("Finished cleaning up old backups")

        case _:
            logger.warning(f"Unknown backup command: {args.backup_command}")


def system_backup_command(args) -> None:
    """Обрабатывает команды системных бэкапов."""
    match args.sys_backup_command:
        case "create":
            backup_id = BackupSystem.create_system_backup(args.comment)
            print(f"Created system backup with ID: {backup_id}")

        case "restore":
            if BackupSystem.restore_system_backup(args.backup_id):
                print(f"Successfully restored system from backup {args.backup_id}")
            else:
                print(f"Failed to restore from backup {args.backup_id}")

        case "list":
            backups = BackupSystem.list_system_backups()
            if not backups:
                print("No system backups available")
                return

            print("Available system backups:")
            for backup in backups:
                print(f"ID: {backup['id']}")
                print(f"Timestamp: {backup['timestamp']}")
                print(f"Location: {backup['path']}")
                print("-" * 50)

        case _:
            logger.warning(f"Unknown system backup command: {args.sys_backup_command}")


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
        case "backup":
            backup_command(args, manager)
        case "system-backup":
            system_backup_command(args)
        case _:
            logger.warning(f'Command "{args.command}" not found!')


if __name__ == "__main__":
    main()
