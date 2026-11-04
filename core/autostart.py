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
