# StealthGuard — Полный исходный код проекта (v2.4)

> Этот файл содержит полный актуальный исходный код приложения **StealthGuard** (Windows 11 Transparent Explorer Interceptor, Cloaking & Decoy Drives, Search Leaks Prevention, Everything.ini Hidden/System Policy v2.4).
> Включает обновления безопасности (PBKDF2-HMAC-SHA256), надёжности (GoBack fallback для адресной строки), производительности (RecentCleaner mtime caching), предотвращения утечек поиска Windows 11 (search-ms: crumb/location parsing, ShowSuperHidden/Hidden stealth policies enforcement, target directory cloaking, max_depth=12), интеграцию с утилитой поиска Everything (everything_cloaker.py) и скрипт аварийного восстановления (emergency_restore.bat).

## Оглавление файлов

- [main.py](#файл-mainpy) — *Точка входа, проверка единого экземпляра (Named Mutex), инициализация QApplication, разбор аргументов командной строки (--stealth, --config).*
- [core/config_manager.py](#файл-coreconfig-managerpy) — *Потокобезопасное (RLock) управление конфигурацией config.json, безопасный PIN-код (PBKDF2-HMAC-SHA256, 600k итераций, соль, secrets.compare_digest, автомиграция со старого SHA-256), асинхронный запуск задач клоакинга и синхронизация скрытых дисков.*
- [core/interceptor.py](#файл-coreinterceptorpy) — *Мониторинг Проводника Windows 11 в реальном времени через COM Shell.Application, мгновенное пробуждение через WinEventWakeThread (GetMessageW), поддержка перехвата поисковых запросов search-ms: (включая crumb=location и crumb=query), безопасный fallback при блокировке.*
- [core/drive_cloaker.py](#файл-coredrive-cloakerpy) — *Скрытие локальных дисков и виртуальных дисков-приманок через реестровую маску NoDrives, мгновенное удаление из левой панели навигации XAML через SHChangeNotify(SHCNE_DRIVEREMOVED), монтирование виртуального диска-приманки через DefineDosDeviceW (Win32 API без прав администратора), скрытие дублирующих съёмных дисков через MountPoints2 и CLSID DelegateFolders.*
- [core/file_cloaker.py](#файл-corefile-cloakerpy) — *Технология Total Cloaking (System + Hidden + NotContentIndexed) для устранения визуального мигания файлов и исключения из поиска Проводника, принудительное отключение показа скрытых файлов в реестре Explorer Advanced (enforce_explorer_stealth_policies), скрытие корневой директории правила, белый список системных файлов Windows, глубина max_depth=12.*
- [core/everything_cloaker.py](#файл-coreeverything-cloakerpy) — *Управление флагами exclude_hidden_files_and_folders и exclude_system_files_and_folders в Everything.ini для исключения защищённых файлов и папок из поисковой выдачи утилиты Everything при активной защите, с тихим перезапуском Everything.exe -quit / -startup только при реальном изменении флагов.*
- [core/decoy_generator.py](#файл-coredecoy-generatorpy) — *Генерация визуальных клонов-приманок на основе омоглифов (кириллица/латиница), поддержка дисков-приманок через drive_cloaker, безопасное удаление и размонтирование приманок.*
- [core/hotkey_manager.py](#файл-corehotkey-managerpy) — *Глобальные горячие клавиши (Ctrl+Shift+Alt+L, Ctrl+Shift+Alt+P) на базе нативного потока RegisterHotKey с fallback на pynput, нечувствительность к раскладке клавиатуры RU/EN.*
- [core/recent_cleaner.py](#файл-corerecent-cleanerpy) — *Оптимизированная очистка системных ярлыков .lnk из %APPDATA%\Microsoft\Windows\Recent с кэшированием mtime (0% CPU в простое) и гарантированным освобождением COM-дескрипторов.*
- [core/autostart.py](#файл-coreautostartpy) — *Двойная регистрация автозапуска в Windows 11: создание ярлыка в Shell:Startup с WorkingDirectory + запись в HKCU Run.*
- [core/utils.py](#файл-coreutilspy) — *Парсинг LocationURL в путь файловой системы с поддержкой search-ms: протокола и crumb параметров, нормализация путей с поддержкой сетевых и UNC-путей, системный диалог ошибки Windows через MessageBoxW.*
- [ui/main_window.py](#файл-uimain-windowpy) — *Главное окно на базе FluentWindow (PySide6-Fluent-Widgets), интеграция в системный трей, анимация сворачивания, обработка PIN-кода при разворачивании, хоткей паузы защиты с синхронизацией дисков.*
- [ui/views/rules_view.py](#файл-uiviewsrules-viewpy) — *Вкладка правил защиты: добавление, редактирование, удаление, кнопка мгновенного создания визуального клона-приманки или виртуального диска.*
- [ui/views/logs_view.py](#файл-uiviewslogs-viewpy) — *Вкладка журнала перехватов: табличный просмотр событий с фильтрацией, подсчётом статистики и очисткой.*
- [ui/views/settings_view.py](#файл-uiviewssettings-viewpy) — *Вкладка настроек: интервал проверки, глобальная защита, мастер-пароль PIN, автозапуск, автоочистка Recent, режим тишины.*
- [ui/dialogs/pin_dialog.py](#файл-uidialogspin-dialogpy) — *Диалоги установки и проверки PIN-кода (автономный PinVerifyDialog без родителя для разворачивания из трея).*
- [build_portable.py](#файл-build-portablepy) — *Скрипт сборки автономного переносимого пакета StealthGuard через PyInstaller с изолированным каталогом dist_build и безопасным обновлением locked DLL.*
- [tests/test_components.py](#файл-teststest-componentspy) — *Комплексный набор из 12 автоматических тестов для всех ключевых подсистем проекта (хоткеи, PBKDF2 PIN + миграция, перехватчик, Total Cloaking, омоглифы, удаление, автозапуск, Drive Cloaker, search-ms парсинг, stealth policies, UI).*
- [emergency_restore.bat](#файл-emergency-restorebat) — *Автономный батник аварийного восстановления Проводника: сброс NoDrives, размонтирование виртуальных дисков subst, снятие атрибутов System/Hidden и перезапуск Shell.*
- [config.json](#файл-configjson) — *Конфигурационный файл приложения (настройки и правила по умолчанию).*
- [run.bat](#файл-runbat) — *Скрипт запуска приложения в обычном режиме GUI.*
- [run_stealth.bat](#файл-run-stealthbat) — *Скрипт запуска приложения в скрытом фоновом режиме без отображения окна.*
- [requirements.txt](#файл-requirementstxt) — *Зависимости проекта Python.*

---

## Файл: main.py

> **Назначение:** Точка входа, проверка единого экземпляра (Named Mutex), инициализация QApplication, разбор аргументов командной строки (--stealth, --config).

```python
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
```

---

## Файл: core/config_manager.py

> **Назначение:** Потокобезопасное (RLock) управление конфигурацией config.json, безопасный PIN-код (PBKDF2-HMAC-SHA256, 600k итераций, соль, secrets.compare_digest, автомиграция со старого SHA-256), асинхронный запуск задач клоакинга и синхронизация скрытых дисков.

```python
import json
import os
import sys
import uuid
import hashlib
import secrets
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

CONFIG_FILE_NAME = "config.json"


@dataclass
class Rule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    target_path: str = ""
    mode: str = "decoy"  # "decoy" or "block"
    decoy_path: str = ""
    enabled: bool = True
    notify_on_block: bool = True
    hide_media: bool = True
    auto_decoy: bool = False
    cloak_all: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            target_path=data.get("target_path", ""),
            mode=data.get("mode", "decoy"),
            decoy_path=data.get("decoy_path", ""),
            enabled=data.get("enabled", True),
            notify_on_block=data.get("notify_on_block", True),
            hide_media=data.get("hide_media", True),
            auto_decoy=data.get("auto_decoy", False),
            cloak_all=data.get("cloak_all", True),
        )


@dataclass
class Settings:
    global_protection_enabled: bool = True
    hotkey: str = "ctrl+shift+alt+l"
    protection_toggle_hotkey: str = "ctrl+shift+alt+p"
    pin_enabled: bool = False
    pin_hash: str = ""
    autostart: bool = False
    clean_recent: bool = True
    check_interval_ms: int = 35
    stealth_startup: bool = False
    show_tray_icon: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        return cls(
            global_protection_enabled=data.get("global_protection_enabled", True),
            hotkey=data.get("hotkey", "ctrl+shift+alt+l"),
            protection_toggle_hotkey=data.get("protection_toggle_hotkey", "ctrl+shift+alt+p"),
            pin_enabled=data.get("pin_enabled", False),
            pin_hash=data.get("pin_hash", ""),
            autostart=data.get("autostart", False),
            clean_recent=data.get("clean_recent", True),
            check_interval_ms=data.get("check_interval_ms", 35),
            stealth_startup=data.get("stealth_startup", False),
            show_tray_icon=data.get("show_tray_icon", False),
        )


def _run_async(func, *args, **kwargs):
    """Выполняет файловые операции клоакинга в фоновом потоке без блокировки GUI."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()


def sync_rules_cloaking(config_manager: "ConfigManager", protection_enabled: Optional[bool] = None):
    """
    Синхронизирует видимость папок и клонов-приманок для всех правил конфигурации,
    а также переключает видимость атрибутов Hidden + System в Everything.
    Реализует умную инверсию видимости:
      - При включённой защите: настоящая папка скрывается (Total Cloaking),
        а визуальный клон-приманка в той же папке делается видимой (uncloak).
        В Everything включается скрытие Hidden + System файлов/папок.
      - При выключенной защите (пауза): визуальный клон-приманка скрывается (cloak),
        а настоящая папка становится видимой (uncloak).
        В Everything снова разрешается показ Hidden + System объектов.
    """
    from core.file_cloaker import cloak_folder, uncloak_folder, cloak_directory, uncloak_directory
    from core.decoy_generator import is_visual_clone
    from core.drive_cloaker import is_drive_root
    from core.everything_cloaker import sync_everything_hidden_policy

    is_active = (
        protection_enabled
        if protection_enabled is not None
        else config_manager.settings.global_protection_enabled
    )

    rules = config_manager.get_rules_snapshot()

    for rule in rules:
        target = rule.target_path.strip() if rule.target_path else ""
        decoy = rule.decoy_path.strip() if rule.decoy_path else ""

        if not target or not os.path.exists(target):
            continue

        is_clone = (
            rule.mode == "decoy"
            and bool(decoy)
            and os.path.exists(decoy)
            and not is_drive_root(target)
            and is_visual_clone(target, decoy)
        )

        if is_active and rule.enabled:
            # Защита активна: скрываем настоящую целевую папку
            if rule.hide_media or getattr(rule, "cloak_all", True):
                cloak_folder(target, all_files=getattr(rule, "cloak_all", True))
            else:
                cloak_directory(target)

            # Если приманка является визуальным клоном в той же директории — делаем её видимой
            if is_clone:
                uncloak_directory(decoy)
            elif rule.mode == "decoy" and getattr(rule, "auto_decoy", False) and os.path.exists(decoy):
                cloak_directory(decoy)
        else:
            # Защита выключена (пауза или правило отключено):
            # Если это визуальный клон — скрываем его, чтобы в проводнике не двоились имена
            if is_clone:
                cloak_directory(decoy)

            # Восстанавливаем видимость настоящей целевой папки
            uncloak_folder(target, all_files=True)

    # Синхронизируем скрытие системных и скрытых объектов в Everything:
    # Если глобальная защита включена -> скрываем Hidden + System в Everything (True)
    # Если глобальная защита выключена -> разрешаем показ Hidden + System в Everything (False)
    try:
        sync_everything_hidden_policy(hide_system_and_hidden=bool(is_active))
    except Exception:
        pass


class ConfigManager:
    """Управляет загрузкой, обновлением и потокобезопасным сохранением config.json."""

    def __init__(self, config_path: Optional[str] = None):
        self._lock = threading.RLock()
        if config_path:
            self.config_path = config_path
        else:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, CONFIG_FILE_NAME)

        self.rules: List[Rule] = []
        self.settings: Settings = Settings()
        self.load()

    def get_rules_snapshot(self) -> List[Rule]:
        """Потокобезопасная копия списка правил для чтения из фонового потока."""
        with self._lock:
            return list(self.rules)

    def _sync_drives(self):
        try:
            from core.drive_cloaker import sync_drives_from_config
            sync_drives_from_config(self)
        except Exception as e:
            print(f"[ConfigManager] Drive sync error: {e}")

    def load(self):
        with self._lock:
            if not os.path.exists(self.config_path):
                self._create_default_config()
                self._sync_drives()
                return

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.settings = Settings.from_dict(data.get("settings", {}))
                raw_rules = data.get("rules", [])
                self.rules = [Rule.from_dict(r) for r in raw_rules]
            except Exception as e:
                print(f"[ConfigManager] Error reading config: {e}. Falling back to defaults.")
                self._create_default_config()

        self._sync_drives()

    def _create_default_config(self):
        self.settings = Settings()
        default_rule = Rule(
            name="Пример защиты (Секретная папка)",
            target_path="C:\\ProtectedFolder",
            mode="decoy",
            decoy_path=os.path.join(os.path.expanduser("~"), "Documents"),
            enabled=False,
            notify_on_block=True
        )
        self.rules = [default_rule]
        self.save()

    def save(self):
        with self._lock:
            data = {
                "settings": asdict(self.settings),
                "rules": [asdict(r) for r in self.rules]
            }
            try:
                temp_path = self.config_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.config_path):
                    os.replace(temp_path, self.config_path)
                else:
                    os.rename(temp_path, self.config_path)
            except Exception as e:
                print(f"[ConfigManager] Failed to save config: {e}")

    def add_rule(self, rule: Rule):
        with self._lock:
            self.rules.append(rule)
            self.save()

        self._sync_drives()

        def _task():
            try:
                sync_rules_cloaking(self)
            except Exception:
                pass
        _run_async(_task)

    def update_rule(self, rule: Rule):
        with self._lock:
            for i, r in enumerate(self.rules):
                if r.id == rule.id:
                    self.rules[i] = rule
                    self.save()
                    break

        self._sync_drives()

        def _task():
            try:
                sync_rules_cloaking(self)
            except Exception:
                pass
        _run_async(_task)

    def remove_rule(self, rule_id: str):
        with self._lock:
            target_rule = next((r for r in self.rules if r.id == rule_id), None)
            if target_rule and target_rule.decoy_path:
                try:
                    from core.drive_cloaker import is_drive_root, unmount_virtual_decoy_drive
                    if is_drive_root(target_rule.decoy_path):
                        unmount_virtual_decoy_drive(target_rule.decoy_path, delete_backing=True)
                except Exception as e:
                    print(f"[ConfigManager] Error unmounting decoy drive: {e}")

            self.rules = [r for r in self.rules if r.id != rule_id]
            self.save()

        self._sync_drives()

        if target_rule:
            def _cleanup_task():
                if target_rule.target_path:
                    try:
                        from core.file_cloaker import uncloak_folder
                        uncloak_folder(target_rule.target_path, all_files=True)
                    except Exception:
                        pass

                if target_rule.mode == "decoy" and target_rule.decoy_path:
                    try:
                        from core.decoy_generator import is_visual_clone, delete_decoy_folder
                        is_auto = getattr(target_rule, "auto_decoy", False) or is_visual_clone(
                            target_rule.target_path, target_rule.decoy_path
                        )
                        if is_auto and os.path.exists(target_rule.decoy_path):
                            delete_decoy_folder(target_rule.decoy_path)
                    except Exception as e:
                        print(f"[ConfigManager] Error removing decoy folder: {e}")

            _run_async(_cleanup_task)

    @staticmethod
    def hash_pin(pin: str) -> str:
        """Хэширует PIN с использованием PBKDF2-HMAC-SHA256 и случайной 16-байтовой соли."""
        salt = secrets.token_hex(16)
        iterations = 600_000
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("ascii"), iterations)
        return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"

    def verify_pin(self, pin: str) -> bool:
        if not self.settings.pin_enabled or not self.settings.pin_hash:
            return True

        stored = self.settings.pin_hash
        # Поддержка нового формата PBKDF2
        if stored.startswith("pbkdf2_sha256$"):
            try:
                _, iter_str, salt, expected_hex = stored.split("$", 3)
                dk = hashlib.pbkdf2_hmac(
                    "sha256",
                    pin.encode("utf-8"),
                    salt.encode("ascii"),
                    int(iter_str)
                )
                return secrets.compare_digest(dk.hex(), expected_hex)
            except Exception:
                return False

        # Обратная совместимость со старым форматом SHA-256 (с автоматической миграцией)
        legacy_hash = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        if secrets.compare_digest(legacy_hash, stored):
            self.settings.pin_hash = self.hash_pin(pin)
            self.save()
            return True
        return False
```

---

## Файл: core/interceptor.py

> **Назначение:** Мониторинг Проводника Windows 11 в реальном времени через COM Shell.Application, мгновенное пробуждение через WinEventWakeThread (GetMessageW), поддержка перехвата поисковых запросов search-ms: (включая crumb=location и crumb=query), безопасный fallback при блокировке.

```python
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
```

---

## Файл: core/drive_cloaker.py

> **Назначение:** Скрытие локальных дисков и виртуальных дисков-приманок через реестровую маску NoDrives, мгновенное удаление из левой панели навигации XAML через SHChangeNotify(SHCNE_DRIVEREMOVED), монтирование виртуального диска-приманки через DefineDosDeviceW (Win32 API без прав администратора), скрытие дублирующих съёмных дисков через MountPoints2 и CLSID DelegateFolders.

```python
import os
import shutil
import ctypes
from ctypes import wintypes
import winreg
from typing import Optional, Set, Dict

kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32

DDD_REMOVE_DEFINITION = 0x00000002

SHCNE_DRIVEREMOVED = 0x00000080
SHCNE_DRIVEADD = 0x00000100
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_PATHW = 0x0005
SHCNF_IDLIST = 0x0000
SHCNF_FLUSH = 0x1000

HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002

EXPLORER_POLICIES_KEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
DELEGATE_FOLDERS_CLSID = r"Software\Classes\CLSID\{F5FB2C77-0E2F-4A16-A381-3E560C68BC83}"

# Кэш активных скрытых букв для корректного восстановления при паузе/удалении
_CURRENTLY_HIDDEN_DRIVES: Set[str] = set()
# Словарь смонтированных виртуальных дисков-приманок: {drive_letter: backing_dir}
_MOUNTED_DECOY_DRIVES: Dict[str, str] = {}


def is_drive_root(path: str) -> bool:
    """Проверяет, является ли путь корнем диска (например, 'Y:\\' или 'Y:')."""
    if not path:
        return False
    clean = os.path.normpath(path.strip())
    return len(clean) in (2, 3) and clean[1] == ":" and clean[0].isalpha()


def get_drive_letter(path: str) -> str:
    """Возвращает заглавную букву диска из пути ('Y:\\' -> 'Y')."""
    if not path:
        return ""
    clean = os.path.normpath(path.strip())
    if len(clean) >= 2 and clean[1] == ":" and clean[0].isalpha():
        return clean[0].upper()
    return ""


def get_decoy_backing_dir(target_drive_letter: str) -> str:
    """Возвращает путь к скрытому системному каталогу, выступающему хранилищем диска-приманки."""
    local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    base = os.path.join(local_appdata, "Microsoft", "Windows", "Explorer", f"VolumeCache_{target_drive_letter.upper()}")
    os.makedirs(base, exist_ok=True)
    try:
        from core.file_cloaker import cloak_directory
        cloak_directory(base)
    except Exception:
        pass
    return base


def get_free_drive_letter(exclude: Optional[Set[str]] = None) -> Optional[str]:
    """Ищет свободную букву диска с конца алфавита (Z..D)."""
    exclude_set = {ch.upper()[0] for ch in (exclude or set()) if ch}
    bitmask = kernel32.GetLogicalDrives()
    for code in range(ord("Z"), ord("D") - 1, -1):
        letter = chr(code)
        if letter in exclude_set:
            continue
        if not (bitmask & (1 << (code - ord("A")))):
            return letter
    return None


def query_dos_device_target(drive_letter: str) -> Optional[str]:
    """Проверяет, смонтирован ли уже виртуальный диск через DefineDosDeviceW."""
    letter = drive_letter.upper()[0]
    buf = ctypes.create_unicode_buffer(1024)
    res = kernel32.QueryDosDeviceW(f"{letter}:", buf, 1024)
    if res > 0:
        val = buf.value
        if val.startswith("\\??\\"):
            return val[4:]
        return val
    return None


def mount_virtual_decoy_drive(target_drive_letter: str, preferred_decoy_letter: Optional[str] = None) -> tuple[bool, str, str]:
    """
    Создаёт и монтирует виртуальный диск-приманку через DefineDosDeviceW.
    Возвращает (success, decoy_root_path, message).
    """
    t_letter = target_drive_letter.upper()[0]
    backing_dir = get_decoy_backing_dir(t_letter)

    # Проверяем, возможно буква приманки уже выбрана и смонтирована
    if preferred_decoy_letter:
        p_letter = preferred_decoy_letter.upper()[0]
        existing = query_dos_device_target(p_letter)
        if existing and os.path.normcase(os.path.normpath(existing)) == os.path.normcase(os.path.normpath(backing_dir)):
            _MOUNTED_DECOY_DRIVES[p_letter] = backing_dir
            return True, f"{p_letter}:\\", f"Виртуальный диск-приманка {p_letter}:\\ активен."
        decoy_letter = p_letter if not existing else get_free_drive_letter({t_letter})
    else:
        decoy_letter = get_free_drive_letter({t_letter})

    if not decoy_letter:
        return False, "", "Нет свободных букв дисков в системе для создания виртуального тома."

    clean_backing = os.path.normpath(backing_dir).rstrip("\\/")
    ok = bool(kernel32.DefineDosDeviceW(0, f"{decoy_letter}:", clean_backing))
    if not ok:
        return False, "", f"Не удалось смонтировать виртуальный том {decoy_letter}: через DefineDosDeviceW."

    _MOUNTED_DECOY_DRIVES[decoy_letter] = clean_backing

    # Задаём нейтральную метку тома в MountPoints2
    try:
        mp_key = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\{decoy_letter}"
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, mp_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "_LabelFromReg", 0, winreg.REG_SZ, "Локальный диск")
    except Exception:
        pass

    return True, f"{decoy_letter}:\\", (
        f"Создан изолированный виртуальный диск-приманка {decoy_letter}:\\.\n"
        f"Оба диска ({t_letter}: и {decoy_letter}:) скрыты из «Этот компьютер» и боковой панели."
    )


def unmount_virtual_decoy_drive(decoy_path_or_letter: str, delete_backing: bool = False) -> bool:
    """Размонтирует виртуальный диск-приманку и опционально очищает папку-хранилище."""
    letter = get_drive_letter(decoy_path_or_letter)
    if not letter and len(decoy_path_or_letter) == 1 and decoy_path_or_letter.isalpha():
        letter = decoy_path_or_letter.upper()
    if not letter:
        return False

    target = query_dos_device_target(letter)
    # Размонтируем только если это виртуальный subst-том (начинается с \??\ в QueryDosDevice)
    buf = ctypes.create_unicode_buffer(1024)
    kernel32.QueryDosDeviceW(f"{letter}:", buf, 1024)
    if not buf.value.startswith("\\??\\"):
        return False

    ok = bool(kernel32.DefineDosDeviceW(DDD_REMOVE_DEFINITION, f"{letter}:", None))
    backing = _MOUNTED_DECOY_DRIVES.pop(letter, target)

    if delete_backing and backing and os.path.exists(backing) and "VolumeCache_" in backing:
        try:
            from core.decoy_generator import delete_decoy_folder
            delete_decoy_folder(backing)
        except Exception:
            pass

    return ok


def _set_navpane_removable_drives_pin(pinned: bool):
    """
    Управляет дублирующим делегатом съёмных дисков в левой боковой панели Windows 11
    через HKCU\Software\Classes\CLSID (без прав администратора).
    """
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, DELEGATE_FOLDERS_CLSID, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "System.IsPinnedToNameSpaceTree", 0, winreg.REG_DWORD, 1 if pinned else 0)
    except Exception:
        pass


def apply_hidden_drives(drive_letters: Set[str]):
    """
    Записывает битовую маску NoDrives и мгновенно обновляет как правую панель «Этот компьютер»,
    так и левую боковую панель (XAML Navigation Pane) Проводника Windows 11 через SHCNE_DRIVEREMOVED.
    """
    global _CURRENTLY_HIDDEN_DRIVES
    new_hidden = {ch.upper()[0] for ch in drive_letters if ch and ch[0].isalpha()}
    prev_hidden = set(_CURRENTLY_HIDDEN_DRIVES)

    mask = 0
    for letter in new_hidden:
        if "A" <= letter <= "Z":
            mask |= (1 << (ord(letter) - ord("A")))

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, EXPLORER_POLICIES_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if mask > 0:
                winreg.SetValueEx(key, "NoDrives", 0, winreg.REG_DWORD, mask)
            else:
                try:
                    winreg.DeleteValue(key, "NoDrives")
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"[DriveCloaker] Failed to write NoDrives: {e}")

    # Отключаем дублирование томов в нижней секции боковой панели Windows 11, если есть скрытые диски
    _set_navpane_removable_drives_pin(pinned=(len(new_hidden) == 0))

    # 1. Широковещательно уведомляем оболочку об изменении политики
    res = wintypes.DWORD()
    user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Policy",
        SMTO_ABORTIFHUNG, 1000, ctypes.byref(res)
    )

    # 2. Точечно заставляем дерево навигации Windows 11 убрать скрытые диски
    for letter in new_hidden:
        drive_root = f"{letter}:\\"
        shell32.SHChangeNotify(
            SHCNE_DRIVEREMOVED,
            SHCNF_PATHW | SHCNF_FLUSH,
            ctypes.c_wchar_p(drive_root),
            None
        )

    # 3. Возвращаем в дерево навигации диски, с которых снята защита
    restored = prev_hidden - new_hidden
    for letter in restored:
        if os.path.exists(f"{letter}:\\"):
            drive_root = f"{letter}:\\"
            shell32.SHChangeNotify(
                SHCNE_DRIVEADD,
                SHCNF_PATHW | SHCNF_FLUSH,
                ctypes.c_wchar_p(drive_root),
                None
            )

    # 4. Обновляем открытые вкладки «Этот компьютер»
    shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST | SHCNF_FLUSH, None, None)
    _CURRENTLY_HIDDEN_DRIVES = new_hidden


def sync_drives_from_config(config_manager):
    """
    Синхронизирует состояние виртуальных дисков-приманок и маски скрытия NoDrives
    на основе активных правил и глобального переключателя защиты.
    """
    if not config_manager.settings.global_protection_enabled:
        apply_hidden_drives(set())
        return

    hidden_letters: Set[str] = set()
    rules_updated = False

    for rule in config_manager.get_rules_snapshot():
        if not rule.enabled or not rule.target_path:
            continue

        if is_drive_root(rule.target_path):
            t_letter = get_drive_letter(rule.target_path)
            if t_letter:
                hidden_letters.add(t_letter)

            if rule.mode == "decoy":
                decoy_letter = get_drive_letter(rule.decoy_path) if is_drive_root(rule.decoy_path) else None
                ok, decoy_root, _ = mount_virtual_decoy_drive(t_letter, preferred_decoy_letter=decoy_letter)
                if ok and decoy_root:
                    d_letter = get_drive_letter(decoy_root)
                    if d_letter:
                        hidden_letters.add(d_letter)
                    if rule.decoy_path != decoy_root:
                        rule.decoy_path = decoy_root
                        rule.auto_decoy = True
                        rules_updated = True

    if rules_updated:
        config_manager.save()

    apply_hidden_drives(hidden_letters)
```

---

## Файл: core/file_cloaker.py

> **Назначение:** Технология Total Cloaking (System + Hidden + NotContentIndexed) для устранения визуального мигания файлов и исключения из поиска Проводника, принудительное отключение показа скрытых файлов в реестре Explorer Advanced (enforce_explorer_stealth_policies), скрытие корневой директории правила, белый список системных файлов Windows, глубина max_depth=12.

```python
import os
import threading
import ctypes
from ctypes import wintypes
import winreg
from typing import Set, Optional

kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32

_PROTECTED_NAMES_LOCK = threading.Lock()
PROTECTED_ITEM_NAMES: Set[str] = set()


def get_protected_item_names() -> Set[str]:
    """Возвращает копию множества защищённых имён объектов (в нижнем регистре)."""
    with _PROTECTED_NAMES_LOCK:
        return set(PROTECTED_ITEM_NAMES)


def clear_protected_item_names():
    """Очищает глобальный кэш защищённых имён объектов."""
    with _PROTECTED_NAMES_LOCK:
        PROTECTED_ITEM_NAMES.clear()


def _add_name_variants(name: str, target_set: Set[str]):
    """Добавляет имя в нижнем регистре с расширением и без расширения (длиной >= 3)."""
    if not name:
        return
    clean = name.strip().lower()
    if len(clean) >= 3:
        target_set.add(clean)
    base, _ = os.path.splitext(clean)
    if base and len(base) >= 3 and base != clean:
        target_set.add(base)

FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x00002000
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

SHCNE_UPDATEDIR = 0x00001000
SHCNE_ALLEVENTS = 0x7FFFFFFF
SHCNF_PATHW = 0x0005
SHCNF_IDLIST = 0x0000
SHCNF_FLUSHNOWAIT = 0x2000

EXPLORER_ADVANCED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Системные файлы и папки Windows, которые НЕЛЬЗЯ модифицировать или расклоакивать
PROTECTED_SYSTEM_NAMES: Set[str] = {
    "$recycle.bin",
    "system volume information",
    "desktop.ini",
    "thumbs.db",
    "pagefile.sys",
    "swapfile.sys",
    "hiberfil.sys",
    "dumpstack.log",
    "dumpstack.log.tmp",
    "recovery",
    "boot",
    "bootmgr",
}

DEFAULT_MEDIA_EXTENSIONS: Set[str] = {
    # Images
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif", ".ico", ".svg", ".raw", ".heic",
    # Videos
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".ts",
    # Audio
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".m4b"
}


def enforce_explorer_stealth_policies() -> bool:
    """
    Принудительно отключает показ защищённых системных файлов (ShowSuperHidden = 0)
    и скрытых файлов (Hidden = 2) в реестре HKCU Проводника Windows.
    Именно из-за включённого ShowSuperHidden или Hidden=1 Проводник показывает
    скрытые файлы при поиске и обходе папок.
    """
    changed = False
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            EXPLORER_ADVANCED_KEY,
            0,
            winreg.KEY_READ | winreg.KEY_SET_VALUE
        ) as key:
            # 1. Запрещаем показ системных файлов (System + Hidden)
            try:
                val, _ = winreg.QueryValueEx(key, "ShowSuperHidden")
            except FileNotFoundError:
                val = 0
            if val != 0:
                winreg.SetValueEx(key, "ShowSuperHidden", 0, winreg.REG_DWORD, 0)
                changed = True

            # 2. Запрещаем показ обычных скрытых файлов (2 = Не показывать скрытые файлы)
            try:
                h_val, _ = winreg.QueryValueEx(key, "Hidden")
            except FileNotFoundError:
                h_val = 2
            if h_val != 2:
                winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 2)
                changed = True
    except Exception:
        pass

    if changed:
        try:
            shell32.SHChangeNotify(SHCNE_ALLEVENTS, SHCNF_IDLIST | SHCNF_FLUSHNOWAIT, None, None)
        except Exception:
            pass
    return changed


def notify_shell_dir_updated(folder_path: str):
    """Уведомляет оболочку Windows и индекс Проводника об изменении атрибутов внутри папки."""
    if not folder_path:
        return
    try:
        norm = os.path.normpath(folder_path)
        shell32.SHChangeNotify(
            SHCNE_UPDATEDIR,
            SHCNF_PATHW | SHCNF_FLUSHNOWAIT,
            ctypes.c_wchar_p(norm),
            None
        )
    except Exception:
        pass


def is_protected_system_item(name: str) -> bool:
    """Проверяет, является ли файл или папка защищённым системным объектом ОС."""
    if not name:
        return False
    low = name.lower()
    return low in PROTECTED_SYSTEM_NAMES or low.startswith("$")


def _is_drive_root_path(path: str) -> bool:
    if not path:
        return False
    clean = os.path.normpath(path.strip())
    return len(clean) in (2, 3) and clean[1] == ":" and clean[0].isalpha()


def cloak_file(file_path: str) -> bool:
    """
    Накладывает атрибуты System + Hidden + NotContentIndexed на файл.
    Полностью скрывает файл из выдачи и поиска Проводника Windows.
    """
    try:
        if is_protected_system_item(os.path.basename(file_path)):
            return False

        attrs = kernel32.GetFileAttributesW(file_path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False

        target_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
        if (attrs & target_flags) == target_flags:
            return True

        new_attrs = attrs | target_flags
        return bool(kernel32.SetFileAttributesW(file_path, new_attrs))
    except Exception:
        return False


def uncloak_file(file_path: str) -> bool:
    """
    Восстанавливает видимость файла, снимая атрибуты System и Hidden
    (игнорирует настоящие системные файлы Windows вроде desktop.ini).
    """
    try:
        if is_protected_system_item(os.path.basename(file_path)):
            return False

        attrs = kernel32.GetFileAttributesW(file_path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False

        remove_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        if not (attrs & remove_flags):
            return True

        new_attrs = attrs & ~remove_flags
        return bool(kernel32.SetFileAttributesW(file_path, new_attrs))
    except Exception:
        return False


def cloak_folder(
    folder_path: str,
    recursive: bool = True,
    extensions: Optional[Set[str]] = None,
    all_files: bool = True,
    max_depth: int = 12
) -> int:
    """
    Скрывает саму целевую папку (если это не корень диска), а также все файлы и подпапки
    внутри неё на глубину до max_depth=12.
    Добавляет имена папки, всех её подпапок и файлов в глобальный кэш PROTECTED_ITEM_NAMES.
    Благодаря скрытию самой корневой папки (System + Hidden + NotContentIndexed)
    поиск Проводника Windows полностью пропускает ветку каталога и не выдаёт файлы внутри.
    """
    if not folder_path or not os.path.exists(folder_path):
        return 0

    # Гарантируем, что в Проводнике отключён показ скрытых и системных файлов
    enforce_explorer_stealth_policies()

    target_exts = extensions if extensions is not None else DEFAULT_MEDIA_EXTENSIONS
    cloaked_count = 0
    base_path = os.path.normpath(folder_path)
    base_depth = base_path.rstrip(os.path.sep).count(os.path.sep)
    names_to_add: Set[str] = set()

    try:
        folder_base_name = os.path.basename(base_path)
        if not _is_drive_root_path(base_path):
            if folder_base_name:
                _add_name_variants(folder_base_name, names_to_add)
            cloak_directory(base_path)
        else:
            folder_attrs = kernel32.GetFileAttributesW(base_path)
            if folder_attrs != INVALID_FILE_ATTRIBUTES:
                kernel32.SetFileAttributesW(base_path, folder_attrs | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)

        for root, dirs, files in os.walk(base_path):
            current_depth = root.rstrip(os.path.sep).count(os.path.sep) - base_depth

            # Исключаем системные каталоги ($RECYCLE.BIN, System Volume Information и т.д.)
            dirs[:] = [d for d in dirs if not is_protected_system_item(d)]

            if all_files:
                for d in dirs:
                    _add_name_variants(d, names_to_add)
                    sub_path = os.path.join(root, d)
                    cloak_directory(sub_path)

            for file in files:
                if is_protected_system_item(file):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if all_files or ext in target_exts:
                    _add_name_variants(file, names_to_add)
                    full_path = os.path.join(root, file)
                    if cloak_file(full_path):
                        cloaked_count += 1

            if not recursive or current_depth >= max_depth:
                dirs.clear()

        if names_to_add:
            with _PROTECTED_NAMES_LOCK:
                PROTECTED_ITEM_NAMES.update(names_to_add)

        notify_shell_dir_updated(base_path)
        parent = os.path.dirname(base_path)
        if parent and parent != base_path:
            notify_shell_dir_updated(parent)
    except Exception:
        pass

    return cloaked_count


def uncloak_folder(
    folder_path: str,
    recursive: bool = True,
    extensions: Optional[Set[str]] = None,
    all_files: bool = True,
    max_depth: int = 12
) -> int:
    """
    Восстанавливает нормальную видимость самой целевой папки, её файлов и подпапок,
    не затрагивая настоящие системные объекты ОС.
    Удаляет имена объектов из глобального кэша PROTECTED_ITEM_NAMES.
    """
    if not folder_path or not os.path.exists(folder_path):
        return 0

    target_exts = extensions if extensions is not None else DEFAULT_MEDIA_EXTENSIONS
    uncloaked_count = 0
    base_path = os.path.normpath(folder_path)
    base_depth = base_path.rstrip(os.path.sep).count(os.path.sep)
    names_to_remove: Set[str] = set()

    try:
        folder_base_name = os.path.basename(base_path)
        if not _is_drive_root_path(base_path):
            if folder_base_name:
                _add_name_variants(folder_base_name, names_to_remove)
            uncloak_directory(base_path)

        for root, dirs, files in os.walk(base_path):
            current_depth = root.rstrip(os.path.sep).count(os.path.sep) - base_depth

            dirs[:] = [d for d in dirs if not is_protected_system_item(d)]

            if all_files:
                for d in dirs:
                    _add_name_variants(d, names_to_remove)
                    sub_path = os.path.join(root, d)
                    uncloak_directory(sub_path)

            for file in files:
                if is_protected_system_item(file):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if all_files or ext in target_exts:
                    _add_name_variants(file, names_to_remove)
                    full_path = os.path.join(root, file)
                    if uncloak_file(full_path):
                        uncloaked_count += 1

            if not recursive or current_depth >= max_depth:
                dirs.clear()

        if names_to_remove:
            with _PROTECTED_NAMES_LOCK:
                PROTECTED_ITEM_NAMES.difference_update(names_to_remove)

        notify_shell_dir_updated(base_path)
        parent = os.path.dirname(base_path)
        if parent and parent != base_path:
            notify_shell_dir_updated(parent)
    except Exception:
        pass

    return uncloaked_count


def cloak_directory(dir_path: str) -> bool:
    """Накладывает System + Hidden + NotContentIndexed на директорию."""
    if not dir_path or not os.path.exists(dir_path):
        return False
    try:
        if _is_drive_root_path(dir_path):
            return False
        if is_protected_system_item(os.path.basename(os.path.normpath(dir_path))):
            return False

        attrs = kernel32.GetFileAttributesW(dir_path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False

        target_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
        if (attrs & target_flags) == target_flags:
            return True

        new_attrs = attrs | target_flags
        return bool(kernel32.SetFileAttributesW(dir_path, new_attrs))
    except Exception:
        return False


def uncloak_directory(dir_path: str) -> bool:
    """Снимает System и Hidden с директории."""
    if not dir_path or not os.path.exists(dir_path):
        return False
    try:
        if _is_drive_root_path(dir_path):
            return False
        if is_protected_system_item(os.path.basename(os.path.normpath(dir_path))):
            return False

        attrs = kernel32.GetFileAttributesW(dir_path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False

        remove_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        if not (attrs & remove_flags):
            return True

        new_attrs = attrs & ~remove_flags
        return bool(kernel32.SetFileAttributesW(dir_path, new_attrs))
    except Exception:
        return False
```

---

## Файл: core/everything_cloaker.py

> **Назначение:** Управление флагами exclude_hidden_files_and_folders и exclude_system_files_and_folders в Everything.ini для исключения защищённых файлов и папок из поисковой выдачи утилиты Everything при активной защите, с тихим перезапуском Everything.exe -quit / -startup только при реальном изменении флагов.

```python
import os
import subprocess
from typing import List, Set, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Кэш последнего применённого состояния, чтобы не перезапускать Everything лишний раз
_LAST_APPLIED_STATE: Optional[bool] = None


def find_everything_ini_paths() -> List[str]:
    """Ищет все конфигурационные файлы Everything.ini (установленные в AppData и портативные)."""
    paths: Set[str] = set()

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for fname in ("Everything.ini", "Everything-1.5a.ini"):
            p = os.path.join(appdata, "Everything", fname)
            if os.path.exists(p):
                paths.add(os.path.normpath(p))

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        for fname in ("Everything.ini", "Everything-1.5a.ini"):
            p = os.path.join(localappdata, "Everything", fname)
            if os.path.exists(p):
                paths.add(os.path.normpath(p))

    if HAS_PSUTIL:
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in ("everything.exe", "everything64.exe"):
                    exe_path = proc.info.get("exe")
                    if exe_path and os.path.exists(exe_path):
                        exe_dir = os.path.dirname(exe_path)
                        for fname in ("Everything.ini", "Everything-1.5a.ini"):
                            cand = os.path.join(exe_dir, fname)
                            if os.path.exists(cand):
                                paths.add(os.path.normpath(cand))
            except Exception:
                continue

    return list(paths)


def _find_running_everything_client_exe() -> str:
    """Возвращает путь к запущенному клиентскому процессу Everything.exe (игнорируя службу -svc)."""
    if not HAS_PSUTIL:
        return ""
    for proc in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in ("everything.exe", "everything64.exe"):
                cmdline = [c.lower() for c in (proc.info.get("cmdline") or [])]
                if "-svc" in cmdline or "-service" in cmdline or "-app-data" in cmdline:
                    if "-svc" in cmdline or "-service" in cmdline:
                        continue
                exe = proc.info.get("exe")
                if exe and os.path.exists(exe):
                    return exe
        except Exception:
            continue
    return ""


def patch_everything_ini_flags(ini_path: str, hide_system_and_hidden: bool) -> bool:
    """
    Устанавливает в Everything.ini только флаги скрытия системных и скрытых объектов:
      - exclude_hidden_files_and_folders=1 (при включенной защите) или 0 (при выключенной)
      - exclude_system_files_and_folders=1 (при включенной защите) или 0 (при выключенной)
    Возвращает True, если значения в файле действительно изменились.
    """
    if not ini_path or not os.path.exists(ini_path):
        return False

    target_val = "1" if hide_system_and_hidden else "0"
    target_keys = {
        "exclude_hidden_files_and_folders": target_val,
        "exclude_system_files_and_folders": target_val,
    }

    try:
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        found_keys = set()
        changed = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith(";"):
                k, v = stripped.split("=", 1)
                k_clean = k.strip()
                v_clean = v.strip()
                if k_clean in target_keys:
                    found_keys.add(k_clean)
                    if v_clean != target_keys[k_clean]:
                        changed = True
                    new_lines.append(f"{k_clean}={target_keys[k_clean]}\n")
                    continue
            new_lines.append(line)

        for k_clean, val in target_keys.items():
            if k_clean not in found_keys:
                new_lines.append(f"{k_clean}={val}\n")
                changed = True

        if changed:
            with open(ini_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        return changed
    except Exception as e:
        print(f"[EverythingCloaker] Failed to patch {ini_path}: {e}")
        return False


def sync_everything_hidden_policy(hide_system_and_hidden: bool, force: bool = False) -> bool:
    """
    Включает (1) или выключает (0) скрытие объектов с атрибутами Hidden и System в Everything.
    Если клиент Everything запущен и настройки изменились, тихо перезапускает клиент в фоне (-startup),
    чтобы изменения вступили в силу мгновенно и не были перезаписаны из памяти процесса.
    """
    global _LAST_APPLIED_STATE
    if not force and _LAST_APPLIED_STATE == hide_system_and_hidden:
        return False

    ini_paths = find_everything_ini_paths()
    if not ini_paths:
        _LAST_APPLIED_STATE = hide_system_and_hidden
        return False

    # Сначала проверяем, нужно ли вообще менять хотя бы один ini-файл
    needs_update = False
    target_val = "1" if hide_system_and_hidden else "0"
    for ini_path in ini_paths:
        try:
            with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if (
                f"exclude_hidden_files_and_folders={target_val}" not in content
                or f"exclude_system_files_and_folders={target_val}" not in content
            ):
                needs_update = True
                break
        except Exception:
            needs_update = True
            break

    if not needs_update and not force:
        _LAST_APPLIED_STATE = hide_system_and_hidden
        return False

    running_exe = _find_running_everything_client_exe()

    # Если клиент Everything открыт, мягко выгружаем его перед записью в Everything.ini
    if running_exe:
        try:
            subprocess.run(
                [running_exe, "-quit"],
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    any_patched = False
    for ini_path in ini_paths:
        if patch_everything_ini_flags(ini_path, hide_system_and_hidden):
            any_patched = True

    # Сразу возвращаем клиент Everything в фоновый режим (-startup)
    if running_exe:
        try:
            subprocess.Popen(
                [running_exe, "-startup"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    _LAST_APPLIED_STATE = hide_system_and_hidden
    return any_patched
```

---

## Файл: core/decoy_generator.py

> **Назначение:** Генерация визуальных клонов-приманок на основе омоглифов (кириллица/латиница), поддержка дисков-приманок через drive_cloaker, безопасное удаление и размонтирование приманок.

```python
import os
from typing import Tuple, List

# Homoglyph character mappings (visually identical between Cyrillic and Latin)
RU_TO_EN = {
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p', 'х': 'x', 'у': 'y',
    'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H', 'К': 'K', 'М': 'M',
    'О': 'O', 'Р': 'P', 'Т': 'T', 'Х': 'X'
}

EN_TO_RU = {v: k for k, v in RU_TO_EN.items()}


def get_clone_candidates(name: str) -> List[str]:
    """
    Generates a prioritized list of visually identical / lookalike folder names.
    Uses homoglyph substitutions between Cyrillic and Latin alphabets,
    as well as subtle typographic equivalents.
    """
    candidates = []
    chars = list(name)

    # 1. Single-character homoglyph substitutions (left to right)
    for i, ch in enumerate(chars):
        if ch in RU_TO_EN:
            c = chars.copy()
            c[i] = RU_TO_EN[ch]
            cand = ''.join(c)
            if cand != name and cand not in candidates:
                candidates.append(cand)
        elif ch in EN_TO_RU:
            c = chars.copy()
            c[i] = EN_TO_RU[ch]
            cand = ''.join(c)
            if cand != name and cand not in candidates:
                candidates.append(cand)

    # 2. Hyphen to en-dash substitution ('-' -> '–')
    if '-' in name:
        cand = name.replace('-', '\u2013')
        if cand != name and cand not in candidates:
            candidates.append(cand)

    # 3. Space to non-breaking space (' ' -> '\u00A0')
    if ' ' in name:
        cand = name.replace(' ', '\u00A0')
        if cand != name and cand not in candidates:
            candidates.append(cand)

    # 4. Multi-character homoglyph substitutions
    multi_chars = chars.copy()
    has_multi = False
    for i, ch in enumerate(multi_chars):
        if ch in RU_TO_EN:
            multi_chars[i] = RU_TO_EN[ch]
            has_multi = True
        elif ch in EN_TO_RU:
            multi_chars[i] = EN_TO_RU[ch]
            has_multi = True
    if has_multi:
        cand = ''.join(multi_chars)
        if cand != name and cand not in candidates:
            candidates.append(cand)

    # 5. Fallback lookalikes if name contains no homoglyph letters
    for suffix in ("_", " ", " (1)", "."):
        cand = f"{name}{suffix}"
        if cand not in candidates:
            candidates.append(cand)

    return candidates


def create_visual_clone_decoy(target_folder_path: str, create_on_disk: bool = True) -> Tuple[bool, str, str]:
    """
    Creates a visually identical decoy folder in the same parent directory
    as target_folder_path.
    Returns (success: bool, decoy_path: str, message: str)
    """
    from core.drive_cloaker import is_drive_root, get_drive_letter, mount_virtual_decoy_drive
    if is_drive_root(target_folder_path):
        t_letter = get_drive_letter(target_folder_path)
        return mount_virtual_decoy_drive(t_letter)

    clean_target = os.path.normpath(target_folder_path.strip().rstrip("\\/"))
    if not clean_target:
        return False, "", "Путь целевой папки не указан."

    parent_dir = os.path.dirname(clean_target)
    folder_name = os.path.basename(clean_target)

    if not parent_dir or not folder_name:
        return False, "", "Не удалось определить родительскую директорию."

    if not os.path.exists(parent_dir):
        return False, "", f"Родительская директория не существует: {parent_dir}"

    candidates = get_clone_candidates(folder_name)
    selected_path = None

    for cand_name in candidates:
        cand_path = os.path.join(parent_dir, cand_name)
        # Check if candidate path is distinct and doesn't exist yet
        if not os.path.exists(cand_path):
            selected_path = cand_path
            break

    if not selected_path:
        # Ultimate fallback
        selected_path = os.path.join(parent_dir, f"{folder_name}_decoy")

    if create_on_disk:
        try:
            os.makedirs(selected_path, exist_ok=True)
            # Cloak the decoy folder (Hidden + System + NotContentIndexed)
            # so that it does not appear as a duplicate in the parent directory
            from core.file_cloaker import cloak_directory
            cloak_directory(selected_path)
        except Exception as e:
            return False, "", f"Не удалось создать папку на диске: {e}"

    return True, selected_path, "Создана визуально идентичная скрытая папка-двойник в той же директории."


def is_visual_clone(target_path: str, decoy_path: str) -> bool:
    """
    Checks if decoy_path appears to be an auto-generated visual clone of target_path.
    Verifies that they share the exact same parent directory and that the decoy name
    is in the candidate list of lookalike / homoglyph names.
    """
    from core.drive_cloaker import is_drive_root
    if is_drive_root(target_path) and is_drive_root(decoy_path):
        return target_path.strip()[0].upper() != decoy_path.strip()[0].upper()

    if not target_path or not decoy_path:
        return False

    target_norm = os.path.normpath(target_path.strip().rstrip("\\/"))
    decoy_norm = os.path.normpath(decoy_path.strip().rstrip("\\/"))

    if target_norm.lower() == decoy_norm.lower():
        return False

    # Parent directories must be the same
    target_parent = os.path.dirname(target_norm).lower()
    decoy_parent = os.path.dirname(decoy_norm).lower()
    if not target_parent or target_parent != decoy_parent:
        return False

    target_name = os.path.basename(target_norm)
    decoy_name = os.path.basename(decoy_norm)

    candidates = get_clone_candidates(target_name)
    if decoy_name == f"{target_name}_decoy":
        return True

    return decoy_name in candidates


def delete_decoy_folder(decoy_path: str) -> bool:
    """
    Safely uncloaks and removes an auto-generated decoy folder from disk.
    Ensures System/Hidden/ReadOnly attributes are removed before deletion.
    """
    from core.drive_cloaker import is_drive_root, unmount_virtual_decoy_drive
    if is_drive_root(decoy_path):
        return unmount_virtual_decoy_drive(decoy_path, delete_backing=True)

    clean_path = os.path.normpath(decoy_path.strip().rstrip("\\/")) if decoy_path else ""
    if not clean_path or not os.path.exists(clean_path):
        return False

    # Safety guard: Never delete system root, drive root, or user root
    if clean_path.endswith(":") or len(clean_path) <= 3:
        return False

    try:
        from core.file_cloaker import uncloak_directory, kernel32
        import shutil

        # First remove System and Hidden attributes
        uncloak_directory(clean_path)
        kernel32.SetFileAttributesW(clean_path, 0x80)  # FILE_ATTRIBUTE_NORMAL

        if os.path.isdir(clean_path):
            def _handle_remove_error(func, path, exc_info):
                try:
                    kernel32.SetFileAttributesW(path, 0x80)
                    func(path)
                except Exception:
                    pass

            shutil.rmtree(clean_path, onerror=_handle_remove_error)
        else:
            os.remove(clean_path)

        return not os.path.exists(clean_path)
    except Exception as e:
        print(f"[DecoyGenerator] Failed to delete decoy folder '{clean_path}': {e}")
        return False
```

---

## Файл: core/hotkey_manager.py

> **Назначение:** Глобальные горячие клавиши (Ctrl+Shift+Alt+L, Ctrl+Shift+Alt+P) на базе нативного потока RegisterHotKey с fallback на pynput, нечувствительность к раскладке клавиатуры RU/EN.

```python
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
```

---

## Файл: core/recent_cleaner.py

> **Назначение:** Оптимизированная очистка системных ярлыков .lnk из %APPDATA%\Microsoft\Windows\Recent с кэшированием mtime (0% CPU в простое) и гарантированным освобождением COM-дескрипторов.

```python
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
```

---

## Файл: core/autostart.py

> **Назначение:** Двойная регистрация автозапуска в Windows 11: создание ярлыка в Shell:Startup с WorkingDirectory + запись в HKCU Run.

```python
import sys
import os
import winreg

APP_NAME = "StealthGuard"
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_startup_shortcut_path() -> str:
    """Returns the path to the shortcut in Windows Startup folder."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser(r"~\AppData\Roaming")
    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    os.makedirs(startup_dir, exist_ok=True)
    return os.path.join(startup_dir, f"{APP_NAME}.lnk")


def get_app_command_and_working_dir() -> tuple[str, str, str, str]:
    """
    Returns (target_exe, arguments, working_dir, full_run_command).
    """
    if getattr(sys, "frozen", False):
        target_exe = sys.executable
        arguments = "--stealth"
        working_dir = os.path.dirname(sys.executable)
        full_command = f'"{target_exe}" {arguments}'
    else:
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        target_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
        main_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        arguments = f'"{main_script}" --stealth'
        working_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_command = f'"{target_exe}" {arguments}'

    return target_exe, arguments, working_dir, full_command


def set_autostart(enabled: bool) -> bool:
    """
    Enables or disables autostart on Windows logon.
    Uses BOTH the CurrentVersion\\Run registry key AND the Windows Startup folder (.lnk)
    for maximum reliability and compatibility across Windows 10 and Windows 11.
    """
    target_exe, arguments, working_dir, full_command = get_app_command_and_working_dir()
    shortcut_path = get_startup_shortcut_path()

    success_reg = False
    success_lnk = False

    # 1. Windows Startup folder shortcut (.lnk)
    try:
        if enabled:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = target_exe
            shortcut.Arguments = arguments
            shortcut.WorkingDirectory = working_dir
            shortcut.IconLocation = target_exe
            shortcut.Description = "StealthGuard Windows 11 Protection"
            shortcut.save()
            success_lnk = True
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            success_lnk = True
    except Exception as e:
        print(f"[Autostart] Startup folder error: {e}")

    # 2. Windows CurrentVersion\\Run registry key
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_REG_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ
        )
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, full_command)
            success_reg = True
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            success_reg = True
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[Autostart] Registry error: {e}")

    return success_lnk or success_reg


def is_autostart_enabled() -> bool:
    """
    Checks if application is registered in Windows Startup (Shortcut or Registry).
    """
    # 1. Check Startup folder shortcut
    shortcut_path = get_startup_shortcut_path()
    if os.path.exists(shortcut_path):
        return True

    # 2. Check Registry Run key
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False
```

---

## Файл: core/utils.py

> **Назначение:** Парсинг LocationURL в путь файловой системы с поддержкой search-ms: протокола и crumb параметров, нормализация путей с поддержкой сетевых и UNC-путей, системный диалог ошибки Windows через MessageBoxW.

```python
import os
import sys
import re
import threading
import urllib.parse
import ctypes


def url_to_path(url: str, location_name: str = "") -> str:
    r"""
    Преобразует file:// или search-ms: URL (из IWebBrowserApp.LocationURL)
    в стандартный нормализованный локальный или UNC путь Windows.
    Поддерживает:
      - file:///C:/Users/User/Secret%20Folder -> C:\Users\User\Secret Folder
      - search-ms:displayname=...&crumb=location:C%3A%5CSecret -> search-ms://C:\Secret|query
    """
    if not url:
        return ""

    low_url = url.lower()

    # 1. Обработка поисковых запросов Проводника Windows 11 (search-ms:)
    if low_url.startswith("search-ms:"):
        unquoted = urllib.parse.unquote(url)
        unquoted = urllib.parse.unquote(unquoted)  # Двойной unquote для вложенных параметров crumb=location:...
        scope_path = ""
        if "crumb=location:" in unquoted.lower():
            idx = unquoted.lower().find("crumb=location:") + len("crumb=location:")
            rest = unquoted[idx:]
            for sep in ("&", "|"):
                if sep in rest:
                    rest = rest.split(sep, 1)[0]
            scope_path = os.path.normpath(rest.strip())
        return f"search-ms://{scope_path}|{unquoted}|{location_name}"

    # 2. Обработка обычных файловых URL (file://)
    if not low_url.startswith("file:"):
        return url

    parsed = urllib.parse.urlsplit(url)
    unquoted_path = urllib.parse.unquote(parsed.path)

    if len(unquoted_path) >= 3 and unquoted_path[0] == "/" and unquoted_path[2] == ":":
        path = unquoted_path[1:]
    elif parsed.netloc:
        path = f"\\\\{parsed.netloc}{unquoted_path}"
    else:
        path = unquoted_path

    return os.path.normpath(path)


def normalize_path(path: str) -> str:
    """
    Возвращает нормализованный абсолютный путь в нижнем регистре без завершающего слэша.
    """
    if not path:
        return ""
    if path.startswith("search-ms://"):
        return path.lower()
    try:
        clean = os.path.normpath(os.path.abspath(path))
        return os.path.normcase(clean).rstrip("\\/")
    except Exception:
        return path.strip().lower().rstrip("\\/")


def is_path_matching(current_path: str, rule_target_path: str) -> bool:
    """
    Проверяет, совпадает ли текущий путь вкладки Проводника с защищаемым путём правила,
    является ли его подпапкой, либо поисковым запросом Проводника (search-ms:),
    затрагивающим защищаемую папку или её имя.
    """
    if not current_path or not rule_target_path:
        return False

    norm_target = normalize_path(rule_target_path)
    if not norm_target:
        return False

    # Проверка поисковой выдачи Проводника (search-ms://scope|raw_query|location_name)
    if current_path.startswith("search-ms://"):
        payload = current_path[len("search-ms://"):]
        parts = payload.split("|", 2)
        scope_path = parts[0] if len(parts) > 0 else ""
        raw_query = (parts[1] if len(parts) > 1 else "").lower()
        loc_name = (parts[2] if len(parts) > 2 else "").lower()

        # А) Если поиск запущен внутри самой защищаемой папки или её подпапки
        if scope_path:
            norm_scope = normalize_path(scope_path)
            if norm_scope == norm_target or norm_scope.startswith(norm_target + "\\"):
                return True

        # Б) Если в строке поиска вбито название защищаемой папки или путь к ней
        target_name = os.path.basename(norm_target).lower()
        if target_name and len(target_name) >= 2:
            if target_name in raw_query or target_name in loc_name:
                return True
        if norm_target in raw_query:
            return True

        # В) Проверка по глобальному индексу PROTECTED_ITEM_NAMES
        # Защита от поиска Windows Search по имени скрытого файла/подпапки при поиске с корня диска
        try:
            from core.file_cloaker import get_protected_item_names
            prot_names = get_protected_item_names()
            if prot_names:
                query_tokens = set(re.findall(r"[\w\.\-]+", raw_query + " " + loc_name))
                system_ignore = {
                    "search-ms", "displayname", "crumb", "location", "query",
                    "search", "results", "this", "computer", "local", "disk"
                }
                for t in query_tokens:
                    t_low = t.strip().lower()
                    if len(t_low) >= 3 and t_low not in system_ignore:
                        if t_low in prot_names:
                            return True
                for name in prot_names:
                    if len(name) >= 3 and name in raw_query:
                        return True
        except Exception:
            pass

        return False

    norm_current = normalize_path(current_path)
    if not norm_current:
        return False

    if norm_current == norm_target:
        return True

    target_prefix = norm_target + "\\"
    return norm_current.startswith(target_prefix)


def show_native_error_dialog(title: str, message: str, parent_hwnd: int = 0):
    """
    Отображает системный диалог ошибки Windows MessageBoxW в фоновом потоке.
    """
    def _worker():
        flags = 0x00000010 | 0x00010000 | 0x00040000
        try:
            ctypes.windll.user32.MessageBoxW(parent_hwnd, message, title, flags)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
```

---

## Файл: ui/main_window.py

> **Назначение:** Главное окно на базе FluentWindow (PySide6-Fluent-Widgets), интеграция в системный трей, анимация сворачивания, обработка PIN-кода при разворачивании, хоткей паузы защиты с синхронизацией дисков.

```python
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
```

---

## Файл: ui/views/rules_view.py

> **Назначение:** Вкладка правил защиты: добавление, редактирование, удаление, кнопка мгновенного создания визуального клона-приманки или виртуального диска.

```python
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QSizePolicy
)
from qfluentwidgets import (
    ScrollArea, CardWidget, LineEdit, PushButton, PrimaryPushButton,
    ToolButton, TransparentToolButton, ComboBox, SwitchButton, CheckBox,
    FluentIcon, SubtitleLabel, CaptionLabel, BodyLabel, StrongBodyLabel,
    InfoBar, InfoBarPosition, FlowLayout
)
from core.config_manager import ConfigManager, Rule
from core.decoy_generator import create_visual_clone_decoy, is_visual_clone, delete_decoy_folder


class RuleCard(CardWidget):
    """
    Card representing a single protection rule.
    """
    rule_changed = Signal(Rule)
    rule_deleted = Signal(str)

    def __init__(self, rule: Rule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(88)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Left Icon
        self.iconLabel = QLabel(self)
        self._update_icon()
        layout.addWidget(self.iconLabel)

        # Middle Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Name and badge
        top_info_layout = QHBoxLayout()
        top_info_layout.setSpacing(8)
        self.nameLabel = StrongBodyLabel(self.rule.name or os.path.basename(self.rule.target_path) or "Правило", self)
        top_info_layout.addWidget(self.nameLabel)
        top_info_layout.addStretch()

        # Path details
        self.targetLabel = CaptionLabel(f"🎯 Перехват: {self.rule.target_path}", self)
        self.targetLabel.setStyleSheet("color: #a0a0a0;")

        self.actionLabel = CaptionLabel(self._get_action_desc(), self)
        self.actionLabel.setStyleSheet("color: #0099ff;" if self.rule.mode == "decoy" else "color: #ff5555;")

        info_layout.addLayout(top_info_layout)
        info_layout.addWidget(self.targetLabel)
        info_layout.addWidget(self.actionLabel)

        layout.addLayout(info_layout, 1)

        # Right Controls: Mode ComboBox, Hide Media Checkbox, Switch, Delete button
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        self.mediaCheck = CheckBox("Анти-мигание", self)
        self.mediaCheck.setToolTip("Делает файлы и подпапки системно скрытыми от Проводника — устраняет задержку и мигание при открытии")
        self.mediaCheck.setChecked(getattr(self.rule, "cloak_all", True))
        self.mediaCheck.stateChanged.connect(self._on_hide_media_toggled)
        controls_layout.addWidget(self.mediaCheck)

        self.modeCombo = ComboBox(self)
        self.modeCombo.addItems(["Подмена", "Блокировка"])
        self.modeCombo.setCurrentIndex(0 if self.rule.mode == "decoy" else 1)
        self.modeCombo.setFixedWidth(135)
        self.modeCombo.currentIndexChanged.connect(self._on_mode_changed)
        controls_layout.addWidget(self.modeCombo)

        # Switch Button for enable/disable
        self.switchBtn = SwitchButton(self)
        self.switchBtn.setChecked(self.rule.enabled)
        self.switchBtn.checkedChanged.connect(self._on_switch_changed)
        controls_layout.addWidget(self.switchBtn)

        # Delete Button
        self.deleteBtn = TransparentToolButton(FluentIcon.DELETE, self)
        self.deleteBtn.setToolTip("Удалить правило")
        self.deleteBtn.clicked.connect(self._on_delete_clicked)
        controls_layout.addWidget(self.deleteBtn)

        layout.addLayout(controls_layout)

    def _update_icon(self):
        icon = FluentIcon.SYNC if self.rule.mode == "decoy" else FluentIcon.CANCEL
        self.iconLabel.setPixmap(icon.icon().pixmap(32, 32))

    def _get_action_desc(self) -> str:
        hide_str = " • 🙈 Анти-мигание активно" if getattr(self.rule, "cloak_all", True) else ""
        if self.rule.mode == "decoy":
            decoy = self.rule.decoy_path or "Документы (по умолчанию)"
            return f"🔄 Подмена -> {decoy}{hide_str}"
        return f"⛔ Блокировка -> Окно ошибки Windows{hide_str}"

    def _on_hide_media_toggled(self, state):
        val = (state == Qt.Checked or state == 2 or bool(state))
        self.rule.hide_media = val
        self.rule.cloak_all = val
        self.actionLabel.setText(self._get_action_desc())
        self.rule_changed.emit(self.rule)

    def _on_mode_changed(self, index: int):
        self.rule.mode = "decoy" if index == 0 else "block"
        self._update_icon()
        self.actionLabel.setText(self._get_action_desc())
        self.actionLabel.setStyleSheet("color: #0099ff;" if self.rule.mode == "decoy" else "color: #ff5555;")
        self.rule_changed.emit(self.rule)

    def _on_switch_changed(self, checked: bool):
        self.rule.enabled = checked
        self.rule_changed.emit(self.rule)

    def _on_delete_clicked(self):
        self.rule_deleted.emit(self.rule.id)


class RulesView(QWidget):
    """
    Main tab view for viewing, adding and editing interception rules.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._last_auto_decoy = False
        self.setObjectName("RulesView")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        self.titleLabel = SubtitleLabel("Правила защиты Проводника", self)
        self.descLabel = CaptionLabel(
            "Прозрачный перехват при открытии через Проводник Windows 11. "
            "Файловая система и фоновые процессы не блокируются.",
            self
        )
        main_layout.addWidget(self.titleLabel)
        main_layout.addWidget(self.descLabel)

        # Panel: Add New Rule
        self.addCard = CardWidget(self)
        add_layout = QVBoxLayout(self.addCard)
        add_layout.setContentsMargins(16, 16, 16, 16)
        add_layout.setSpacing(12)

        add_title = StrongBodyLabel("➕ Добавить новое правило перехвата", self.addCard)
        add_layout.addWidget(add_title)

        # Row 1: Target path
        r1_layout = QHBoxLayout()
        r1_layout.setSpacing(8)
        self.targetInput = LineEdit(self.addCard)
        self.targetInput.setPlaceholderText("Защищаемая папка или путь (например: D:\\SecretFolder)")
        self.targetInput.setClearButtonEnabled(True)

        self.browseTargetBtn = PushButton(FluentIcon.FOLDER, "Обзор папки", self.addCard)
        self.browseTargetBtn.clicked.connect(self._browse_target)
        r1_layout.addWidget(self.targetInput, 1)
        r1_layout.addWidget(self.browseTargetBtn)
        add_layout.addLayout(r1_layout)

        # Row 2: Mode + Decoy path + Rule name
        r2_layout = QHBoxLayout()
        r2_layout.setSpacing(8)

        mode_label = BodyLabel("Режим:", self.addCard)
        self.modeCombo = ComboBox(self.addCard)
        self.modeCombo.addItems(["Подмена (Decoy)", "Блокировка (Block)"])
        self.modeCombo.setCurrentIndex(0)
        self.modeCombo.currentIndexChanged.connect(self._on_add_mode_changed)

        self.decoyInput = LineEdit(self.addCard)
        self.decoyInput.setPlaceholderText("Папка-приманка (например: C:\\Users\\User\\Documents)")
        self.decoyInput.setClearButtonEnabled(True)

        self.browseDecoyBtn = PushButton(FluentIcon.FOLDER, "Обзор", self.addCard)
        self.browseDecoyBtn.clicked.connect(self._browse_decoy)

        self.autoCloneBtn = PushButton(FluentIcon.COPY, "⚡ Клон-приманка", self.addCard)
        self.autoCloneBtn.setToolTip("Автоматически создать неотличимую папку-двойника (омоглиф) в этой же директории")
        self.autoCloneBtn.clicked.connect(self._create_auto_clone_decoy)

        r2_layout.addWidget(mode_label)
        r2_layout.addWidget(self.modeCombo)
        r2_layout.addWidget(self.decoyInput, 1)
        r2_layout.addWidget(self.browseDecoyBtn)
        r2_layout.addWidget(self.autoCloneBtn)
        add_layout.addLayout(r2_layout)

        # Row 2.5: Anti-flicker / Total Cloaking Checkbox
        self.hideMediaCheck = CheckBox("🔒 Режим анти-мигания (скрывать файлы в папке: System + Hidden)", self.addCard)
        self.hideMediaCheck.setChecked(True)
        self.hideMediaCheck.setToolTip("Делает файлы и подпапки невидимыми для Проводника, полностью устраняя мигание при переходе в приманку")
        add_layout.addWidget(self.hideMediaCheck)

        # Row 3: Name & Add Button
        r3_layout = QHBoxLayout()
        r3_layout.setSpacing(8)

        self.nameInput = LineEdit(self.addCard)
        self.nameInput.setPlaceholderText("Название правила (опционально)")
        self.nameInput.setClearButtonEnabled(True)

        self.addRuleBtn = PrimaryPushButton(FluentIcon.ADD, "Создать правило", self.addCard)
        self.addRuleBtn.clicked.connect(self._create_rule)

        r3_layout.addWidget(self.nameInput, 1)
        r3_layout.addWidget(self.addRuleBtn)
        add_layout.addLayout(r3_layout)

        main_layout.addWidget(self.addCard)

        # Rules List Header
        self.rulesHeader = StrongBodyLabel("Активные правила", self)
        main_layout.addWidget(self.rulesHeader)

        # Scroll Area for Rules
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("background: transparent; border: none;")

        self.scrollWidget = QWidget()
        self.scrollWidget.setStyleSheet("background: transparent;")
        self.rulesLayout = QVBoxLayout(self.scrollWidget)
        self.rulesLayout.setContentsMargins(0, 0, 0, 0)
        self.rulesLayout.setSpacing(10)
        self.rulesLayout.addStretch()

        self.scrollArea.setWidget(self.scrollWidget)
        main_layout.addWidget(self.scrollArea, 1)

        # Populate rules
        self.refresh_rules_list()

    def _browse_target(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите защищаемую папку")
        if folder:
            self.targetInput.setText(os.path.normpath(folder))
            if not self.nameInput.text():
                self.nameInput.setText(os.path.basename(os.path.normpath(folder)))

    def _browse_decoy(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку-приманку для подмены")
        if folder:
            self.decoyInput.setText(os.path.normpath(folder))
            self._last_auto_decoy = False

    def _on_add_mode_changed(self, index: int):
        is_decoy = (index == 0)
        self.decoyInput.setEnabled(is_decoy)
        self.browseDecoyBtn.setEnabled(is_decoy)
        self.autoCloneBtn.setEnabled(is_decoy)
        if not is_decoy:
            self.decoyInput.setPlaceholderText("Для блокировки папка-приманка не требуется")
        else:
            self.decoyInput.setPlaceholderText("Папка-приманка (например: C:\\Users\\User\\Documents)")

    def _create_auto_clone_decoy(self):
        target = self.targetInput.text().strip()
        if not target:
            InfoBar.warning(
                title="Укажите целевую папку",
                content="Сначала выберите или введите защищаемую папку выше, чтобы создать для неё папку-двойника.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3500
            )
            return

        # If previous decoy was generated and not yet added, delete it to avoid clutter
        prev_decoy = self.decoyInput.text().strip()
        if self._last_auto_decoy and prev_decoy and os.path.exists(prev_decoy):
            if is_visual_clone(target, prev_decoy):
                delete_decoy_folder(prev_decoy)

        success, decoy_path, msg = create_visual_clone_decoy(target, create_on_disk=True)
        if success:
            self._last_auto_decoy = True
            self.decoyInput.setText(decoy_path)
            title = "Папка-приманка создана!"
            content = f"Создан визуальный клон:\n{decoy_path}\n(Папка скрыта атрибутами System+Hidden и не видна в родительском каталоге)"

            InfoBar.success(
                title=title,
                content=content,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000
            )
        else:
            InfoBar.error(
                title="Ошибка создания приманки",
                content=msg,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000
            )

    def _create_rule(self):
        target = self.targetInput.text().strip()
        if not target:
            InfoBar.warning(
                title="Укажите путь",
                content="Необходимо указать целевую защищаемую папку или путь.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
            return

        mode = "decoy" if self.modeCombo.currentIndex() == 0 else "block"
        decoy = self.decoyInput.text().strip()
        auto_decoy = self._last_auto_decoy
        if mode == "decoy" and not decoy:
            from core.drive_cloaker import is_drive_root, get_drive_letter, mount_virtual_decoy_drive
            if is_drive_root(target):
                ok, decoy_drive, _ = mount_virtual_decoy_drive(get_drive_letter(target))
                if ok:
                    decoy = decoy_drive
                    auto_decoy = True
            if not decoy:
                # Default decoy: User Documents
                decoy = os.path.join(os.path.expanduser("~"), "Documents")

        name = self.nameInput.text().strip() or os.path.basename(os.path.normpath(target)) or "Защита"
        cloak_all = self.hideMediaCheck.isChecked()
        hide_media = cloak_all

        new_rule = Rule(
            name=name,
            target_path=target,
            mode=mode,
            decoy_path=decoy,
            enabled=True,
            notify_on_block=True,
            hide_media=hide_media,
            auto_decoy=auto_decoy,
            cloak_all=cloak_all
        )

        self.config_manager.add_rule(new_rule)
        self._last_auto_decoy = False

        # Cloak decoy folder if it exists
        if mode == "decoy" and decoy and os.path.exists(decoy):
            try:
                from core.file_cloaker import cloak_directory
                cloak_directory(decoy)
            except Exception:
                pass

        # Clear inputs
        self.targetInput.clear()
        self.decoyInput.clear()
        self.nameInput.clear()

        self.refresh_rules_list()

        msg = f"Правило для «{name}» успешно активировано."
        if cloak_all:
            msg += " Включен режим анти-мигания (файлы системно скрыты)."

        InfoBar.success(
            title="Правило сохранено",
            content=msg,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000
        )

    def refresh_rules_list(self):
        # Clear existing rule cards
        while self.rulesLayout.count() > 1:
            item = self.rulesLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rule in self.config_manager.rules:
            card = RuleCard(rule, self.scrollWidget)
            card.rule_changed.connect(self._on_rule_modified)
            card.rule_deleted.connect(self._on_rule_deleted)
            self.rulesLayout.insertWidget(self.rulesLayout.count() - 1, card)

        count = len(self.config_manager.rules)
        self.rulesHeader.setText(f"Активные правила ({count})")

    def _on_rule_modified(self, rule: Rule):
        self.config_manager.update_rule(rule)

    def _on_rule_deleted(self, rule_id: str):
        target_rule = next((r for r in self.config_manager.rules if r.id == rule_id), None)
        decoy_removed = False
        if target_rule and target_rule.mode == "decoy" and target_rule.decoy_path:
            is_auto = getattr(target_rule, "auto_decoy", False) or is_visual_clone(
                target_rule.target_path, target_rule.decoy_path
            )
            if is_auto and os.path.exists(target_rule.decoy_path):
                decoy_removed = True

        self.config_manager.remove_rule(rule_id)
        self.refresh_rules_list()

        msg = "Правило защиты удалено из конфигурации."
        if decoy_removed:
            msg += " Автоматически созданная папка-приманка удалена с диска."

        InfoBar.info(
            title="Правило удалено",
            content=msg,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500
        )
```

---

## Файл: ui/views/logs_view.py

> **Назначение:** Вкладка журнала перехватов: табличный просмотр событий с фильтрацией, подсчётом статистики и очисткой.

```python
import csv
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QFileDialog
)
from qfluentwidgets import (
    TableWidget, SubtitleLabel, CaptionLabel, TransparentPushButton,
    FluentIcon, InfoBar, InfoBarPosition
)


class LogsView(QWidget):
    """
    Tab view displaying real-time log of folder interception events.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogsView")
        self.log_entries = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header with actions
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        self.titleLabel = SubtitleLabel("Журнал перехватов", self)
        self.descLabel = CaptionLabel("История попыток доступа к защищенным папкам через Проводник Windows", self)
        header_text_layout.addWidget(self.titleLabel)
        header_text_layout.addWidget(self.descLabel)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.exportBtn = TransparentPushButton(FluentIcon.FOLDER, "Экспорт в CSV", self)
        self.exportBtn.clicked.connect(self._export_csv)
        header_layout.addWidget(self.exportBtn)

        self.clearBtn = TransparentPushButton(FluentIcon.DELETE, "Очистить журнал", self)
        self.clearBtn.clicked.connect(self._clear_logs)
        header_layout.addWidget(self.clearBtn)

        main_layout.addLayout(header_layout)

        # Log Table
        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Время", "Правило", "Защищенный путь", "Действие", "Назначение / Результат"
        ])

        # Configure columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)

        main_layout.addWidget(self.table, 1)

    def add_log_entry(self, data: dict):
        """
        Receives event dictionary from ExplorerInterceptor and prepends it to the table.
        """
        self.log_entries.insert(0, data)

        self.table.insertRow(0)
        self.table.setItem(0, 0, self._create_item(data.get("timestamp", "")))
        self.table.setItem(0, 1, self._create_item(data.get("rule_name", "")))
        self.table.setItem(0, 2, self._create_item(data.get("target_path", "")))
        self.table.setItem(0, 3, self._create_item(data.get("mode", "")))
        self.table.setItem(0, 4, self._create_item(data.get("decoy_path", "")))

        # Limit to 500 rows to keep memory small
        if self.table.rowCount() > 500:
            self.table.removeRow(500)
            self.log_entries = self.log_entries[:500]

    def _create_item(self, text: str):
        from PySide6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _clear_logs(self):
        self.table.setRowCount(0)
        self.log_entries.clear()
        InfoBar.info(
            title="Журнал очищен",
            content="Все записи журнала перехватов были удалены.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000
        )

    def _export_csv(self):
        if not self.log_entries:
            InfoBar.warning(
                title="Журнал пуст",
                content="Нет записей для экспорта.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "stealthguard_log.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Rule Name", "Target Path", "Mode", "Destination"])
                for e in self.log_entries:
                    writer.writerow([
                        e.get("timestamp", ""),
                        e.get("rule_name", ""),
                        e.get("target_path", ""),
                        e.get("mode", ""),
                        e.get("decoy_path", "")
                    ])

            InfoBar.success(
                title="Экспорт завершен",
                content=f"Журнал успешно экспортирован в {file_path}",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title="Ошибка экспорта",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
```

---

## Файл: ui/views/settings_view.py

> **Назначение:** Вкладка настроек: интервал проверки, глобальная защита, мастер-пароль PIN, автозапуск, автоочистка Recent, режим тишины.

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from qfluentwidgets import (
    ScrollArea, CardWidget, SubtitleLabel, CaptionLabel, StrongBodyLabel,
    BodyLabel, SwitchButton, PushButton, PrimaryPushButton, LineEdit,
    ComboBox, TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition
)
from core.config_manager import ConfigManager
from core.autostart import set_autostart, is_autostart_enabled
from ui.dialogs.pin_dialog import PinSetDialog


class SettingsView(QWidget):
    """
    Settings tab for configuring global switch, hotkeys, PIN protection and behavior.
    """
    settings_changed = Signal()
    hotkey_updated = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setObjectName("SettingsView")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        self.titleLabel = SubtitleLabel("Параметры StealthGuard", self)
        self.descLabel = CaptionLabel("Настройка системных триггеров, защиты доступа и производительности", self)
        main_layout.addWidget(self.titleLabel)
        main_layout.addWidget(self.descLabel)

        # Scroll Area for Cards
        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(scroll_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        # 1. Global Protection Switch Card
        self.globalCard = self._create_switch_card(
            title="Глобальная защита Проводника",
            description="Включение и отключение всех правил перехвата в реальном времени",
            checked=self.config_manager.settings.global_protection_enabled,
            callback=self._on_global_switch_toggled
        )
        cards_layout.addWidget(self.globalCard)

        # 2. Recent Files Cleaner Switch Card
        self.recentCard = self._create_switch_card(
            title="Очистка недавних файлов (Recent Cleaner)",
            description="Автоматически стирать ярлыки .lnk защищенных объектов из %AppData%\\Microsoft\\Windows\\Recent",
            checked=self.config_manager.settings.clean_recent,
            callback=self._on_recent_switch_toggled
        )
        cards_layout.addWidget(self.recentCard)

        # 3. Autostart Switch Card
        self.autostartCard = self._create_switch_card(
            title="Автозапуск при старте Windows",
            description="Запуск приложения в скрытом фоновом режиме при входе в систему",
            checked=is_autostart_enabled(),
            callback=self._on_autostart_switch_toggled
        )
        cards_layout.addWidget(self.autostartCard)

        # 4. Tray Icon Card
        self.trayCard = self._create_switch_card(
            title="Иконка в системном трее",
            description="Отображать иконку в области уведомлений Windows (отключите для полной невидимости)",
            checked=self.config_manager.settings.show_tray_icon,
            callback=self._on_tray_switch_toggled
        )
        cards_layout.addWidget(self.trayCard)

        # 5. Global Hotkey Card
        self.hotkeyCard = CardWidget(scroll_widget)
        hotkey_layout = QHBoxLayout(self.hotkeyCard)
        hotkey_layout.setContentsMargins(16, 16, 16, 16)

        hotkey_info = QVBoxLayout()
        hotkey_info.addWidget(StrongBodyLabel("Глобальное сочетание клавиш вызова", self.hotkeyCard))
        hotkey_info.addWidget(CaptionLabel("Хоткей для отображения главного окна из фонового скрытого режима", self.hotkeyCard))
        hotkey_layout.addLayout(hotkey_info, 1)

        self.hotkeyInput = LineEdit(self.hotkeyCard)
        self.hotkeyInput.setText(self.config_manager.settings.hotkey)
        self.hotkeyInput.setFixedWidth(180)

        self.applyHotkeyBtn = PushButton(FluentIcon.ACCEPT, "Применить", self.hotkeyCard)
        self.applyHotkeyBtn.clicked.connect(self._apply_hotkey)

        hotkey_layout.addWidget(self.hotkeyInput)
        hotkey_layout.addWidget(self.applyHotkeyBtn)
        cards_layout.addWidget(self.hotkeyCard)

        # 5b. Protection Toggle Hotkey Card
        self.protHotkeyCard = CardWidget(scroll_widget)
        prot_layout = QHBoxLayout(self.protHotkeyCard)
        prot_layout.setContentsMargins(16, 16, 16, 16)

        prot_info = QVBoxLayout()
        prot_info.addWidget(StrongBodyLabel("Хоткей отключения / включения защиты", self.protHotkeyCard))
        prot_info.addWidget(CaptionLabel("Быстрая пауза и возобновление перехвата и скрытия без открытия окна", self.protHotkeyCard))
        prot_layout.addLayout(prot_info, 1)

        self.protHotkeyInput = LineEdit(self.protHotkeyCard)
        self.protHotkeyInput.setText(self.config_manager.settings.protection_toggle_hotkey)
        self.protHotkeyInput.setFixedWidth(180)

        self.applyProtHotkeyBtn = PushButton(FluentIcon.ACCEPT, "Применить", self.protHotkeyCard)
        self.applyProtHotkeyBtn.clicked.connect(self._apply_protection_hotkey)

        prot_layout.addWidget(self.protHotkeyInput)
        prot_layout.addWidget(self.applyProtHotkeyBtn)
        cards_layout.addWidget(self.protHotkeyCard)

        # 4. PIN Protection Card
        self.pinCard = CardWidget(scroll_widget)
        pin_layout = QHBoxLayout(self.pinCard)
        pin_layout.setContentsMargins(16, 16, 16, 16)

        pin_info = QVBoxLayout()
        pin_info.addWidget(StrongBodyLabel("Мастер-пароль / PIN-код доступа", self.pinCard))
        pin_info.addWidget(CaptionLabel("Запрашивать ввод PIN-кода при разворачивании окна из фона", self.pinCard))
        pin_layout.addLayout(pin_info, 1)

        self.setPinBtn = PushButton(FluentIcon.EDIT, "Сменить пароль", self.pinCard)
        self.setPinBtn.clicked.connect(self._open_set_pin_dialog)

        self.pinSwitch = SwitchButton(self.pinCard)
        self.pinSwitch.setChecked(self.config_manager.settings.pin_enabled)
        self.pinSwitch.checkedChanged.connect(self._on_pin_switch_toggled)

        pin_layout.addWidget(self.setPinBtn)
        pin_layout.addWidget(self.pinSwitch)
        cards_layout.addWidget(self.pinCard)

        # 5. Polling Interval Card
        self.intervalCard = CardWidget(scroll_widget)
        interval_layout = QHBoxLayout(self.intervalCard)
        interval_layout.setContentsMargins(16, 16, 16, 16)
        interval_layout.setSpacing(12)

        interval_info = QVBoxLayout()
        interval_info.addWidget(StrongBodyLabel("Частота опроса Проводника (мс)", self.intervalCard))
        interval_info.addWidget(CaptionLabel("Задержка между проверками вкладок. Рекомендуется 50–100 мс.", self.intervalCard))
        interval_layout.addLayout(interval_info, 1)

        # Controls container
        controls_container = QHBoxLayout()
        controls_container.setSpacing(8)

        # Quick Preset ComboBox
        self.intervalCombo = ComboBox(self.intervalCard)
        self.intervalCombo.addItems([
            "50 мс (Быстрый)",
            "75 мс (Рекомендуется)",
            "100 мс (Стандартный)",
            "150 мс (Экономный)",
            "200 мс (Минимум CPU)",
            "Своё значение"
        ])
        self.intervalCombo.setFixedWidth(170)
        self.intervalCombo.currentIndexChanged.connect(self._on_interval_combo_changed)
        controls_container.addWidget(self.intervalCombo)

        # Minus button
        self.minusBtn = TransparentToolButton(FluentIcon.REMOVE, self.intervalCard)
        self.minusBtn.setToolTip("Уменьшить на 10 мс")
        self.minusBtn.clicked.connect(self._step_interval_down)
        controls_container.addWidget(self.minusBtn)

        # Direct number input (clearly visible, editable)
        self.intervalInput = LineEdit(self.intervalCard)
        self.intervalInput.setFixedWidth(75)
        self.intervalInput.setAlignment(Qt.AlignCenter)
        self.intervalInput.setValidator(QIntValidator(20, 2000, self.intervalCard))
        current_val = self.config_manager.settings.check_interval_ms
        self.intervalInput.setText(str(current_val))
        self.intervalInput.textChanged.connect(self._on_interval_text_changed)
        controls_container.addWidget(self.intervalInput)

        # Plus button
        self.plusBtn = TransparentToolButton(FluentIcon.ADD, self.intervalCard)
        self.plusBtn.setToolTip("Увеличить на 10 мс")
        self.plusBtn.clicked.connect(self._step_interval_up)
        controls_container.addWidget(self.plusBtn)

        ms_lbl = CaptionLabel("мс", self.intervalCard)
        ms_lbl.setStyleSheet("color: #a0a0a0; font-weight: bold;")
        controls_container.addWidget(ms_lbl)

        interval_layout.addLayout(controls_container)
        cards_layout.addWidget(self.intervalCard)

        # Sync initial combo selection with current interval
        self._sync_combo_with_val(current_val)

        cards_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)

    def _create_switch_card(self, title: str, description: str, checked: bool, callback) -> CardWidget:
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QVBoxLayout()
        info.addWidget(StrongBodyLabel(title, card))
        info.addWidget(CaptionLabel(description, card))
        layout.addLayout(info, 1)

        switch = SwitchButton(card)
        switch.setChecked(checked)
        switch.checkedChanged.connect(callback)
        layout.addWidget(switch)
        return card

    def _on_global_switch_toggled(self, checked: bool):
        self.config_manager.settings.global_protection_enabled = checked
        self.config_manager.save()
        try:
            from core.drive_cloaker import sync_drives_from_config
            sync_drives_from_config(self.config_manager)
        except Exception:
            pass

        # Асинхронное переключение видимости папок и приманок
        def _async_sync_folders():
            try:
                from core.config_manager import sync_rules_cloaking
                sync_rules_cloaking(self.config_manager, protection_enabled=checked)
            except Exception:
                pass
        from core.config_manager import _run_async
        _run_async(_async_sync_folders)

        self.settings_changed.emit()
        status_text = "включена" if checked else "приостановлена"
        InfoBar.info(
            title="Глобальная защита",
            content=f"Защита Проводника {status_text}.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000
        )

    def _on_recent_switch_toggled(self, checked: bool):
        self.config_manager.settings.clean_recent = checked
        self.config_manager.save()
        self.settings_changed.emit()

    def _on_autostart_switch_toggled(self, checked: bool):
        self.config_manager.settings.autostart = checked
        self.config_manager.save()
        success = set_autostart(checked)
        if success:
            msg = "Автозапуск включен" if checked else "Автозапуск отключен"
            InfoBar.success(
                title="Автозапуск",
                content=msg,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )
        else:
            InfoBar.error(
                title="Ошибка",
                content="Не удалось изменить запись в реестре Windows.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )

    def _on_tray_switch_toggled(self, checked: bool):
        self.config_manager.settings.show_tray_icon = checked
        self.config_manager.save()
        win = self.window()
        if hasattr(win, "tray_icon"):
            win.tray_icon.setVisible(checked)
        self.settings_changed.emit()

    def _apply_hotkey(self):
        new_hk = self.hotkeyInput.text().strip().lower()
        if not new_hk:
            return
        self.config_manager.settings.hotkey = new_hk
        self.config_manager.save()
        self.hotkey_updated.emit()
        InfoBar.success(
            title="Горячая клавиша обновлена",
            content=f"Хоткей вызова окна: {new_hk.upper()}",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500
        )

    def _apply_protection_hotkey(self):
        new_hk = self.protHotkeyInput.text().strip().lower()
        if not new_hk:
            return
        self.config_manager.settings.protection_toggle_hotkey = new_hk
        self.config_manager.save()
        self.hotkey_updated.emit()
        InfoBar.success(
            title="Горячая клавиша обновлена",
            content=f"Хоткей отключения/включения защиты: {new_hk.upper()}",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500
        )

    def _on_pin_switch_toggled(self, checked: bool):
        if checked and not self.config_manager.settings.pin_hash:
            # Need to set PIN first
            self._open_set_pin_dialog()
            if not self.config_manager.settings.pin_hash:
                self.pinSwitch.setChecked(False)
                return

        self.config_manager.settings.pin_enabled = checked
        self.config_manager.save()
        self.settings_changed.emit()

    def _open_set_pin_dialog(self):
        dialog = PinSetDialog(self.config_manager, None)
        if dialog.exec():
            pin = dialog.get_pin()
            self.config_manager.settings.pin_hash = ConfigManager.hash_pin(pin)
            self.config_manager.settings.pin_enabled = True
            self.pinSwitch.setChecked(True)
            self.config_manager.save()
            InfoBar.success(
                title="Мастер-пароль установлен",
                content="PIN-код успешно сохранен и активирован.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2500
            )

    def _on_interval_combo_changed(self, index: int):
        presets = [50, 75, 100, 150, 200]
        if index < len(presets):
            val = presets[index]
            self.intervalInput.blockSignals(True)
            self.intervalInput.setText(str(val))
            self.intervalInput.blockSignals(False)
            self._save_interval(val)

    def _on_interval_text_changed(self, text: str):
        if text.isdigit():
            val = int(text)
            if 20 <= val <= 2000:
                self._sync_combo_with_val(val)
                self._save_interval(val)

    def _step_interval_down(self):
        cur = self._get_current_interval()
        new_val = max(20, cur - 10)
        self.intervalInput.setText(str(new_val))

    def _step_interval_up(self):
        cur = self._get_current_interval()
        new_val = min(2000, cur + 10)
        self.intervalInput.setText(str(new_val))

    def _get_current_interval(self) -> int:
        text = self.intervalInput.text()
        return int(text) if text.isdigit() else 75

    def _sync_combo_with_val(self, val: int):
        presets = {50: 0, 75: 1, 100: 2, 150: 3, 200: 4}
        idx = presets.get(val, 5)
        self.intervalCombo.blockSignals(True)
        self.intervalCombo.setCurrentIndex(idx)
        self.intervalCombo.blockSignals(False)

    def _save_interval(self, value: int):
        self.config_manager.settings.check_interval_ms = value
        self.config_manager.save()
        self.settings_changed.emit()
```

---

## Файл: ui/dialogs/pin_dialog.py

> **Назначение:** Диалоги установки и проверки PIN-кода (автономный PinVerifyDialog без родителя для разворачивания из трея).

```python
import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QMouseEvent

from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, PasswordLineEdit,
    PrimaryPushButton, PushButton, FluentIcon
)
from core.config_manager import ConfigManager


class PinVerifyDialog(QDialog):
    """
    Standalone top-level Fluent modal dialog to verify user PIN before
    restoring StealthGuard from hidden background mode.
    Works independently of whether the main window is visible or hidden.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        # Independent topmost frameless window
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self._drag_pos = QPoint()
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(400, 260)

        # Outer layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Inner container card with shadow and dark Fluent style
        self.card = QFrame(self)
        self.card.setObjectName("dialogCard")
        self.card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #202020;
                border: 1px solid #383838;
                border-radius: 12px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.iconLabel = QLabel(self.card)
        self.iconLabel.setPixmap(FluentIcon.FINGERPRINT.icon().pixmap(28, 28))
        header_layout.addWidget(self.iconLabel)

        self.titleLabel = SubtitleLabel("StealthGuard Доступ", self.card)
        header_layout.addWidget(self.titleLabel, 1)
        card_layout.addLayout(header_layout)

        self.captionLabel = CaptionLabel("Введите PIN-код или пароль для разблокировки окна:", self.card)
        self.captionLabel.setStyleSheet("color: #a0a0a0;")
        card_layout.addWidget(self.captionLabel)

        # Password input
        self.pinInput = PasswordLineEdit(self.card)
        self.pinInput.setPlaceholderText("PIN-код / Пароль")
        self.pinInput.setClearButtonEnabled(True)
        self.pinInput.returnPressed.connect(self._handle_submit)
        card_layout.addWidget(self.pinInput)

        # Error label (hidden by default)
        self.errorLabel = CaptionLabel("", self.card)
        self.errorLabel.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.errorLabel.hide()
        card_layout.addWidget(self.errorLabel)

        card_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancelBtn = PushButton("Отмена", self.card)
        self.cancelBtn.setFixedWidth(100)
        self.cancelBtn.clicked.connect(self.reject)

        self.loginBtn = PrimaryPushButton("Войти", self.card)
        self.loginBtn.setFixedWidth(110)
        self.loginBtn.clicked.connect(self._handle_submit)

        btn_layout.addWidget(self.cancelBtn)
        btn_layout.addWidget(self.loginBtn)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        # Center dialog on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Auto-focus input
        self.pinInput.setFocus()
        self.pinInput.clear()
        self.errorLabel.hide()

        # Bring window to foreground
        self.raise_()
        self.activateWindow()
        try:
            import win32gui
            win32gui.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def _handle_submit(self):
        pin = self.pinInput.text()
        if self.config_manager.verify_pin(pin):
            self.errorLabel.hide()
            self.accept()
        else:
            self.errorLabel.setText("❌ Неверный PIN-код или пароль")
            self.errorLabel.show()
            self.pinInput.selectAll()
            self.pinInput.setFocus()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class PinSetDialog(QDialog):
    """
    Standalone Fluent dialog to set or change the master PIN.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._drag_pos = QPoint()
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(420, 310)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.card = QFrame(self)
        self.card.setObjectName("dialogCard")
        self.card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #202020;
                border: 1px solid #383838;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        icon_label = QLabel(self.card)
        icon_label.setPixmap(FluentIcon.FINGERPRINT.icon().pixmap(28, 28))
        header_layout.addWidget(icon_label)

        title = SubtitleLabel("Установка мастер-пароля", self.card)
        header_layout.addWidget(title, 1)
        card_layout.addLayout(header_layout)

        desc = CaptionLabel("Задайте PIN-код или пароль для скрытого вызова:", self.card)
        desc.setStyleSheet("color: #a0a0a0;")
        card_layout.addWidget(desc)

        self.pinInput = PasswordLineEdit(self.card)
        self.pinInput.setPlaceholderText("Новый PIN-код / Пароль")
        self.pinInput.setClearButtonEnabled(True)
        card_layout.addWidget(self.pinInput)

        self.confirmInput = PasswordLineEdit(self.card)
        self.confirmInput.setPlaceholderText("Повторите PIN-код / Пароль")
        self.confirmInput.setClearButtonEnabled(True)
        self.confirmInput.returnPressed.connect(self._handle_submit)
        card_layout.addWidget(self.confirmInput)

        self.errorLabel = CaptionLabel("", self.card)
        self.errorLabel.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.errorLabel.hide()
        card_layout.addWidget(self.errorLabel)

        card_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancelBtn = PushButton("Отмена", self.card)
        self.cancelBtn.setFixedWidth(100)
        self.cancelBtn.clicked.connect(self.reject)

        self.saveBtn = PrimaryPushButton("Сохранить", self.card)
        self.saveBtn.setFixedWidth(110)
        self.saveBtn.clicked.connect(self._handle_submit)

        btn_layout.addWidget(self.cancelBtn)
        btn_layout.addWidget(self.saveBtn)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.pinInput.setFocus()
        self.pinInput.clear()
        self.confirmInput.clear()
        self.errorLabel.hide()

    def get_pin(self) -> str:
        return self.pinInput.text()

    def _handle_submit(self):
        p1 = self.pinInput.text()
        p2 = self.confirmInput.text()
        if not p1:
            self.errorLabel.setText("❌ Пароль не может быть пустым")
            self.errorLabel.show()
            return
        if p1 != p2:
            self.errorLabel.setText("❌ Пароли не совпадают")
            self.errorLabel.show()
            return
        self.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
```

---

## Файл: build_portable.py

> **Назначение:** Скрипт сборки автономного переносимого пакета StealthGuard через PyInstaller с изолированным каталогом dist_build и безопасным обновлением locked DLL.

```python
import os
import sys
import shutil
import subprocess

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    print("[StealthGuard Portable Builder] Starting build process...")

    portable_folder = os.path.join(dist_dir, "StealthGuard")
    dst_config = os.path.join(portable_folder, "config.json")
    saved_config_content = None
    if os.path.exists(dst_config):
        try:
            with open(dst_config, "r", encoding="utf-8") as f:
                saved_config_content = f.read()
            print("[StealthGuard Portable Builder] Backed up existing portable config.json")
        except Exception as e:
            print(f"[StealthGuard Portable Builder] Warning: failed to backup existing config: {e}")

    dist_build_dir = os.path.join(base_dir, "dist_build")

    # PyInstaller arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=StealthGuard",
        "--noconsole",
        "--onedir",
        "--distpath=" + dist_build_dir,
        "--clean",
        "-y",
        "--collect-all=qfluentwidgets",
        "--collect-all=pysidesix_frameless_window",
        "--hidden-import=pywintypes",
        "--hidden-import=win32com",
        "--hidden-import=win32com.client",
        "--hidden-import=pythoncom",
        "--hidden-import=win32gui",
        "--hidden-import=win32process",
        "--hidden-import=win32con",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=ctypes.wintypes",
        "--hidden-import=psutil",
        os.path.join(base_dir, "main.py")
    ]

    print("[StealthGuard Portable Builder] Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=base_dir)

    if res.returncode != 0:
        print("[StealthGuard Portable Builder] ERROR: Build failed with code", res.returncode)
        sys.exit(res.returncode)

    built_folder = os.path.join(dist_build_dir, "StealthGuard")
    portable_folder = os.path.join(dist_dir, "StealthGuard")
    os.makedirs(portable_folder, exist_ok=True)

    # Safe copy files from built_folder into portable_folder
    for root, dirs, files in os.walk(built_folder):
        rel = os.path.relpath(root, built_folder)
        dest_root = os.path.join(portable_folder, rel)
        os.makedirs(dest_root, exist_ok=True)
        for f in files:
            src_f = os.path.join(root, f)
            dest_f = os.path.join(dest_root, f)
            try:
                shutil.copy2(src_f, dest_f)
            except Exception:
                pass

    # Restore saved config or copy default
    src_config = os.path.join(base_dir, "config.json")
    dst_config = os.path.join(portable_folder, "config.json")
    if saved_config_content:
        try:
            with open(dst_config, "w", encoding="utf-8") as f:
                f.write(saved_config_content)
            print(f"[StealthGuard Portable Builder] Restored previous config.json in {portable_folder}")
        except Exception as e:
            print(f"[StealthGuard Portable Builder] Failed to restore config: {e}")
    elif os.path.exists(src_config) and not os.path.exists(dst_config):
        shutil.copy2(src_config, dst_config)
        print(f"[StealthGuard Portable Builder] Copied default config.json to {portable_folder}")

    # Copy run scripts into portable folder
    run_bat_content = '@echo off\nstart "" "%~dp0StealthGuard.exe" %*\n'
    with open(os.path.join(portable_folder, "run.bat"), "w", encoding="utf-8") as f:
        f.write(run_bat_content)

    run_stealth_bat_content = '@echo off\nstart "" "%~dp0StealthGuard.exe" --stealth %*\n'
    with open(os.path.join(portable_folder, "run_stealth.bat"), "w", encoding="utf-8") as f:
        f.write(run_stealth_bat_content)

    # Copy emergency_restore.bat if exists
    src_emergency = os.path.join(base_dir, "emergency_restore.bat")
    if os.path.exists(src_emergency):
        shutil.copy2(src_emergency, os.path.join(portable_folder, "emergency_restore.bat"))
        print(f"[StealthGuard Portable Builder] Copied emergency_restore.bat to {portable_folder}")

    print("\n" + "="*60)
    print("SUCCESS! Portable StealthGuard is ready in:")
    print(portable_folder)
    print("="*60)

if __name__ == "__main__":
    build()
```

---

## Файл: tests/test_components.py

> **Назначение:** Комплексный набор из 12 автоматических тестов для всех ключевых подсистем проекта (хоткеи, PBKDF2 PIN + миграция, перехватчик, Total Cloaking, омоглифы, удаление, автозапуск, Drive Cloaker, search-ms парсинг, stealth policies, UI).

```python
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.config_manager import ConfigManager, Rule
from core.recent_cleaner import RecentCleaner
from core.interceptor import ExplorerInterceptor
from core.hotkey_manager import GlobalHotkeyManager, normalize_hotkey_for_pynput
from core.utils import url_to_path, normalize_path, is_path_matching
from ui.main_window import MainWindow


def test_full_pipeline():
    # 1. Hotkey normalization
    hk_list = normalize_hotkey_for_pynput("Ctrl + Shift + Alt + L")
    assert any("<ctrl>" in hk and "<shift>" in hk and "<alt>" in hk and "l" in hk for hk in hk_list)
    prot_hk_list = normalize_hotkey_for_pynput("Ctrl + Shift + Alt + P")
    assert any("<ctrl>" in hk and "<shift>" in hk and "<alt>" in hk and "p" in hk for hk in prot_hk_list)
    assert any("з" in hk for hk in prot_hk_list)
    print("[PASS] Hotkey normalization passed")

    # 2. Config manager & PIN
    test_cfg_path = os.path.join(os.path.dirname(__file__), "pipeline_test_config.json")
    if os.path.exists(test_cfg_path):
        os.remove(test_cfg_path)

    cm = ConfigManager(config_path=test_cfg_path)
    pin_hash = ConfigManager.hash_pin("1234")
    assert pin_hash.startswith("pbkdf2_sha256$")
    cm.settings.pin_hash = pin_hash
    cm.settings.pin_enabled = True
    assert cm.verify_pin("1234") is True
    assert cm.verify_pin("wrong") is False

    # Test legacy SHA-256 auto-migration
    import hashlib
    legacy_sha256 = hashlib.sha256("5678".encode("utf-8")).hexdigest()
    cm.settings.pin_hash = legacy_sha256
    assert cm.verify_pin("5678") is True
    # Verify it automatically migrated to pbkdf2 format!
    assert cm.settings.pin_hash.startswith("pbkdf2_sha256$")
    assert cm.verify_pin("5678") is True
    assert cm.verify_pin("wrong") is False
    # Restore pin_hash to "1234" for subsequent UI dialog tests
    cm.settings.pin_hash = pin_hash
    print("[PASS] PIN PBKDF2-HMAC-SHA256 & Legacy Migration passed")

    # 3. Interceptor setup
    cleaner = RecentCleaner(cm)
    interceptor = ExplorerInterceptor(cm, cleaner)
    assert hasattr(interceptor, "intercepted")
    assert hasattr(interceptor, "status_changed")
    print("[PASS] Interceptor initialization passed")

    # 3a. File Cloaker test
    from core.file_cloaker import cloak_folder, uncloak_folder, cloak_file, uncloak_file, FILE_ATTRIBUTE_SYSTEM, FILE_ATTRIBUTE_HIDDEN
    import ctypes
    test_folder = os.path.join(os.path.dirname(__file__), "cloaker_test_dir")
    os.makedirs(test_folder, exist_ok=True)
    img_file = os.path.join(test_folder, "photo.png")
    doc_file = os.path.join(test_folder, "notes.txt")
    with open(img_file, "w") as f: f.write("img")
    with open(doc_file, "w") as f: f.write("doc")

    # Cloak folder with Total Cloaking (all_files=True)
    cloaked = cloak_folder(test_folder, all_files=True)
    assert cloaked == 2  # Both photo.png and notes.txt!
    attrs = ctypes.windll.kernel32.GetFileAttributesW(img_file)
    assert attrs & FILE_ATTRIBUTE_SYSTEM and attrs & FILE_ATTRIBUTE_HIDDEN
    doc_attrs = ctypes.windll.kernel32.GetFileAttributesW(doc_file)
    assert doc_attrs & FILE_ATTRIBUTE_SYSTEM and doc_attrs & FILE_ATTRIBUTE_HIDDEN

    # Cloak directory test
    from core.file_cloaker import cloak_directory, uncloak_directory
    assert cloak_directory(test_folder) is True
    folder_attrs = ctypes.windll.kernel32.GetFileAttributesW(test_folder)
    assert folder_attrs & FILE_ATTRIBUTE_SYSTEM and folder_attrs & FILE_ATTRIBUTE_HIDDEN

    # Uncloak folder
    uncloaked = uncloak_folder(test_folder, all_files=True)
    assert uncloaked == 2
    attrs_after = ctypes.windll.kernel32.GetFileAttributesW(img_file)
    assert not (attrs_after & FILE_ATTRIBUTE_SYSTEM)
    doc_attrs_after = ctypes.windll.kernel32.GetFileAttributesW(doc_file)
    assert not (doc_attrs_after & FILE_ATTRIBUTE_SYSTEM)
    uncloak_directory(test_folder)

    # Clean up test folder
    os.remove(img_file)
    os.remove(doc_file)
    os.rmdir(test_folder)
    print("[PASS] File & Directory Cloaker (System + Hidden) verified")

    # 3b. Decoy Generator test (Visual Homoglyph Clone + Auto-Cloak + Auto-Deletion)
    from core.decoy_generator import get_clone_candidates, create_visual_clone_decoy, is_visual_clone, delete_decoy_folder
    # Test candidate generation
    ru_candidates = get_clone_candidates("Секреты")
    assert len(ru_candidates) > 0
    assert ru_candidates[0] != "Секреты"

    # Test actual folder creation with automatic cloaking
    dummy_target = os.path.join(os.path.dirname(__file__), "ТестоваяПапка")
    os.makedirs(dummy_target, exist_ok=True)
    success, clone_path, msg = create_visual_clone_decoy(dummy_target, create_on_disk=True)
    assert success is True
    assert clone_path != dummy_target
    assert os.path.exists(clone_path)
    clone_attrs = ctypes.windll.kernel32.GetFileAttributesW(clone_path)
    assert clone_attrs & FILE_ATTRIBUTE_SYSTEM and clone_attrs & FILE_ATTRIBUTE_HIDDEN
    assert os.path.basename(clone_path) != os.path.basename(dummy_target)

    # Test clone detection
    assert is_visual_clone(dummy_target, clone_path) is True
    assert is_visual_clone(dummy_target, "C:\\DifferentPath\\Clone") is False

    # Test safe deletion of cloaked decoy folder
    assert delete_decoy_folder(clone_path) is True
    assert not os.path.exists(clone_path)
    os.rmdir(dummy_target)
    print("[PASS] Decoy Generator (Visual Clone + Auto-Cloaking + Deletion) verified")

    # Test ConfigManager remove_rule auto-deleting decoy
    dummy_target2 = os.path.join(os.path.dirname(__file__), "AutoDelTarget")
    os.makedirs(dummy_target2, exist_ok=True)
    _, dummy_decoy2, _ = create_visual_clone_decoy(dummy_target2, create_on_disk=True)
    rule_to_del = Rule(name="DelTest", target_path=dummy_target2, mode="decoy", decoy_path=dummy_decoy2, auto_decoy=True)
    cm.add_rule(rule_to_del)
    assert os.path.exists(dummy_decoy2)
    cm.remove_rule(rule_to_del.id)
    # Wait for async background cleanup thread to complete deletion
    import time
    for _ in range(40):
        if not os.path.exists(dummy_decoy2):
            break
        time.sleep(0.05)
    assert not os.path.exists(dummy_decoy2)
    os.rmdir(dummy_target2)
    print("[PASS] ConfigManager remove_rule decoy cleanup verified")

    # 3c. Autostart Dual-Registration test
    from core.autostart import set_autostart, is_autostart_enabled, get_startup_shortcut_path
    assert set_autostart(True) is True
    assert is_autostart_enabled() is True
    sc_path = get_startup_shortcut_path()
    assert os.path.exists(sc_path)
    assert set_autostart(False) is True
    assert not os.path.exists(sc_path)
    print("[PASS] Dual Autostart (Startup shortcut + Registry) verified")

    # 3d. Drive Cloaker and Virtual Decoy Drive test
    from core.drive_cloaker import (
        is_drive_root, get_drive_letter, get_free_drive_letter,
        mount_virtual_decoy_drive, unmount_virtual_decoy_drive,
        apply_hidden_drives, query_dos_device_target
    )
    assert is_drive_root("Y:\\") is True
    assert is_drive_root("Y:") is True
    assert is_drive_root("C:\\Windows") is False
    assert get_drive_letter("Y:\\") == "Y"
    free_l = get_free_drive_letter()
    assert free_l is not None

    # Test mount & unmount virtual decoy drive
    ok, decoy_root, _ = mount_virtual_decoy_drive("Y")
    assert ok is True
    decoy_l = get_drive_letter(decoy_root)
    assert query_dos_device_target(decoy_l) is not None
    assert unmount_virtual_decoy_drive(decoy_root, delete_backing=True) is True
    assert query_dos_device_target(decoy_l) is None

    # Test decoy generator drive wrapper
    ok_wrap, decoy_wrap, _ = create_visual_clone_decoy("Y:\\")
    assert ok_wrap is True
    assert is_visual_clone("Y:\\", decoy_wrap) is True
    assert is_visual_clone("Y:\\", "Y:\\") is False
    assert delete_decoy_folder(decoy_wrap) is True

    # Test NoDrives mask apply and clean
    apply_hidden_drives({"Y", "W"})
    apply_hidden_drives(set())
    print("[PASS] Drive Cloaker (Virtual Decoy Drive + NoDrives + SHChangeNotify) verified")

    # 3e. Search-ms protocol URL parsing & Stealth Policy test
    from core.file_cloaker import enforce_explorer_stealth_policies

    # Test enforce_explorer_stealth_policies runs safely
    stealth_res = enforce_explorer_stealth_policies()
    assert isinstance(stealth_res, bool)

    # Test search-ms URL with location scope
    search_url_location = (
        "search-ms:displayname=Search%20Results%20in%20Secret"
        "&crumb=location:C%3A%5CUsers%5CUser%5CDocuments%5CSecret"
    )
    parsed_location = url_to_path(search_url_location, location_name="Search Results in Secret")
    assert parsed_location.startswith("search-ms://")
    assert "c:\\users\\user\\documents\\secret" in parsed_location.lower()
    assert is_path_matching(parsed_location, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_location, "C:\\Users\\User\\Documents\\OtherFolder") is False

    # Test search-ms URL inside protected subfolder
    search_url_sub = (
        "search-ms:displayname=Search%20Results"
        "&crumb=location:C%3A%5CUsers%5CUser%5CDocuments%5CSecret%5CDeepSubFolder"
    )
    parsed_sub = url_to_path(search_url_sub, location_name="Search Results")
    assert is_path_matching(parsed_sub, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_sub, "C:\\Users\\User\\Documents\\Secret2") is False

    # Test search-ms URL query by keyword matching folder name
    search_url_keyword = "search-ms:displayname=Search%20Results&crumb=Secret"
    parsed_kw = url_to_path(search_url_keyword, location_name="Search Results")
    assert is_path_matching(parsed_kw, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_kw, "C:\\Users\\User\\Documents\\Photos") is False

    # Test classic file:// URLs remain fully functional
    file_url = "file:///C:/Users/User/Secret%20Folder"
    parsed_file = url_to_path(file_url)
    assert os.path.normcase(parsed_file) == os.path.normcase("C:\\Users\\User\\Secret Folder")
    assert is_path_matching(parsed_file, "C:\\Users\\User\\Secret Folder") is True
    assert is_path_matching(parsed_file, "C:\\Users\\User\\Secret Folder\\Sub") is False
    assert is_path_matching("C:\\Users\\User\\Secret Folder\\Sub\\file.txt", "C:\\Users\\User\\Secret Folder") is True
    print("[PASS] Search-ms URL parsing, path matching & stealth policies verified")

    # 3f. PROTECTED_ITEM_NAMES & Deep Search Interception by File Name test
    from core.file_cloaker import get_protected_item_names, clear_protected_item_names
    test_search_dir = os.path.join(os.path.dirname(__file__), "deep_search_test_dir")
    os.makedirs(test_search_dir, exist_ok=True)
    deep_file = os.path.join(test_search_dir, "nda_contract_2026.pdf")
    with open(deep_file, "w") as f:
        f.write("confidential")

    # Cloak folder and verify names added to PROTECTED_ITEM_NAMES
    cloak_folder(test_search_dir, all_files=True)
    prot_names = get_protected_item_names()
    assert "nda_contract_2026.pdf" in prot_names
    assert "nda_contract_2026" in prot_names

    # Test search query executed from drive root matching file name token
    root_search_url = (
        "search-ms:displayname=Search%20Results%20in%20Local%20Disk%20(C:)"
        "&crumb=location:C%3A%5C&crumb=nda_contract_2026"
    )
    parsed_root = url_to_path(root_search_url, location_name="Search Results in Local Disk (C:)")
    assert is_path_matching(parsed_root, test_search_dir) is True

    # Test search query with unrelated file token does not match
    unrelated_search_url = (
        "search-ms:displayname=Search%20Results%20in%20Local%20Disk%20(C:)"
        "&crumb=location:C%3A%5C&crumb=unrelated_vacation_photos"
    )
    parsed_unrelated = url_to_path(unrelated_search_url, location_name="Search Results in Local Disk (C:)")
    assert is_path_matching(parsed_unrelated, test_search_dir) is False

    # Uncloak and verify removal from index
    uncloak_folder(test_search_dir, all_files=True)
    prot_names_after = get_protected_item_names()
    assert "nda_contract_2026.pdf" not in prot_names_after
    os.remove(deep_file)
    os.rmdir(test_search_dir)
    print("[PASS] PROTECTED_ITEM_NAMES cache & Root Search Interception verified")

    # 3g. Smart Visibility Inversion for Visual Clone Decoys test
    from core.config_manager import sync_rules_cloaking
    from core.decoy_generator import create_visual_clone_decoy
    inversion_base = os.path.join(os.path.dirname(__file__), "inversion_test_base")
    os.makedirs(inversion_base, exist_ok=True)
    real_target = os.path.join(inversion_base, "СекретныеДокументы")
    os.makedirs(real_target, exist_ok=True)
    _, decoy_clone, _ = create_visual_clone_decoy(real_target, create_on_disk=True)

    inversion_rule = Rule(
        name="SmartInversionRule",
        target_path=real_target,
        mode="decoy",
        decoy_path=decoy_clone,
        enabled=True
    )
    cm.add_rule(inversion_rule)

    # 1) Protection ENABLED: Target is HIDDEN, Decoy Clone is VISIBLE
    sync_rules_cloaking(cm, protection_enabled=True)
    target_attrs_on = ctypes.windll.kernel32.GetFileAttributesW(real_target)
    decoy_attrs_on = ctypes.windll.kernel32.GetFileAttributesW(decoy_clone)
    assert (target_attrs_on & FILE_ATTRIBUTE_HIDDEN) and (target_attrs_on & FILE_ATTRIBUTE_SYSTEM)
    assert not (decoy_attrs_on & FILE_ATTRIBUTE_HIDDEN)

    # 2) Protection DISABLED (Pause): Target is VISIBLE, Decoy Clone is HIDDEN
    sync_rules_cloaking(cm, protection_enabled=False)
    target_attrs_off = ctypes.windll.kernel32.GetFileAttributesW(real_target)
    decoy_attrs_off = ctypes.windll.kernel32.GetFileAttributesW(decoy_clone)
    assert not (target_attrs_off & FILE_ATTRIBUTE_HIDDEN)
    assert (decoy_attrs_off & FILE_ATTRIBUTE_HIDDEN) and (decoy_attrs_off & FILE_ATTRIBUTE_SYSTEM)

    # Clean up inversion test
    cm.remove_rule(inversion_rule.id)
    time.sleep(0.1)
    if os.path.exists(decoy_clone):
        delete_decoy_folder(decoy_clone)
    if os.path.exists(real_target):
        os.rmdir(real_target)
    if os.path.exists(inversion_base):
        os.rmdir(inversion_base)
    print("[PASS] Smart Visibility Inversion (Protection ON/OFF) verified")

    # 3h. EverythingCloaker patch_everything_ini_flags test
    from core.everything_cloaker import patch_everything_ini_flags
    test_everything_ini = os.path.join(os.path.dirname(__file__), "test_Everything.ini")
    with open(test_everything_ini, "w", encoding="utf-8") as f:
        f.write("; Everything configuration stub\n"
                "window_x=120\n"
                "window_y=80\n"
                "exclude_hidden_files_and_folders=0\n"
                "exclude_system_files_and_folders=0\n")

    # 1) Switch to 1 (Protection ENABLED: hide system & hidden objects)
    switched_on = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True)
    assert switched_on is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_on = f.read()
    assert "exclude_hidden_files_and_folders=1" in content_on
    assert "exclude_system_files_and_folders=1" in content_on

    # 2) Idempotent call (already 1 -> returns False)
    assert patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True) is False

    # 3) Switch back to 0 (Protection DISABLED: allow system & hidden objects)
    switched_off = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=False)
    assert switched_off is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_off = f.read()
    assert "exclude_hidden_files_and_folders=0" in content_off
    assert "exclude_system_files_and_folders=0" in content_off

    # 4) Idempotent call (already 0 -> returns False)
    assert patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=False) is False

    # 5) Missing keys append test
    with open(test_everything_ini, "w", encoding="utf-8") as f:
        f.write("window_x=200\n")
    appended = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True)
    assert appended is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_appended = f.read()
    assert "exclude_hidden_files_and_folders=1" in content_appended
    assert "exclude_system_files_and_folders=1" in content_appended

    # Clean up test ini file
    if os.path.exists(test_everything_ini):
        os.remove(test_everything_ini)
    print("[PASS] Everything.ini flags patch (exclude_hidden & exclude_system) verified")

    # 4. Qt App and Main Window UI verification
    app = QApplication.instance() or QApplication(sys.argv)

    # 3b. Test PinVerifyDialog standalone with hidden/none parent
    from ui.dialogs.pin_dialog import PinVerifyDialog
    dialog = PinVerifyDialog(cm, None)
    assert dialog.parent() is None
    dialog.pinInput.setText("wrong")
    dialog._handle_submit()
    assert not dialog.errorLabel.isHidden()
    dialog.pinInput.setText("1234")
    dialog._handle_submit()
    assert dialog.result() == 1  # Accepted!
    print("[PASS] Standalone PinVerifyDialog verified")

    hk_manager = GlobalHotkeyManager(cm.settings.hotkey)
    window = MainWindow(cm, interceptor, hk_manager)

    assert window.windowTitle().startswith("StealthGuard")
    assert window.rules_view is not None
    assert window.logs_view is not None
    assert window.settings_view is not None

    # Test adding a log entry
    sample_event = {
        "timestamp": "2026-10-31 12:00:00",
        "rule_name": "Test Rule",
        "target_path": "Y:\\Secret",
        "mode": "Подмена (Decoy)",
        "decoy_path": "C:\\Users\\Public\\Documents",
        "hwnd": 12345
    }
    window.logs_view.add_log_entry(sample_event)
    assert window.logs_view.table.rowCount() == 1
    assert window.logs_view.table.item(0, 1).text() == "Test Rule"
    print("[PASS] LogsView UI integration passed")

    # Test RulesView auto-clone button logic
    assert hasattr(window.rules_view, "autoCloneBtn")
    dummy_ui_target = os.path.join(os.path.dirname(__file__), "UI_Clone_Target")
    os.makedirs(dummy_ui_target, exist_ok=True)
    window.rules_view.targetInput.setText(dummy_ui_target)
    window.rules_view._create_auto_clone_decoy()
    created_decoy = window.rules_view.decoyInput.text()
    assert os.path.exists(created_decoy)
    assert created_decoy != dummy_ui_target
    os.rmdir(created_decoy)
    os.rmdir(dummy_ui_target)
    print("[PASS] RulesView Auto-Clone UI action passed")

    # Test protection toggle hotkey handler
    assert cm.settings.global_protection_enabled is True
    window.on_toggle_protection_hotkey()
    assert cm.settings.global_protection_enabled is False
    window.on_toggle_protection_hotkey()
    assert cm.settings.global_protection_enabled is True
    print("[PASS] Global Protection Toggle hotkey action passed")

    # Clean up
    window.close()
    if os.path.exists(test_cfg_path):
        os.remove(test_cfg_path)

    print("[PASS] All pipeline components validated successfully!")


if __name__ == "__main__":
    test_full_pipeline()
```

---

## Файл: emergency_restore.bat

> **Назначение:** Автономный батник аварийного восстановления Проводника: сброс NoDrives, размонтирование виртуальных дисков subst, снятие атрибутов System/Hidden и перезапуск Shell.

```batch
@echo off
chcp 65001 >nul
title StealthGuard — Аварийное восстановление видимости
echo ========================================================
echo   StealthGuard — Аварийное восстановление видимости
echo ========================================================
echo.

:: 1. Сброс маски скрытия дисков в реестре
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDrives /f >nul 2>nul
echo [OK] Маска скрытия дисков (NoDrives) успешно удалена из реестра.

:: 2. Восстановление боковой панели навигации Проводника
reg add "HKCU\Software\Classes\CLSID\{F5FB2C77-0E2F-4A16-A381-3E560C68BC83}" /v "System.IsPinnedToNameSpaceTree" /t REG_DWORD /d 1 /f >nul 2>nul
echo [OK] Отображение дисков в боковой панели навигации Проводника включено.

:: 3. Размонтирование возможных виртуальных дисков-приманок
for %%D in (W V U T S R Q P O N M L K J I H G F E D) do (
    subst %%D: /d >nul 2>nul
)
echo [OK] Виртуальные диски-приманки (subst) отмонтированы.

echo.
:: 4. Восстановление атрибутов файлов
set /p TARGET_PATH="Введите путь к защищавшейся папке или диску для возврата видимости (например, Y:\Secret или Y:\) или нажмите Enter для пропуска: "
if not "%TARGET_PATH%"=="" (
    echo Снятие атрибутов System и Hidden с %TARGET_PATH%...
    attrib -s -h "%TARGET_PATH%" >nul 2>nul
    attrib -s -h "%TARGET_PATH%\*" /s /d >nul 2>nul
    echo [OK] Атрибуты видимости файлов и папок восстановлены.
)

echo.
:: 5. Перезапуск Проводника Windows для применения изменений
echo Перезапуск Проводника Windows...
taskkill /f /im explorer.exe >nul 2>nul
timeout /t 1 /nobreak >nul
start explorer.exe
echo.
echo ========================================================
echo [ГОТОВО] Все настройки проводника и видимость восстановлены!
echo ========================================================
echo.
pause
```

---

## Файл: config.json

> **Назначение:** Конфигурационный файл приложения (настройки и правила по умолчанию).

```json
{
  "settings": {
    "global_protection_enabled": true,
    "hotkey": "ctrl+shift+alt+l",
    "protection_toggle_hotkey": "ctrl+shift+alt+p",
    "pin_enabled": false,
    "pin_hash": "",
    "autostart": true,
    "clean_recent": true,
    "check_interval_ms": 35,
    "stealth_startup": false,
    "show_tray_icon": true
  },
  "rules": []
}
```

---

## Файл: run.bat

> **Назначение:** Скрипт запуска приложения в обычном режиме GUI.

```batch
@echo off
setlocal
cd /d "%~dp0"

:: 1. Check if compiled standalone portable exe exists
if exist "%~dp0dist\StealthGuard\StealthGuard.exe" (
    start "" "%~dp0dist\StealthGuard\StealthGuard.exe" %*
    exit /b 0
)
if exist "%~dp0StealthGuard.exe" (
    start "" "%~dp0StealthGuard.exe" %*
    exit /b 0
)

:: 2. Fallback to Python
set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    )
)

start "" "%PYTHON_EXE%" "%~dp0main.py" %*
```

---

## Файл: run_stealth.bat

> **Назначение:** Скрипт запуска приложения в скрытом фоновом режиме без отображения окна.

```batch
@echo off
setlocal
cd /d "%~dp0"

:: 1. Check if compiled standalone portable exe exists
if exist "%~dp0dist\StealthGuard\StealthGuard.exe" (
    start "" "%~dp0dist\StealthGuard\StealthGuard.exe" --stealth %*
    exit /b 0
)
if exist "%~dp0StealthGuard.exe" (
    start "" "%~dp0StealthGuard.exe" --stealth %*
    exit /b 0
)

:: 2. Fallback to Pythonw (windowless)
set "PYTHONW_EXE=pythonw"
where pythonw >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
        set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    )
)

start "" "%PYTHONW_EXE%" "%~dp0main.py" --stealth %*
```

---

## Файл: requirements.txt

> **Назначение:** Зависимости проекта Python.

```text
PySide6>=6.5.0
PySide6-Fluent-Widgets>=1.5.0
pywin32>=306
psutil>=5.9.0
pynput>=1.7.6
```

---
