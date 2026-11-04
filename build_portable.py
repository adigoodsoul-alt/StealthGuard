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
