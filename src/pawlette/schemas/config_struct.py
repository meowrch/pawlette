from pydantic import BaseModel
from pydantic import Field


class LoggingConfig(BaseModel):
    """Конфигурация логирования"""
    enable_console: bool = Field(default=False, description="Включить вывод логов в консоль")
    console_level: str = Field(default="INFO", description="Уровень логирования для консоли (DEBUG, INFO, WARNING, ERROR)")
    file_level: str = Field(default="DEBUG", description="Уровень логирования для файла")
    journal_level: str = Field(default="INFO", description="Уровень логирования для systemd journal")
    enable_colors: bool = Field(default=True, description="Включить цветной вывод в консоли")


class Config(BaseModel):
    max_backups: int = Field(default=5)
    comment_styles: dict[str, str]
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
