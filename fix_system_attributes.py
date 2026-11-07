"""
Скрипт для восстановления исходных атрибутов (System + Hidden)
у случайно раскрытых системных файлов Windows (desktop.ini, thumbs.db, $RECYCLE.BIN и т.д.).
"""

import sys
import os
import ctypes

FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004

PROTECTED_SYSTEM_NAMES = {
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
}


def is_system_item(name: str) -> bool:
    low = name.lower()
    return low in PROTECTED_SYSTEM_NAMES or low.startswith("$") or low.endswith(".sys")


def fix_folder_system_attributes(target_path: str) -> int:
    """
    Рекурсивно обходит папку и возвращает флаги System + Hidden всем системным файлам и каталогам.
    """
    if not os.path.exists(target_path):
        print(f"[!] Путь не существует: {target_path}")
        return 0

    fixed_count = 0
    k32 = ctypes.windll.kernel32

    # Проверяем сам каталог
    target_norm = os.path.normpath(target_path)
    base_name = os.path.basename(target_norm)
    if is_system_item(base_name):
        attrs = k32.GetFileAttributesW(target_norm)
        if attrs != 0xFFFFFFFF and not (attrs & FILE_ATTRIBUTE_SYSTEM and attrs & FILE_ATTRIBUTE_HIDDEN):
            k32.SetFileAttributesW(target_norm, attrs | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
            fixed_count += 1
            print(f"  [+] Скрыта системная папка: {target_norm}")

    for root, dirs, files in os.walk(target_norm):
        for d in dirs:
            if is_system_item(d):
                sub_d = os.path.join(root, d)
                attrs = k32.GetFileAttributesW(sub_d)
                if attrs != 0xFFFFFFFF and not (attrs & FILE_ATTRIBUTE_SYSTEM and attrs & FILE_ATTRIBUTE_HIDDEN):
                    k32.SetFileAttributesW(sub_d, attrs | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
                    fixed_count += 1
                    print(f"  [+] Скрыта системная папка: {sub_d}")

        for f in files:
            if is_system_item(f):
                sub_f = os.path.join(root, f)
                attrs = k32.GetFileAttributesW(sub_f)
                if attrs != 0xFFFFFFFF and not (attrs & FILE_ATTRIBUTE_SYSTEM and attrs & FILE_ATTRIBUTE_HIDDEN):
                    k32.SetFileAttributesW(sub_f, attrs | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN)
                    fixed_count += 1
                    print(f"  [+] Скрыт системный файл: {sub_f}")

    return fixed_count


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1].strip('\"')
    else:
        path = input("Введите путь к папке или диску для исправления системных файлов: ").strip('\"')

    if path:
        print(f"\nПоиск и скрытие системных файлов в: {path}...")
        count = fix_folder_system_attributes(path)
        print(f"\n[ГОТОВО] Восстановлены системные атрибуты для {count} объектов.\n")
    else:
        print("[!] Путь не указан.")
