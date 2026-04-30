import shutil
from pathlib import Path


def confirm(prompt):
    res = input(f"{prompt} [Y/n]: ").strip().lower()
    return res in ("", "y", "yes")


def migrate_from_v1():
    home = Path.home()
    config_dir = home / ".config" / "pawlette"
    share_dir = home / ".local" / "share" / "pawlette"
    state_dir = home / ".local" / "state" / "pawlette"
    themes_dir = share_dir / "themes"

    # 1. Удаляем pawlette.json
    json_config = config_dir / "pawlette.json"
    if json_config.exists():
        json_config.unlink()

    # 2. Удаляем папку logs
    logs_dir = share_dir / "logs"
    if logs_dir.is_dir():
        shutil.rmtree(logs_dir)

    # 3. Удаляем симлинк theme_wallpapers
    wallpaper_link = share_dir / "theme_wallpapers"
    if wallpaper_link.is_symlink() or wallpaper_link.exists():
        wallpaper_link.unlink()

    # 4. Чистим темы
    if themes_dir.is_dir():
        for theme_path in themes_dir.iterdir():
            if theme_path.is_dir():
                if confirm(f"Can the '{theme_path.name}' theme be deleted?"):
                    has_meta = (theme_path / "meta.toml").exists()
                    has_colors = (theme_path / "colors.toml").exists()

                    if not has_meta and not has_colors:
                        shutil.rmtree(theme_path)
                        print(
                            f"The theme '{theme_path.name}' was empty and has been deleted."
                        )
                    else:
                        for item in theme_path.iterdir():
                            if item.name not in ["meta.toml", "colors.toml"]:
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()

    # 5. Чистим состояние
    if state_dir.is_dir():
        # Удаляем config_state.git
        git_state = state_dir / "config_state.git"
        if git_state.is_dir():
            if confirm("Do you want to delete the config_state.git folder?"):
                shutil.rmtree(git_state)

        # Удаляем installed_themes.json
        installed_json = state_dir / "installed_themes.json"
        if installed_json.exists():
            installed_json.unlink()

        # Удаляем файлы .version
        versions = list(state_dir.glob("*.version"))
        if versions:
            for version_file in versions:
                version_file.unlink()
