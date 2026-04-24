# 🐾 Pawlette
Universal theme manager.
Easily switch between themes for your desktop while preserving individual settings.
Under the hood — flexible patch system and atomic operations.

## 🌟 Features
- **Full XDG support**
- **Modular architecture** for config handlers
- **Custom theme support** through unified format
- **Partial configuration changes** (patch)
- **Git-based version control** for user modifications
- **Smart ignoring** of temporary files and caches
- **Automatic saving** of user settings when switching themes

## ⚡ Quick Start
To install on Arch Linux, run:
```bash
yay -S pawlette
```

## 🛠 Theme Architecture
Themes are stored in `/usr/share/pawlette/themes/` or `~/.local/share/pawlette/themes/` with the following structure:
```text
theme-name/
├── configs/           # Application configurations
│   ├── kitty/
│   │   └── kitty.conf.prepaw  # patch file
│   ├── waybar/
│   │   ├── style.css
│   │   └── config.json
│   └── ...
├── gtk-theme/     # GTK theme folder
├── icon-theme/    # Icon theme folder
└── wallpapers/    # Wallpapers folder
```
The `configs` folder must have the same architecture as `~/.config`.
You can create folders for each application and add configurations.
You don't need to add absolutely all configurations.
You can limit yourself to only those that should change from theme to theme.

Theme application happens as a merge of two directories.
If a certain file/folder didn't exist, it will be created.
If it existed, it will change the content to what was written in your theme.

### Configuration Patching
If a file already exists in `.config/.../`,
and you need to partially modify it (insert something at the beginning or end),
we've implemented a patching system for you.

It consists of creating a file with exactly the same name and extension
as in `.config/.../`, but adding the suffix ".prepaw" or ".postpaw" at the end.

> [!NOTE]
> For example, if you had `kitty/kitty.conf`, it becomes `kitty/kitty.conf.prepaw` \
> Such a file will be treated as a patch.

If the suffix is `.prepaw`, the content of this file will be inserted before the main part of the original configuration.
Accordingly, if the suffix is `.postpaw`, the content will be inserted after the main part of the original configuration.

In addition to insertions, JSON merge-patch is available: create a file with the `.jsonpaw` suffix next to the target JSON (for example, `waybar/config.json.jsonpaw`). Its content must be a JSON object; it will be recursively merged into the target file:

- existing keys are overridden with values from `.jsonpaw`;
- missing keys are added;
- nested objects are merged deeply.

Example:

Original `~/.config/waybar/config.json`:
```json
{
  "layer": "bottom",
  "modules-left": ["menu"],
  "style": { "font": "Sans 10" }
}
```

Patch `configs/waybar/config.json.jsonpaw`:
```json
{
  "layer": "top",
  "style": { "font": "JetBrainsMono 11", "color": "#cba6f7" },
  "custom-key": true
}
```

Result:
```json
{
  "layer": "top",
  "modules-left": ["menu"],
  "style": { "font": "JetBrainsMono 11", "color": "#cba6f7" },
  "custom-key": true
}
```

JSON merge is applied before `.prepaw`/`.postpaw`.

## 🧠 Selective Theme Manager
Pawlette uses an innovative selective theme management system based on Git. This means:

- **Each theme = separate branch** in internal git repository
- **User changes** are automatically saved as uncommitted changes
- **Switching between themes** preserves your individual settings
- **Change history** is available for each theme
- **Smart ignoring** of temporary files and caches

### Workflow:
1. **Apply theme** → theme branch is created, base configurations are applied
2. **Your changes** → tracked as uncommitted changes in git
3. **Switch theme** → automatically saves your changes and switches to another branch
4. **Return to theme** → restores your personalized version

### Benefits:
- 🔄 **Safety**: impossible to lose user settings
- 📚 **History**: complete change history for each theme
- 🎯 **Selectivity**: only relevant files are changed
- 🧹 **Cleanliness**: automatic ignoring of "junk" files

