#!/usr/bin/env python3
import argparse
import json

from loguru import logger

import pawlette.constants as cnst
from pawlette.common.setup_loguru import setup_loguru
from pawlette.config import generate_default_config
from pawlette.config import load_config
from pawlette.core.manager import ThemeManager


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

    # Apply theme (alias)
    apply_theme_parser_alias = subparsers.add_parser(
        "apply", help="Apply specified theme (alias for set-theme)"
    )
    apply_theme_parser_alias.add_argument(
        "theme_name", type=str, help="Name of theme to apply"
    )

    # Restore
    subparsers.add_parser("restore", help="Restore the original look")

    # Reset theme to clean state
    reset_theme_parser = subparsers.add_parser(
        "reset-theme", help="Reset theme to clean state (remove user changes)"
    )
    reset_theme_parser.add_argument(
        "theme_name", type=str, help="Name of theme to reset"
    )

    # Get current theme
    subparsers.add_parser("current-theme", help="Show current active theme")

    # Show git status
    subparsers.add_parser("status", help="Show git repository status")

    # Show history of current theme
    history_parser = subparsers.add_parser(
        "history", help="Show commit history for current or specified theme"
    )
    history_parser.add_argument(
        "theme_name",
        type=str,
        nargs="?",
        help="Name of theme to show history for (current theme if not specified)",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of commits to show (default: 10)",
    )

    # Show user changes info
    user_changes_parser = subparsers.add_parser(
        "user-changes", help="Show information about uncommitted user changes"
    )
    user_changes_parser.add_argument(
        "theme_name",
        type=str,
        nargs="?",
        help="Name of theme to check (current theme if not specified)",
    )

    # Restore specific commit
    restore_commit_parser = subparsers.add_parser(
        "restore-commit", help="Restore user changes from a specific commit"
    )
    restore_commit_parser.add_argument(
        "commit_hash", type=str, help="Hash of the commit to restore"
    )
    restore_commit_parser.add_argument(
        "theme_name",
        type=str,
        nargs="?",
        help="Name of theme (current theme if not specified)",
    )

    return parser


def main() -> None:
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

    ##==> Загрузка конфигурации и настройка логирования
    ##########################################
    config = load_config(cnst.APP_CONFIG_FILE)
    setup_loguru(config)

    ##==> Инициализация менеджера тем
    ##########################################
    manager = ThemeManager(config)

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
            print(json.dumps(manager.installer.fetch_available_themes()))
        case "get-themes-info":
            print(manager.get_all_themes_info())
        case "install-theme":
            if args.theme_name:
                manager.installer.install_theme(args.theme_name)
        case "update-theme":
            if args.theme_name:
                manager.installer.update_theme(args.theme_name)
        case "update-all-themes":
            manager.installer.update_all_themes()
        case "set-theme" | "apply":
            if args.theme_name:
                manager.apply_theme(args.theme_name)
        case "restore":
            manager.restore_original()
        case "reset-theme":
            if args.theme_name:
                manager.reset_theme_to_clean(args.theme_name)
                print(f"Theme '{args.theme_name}' has been reset to clean state")
        case "current-theme":
            current_theme = manager.get_current_theme_name()
            if current_theme:
                print(f"Current theme: {current_theme}")
            else:
                print("No theme is currently active (base state)")
        case "status":
            if manager.use_selective:
                current_theme = manager.get_current_theme_name()
                if current_theme:
                    print(f"Current theme: {current_theme}")
                    changes_info = manager.selective_manager.get_user_changes_info()
                    if changes_info["has_changes"]:
                        print(
                            f"⚠️  You have {len(changes_info['files'])} uncommitted changes"
                        )
                        print("Modified files:")
                        for file in changes_info["files"][:5]:  # Show first 5 files
                            print(f"  - {file}")
                        if len(changes_info["files"]) > 5:
                            print(f"  ... and {len(changes_info['files']) - 5} more")
                    else:
                        print("✅ No uncommitted changes")
                else:
                    print("No theme is currently active (base state)")
            else:
                print(f"Current branch: {manager.git.get_current_branch()}")
                print(f"Git status:\n{manager.git.get_status()}")
                if manager.git.has_uncommitted_changes():
                    print("⚠️  You have uncommitted changes")
                else:
                    print("✅ No uncommitted changes")
        case "history":
            if not manager.use_selective:
                print("History command is only available in selective mode")
                return

            theme_name = args.theme_name or manager.get_current_theme_name()
            if not theme_name:
                print("No theme specified and no current theme active")
                return

            print(f"📜 History for theme: {theme_name}")
            print("-" * 60)

            # Get all commits for this theme branch
            import subprocess

            try:
                result = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(manager.selective_manager.git_repo),
                        "log",
                        "--oneline",
                        f"--max-count={args.limit}",
                        theme_name,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        parts = line.split(" ", 1)
                        if len(parts) >= 2:
                            hash_short = parts[0]
                            message = parts[1]
                            # Mark user commits with a special icon
                            icon = "👤" if "[USER]" in message else "🔧"
                            print(f"{icon} {hash_short} {message}")
                else:
                    print("No commits found for this theme")
            except subprocess.CalledProcessError:
                print(f"Failed to get history for theme: {theme_name}")
        case "user-changes":
            if not manager.use_selective:
                print("User-changes command is only available in selective mode")
                return

            theme_name = args.theme_name or manager.get_current_theme_name()
            if not theme_name:
                print("No theme specified and no current theme active")
                return

            changes_info = manager.selective_manager.get_user_changes_info(theme_name)

            print(f"🔍 User changes for theme: {theme_name}")
            print("-" * 60)

            if changes_info["has_changes"]:
                print(f"Found {len(changes_info['files'])} modified files:")
                for file in changes_info["files"]:
                    print(f"  📝 {file}")
                print(
                    "\n💡 These changes will be automatically saved when you switch themes"
                )
            else:
                print("✅ No uncommitted changes found")
        case "restore-commit":
            if not manager.use_selective:
                print("Restore-commit command is only available in selective mode")
                return

            theme_name = args.theme_name or manager.get_current_theme_name()
            if not theme_name:
                print("No theme specified and no current theme active")
                return

            try:
                manager.selective_manager.restore_user_commit(
                    theme_name, args.commit_hash
                )
                print(
                    f"✅ Successfully restored commit {args.commit_hash} for theme {theme_name}"
                )
            except Exception as e:
                print(f"❌ Failed to restore commit: {e}")
        case _:
            logger.warning(f'Command "{args.command}" not found!')


if __name__ == "__main__":
    main()
