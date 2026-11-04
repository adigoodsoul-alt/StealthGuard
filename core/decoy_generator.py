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

