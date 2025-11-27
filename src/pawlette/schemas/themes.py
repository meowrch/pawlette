from pathlib import Path
from enum import Enum

from pydantic import BaseModel
from pydantic import Field

from pawlette.constants import DEFAULT_THEME_LOGO


class Theme(BaseModel):
    name: str
    path: Path
    theme_logo: Path = Field(default=None, exclude=True)
    wallpapers_folder: Path = Field(default=None, exclude=True)
    gtk_folder: Path = Field(default=None, exclude=True)
    icons_folder: Path = Field(default=None, exclude=True)


    def __init__(self, **data):
        super().__init__(**data)
        self.gtk_folder = self.path / "gtk-theme"
        self.wallpapers_folder = self.path / "wallpapers"
        self.icons_folder = self.path / "icons"
        self.theme_logo = self.path / "logo.png"

        if not self.theme_logo.exists():
            self.theme_logo = DEFAULT_THEME_LOGO


class ThemeSource(Enum):
    OFFICIAL = "official"
    COMMUNITY = "community"


class RemoteTheme(BaseModel):
    name: str
    url: str
    source: ThemeSource


class InstalledThemeInfo(BaseModel):
    name: str
    version: str
    source_url: str
    installed_path: Path
    source: ThemeSource | None = None
