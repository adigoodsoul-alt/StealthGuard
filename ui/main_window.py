import sys
import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QCloseEvent, QAction, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    setTheme, Theme, InfoBar, InfoBarPosition
)

from core.config_manager import ConfigManager
from core.interceptor import ExplorerInterceptor
from core.hotkey_manager import GlobalHotkeyManager
from core.recent_cleaner import RecentCleaner
from ui.views.rules_view import RulesView
from ui.views.logs_view import LogsView
from ui.views.settings_view import SettingsView
from ui.dialogs.pin_dialog import PinVerifyDialog


class MainWindow(FluentWindow):
    """
    StealthGuard Main Application Window built with Fluent Design System,
    Mica effect on Windows 11, Dark theme, System Tray integration, and
    rock-solid global hotkey restore.
    """

    def __init__(self, config_manager: ConfigManager, interceptor: ExplorerInterceptor, hotkey_manager: GlobalHotkeyManager):
        super().__init__()
        self.config_manager = config_manager
        self.interceptor = interceptor
        self.hotkey_manager = hotkey_manager

        # Force dark theme for modern Windows 11 aesthetic
        setTheme(Theme.DARK)

        self.init_window()
        self.init_sub_interfaces()
        self.init_navigation()
        self.init_tray_icon()
        self.connect_signals()

    def init_window(self):
        self.setWindowTitle("StealthGuard — Защита и подмена Проводника Windows 11")
        self.resize(1000, 720)
        self.setMinimumSize(850, 600)

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def init_sub_interfaces(self):
        # Create tabs
        self.rules_view = RulesView(self.config_manager, self)
        self.logs_view = LogsView(self)
        self.settings_view = SettingsView(self.config_manager, self)

    def init_navigation(self):
        # Add navigation items
        self.addSubInterface(
            self.rules_view,
            FluentIcon.FINGERPRINT,
            "Правила защиты",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.logs_view,
            FluentIcon.HISTORY,
            "Журнал перехватов",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            "Настройки",
            NavigationItemPosition.BOTTOM
        )

        # Bottom custom button to hide window into stealth background mode
        self.navigationInterface.addItem(
            routeKey="hide_to_stealth",
            icon=FluentIcon.HIDE,
            text="Скрыть в фон (Стелс)",
            onClick=self.hide_to_stealth,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

    def init_tray_icon(self):
        """Initializes system tray icon for background control."""
        # Create a stylish shield/lock tray icon programmatically
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#0078D4"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(12, 10, 8, 8)
        painter.drawRoundedRect(10, 15, 12, 10, 2, 2)
        painter.end()
        icon = QIcon(pixmap)

        self.setWindowIcon(icon)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("StealthGuard — Защита Проводника Windows 11")

        # Tray Context Menu
        tray_menu = QMenu()
        open_action = QAction("Открыть StealthGuard", self)
        open_action.triggered.connect(self.on_hotkey_pressed)
        tray_menu.addAction(open_action)

        self.toggle_protect_action = QAction("Глобальная защита: Включена", self)
        self.toggle_protect_action.triggered.connect(self._toggle_protection_from_tray)
        tray_menu.addAction(self.toggle_protect_action)

        tray_menu.addSeparator()

        quit_action = QAction("Полный выход", self)
        quit_action.triggered.connect(self.force_quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        if self.config_manager.settings.show_tray_icon:
            self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.on_hotkey_pressed()

    def _toggle_protection_from_tray(self):
        self.on_toggle_protection_hotkey()

    def on_toggle_protection_hotkey(self):
        """Toggles global protection on/off via global hotkey or tray."""
        current = self.config_manager.settings.global_protection_enabled
        new_val = not current
        self.config_manager.settings.global_protection_enabled = new_val
        self.config_manager.save()
        try:
            from core.drive_cloaker import sync_drives_from_config
            sync_drives_from_config(self.config_manager)
        except Exception:
            pass

        # Update UI switch in SettingsView
        try:
            from qfluentwidgets import SwitchButton
            for child in self.settings_view.globalCard.findChildren(SwitchButton):
                child.blockSignals(True)
                child.setChecked(new_val)
                child.blockSignals(False)
        except Exception:
            pass

        # Handle cloaking / uncloaking on global protection change asynchronously
        def _async_sync_folders():
            try:
                from core.config_manager import sync_rules_cloaking
                sync_rules_cloaking(self.config_manager, protection_enabled=new_val)
            except Exception:
                pass

        from core.config_manager import _run_async
        _run_async(_async_sync_folders)

        # Subtle audio feedback
        try:
            import ctypes
            beep_type = 0x00000040 if new_val else 0x00000030
            ctypes.windll.user32.MessageBeep(beep_type)
        except Exception:
            pass

        status_text = "Включена" if new_val else "Приостановлена"
        if hasattr(self, "toggle_protect_action"):
            self.toggle_protect_action.setText(f"Глобальная защита: {status_text}")

        if self.isVisible() and not self.isMinimized():
            info_func = InfoBar.success if new_val else InfoBar.warning
            info_func(
                title="Глобальная защита",
                content=f"Защита Проводника {status_text.lower()}.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2500
            )
        elif hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "StealthGuard",
                f"Защита Проводника {status_text.lower()}.",
                QSystemTrayIcon.Information,
                2000
            )

    def show_stealth_notification(self):
        """Displays subtle hint that app is running in stealth mode."""
        hk = self.config_manager.settings.hotkey.upper()
        prot_hk = self.config_manager.settings.protection_toggle_hotkey.upper()
        if self.config_manager.settings.show_tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "StealthGuard активен в фоне",
                f"Защита Проводника включена.\nОткрыть окно: {hk}\nВкл/Выкл защиту: {prot_hk}",
                QSystemTrayIcon.Information,
                4000
            )

    def connect_signals(self):
        # Connect interceptor logs
        self.interceptor.intercepted.connect(self.logs_view.add_log_entry)

        # Connect hotkeys
        self.hotkey_manager.hotkey_triggered.connect(self.on_hotkey_pressed)
        self.hotkey_manager.protection_toggle_triggered.connect(self.on_toggle_protection_hotkey)

        # Connect settings updates
        self.settings_view.hotkey_updated.connect(self._restart_hotkeys)

    def _restart_hotkeys(self):
        self.hotkey_manager.start(
            self.config_manager.settings.hotkey,
            self.config_manager.settings.protection_toggle_hotkey
        )

    def on_hotkey_pressed(self):
        """Called when global hotkey is pressed from anywhere in Windows."""
        if self.isVisible() and not self.isMinimized():
            self.bring_to_foreground()
            return

        # Check PIN requirement if enabled
        if self.config_manager.settings.pin_enabled and self.config_manager.settings.pin_hash:
            if getattr(self, "_pin_dialog_open", False):
                return
            self._pin_dialog_open = True
            try:
                dialog = PinVerifyDialog(self.config_manager, None)
                if dialog.exec():
                    self.show_normal_and_raise()
            finally:
                self._pin_dialog_open = False
        else:
            self.show_normal_and_raise()

    def show_normal_and_raise(self):
        self.showNormal()
        if hasattr(self, "tray_icon") and self.config_manager.settings.show_tray_icon:
            self.tray_icon.show()
        self.bring_to_foreground()

    def bring_to_foreground(self):
        """Forces window to foreground over all other Windows applications."""
        self.raise_()
        self.activateWindow()
        try:
            import win32gui
            import win32con
            hwnd = int(self.winId())
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def hide_to_stealth(self):
        """Hides the window and removes tray icon completely for 100% invisible stealth."""
        self.hide()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

    def closeEvent(self, event: QCloseEvent):
        """
        Minimizes to stealth instead of exiting the background interceptor.
        """
        event.ignore()
        self.hide_to_stealth()

    def force_quit(self):
        """Completely exits application."""
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()
