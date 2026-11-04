import sys
import os
import argparse
import ctypes

# In portable/frozen mode, add executable directory to sys.path and set working directory
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)
os.chdir(app_dir)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.config_manager import ConfigManager
from core.recent_cleaner import RecentCleaner
from core.interceptor import ExplorerInterceptor
from core.hotkey_manager import GlobalHotkeyManager
from core.autostart import set_autostart, is_autostart_enabled
from ui.main_window import MainWindow

MUTEX_NAME = "Local\\StealthGuardSingleInstance_Mutex_v1"


def main():
    parser = argparse.ArgumentParser(description="StealthGuard — Windows 11 Explorer Protection & Decoy")
    parser.add_argument("--stealth", action="store_true", help="Start directly in hidden background stealth mode")
    parser.add_argument("--config", type=str, default=None, help="Path to config.json")
    args = parser.parse_args()

    # Single instance check via Windows Named Mutex
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[StealthGuard] Приложение уже запущено в системе.")
        # If launched again, trigger hotkey window by simulating Ctrl+Shift+Alt+L or exiting
        sys.exit(0)

    # Enable High DPI attribute
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("StealthGuard")
    app.setOrganizationName("StealthGuard")

    # Prevent application from closing when main window is hidden
    app.setQuitOnLastWindowClosed(False)

    # Initialize Core Components
    config_manager = ConfigManager(config_path=args.config)

    # Sync autostart configuration if enabled in settings
    try:
        if config_manager.settings.autostart and not is_autostart_enabled():
            set_autostart(True)
    except Exception:
        pass

    recent_cleaner = RecentCleaner(config_manager)
    interceptor = ExplorerInterceptor(config_manager, recent_cleaner)
    hotkey_manager = GlobalHotkeyManager(
        config_manager.settings.hotkey,
        config_manager.settings.protection_toggle_hotkey
    )

    # Initialize Main UI
    window = MainWindow(config_manager, interceptor, hotkey_manager)

    # Start Background Services
    interceptor.start()
    hotkey_manager.start(
        config_manager.settings.hotkey,
        config_manager.settings.protection_toggle_hotkey
    )

    # Handle clean termination
    def cleanup():
        print("[StealthGuard] Остановка служб...")
        interceptor.stop()
        hotkey_manager.stop()
        if mutex:
            kernel32.CloseHandle(mutex)

    app.aboutToQuit.connect(cleanup)

    # Initial show logic
    if args.stealth or config_manager.settings.stealth_startup:
        print(f"[StealthGuard] Приложение запущено в скрытом режиме.")
        print(f"[StealthGuard] Для вызова окна: {config_manager.settings.hotkey.upper()}")
        print(f"[StealthGuard] Для вкл/выкл защиты: {config_manager.settings.protection_toggle_hotkey.upper()}")
        if config_manager.settings.show_tray_icon:
            window.show_stealth_notification()
        else:
            if hasattr(window, "tray_icon"):
                window.tray_icon.hide()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
