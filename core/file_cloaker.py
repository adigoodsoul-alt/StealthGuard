import os
import sys
import json
import threading
import ctypes
from ctypes import wintypes
import winreg
from typing import Set, Dict, Optional

kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32

_PROTECTED_NAMES_LOCK = threading.Lock()
PROTECTED_ITEM_NAMES: Set[str] = set()

_CACHE_LOCK = threading.Lock()
_ORIGINAL_ATTRIBUTES: Dict[str, int] = {}
_CLOAKED_FOLDERS: Set[str] = set()


def _get_system_cache_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "system_attributes_cache.json")


def _load_system_attributes_cache():
    global _ORIGINAL_ATTRIBUTES, _CLOAKED_FOLDERS
    cache_path = _get_system_cache_path()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with _CACHE_LOCK:
                _ORIGINAL_ATTRIBUTES = {
                    os.path.normcase(k): int(v)
                    for k, v in data.get("attributes", {}).items()
                }
                _CLOAKED_FOLDERS = {
                    os.path.normcase(p)
                    for p in data.get("cloaked_folders", [])
                }
        except Exception:
            pass


def _save_system_attributes_cache():
    cache_path = _get_system_cache_path()
    try:
        with _CACHE_LOCK:
            data = {
                "attributes": dict(_ORIGINAL_ATTRIBUTES),
                "cloaked_folders": list(_CLOAKED_FOLDERS)
            }
        temp_path = cache_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(cache_path):
            os.replace(temp_path, cache_path)
        else:
            os.rename(temp_path, cache_path)
    except Exception:
        pass


def get_recorded_original_attributes() -> Dict[str, int]:
    """Возвращает копию словаря оригинальных системных/скрытых атрибутов файлов."""
    with _CACHE_LOCK:
        return dict(_ORIGINAL_ATTRIBUTES)


def clear_system_attributes_cache():
    """Очищает кэш оригинальных атрибутов и удаляет файл кэша."""
    global _ORIGINAL_ATTRIBUTES, _CLOAKED_FOLDERS
    with _CACHE_LOCK:
        _ORIGINAL_ATTRIBUTES.clear()
        _CLOAKED_FOLDERS.clear()
    cache_path = _get_system_cache_path()
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass


_load_system_attributes_cache()


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
    Восстанавливает видимость файла, не снимая оригинальные системные и скрытые атрибуты,
    если файл изначально был системным или скрытым до наложения защиты.
    """
    try:
        if is_protected_system_item(os.path.basename(file_path)):
            return False

        attrs = kernel32.GetFileAttributesW(file_path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False

        norm_p = os.path.normcase(os.path.normpath(file_path))
        with _CACHE_LOCK:
            orig_flags = _ORIGINAL_ATTRIBUTES.get(norm_p, 0)

        remove_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        new_attrs = (attrs & ~remove_flags) | orig_flags
        if new_attrs == attrs:
            return True

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
    Фиксирует исходные системные и скрытые атрибуты файлов для их сохранения при снятии защиты.
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
    base_norm = os.path.normcase(base_path)
    names_to_add: Set[str] = set()

    with _CACHE_LOCK:
        was_already_cloaked = base_norm in _CLOAKED_FOLDERS

    # Если папка ещё не находилась в состоянии скрытия, фиксируем исходные атрибуты файлов и подпапок
    if not was_already_cloaked:
        try:
            if not _is_drive_root_path(base_norm):
                d_attrs = kernel32.GetFileAttributesW(base_norm)
                if d_attrs != INVALID_FILE_ATTRIBUTES:
                    orig_d = d_attrs & (FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
                    if orig_d:
                        with _CACHE_LOCK:
                            _ORIGINAL_ATTRIBUTES[base_norm] = orig_d

            for root, dirs, files in os.walk(base_norm):
                c_depth = root.rstrip(os.path.sep).count(os.path.sep) - base_depth
                dirs[:] = [d for d in dirs if not is_protected_system_item(d)]
                for d in dirs:
                    sub_d = os.path.normcase(os.path.join(root, d))
                    sub_attrs = kernel32.GetFileAttributesW(sub_d)
                    if sub_attrs != INVALID_FILE_ATTRIBUTES:
                        orig = sub_attrs & (FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
                        if orig:
                            with _CACHE_LOCK:
                                _ORIGINAL_ATTRIBUTES[sub_d] = orig
                for f in files:
                    if is_protected_system_item(f):
                        continue
                    full_f = os.path.normcase(os.path.join(root, f))
                    f_attrs = kernel32.GetFileAttributesW(full_f)
                    if f_attrs != INVALID_FILE_ATTRIBUTES:
                        orig = f_attrs & (FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
                        if orig:
                            with _CACHE_LOCK:
                                _ORIGINAL_ATTRIBUTES[full_f] = orig
                if not recursive or c_depth >= max_depth:
                    dirs.clear()
        except Exception:
            pass

        with _CACHE_LOCK:
            _CLOAKED_FOLDERS.add(base_norm)
        _save_system_attributes_cache()

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

        base_norm = os.path.normcase(base_path)
        with _CACHE_LOCK:
            _CLOAKED_FOLDERS.discard(base_norm)
        _save_system_attributes_cache()

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
    """
    Снимает System и Hidden с директории, сохраняя оригинальные системные и скрытые атрибуты.
    """
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

        norm_p = os.path.normcase(os.path.normpath(dir_path))
        with _CACHE_LOCK:
            orig_flags = _ORIGINAL_ATTRIBUTES.get(norm_p, 0)

        remove_flags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        new_attrs = (attrs & ~remove_flags) | orig_flags
        if new_attrs == attrs:
            return True

        return bool(kernel32.SetFileAttributesW(dir_path, new_attrs))
    except Exception:
        return False
