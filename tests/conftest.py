
import io
import json
import os
import tarfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from loguru import logger

from pawlette.schemas.config_struct import Config, LoggingConfig

# Disable loguru output during tests to keep it clean
logger.remove()

@pytest.fixture
def mock_xdg(tmp_path, monkeypatch):
    """Sets up XDG environment variables to point to a temp directory."""
    config_home = tmp_path / ".config"
    data_home = tmp_path / ".local/share"
    state_home = tmp_path / ".local/state"
    
    config_home.mkdir(parents=True)
    data_home.mkdir(parents=True)
    state_home.mkdir(parents=True)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    monkeypatch.setenv("HOME", str(tmp_path)) # For expanduser calls

    # We also need to patch constants because they might be evaluated at import time
    # However, since we import modules inside tests or after fixture setup, 
    # relying on env vars usually works if constants use os.environ or pathlib.Path.home()
    # Let's check if we need to reload modules. 
    # Pawlette constants usually use `Path.home()` or `os.environ`.
    # To be safe, let's patch the constants directly if possible.
    
    import pawlette.constants as cnst
    monkeypatch.setattr(cnst, "XDG_CONFIG_HOME", config_home)
    monkeypatch.setattr(cnst, "XDG_DATA_HOME", data_home)
    monkeypatch.setattr(cnst, "APP_STATE_DIR", state_home / "pawlette")
    monkeypatch.setattr(cnst, "THEMES_FOLDER", data_home / "pawlette" / "themes")
    monkeypatch.setattr(cnst, "VERSIONS_FILE", state_home / "pawlette" / "installed_themes.json")
    
    return tmp_path

@pytest.fixture
def mock_config():
    return Config(
        comment_styles={
            ".conf": "#",
            ".ini": ";",
            ".json": "//", # Special handling in many parsers or treated as JS comments
            ".jsonpaw": "//",
            ".toml": "#",
            ".yaml": "#",
            ".yml": "#",
            ".css": "/* */",
            ".scss": "//",
        },
        logging=LoggingConfig()
    )

def create_tarball_bytes(theme_name: str, version: str, files: dict[str, str]) -> bytes:
    """Creates an in-memory tar.gz file."""
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tar:
        root_dir = f"{theme_name}-v{version}"
        for path, content in files.items():
            info = tarfile.TarInfo(name=f"{root_dir}/{path}")
            data = content.encode("utf-8")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return bio.getvalue()

@pytest.fixture
def mock_requests(monkeypatch):
    """Mocks requests.get/head for theme downloads."""
    mock_get = MagicMock()
    mock_head = MagicMock()

    def side_effect_get(url, stream=False, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        
        # Extract name/version from URL
        # URL format: .../archive/refs/tags/v1.7.4.tar.gz -> v1.7.4
        version = "1.7.4" 
        if "v1.7.4" in url:
            version = "1.7.4"
        elif "v2.0.0" in url:
            version = "2.0.0"

        theme_name = "unknown"
        if "catppuccin-mocha" in url:
            theme_name = "catppuccin-mocha"
        elif "catppuccin-latte" in url:
            theme_name = "catppuccin-latte"

        # Create dummy theme content
        files = {
            "configs/kitty/kitty.conf": f"# Kitty config for {theme_name}\ninclude theme.conf",
            "configs/kitty/theme.conf": f"# Theme colors for {theme_name}",
            "configs/hypr/hyprland.conf": f"# Hyprland config for {theme_name}\n",
        }
        
        # Add patch file for testing patches
        if theme_name == "catppuccin-mocha":
             files["configs/dunst/dunstrc.postpaw"] = """
[global]
    # PAW-THEME-POST-START: dunst-theme
    frame_color = "#1e1e2e"
    # PAW-THEME-POST-END: dunst-theme
"""
             files["configs/dunst/dunstrc"] = "[global]\n    font = Monospace 10"

        tar_bytes = create_tarball_bytes(theme_name, version, files)
        
        if stream:
            resp.iter_content.return_value = [tar_bytes]
            # Also mock raw file context manager
            resp.__enter__.return_value = resp
            resp.__exit__.return_value = None
        else:
            resp.content = tar_bytes
            resp.text = "mock response text" # Should not be used for tarballs

        return resp

    def side_effect_head(url, **kwargs):
        resp = MagicMock()
        resp.headers = {"content-length": "1024"}
        return resp

    mock_get.side_effect = side_effect_get
    mock_head.side_effect = side_effect_head

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.head", mock_head)
    
    return mock_get

