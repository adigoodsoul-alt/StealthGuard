import os
import sys
import ctypes
from ctypes import wintypes
import threading
from typing import Optional, Callable, List, Tuple
from PySide6.QtCore import QObject, Signal

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# Windows API constants for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

HOTKEY_ID_WINDOW = 0x5447       # 'TG' - Show/Hide Window
HOTKEY_ID_PROTECTION = 0x5448   # 'TH' - Toggle Protection

EN_TO_RU = {
    'a': 'ф', 'b': 'и', 'c': 'с', 'd': 'в', 'e': 'у', 'f': 'а',
    'g': 'п', 'h': 'р', 'i': 'ш', 'j': 'о', 'k': 'л', 'l': 'д',
    'm': 'ь', 'n': 'т', 'o': 'щ', 'p': 'з', 'q': 'й', 'r': 'к',
    's': 'ы', 't': 'е', 'u': 'г', 'v': 'м', 'w': 'ц', 'x': 'ч',
    'y': 'я', 'z': 'ж'
}
RU_TO_EN = {v: k for k, v in EN_TO_RU.items()}


def parse_hotkey_to_winapi(hotkey_str: str) -> tuple[int, int]:
    """
    Parses string like 'Ctrl+Shift+Alt+L' into (fsModifiers, vk_code).
    Immune to keyboard layout because it uses virtual key codes.
    """
    tokens = [t.strip().lower() for t in hotkey_str.replace(" ", "").split("+") if t.strip()]
    modifiers = MOD_NOREPEAT
    vk = 0x4C  # Default to 'L'

    for t in tokens:
        if t in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif t in ("alt", "menu"):
            modifiers |= MOD_ALT
        elif t == "shift":
            modifiers |= MOD_SHIFT
        elif t in ("win", "cmd", "super"):
            modifiers |= MOD_WIN
        elif len(t) == 1 and t.isalnum():
            # Translate English letter or Russian layout equivalent to VK code
            char = t.lower()
            char = RU_TO_EN.get(char, char).upper()
            vk = ord(char)
        elif t.startswith("f") and t[1:].isdigit():
            # Function keys F1-F12
            f_num = int(t[1:])
            if 1 <= f_num <= 12:
                vk = 0x70 + (f_num - 1)

    return modifiers, vk


def normalize_hotkey_for_pynput(hotkey_str: str) -> list[str]:
    """
    Converts friendly string to pynput formats for BOTH English and Russian layouts.
    e.g. '<ctrl>+<shift>+<alt>+p' and '<ctrl>+<shift>+<alt>+з'
    """
    parts = [p.strip().lower() for p in hotkey_str.replace(" ", "").split("+") if p.strip()]
    base_mods = []
    main_char = "l"

    for p in parts:
        if p in ("ctrl", "control"):
            base_mods.append("<ctrl>")
        elif p in ("alt", "menu"):
            base_mods.append("<alt>")
        elif p == "shift":
            base_mods.append("<shift>")
        elif p in ("win", "cmd", "super"):
            base_mods.append("<cmd>")
        else:
            main_char = p

    en_char = RU_TO_EN.get(main_char, main_char)
    ru_char = EN_TO_RU.get(en_char, en_char)

    hk1 = "+".join(base_mods + [en_char])
    hk2 = "+".join(base_mods + [ru_char])
    return [hk1, hk2] if hk1 != hk2 else [hk1]


class NativeWinHotKeyThread(threading.Thread):
    """
    Background worker that runs a Windows message pump to catch WM_HOTKEY messages
    from WinAPI RegisterHotKey for multiple shortcuts layout-independently.
    """

    def __init__(self, hotkey_entries: List[Tuple[int, int, int, Callable]]):
        """
        hotkey_entries: List of (hotkey_id, modifiers, vk, callback)
        """
        super().__init__(daemon=True)
        self.hotkey_entries = hotkey_entries
        self.thread_id = 0
        self._running = False
        self._ready_event = threading.Event()
        self._registered_ids: List[int] = []

    def run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()

        # Register all hotkeys on current thread
        any_success = False
        for hk_id, mods, vk, _ in self.hotkey_entries:
            success = user32.RegisterHotKey(0, hk_id, mods, vk)
            if success:
                self._registered_ids.append(hk_id)
                any_success = True

        self._running = any_success
        self._ready_event.set()

        if not any_success:
            return

        msg = wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY:
                for hk_id, _, _, callback in self.hotkey_entries:
                    if msg.wParam == hk_id:
                        try:
                            callback()
                        except Exception:
                            pass

        for hk_id in self._registered_ids:
            try:
                user32.UnregisterHotKey(0, hk_id)
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self.thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass


class GlobalHotkeyManager(QObject):
    """
    Manages global keyboard shortcuts:
    - hotkey_triggered: Window restore / show / hide
    - protection_toggle_triggered: Quick toggle / disable / enable protection
    """
    hotkey_triggered = Signal()
    protection_toggle_triggered = Signal()

    def __init__(self, hotkey_str: str = "ctrl+shift+alt+l", protection_hotkey_str: str = "ctrl+shift+alt+p"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.protection_hotkey_str = protection_hotkey_str
        self._win_thread: Optional[NativeWinHotKeyThread] = None
        self._pynput_listener: Optional[keyboard.GlobalHotKeys] = None
        self._is_running = False

    def start(self, hotkey_str: Optional[str] = None, protection_hotkey_str: Optional[str] = None):
        if hotkey_str:
            self.hotkey_str = hotkey_str
        if protection_hotkey_str:
            self.protection_hotkey_str = protection_hotkey_str

        self.stop()

        # 1. Primary: Windows API RegisterHotKey (immune to keyboard layout)
        try:
            mods_win, vk_win = parse_hotkey_to_winapi(self.hotkey_str)
            mods_prot, vk_prot = parse_hotkey_to_winapi(self.protection_hotkey_str)

            entries = [
                (HOTKEY_ID_WINDOW, mods_win, vk_win, self._on_window_triggered),
                (HOTKEY_ID_PROTECTION, mods_prot, vk_prot, self._on_protection_triggered)
            ]

            self._win_thread = NativeWinHotKeyThread(entries)
            self._win_thread.start()
            self._win_thread._ready_event.wait(timeout=1.0)
            if self._win_thread._running:
                self._is_running = True
                return
        except Exception:
            pass

        # 2. Secondary fallback: pynput with both EN and RU keys
        if HAS_PYNPUT:
            try:
                hotkey_map = {}
                for hk in normalize_hotkey_for_pynput(self.hotkey_str):
                    hotkey_map[hk] = self._on_window_triggered
                for hk in normalize_hotkey_for_pynput(self.protection_hotkey_str):
                    hotkey_map[hk] = self._on_protection_triggered

                self._pynput_listener = keyboard.GlobalHotKeys(hotkey_map)
                self._pynput_listener.daemon = True
                self._pynput_listener.start()
                self._is_running = True
            except Exception:
                pass

    def _on_window_triggered(self):
        self.hotkey_triggered.emit()

    def _on_protection_triggered(self):
        self.protection_toggle_triggered.emit()

    def stop(self):
        if self._win_thread:
            try:
                self._win_thread.stop()
            except Exception:
                pass
            self._win_thread = None

        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass
            self._pynput_listener = None

        self._is_running = False
