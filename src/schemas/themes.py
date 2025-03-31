from pathlib import Path

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from errors.themes import ThemeNotFound


class Theme(BaseModel):
    name: str
    path: Path
    gtk_folder: Path = Field(default=None, exclude=True)

    class Config:
        # To support Path objects in JSON
        json_encoders = {Path: str}

    def __init__(self, **data):
        super().__init__(**data)
        self.gtk_folder = self.path / "global" / "gtk-theme"

    @field_validator("path")
    def validate_path(cls, v):
        if not isinstance(v, Path):
            v = Path(v)

        if not v.exists():
            raise ThemeNotFound(v.name)

        return v
