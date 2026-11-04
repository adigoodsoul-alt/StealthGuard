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
