import os
from pathlib import Path

from loguru import logger
from systemd import journal


def ensure_log_directory():
    """Создаем директорию для логов с правильными правами"""
    # Список возможных директорий для логов в порядке приоритета
    log_dirs = [
        "/var/log/pawlette",
        f"{Path.home()}/.local/share/pawlette/logs",
        "/tmp/pawlette",
    ]

    for log_dir in log_dirs:
        log_file = f"{log_dir}/app.log"
        try:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            # Проверяем, можем ли мы создать и записать в файл
            test_file = Path(log_file)
            if not test_file.exists():
                test_file.touch(exist_ok=True)

            # Проверяем права на запись
            if not os.access(log_file, os.W_OK):
                raise PermissionError(f"No write access to: {log_file}")

            return log_file
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot use {log_dir}: {e}")
            continue

    # Если все варианты не удались, используем /tmp
    fallback_file = "/tmp/pawlette_app.log"
    logger.warning(f"Failed to create log directory, using fallback: {fallback_file}")
    return fallback_file


def disable_logging():
    logger.remove()


def setup_loguru(config) -> None:
    disable_logging()

    # Настройка вывода в systemd journal
    logger.add(
        journal.JournaldLogHandler("pawlette"),
        level=config.logging.journal_level,
        format="{message}",
    )

    # Настройка вывода в файл
    log_file = ensure_log_directory()
    logger.add(
        log_file,
        rotation="10 MB",
        retention="14 days",
        compression="gz",
        level=config.logging.file_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        enqueue=True,
    )

    # Добавляем вывод в терминал, если это указано в конфиге
    if config.logging.enable_console:
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level=config.logging.console_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            colorize=config.logging.enable_colors,
        )

    return True
