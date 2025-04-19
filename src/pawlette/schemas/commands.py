from pydantic import BaseModel
from pydantic import Field


class CommandInfo(BaseModel):
    command: str
    check_command_exists: str = Field(default=None)
    check_process: str = Field(default=None)
