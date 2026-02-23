import io
import os
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from loguru import logger

from pawlette.schemas.config_struct import Config, LoggingConfig

# Disable logging to keep output clean
logger.remove()

# Standard git identity for tests
_GIT_ID = {
    "GIT_AUTHOR_NAME": "Pawlette Test",
    "GIT_AUTHOR_EMAIL": "test@pawlette.test",
    "GIT_COMMITTER_NAME": "Pawlette Test",
    "GIT_COMMITTER_EMAIL": "test@pawlette.test",
}


@pytest.fixture
def mock_xdg(tmp_path, monkeypatch):
    """Set up a fully isolated XDG environment and git configuration."""
    config_home = tmp_path / ".config"
    data_home = tmp_path / ".local" / "share"
    state_home = tmp_path / ".local" / "state"
    pawlette_state = state_home / "pawlette"
    pawlette_themes = data_home / "pawlette" / "themes"

    # Ensure all directories exist
    for d in [config_home, data_home, state_home, pawlette_state, pawlette_themes]:
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    monkeypatch.setenv("HOME", str(tmp_path))

    import pawlette.constants as cnst
    monkeypatch.setattr(cnst, "XDG_CONFIG_HOME", config_home)
    monkeypatch.setattr(cnst, "XDG_DATA_HOME", data_home)
    monkeypatch.setattr(cnst, "APP_STATE_DIR", pawlette_state)
    monkeypatch.setattr(cnst, "THEMES_FOLDER", pawlette_themes)
    monkeypatch.setattr(cnst, "VERSIONS_FILE", pawlette_state / "installed_themes.json")

    # Configure git globally for this test session to avoid any host dependency
    git_env = {**os.environ, "HOME": str(tmp_path)}
    subprocess.run(["git", "config", "--global", "user.email", "test@pawlette.test"], env=git_env, check=False)
    subprocess.run(["git", "config", "--global", "user.name", "Pawlette Test"], env=git_env, check=False)
    subprocess.run(["git", "config", "--global", "init.defaultBranch", "main"], env=git_env, check=False)

    return tmp_path


@pytest.fixture
def mock_config():
    return Config(
        comment_styles={
            ".conf": "#",
            ".ini": ";",
            ".json": "//",
            ".jsonpaw": "//",
            ".toml": "#",
            ".yaml": "#",
            ".yml": "#",
            ".css": "/* */",
            ".scss": "//",
        },
        logging=LoggingConfig(),
    )


def _bootstrap_git_repo(mgr, home_dir: Path) -> None:
    """Ensure the manager's git repository is fully initialized with a 'main' branch."""
    mgr._init_git_repo()
    git_dir = str(mgr.git_repo)
    work_tree = str(mgr.config_dir)
    # We MUST provide identity here because mgr._run_git might not see the global config in some envs
    git_env = {**os.environ, "HOME": str(home_dir), **_GIT_ID}

    # Verify if HEAD exists. If not, the repo is 'empty' and 'main' is not a real ref yet.
    res = subprocess.run(["git", "--git-dir", git_dir, "rev-parse", "HEAD"], capture_output=True, env=git_env)
    if res.returncode != 0:
        # Create an initial empty commit to make 'main' branch exist for real.
        # This is required for 'git checkout -b <theme> main' to work later.
        subprocess.run(
            ["git", "--git-dir", git_dir, "--work-tree", work_tree, "commit", "--allow-empty", "-m", "Initial commit"],
            env=git_env,
            check=True,
        )


@pytest.fixture
def installer(mock_xdg, mock_requests):
    from pawlette.core.installer import Installer
    return Installer()


@pytest.fixture
def manager(mock_xdg, mock_config):
    from pawlette.core.selective_manager import SelectiveThemeManager
    mgr = SelectiveThemeManager(config=mock_config)
    _bootstrap_git_repo(mgr, home_dir=mock_xdg)
    return mgr


def create_tarball_bytes(theme_name: str, version: str, files: dict[str, str]) -> bytes:
    """Generate a .tar.gz archive with a root directory prefix.
    
    The root directory (e.g., 'theme-v1.2.3/') is expected by the Installer, 
    which calculates the common path prefix and strips it during extraction.
    """
    bio = io.BytesIO()
    root_prefix = f"{theme_name}-v{version}"
    with tarfile.open(fileobj=bio, mode="w:gz") as tar:
        # Explicitly add the root directory to ensure os.path.commonpath returns ONLY the root prefix
        # and doesn't accidentally include "configs" when calculating common path.
        root_info = tarfile.TarInfo(name=root_prefix)
        root_info.type = tarfile.DIRTYPE
        root_info.mode = 0o755
        tar.addfile(root_info)

        for path, content in files.items():
            # e.g., 'theme-v1.7.4/configs/kitty/kitty.conf'
            full_path = f"{root_prefix}/{path}"
            info = tarfile.TarInfo(name=full_path)
            data = content.encode("utf-8")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return bio.getvalue()


@pytest.fixture
def mock_requests(monkeypatch):
    """Mocks network requests to return synthetic theme archives."""

    def side_effect_get(url, stream=False, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None

        # Extract theme details from URL
        version = "2.0.0" if "v2.0.0" in url else "1.7.4"
        if "catppuccin-mocha" in url:
            theme_name = "pawlette-catppuccin-mocha-theme"
        elif "catppuccin-latte" in url:
            theme_name = "pawlette-catppuccin-latte-theme"
        else:
            theme_name = "unknown"

        # Define internal structure
        files = {
            "configs/kitty/kitty.conf": f"# Kitty config for {theme_name}\ninclude theme.conf",
            "configs/kitty/theme.conf": f"# Theme colors for {theme_name}\n",
            "configs/hypr/hyprland.conf": f"# Hyprland config for {theme_name}\n",
        }

        if "mocha" in theme_name:
            files["configs/dunst/dunstrc"] = "[global]\n    font = Monospace 10\n"
            files["configs/dunst/dunstrc.postpaw"] = (
                "[global]\n"
                "    # PAW-THEME-POST-START: dunst-theme\n"
                '    frame_color = "#1e1e2e"\n'
                "    # PAW-THEME-POST-END: dunst-theme\n"
            )

        tar_bytes = create_tarball_bytes(theme_name, version, files)

        if stream:
            resp.iter_content.return_value = [tar_bytes]
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
        else:
            resp.content = tar_bytes
            resp.text = ""

        return resp

    def side_effect_head(url, **kwargs):
        resp = MagicMock()
        resp.headers = {"content-length": "1024"}
        return resp

    monkeypatch.setattr("requests.get", side_effect_get)
    monkeypatch.setattr("requests.head", side_effect_head)
