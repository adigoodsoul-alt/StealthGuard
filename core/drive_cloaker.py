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
