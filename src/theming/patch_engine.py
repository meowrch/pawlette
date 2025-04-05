import re
import shutil
import tempfile
from pathlib import Path

from loguru import logger

from config import cfg

from .backup import BackupSystem


class FormatManager:
    @staticmethod
    def get_comment_style(file_path: Path) -> str:
        ext = file_path.suffix.lower()
        return cfg.comment_styles.get(ext, "#")


class PatchEngine:
    @staticmethod
    def apply_to_file(
        theme_name: str,
        target_file: Path,
        pre_content: str | None = None,
        post_content: str | None = None,
    ) -> bool:
        tmp_path = None
        BackupSystem.create_backup(target_file)

        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
                style = FormatManager.get_comment_style(target_file)
                new_content = ""

                original = target_file.read_text() if target_file.exists() else ""

                # Динамическое создание регулярного выражения для удаления текущей темы
                theme_pattern = re.compile(
                    rf"^\s*{re.escape(style)}\s+PAW-THEME-(PRE|POST)-START:\s*{re.escape(theme_name)}.*?^\s*{re.escape(style)}\s+PAW-THEME-\1-END:\s*{re.escape(theme_name)}\s*$",
                    flags=re.DOTALL | re.IGNORECASE | re.MULTILINE,
                )
                cleaned = theme_pattern.sub("", original)

                if pre_content:
                    new_content += (
                        f"{style} PAW-THEME-PRE-START: {theme_name}\n"
                        f"{pre_content}"
                        f"{style} PAW-THEME-PRE-END: {theme_name}\n\n"
                    )

                new_content += cleaned.strip() + "\n"

                if post_content:
                    new_content += (
                        f"\n{style} PAW-THEME-POST-START: {theme_name}\n"
                        f"{post_content}"
                        f"{style} PAW-THEME-POST-END: {theme_name}\n"
                    )

                tmp.write(new_content.strip())
                tmp_path = Path(tmp.name)

            shutil.move(str(tmp_path), str(target_file))
            return True
        except Exception as e:
            logger.error(f"Failed to patch {target_file}: {str(e)}")
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            return False
