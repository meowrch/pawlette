import os
from functools import lru_cache
from pathlib import Path

from loguru import logger
from systemd import journal


def ensure_log_directory():
    """Создаем директорию для логов с правильными правами"""
    log_dir = "/var/log/pawlette"
    log_file = f"{log_dir}/app.log"

    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        if not Path(log_file).exists():
            Path(log_file).touch(exist_ok=True)

        return log_file
    except PermissionError:
        logger.warning(f"No permission to create {log_dir}, falling back to /tmp")
        return "/tmp/pawlette_app.log"


def disable_logging():
    logger.remove()


@lru_cache(maxsize=None)
def setup_loguru() -> None:
    disable_logging()

    # Настройка вывода в systemd journal
    logger.add(journal.JournaldLogHandler("pawlette"), level="INFO", format="{message}")

    # Настройка вывода в файл
    log_file = ensure_log_directory()
    logger.add(
        log_file,
        rotation="10 MB",
        retention="14 days",
        compression="gz",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        enqueue=True,
    )
    return True
