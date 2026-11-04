import os
import time
from typing import List
from core.utils import normalize_path, is_path_matching
from core.config_manager import ConfigManager

try:
    import pythoncom
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


class RecentCleaner:
    """
    Очищает ярлыки (.lnk), указывающие на защищённые папки и файлы внутри них,
    из %APPDATA%\Microsoft\Windows\Recent, чтобы они не всплывали в Быстром доступе,
    Рекомендациях и поиске Проводника Windows 11.
    Потокобезопасно использует get_rules_snapshot().
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.recent_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Recent"
        )
        self._last_dir_mtime: float = 0.0

    def clean_once(self, force: bool = False) -> int:
        if not self.config_manager.settings.clean_recent:
            return 0

        if not os.path.exists(self.recent_dir):
            return 0

        try:
            current_mtime = os.path.getmtime(self.recent_dir)
            if not force and current_mtime == self._last_dir_mtime:
                return 0
            self._last_dir_mtime = current_mtime
        except OSError:
            pass

        protected_targets = [
            rule.target_path
            for rule in self.config_manager.get_rules_snapshot()
            if rule.enabled and rule.target_path.strip()
        ]

        if not protected_targets:
            return 0

        deleted_count = 0
        wscript = None
        com_initialized = False

        if HAS_PYWIN32:
            try:
                pythoncom.CoInitialize()
                com_initialized = True
                wscript = win32com.client.Dispatch("WScript.Shell")
            except Exception:
                wscript = None

        try:
            for root, dirs, files in os.walk(self.recent_dir):
                for file in files:
                    if not file.lower().endswith(".lnk"):
                        continue

                    full_path = os.path.join(root, file)
                    target_path = ""

                    if wscript:
                        try:
                            shortcut = wscript.CreateShortcut(full_path)
                            target_path = shortcut.TargetPath
                            shortcut = None
                        except Exception:
                            target_path = ""
                            shortcut = None

                    matched = False
                    if target_path:
                        for p in protected_targets:
                            if is_path_matching(target_path, p):
                                matched = True
                                break

                    if not matched:
                        base_name_without_ext = os.path.splitext(file)[0].lower()
                        for p in protected_targets:
                            folder_name = os.path.basename(os.path.normpath(p)).lower()
                            if folder_name and folder_name == base_name_without_ext:
                                matched = True
                                break

                    if matched:
                        try:
                            os.remove(full_path)
                            deleted_count += 1
                        except Exception:
                            pass

        finally:
            wscript = None
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        return deleted_count
