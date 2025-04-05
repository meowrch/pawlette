import hashlib
import json
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger

import constants as cnst
from config import cfg


class BackupSystem:
    __backup_metadata_file = cnst.APP_BACKUP_DIR / "backup_metadata.json"
    __system_backups_dir = cnst.APP_BACKUP_DIR / "system"

    @staticmethod
    def _load_metadata() -> Dict[str, List[Dict[str, str]]]:
        """Загружает метаданные бэкапов из JSON файла."""
        if not BackupSystem.__backup_metadata_file.exists():
            return {}
        try:
            with open(BackupSystem.__backup_metadata_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            return {}

    @staticmethod
    def _save_metadata(metadata: Dict[str, List[Dict[str, str]]]) -> None:
        """Сохраняет метаданные бэкапов в JSON файл."""
        try:
            BackupSystem.__backup_metadata_file.parent.mkdir(
                parents=True, exist_ok=True
            )
            with open(BackupSystem.__backup_metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")

    @staticmethod
    def _get_backup_info(target_file: Path) -> Tuple[Path, str]:
        """Get backup directory and relative path for the target file."""
        relative_path = target_file.relative_to(Path.home())
        backup_dir = cnst.APP_BACKUP_DIR / relative_path.parent
        backup_key = str(relative_path)
        return backup_dir, backup_key

    @staticmethod
    def create_backup(target: Path) -> Optional[Path]:
        """Создает бэкап файла с учетом изменений."""
        if not target.exists() or not target.is_file():
            return None

        try:
            relative_path = target.relative_to(Path.home())
            backup_dir = cnst.APP_BACKUP_DIR / relative_path.parent
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_hash = hashlib.sha256(target.read_bytes()).hexdigest()[:8]
            backup_file = backup_dir / f"{timestamp}_{content_hash}.bak"

            # Проверяем, есть ли идентичный бэкап
            for existing in backup_dir.glob("*.bak"):
                if BackupSystem._files_identical(target, existing):
                    return None

            shutil.copy2(target, backup_file)

            # Обновляем метаданные
            metadata = BackupSystem._load_metadata()
            backup_key = str(relative_path)

            backup_entry = {
                "path": str(backup_file),
                "timestamp": timestamp,
                "original": str(target),
                "hash": content_hash,
            }

            if backup_key not in metadata:
                metadata[backup_key] = []

            metadata[backup_key].append(backup_entry)

            # Очистка старых бэкапов
            while len(metadata[backup_key]) > cfg.max_backups:
                oldest = metadata[backup_key].pop(0)
                Path(oldest["path"]).unlink(missing_ok=True)

            BackupSystem._save_metadata(metadata)
            return backup_file

        except Exception as e:
            logger.error(f"Failed to create backup for {target}: {e}")
            return None

    @staticmethod
    def create_system_backup(comment: str = "") -> str:
        """
        Создает полный системный бэкап всех конфигов.
        Возвращает ID созданного бэкапа.
        """
        BackupSystem.__system_backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"system_{timestamp}"
        backup_path = BackupSystem.__system_backups_dir / f"{backup_id}.tar.gz"

        # Собираем список всех конфигов, которые могут быть изменены темами
        config_paths = []
        for theme_dir in cnst.THEMES_FOLDER.iterdir():
            for app_dir in (theme_dir / "configs").iterdir():
                if app_dir.is_dir():
                    target_dir = cnst.XDG_CONFIG_HOME / app_dir.name
                    if target_dir.exists():
                        config_paths.append(target_dir)

        # Создаем временный файл со списком изменений
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as list_file:
            list_file.write(f"Backup ID: {backup_id}\n")
            list_file.write(f"Timestamp: {timestamp}\n")
            list_file.write(f"Comment: {comment}\n\n")
            list_file.write("Included paths:\n")
            for path in config_paths:
                list_file.write(f"- {path}\n")
            list_file_path = Path(list_file.name)

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(list_file_path, arcname="backup_info.txt")
                for config_dir in config_paths:
                    tar.add(config_dir, arcname=config_dir.relative_to(Path.home()))

                # Добавляем текущие GTK конфиги
                for gtk_config in [
                    cnst.GTK2_CFG,
                    cnst.GTK3_CFG,
                    cnst.GTK4_CFG,
                    cnst.XSETTINGSD_CONFIG,
                ]:
                    if gtk_config.exists():
                        tar.add(gtk_config, arcname=gtk_config.relative_to(Path.home()))

            logger.info(f"Created system backup: {backup_path}")
            return backup_id
        except Exception as e:
            logger.error(f"Failed to create system backup: {e}")
            raise
        finally:
            list_file_path.unlink(missing_ok=True)

    @staticmethod
    def restore_system_backup(backup_id: str) -> bool:
        """Восстанавливает систему из полного бэкапа."""
        backup_path = BackupSystem.__system_backups_dir / f"{backup_id}.tar.gz"
        if not backup_path.exists():
            logger.error(f"Backup {backup_id} not found")
            return False

        try:
            # Сначала создаем бэкап текущего состояния
            current_state_id = BackupSystem.create_system_backup(
                f"Pre-restore backup before restoring {backup_id}"
            )
            logger.info(f"Created pre-restore backup: {current_state_id}")

            # Восстанавливаем файлы
            with tarfile.open(backup_path, "r:gz") as tar:
                # Проверяем целостность
                if not all(member.isreg() or member.isdir() for member in tar):
                    raise ValueError("Invalid backup archive")

                # Извлекаем с сохранением прав
                tar.extractall(path=Path.home(), filter="data")

            logger.info(f"Successfully restored system from backup {backup_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore system backup: {e}")
            return False

    @staticmethod
    def list_system_backups() -> List[Dict[str, str]]:
        """Возвращает список всех системных бэкапов."""
        backups = []
        for backup_file in BackupSystem.__system_backups_dir.glob("system_*.tar.gz"):
            backup_id = backup_file.stem
            timestamp = backup_id.split("_")[1]
            backups.append(
                {
                    "id": backup_id,
                    "path": str(backup_file),
                    "timestamp": datetime.strptime(
                        timestamp, "%Y%m%d%H%M%S"
                    ).isoformat(),
                }
            )
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

    @staticmethod
    def _files_identical(file1: Path, file2: Path) -> bool:
        """Проверяет идентичность файлов по содержимому."""
        try:
            return file1.read_bytes() == file2.read_bytes()
        except Exception:
            return False

    @staticmethod
    def get_backups(target: Path) -> List[Dict[str, str]]:
        """Get all available backups for a file in chronological order (newest first)."""
        _, backup_key = BackupSystem._get_backup_info(target)
        metadata = BackupSystem._load_metadata()
        backups = metadata.get(backup_key, [])
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

    @staticmethod
    def restore_backup(target: Path, backup_hash: Optional[str] = None) -> bool:
        """Restore a file from backup.

        Args:
            target: Original file path to restore
            backup_hash: Specific backup hash to restore (None for latest)

        Returns:
            bool: True if restore succeeded, False otherwise
        """
        try:
            backups = BackupSystem.get_backups(target)
            if not backups:
                logger.warning(f"No backups available for {target}")
                return False

            if backup_hash:
                backup_entry = next(
                    (b for b in backups if b["hash"] == backup_hash), None
                )
                if not backup_entry:
                    logger.warning(f"Specified backup not found for {target}")
                    return False
            else:
                backup_entry = backups[0]

            backup_path = Path(backup_entry["path"])
            if not backup_path.exists():
                logger.warning(f"Backup file missing: {backup_path}")
                return False

            # Restore the selected backup
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target)
            logger.info(f"Restored {target} from backup {backup_entry['timestamp']}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore {target}: {e}")
            return False

    @staticmethod
    def cleanup_old_backups() -> None:
        """Clean up backups that exceed the maximum allowed count."""
        metadata = BackupSystem._load_metadata()
        modified = False

        for file_key, backups in metadata.items():
            if len(backups) > cfg.max_backups:
                # Sort backups oldest first
                sorted_backups = sorted(backups, key=lambda x: x["timestamp"])
                backups_to_remove = len(backups) - cfg.max_backups

                for backup in sorted_backups[:backups_to_remove]:
                    backup_path = Path(backup["path"])
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.debug(f"Removed old backup: {backup_path}")

                # Update metadata
                metadata[file_key] = sorted_backups[backups_to_remove:]
                modified = True

        if modified:
            BackupSystem._save_metadata(metadata)
