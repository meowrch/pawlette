import shutil
import subprocess

from loguru import logger


class WMReloader:
    @staticmethod
    def _is_process_running(process_name: str) -> bool:
        """Проверяет, запущен ли процесс"""
        try:
            subprocess.run(
                ["pgrep", "-x", process_name],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def _is_command_available(command: str) -> bool:
        """Проверяет доступность команды"""
        return shutil.which(command) is not None

    @staticmethod
    def reload_hyprland() -> bool:
        if not WMReloader._is_process_running("Hyprland"):
            return False

        if not WMReloader._is_command_available("hyprctl"):
            logger.warning("hyprctl не найден")
            return False

        try:
            subprocess.run(
                ["hyprctl", "reload"],
                check=True,
                capture_output=True,
            )
            logger.info("✓ Hyprland перезагружен")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка перезагрузки Hyprland: {e}")
            return False

    @staticmethod
    def reload_bspwm() -> bool:
        """Перезагружает конфиг bspwm"""
        if not WMReloader._is_process_running("bspwm"):
            return False

        try:
            subprocess.run(
                ["bspc", "wm", "-r"],
                check=True,
                capture_output=True,
            )
            logger.info("✓ bspwm перезагружен")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка перезагрузки bspwm: {e}")
            return False

    @staticmethod
    def reload_current_wm() -> bool:
        """Автоматически определяет и перезагружает текущий WM"""
        if WMReloader._is_process_running("Hyprland"):
            return WMReloader.reload_hyprland()
        elif WMReloader._is_process_running("bspwm"):
            return WMReloader.reload_bspwm()
        else:
            logger.debug(
                "WM для перезагрузки не обнаружен (поддерживаются: Hyprland, bspwm)"
            )
            return False
