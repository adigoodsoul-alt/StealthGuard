import os
import time
import ctypes
from ctypes import wintypes
import threading
from datetime import datetime
from typing import Optional, Dict

from PySide6.QtCore import QThread, Signal

from core.utils import url_to_path, normalize_path, is_path_matching, show_native_error_dialog
from core.config_manager import ConfigManager, Rule
from core.recent_cleaner import RecentCleaner

try:
    import pythoncom
    import win32com.client
    import win32gui
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


class WinEventWakeThread(threading.Thread):
    """
    Выделенный поток с нативным циклом сообщений Win32 (GetMessageW),
    необходимым для доставки колбэков SetWinEventHook (WINEVENT_OUTOFCONTEXT).
    Мгновенно будит ExplorerInterceptor (< 1 мс) при смене пути, поискового запроса или активного окна.
    """

    def __init__(self, wake_event: threading.Event):
        super().__init__(daemon=True)
        self.wake_event = wake_event
        self.thread_id = 0
        self._cb_ref = None

    def run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()

        WINEVENTPROC = ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD
        )

        def _on_winevent(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            self.wake_event.set()

        self._cb_ref = WINEVENTPROC(_on_winevent)
        hook1 = None
        hook2 = None

        try:
            # 0x800C = EVENT_OBJECT_NAMECHANGE, 0x0003 = EVENT_SYSTEM_FOREGROUND
            hook1 = user32.SetWinEventHook(0x800C, 0x800C, 0, self._cb_ref, 0, 0, 0)
            hook2 = user32.SetWinEventHook(0x0003, 0x0003, 0, self._cb_ref, 0, 0, 0)

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            pass
        finally:
            if hook1:
                try:
                    user32.UnhookWinEvent(hook1)
                except Exception:
                    pass
            if hook2:
                try:
                    user32.UnhookWinEvent(hook2)
                except Exception:
                    pass

    def stop(self):
        if self.thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            except Exception:
                pass


class ExplorerInterceptor(QThread):
    """
    Фоновый поток мониторинга вкладок, окон и поисковых запросов Проводника Windows 11
    через COM-интерфейс Shell.Application.
    """

    intercepted = Signal(dict)
    status_changed = Signal(str)

    def __init__(self, config_manager: ConfigManager, recent_cleaner: Optional[RecentCleaner] = None):
        super().__init__()
        self.config_manager = config_manager
        self.recent_cleaner = recent_cleaner or RecentCleaner(config_manager)
        self._running = False
        self._wake_event = threading.Event()
        self._redirection_cache: Dict[int, tuple] = {}
        self._cleanup_counter = 0
        self._last_recloak_time = 0.0
        self._recloak_thread: Optional[threading.Thread] = None

    def _apply_startup_cloaking(self):
        try:
            from core.file_cloaker import enforce_explorer_stealth_policies
            from core.drive_cloaker import sync_drives_from_config
            from core.config_manager import sync_rules_cloaking
            enforce_explorer_stealth_policies()
            sync_drives_from_config(self.config_manager)
            sync_rules_cloaking(self.config_manager)
        except Exception:
            pass

    def run(self):
        self._running = True
        self.status_changed.emit("Запуск мониторинга Проводника Windows...")

        if not HAS_PYWIN32:
            self.status_changed.emit("Ошибка: pywin32 не установлен. Мониторинг остановлен.")
            return

        pythoncom.CoInitialize()

        shell = None
        retry_count = 0
        while self._running and shell is None:
            try:
                shell = win32com.client.Dispatch("Shell.Application")
                self.status_changed.emit("Мониторинг активен")
            except Exception:
                retry_count += 1
                if retry_count % 5 == 0:
                    self.status_changed.emit(f"Ожидание готовности Проводника Windows ({retry_count}с)...")
                self.msleep(1000)

        if not shell or not self._running:
            pythoncom.CoUninitialize()
            return

        # Первичный проход клоакинга и применение реестровых политик скрытия при старте
        self._apply_startup_cloaking()

        wake_thread = WinEventWakeThread(self._wake_event)
        wake_thread.start()

        try:
            while self._running:
                if not self.config_manager.settings.global_protection_enabled:
                    self.msleep(150)
                    continue

                active_rules = [
                    r for r in self.config_manager.get_rules_snapshot()
                    if r.enabled and r.target_path.strip()
                ]

                if not active_rules:
                    self.msleep(150)
                    continue

                now = time.time()
                self._redirection_cache = {
                    h: val for h, val in self._redirection_cache.items()
                    if now - val[1] < 3.0
                }

                self._cleanup_counter += 1
                if self._cleanup_counter >= 200:
                    self._cleanup_counter = 0
                    if self.recent_cleaner:
                        self.recent_cleaner.clean_once()

                # Периодический фоновый ре-клоакинг в отдельном потоке (не чаще 1 раза в 30 сек)
                if now - self._last_recloak_time >= 30.0:
                    if self._recloak_thread is None or not self._recloak_thread.is_alive():
                        self._last_recloak_time = now
                        def _bg_recloak():
                            try:
                                from core.file_cloaker import enforce_explorer_stealth_policies
                                from core.config_manager import sync_rules_cloaking
                                enforce_explorer_stealth_policies()
                                sync_rules_cloaking(self.config_manager, protection_enabled=True)
                            except Exception:
                                pass
                        self._recloak_thread = threading.Thread(target=_bg_recloak, daemon=True)
                        self._recloak_thread.start()

                windows = None
                try:
                    windows = shell.Windows()
                    count = windows.Count
                except Exception:
                    # Если Проводник перезапустился (Explorer crash/restart), переподключаемся и синхронизируем маску дисков
                    self.msleep(150)
                    try:
                        shell = win32com.client.Dispatch("Shell.Application")
                        self._apply_startup_cloaking()
                    except Exception:
                        pass
                    continue

                try:
                    for i in range(count):
                        window = None
                        try:
                            window = windows.Item(i)
                            if not window:
                                continue

                            full_name = str(getattr(window, "FullName", "")).lower()
                            if "explorer.exe" not in full_name:
                                continue

                            hwnd = 0
                            try:
                                hwnd = int(getattr(window, "HWND", 0))
                            except Exception:
                                hwnd = 0

                            location_url = str(getattr(window, "LocationURL", ""))
                            location_name = str(getattr(window, "LocationName", ""))
                            if not location_url:
                                continue

                            current_path = url_to_path(location_url, location_name)
                            if not current_path:
                                continue

                            matched_rule = None
                            for rule in active_rules:
                                if is_path_matching(current_path, rule.target_path):
                                    matched_rule = rule
                                    break

                            if not matched_rule:
                                continue

                            if hwnd in self._redirection_cache:
                                last_url, last_ts = self._redirection_cache[hwnd]
                                if now - last_ts < 0.8 and last_url == current_path:
                                    continue

                            self._redirection_cache[hwnd] = (current_path, now)
                            self._handle_matched_tab(window, current_path, matched_rule, hwnd)

                        except Exception:
                            continue
                        finally:
                            window = None
                finally:
                    windows = None

                interval = max(20, min(self.config_manager.settings.check_interval_ms, 2000))
                self._wake_event.wait(timeout=interval / 1000.0)
                self._wake_event.clear()

        finally:
            wake_thread.stop()
            shell = None
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            self.status_changed.emit("Мониторинг остановлен")

    def _handle_matched_tab(self, window, current_path: str, rule: Rule, hwnd: int):
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_target = rule.target_path if current_path.startswith("search-ms://") else current_path

        if rule.mode == "decoy":
            decoy_path = rule.decoy_path.strip()
            if not decoy_path or not os.path.exists(decoy_path):
                docs = os.path.join(os.path.expanduser("~"), "Documents")
                decoy_path = docs if os.path.exists(docs) else os.path.expanduser("~")

            try:
                window.Navigate2(decoy_path)
            except Exception as e:
                print(f"[Interceptor] Navigate2 failed: {e}")

            event_data = {
                "timestamp": timestamp_str,
                "target_path": display_target,
                "mode": "Подмена (Decoy)",
                "decoy_path": decoy_path,
                "rule_name": rule.name or os.path.basename(rule.target_path),
                "hwnd": hwnd
            }
            self.intercepted.emit(event_data)

        elif rule.mode == "block":
            norm_target = os.path.normpath(rule.target_path)
            parent_dir = os.path.dirname(norm_target)
            if not parent_dir or not os.path.exists(parent_dir) or os.path.normcase(parent_dir) == os.path.normcase(norm_target):
                safe_destination = "shell:MyComputerFolder"
            else:
                safe_destination = parent_dir

            try:
                if current_path.startswith("search-ms://"):
                    window.Navigate2(safe_destination)
                else:
                    before_url = str(getattr(window, "LocationURL", ""))
                    try:
                        window.GoBack()
                    except Exception:
                        pass
                    after_url = str(getattr(window, "LocationURL", ""))
                    if not after_url or after_url == before_url or is_path_matching(url_to_path(after_url), rule.target_path):
                        window.Navigate2(safe_destination)
            except Exception as e:
                print(f"[Interceptor] Block navigation failed: {e}")

            event_data = {
                "timestamp": timestamp_str,
                "target_path": display_target,
                "mode": "Блокировка (Block)",
                "decoy_path": safe_destination,
                "rule_name": rule.name or os.path.basename(rule.target_path),
                "hwnd": hwnd
            }
            self.intercepted.emit(event_data)

            if rule.notify_on_block:
                folder_name = os.path.basename(os.path.normpath(rule.target_path)) or rule.target_path
                show_native_error_dialog(
                    title="Проводник Windows",
                    message=f"Нет доступа к {folder_name}.\n\n"
                            f"Вам отказано в доступе к этой папке.\n"
                            f"Для получения доступа обратитесь к системному администратору.",
                    parent_hwnd=hwnd
                )

        if self.recent_cleaner and self.config_manager.settings.clean_recent:
            try:
                self.recent_cleaner.clean_once(force=True)
            except Exception:
                pass

    def stop(self):
        self._running = False
        self._wake_event.set()
        self.wait(1500)
