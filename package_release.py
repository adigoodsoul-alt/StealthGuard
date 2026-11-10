import os
import zipfile
import json

def package_release():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist", "StealthGuard")
    zip_path = os.path.join(base_dir, "StealthGuard-v2.5-Portable.zip")

    if not os.path.exists(dist_dir):
        print(f"Error: {dist_dir} does not exist!")
        return False

    cfg_file = os.path.join(dist_dir, "config.json")
    orig_cfg = None
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            orig_cfg = f.read()

    clean_cfg = {
        "settings": {
            "global_protection_enabled": True,
            "hotkey": "ctrl+shift+alt+l",
            "protection_toggle_hotkey": "ctrl+shift+alt+p",
            "pin_enabled": False,
            "pin_hash": "",
            "autostart": True,
            "clean_recent": True,
            "check_interval_ms": 35,
            "stealth_startup": False,
            "show_tray_icon": True
        },
        "rules": []
    }

    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(clean_cfg, f, indent=2, ensure_ascii=False)

        print(f"Packaging {dist_dir} -> {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.join("StealthGuard", os.path.relpath(full_p, dist_dir))
                    zf.write(full_p, rel_p)

        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"Success! Archive created: {zip_path} ({size_mb:.2f} MB)")
        return True
    finally:
        if orig_cfg is not None:
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write(orig_cfg)

if __name__ == "__main__":
    package_release()
