from pydantic import BaseModel
from pydantic import Field


class Config(BaseModel):
    max_backups: int = Field(default=5)
    comment_styles: dict[str, str]
