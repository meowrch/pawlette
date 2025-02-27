import hashlib
import shutil
from pathlib import Path

import constants as cnst
from config import cfg


class BackupSystem:
    @staticmethod
    def create_backup(target: Path) -> None:
        """Создание дельта-бэкапа"""
        if not target.exists():
            return

        backup_dir = cnst.APP_BACKUP_DIR / target.relative_to(Path.home())
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Генерация имени бэкапа по хэшу
        content_hash = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
        backup_file = backup_dir / f"{content_hash}.bak"

        if not backup_file.exists():
            shutil.copy2(target, backup_file)
            BackupSystem.rotate_backups(backup_dir)

    @staticmethod
    def rotate_backups(backup_dir: Path) -> None:
        """Удаление старых бэкапов по FIFO"""
        backups = sorted(backup_dir.glob("*.bak"), key=lambda f: f.stat().st_mtime)
        while len(backups) > cfg.max_backups:
            backups[0].unlink()
            backups = backups[1:]

    @staticmethod
    def restore_file(target: Path) -> bool:
        """Восстановление файла из последнего бэкапа"""
        backup_dir = cnst.APP_BACKUP_DIR / target.relative_to(Path.home())
        if not backup_dir.exists():
            return False

        last_backup = max(
            backup_dir.glob("*.bak"), key=lambda f: f.stat().st_mtime, default=None
        )
        if last_backup:
            shutil.copy2(last_backup, target)
            return True
        return False