## 🎛 Theme Management
| Command                    | Description                                   |
| -------------------------- | --------------------------------------------- |
| `pawlette generate-config` | Generate default configuration                |
| `pawlette get-themes`      | List installed themes                         |
| `pawlette get-themes-info` | JSON with information about installed themes  |
| `pawlette set-theme <name>`| Apply specified theme                         |
| `pawlette apply <name>`    | Apply specified theme (alias)                 |
| `pawlette current-theme`   | Show current active theme                     |
| `pawlette restore`         | Restore original appearance                   |
| `pawlette reset-theme <name>` | Reset theme to clean state                |

## 📦 Installing, Updating and Removing Themes
| Command                              | Description                                 |
| ------------------------------------ | ------------------------------------------- |
| `pawlette get-store-themes`          | JSON with all themes from remote store      |
| `pawlette install-theme <name/url/path>` | Install theme by name from repository, by archive URL or from local archive file |
| `pawlette update-theme <name>`       | Update theme from official repository       |
| `pawlette update-all-themes`         | Update all themes                           |
| `pawlette uninstall-theme <name>`    | Remove theme (local files and cache)        |

## 📜 Version Control and History
| Command                                      | Description                                 |
| -------------------------------------------- | ------------------------------------------- |
| `pawlette status`                            | Show status and uncommitted changes         |
| `pawlette history [theme] [--limit N]`      | Show commit history for theme               |
| `pawlette user-changes [theme]`              | Show information about user changes         |
| `pawlette restore-commit <hash> [theme]`    | Restore changes from specific commit        |

### Usage Examples:
```bash
# Check current status
pawlette status
# ➤ Current theme: dark-blue
# ⚠️  You have 3 uncommitted changes
# Modified files:
#   - kitty/kitty.conf
#   - waybar/config.json
#   - alacritty/alacritty.yml

# View history of current theme
pawlette history
# 📜 History for theme: dark-blue
# 👤 a1b2c3d Personal font settings [USER]
# 🔧 e4f5g6h Update waybar configuration
# 🔧 h7i8j9k Initial theme application

# View which files are modified in theme
pawlette user-changes dark-blue
# 🔍 User changes for theme: dark-blue
# Found 2 modified files:
#   📝 kitty/kitty.conf
#   📝 waybar/style.css

# Restore specific commit
pawlette restore-commit a1b2c3d
# ✅ Successfully restored commit a1b2c3d for theme dark-blue
```

## 🔄 Backup Management
| Command                                                             | Description                    |
| ------------------------------------------------------------------- | ------------------------------ |
| `pawlette backup list ~/.config/<APP>/config.conf`                  | Show all versions of file      |
| `pawlette backup restore ~/.config/<APP>/config.conf`               | Restore latest version         |
| `pawlette backup restore ~/.config/<APP>/config.conf --hash abc123` | Restore specific version       |
| `pawlette system-backup list`                                       | Show system backups            |
| `pawlette system-backup create --comment "Before dark theme"`       | Create full backup             |
| `pawlette system-backup restore BACKUP_ID`                          | Rollback entire system         |

## ☕ Support the Project
If Pawlette makes your desktop more beautiful:
| Cryptocurrency | Address                                            |
| -------------- | -------------------------------------------------- |
| **TON**        | `UQB9qNTcAazAbFoeobeDPMML9MG73DUCAFTpVanQnLk3BHg3` |
| **Ethereum**   | `0x56e8bf8Ec07b6F2d6aEdA7Bd8814DB5A72164b13`       |
| **Bitcoin**    | `bc1qt5urnw7esunf0v7e9az0jhatxrdd0smem98gdn`       |
| **Tron**       | `TBTZ5RRMfGQQ8Vpf8i5N8DZhNxSum2rzAs`               |

Your support motivates us to make more cool features! ❤️

## 📊 Statistics
[![Star History Chart](https://api.star-history.com/svg?repos=meowrch/pawlette&type=Date)](https://star-history.com/#meowrch/pawlette&Date)
