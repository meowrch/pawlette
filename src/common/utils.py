import shutil
from pathlib import Path

from loguru import logger


def create_symlink_dir(target: Path, link: Path) -> bool:
    """
    Creates a symlink to a folder. Removes existing file/directory/symlink if present.

    Args:
        target: The path to the target folder
        link: The path where the symlink will be created

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if link.exists():
            if link.is_dir() and not link.is_symlink():
                shutil.rmtree(link)
            else:
                link.unlink()

        link.symlink_to(target, target_is_dir=True)
        return True
    except OSError as e:
        logger.error(f"Failed to create symlink from {link} to {target}: {e}")
        return False
