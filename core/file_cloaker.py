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
