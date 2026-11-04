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
