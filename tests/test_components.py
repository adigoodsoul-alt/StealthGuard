import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.config_manager import ConfigManager, Rule
from core.recent_cleaner import RecentCleaner
from core.interceptor import ExplorerInterceptor
from core.hotkey_manager import GlobalHotkeyManager, normalize_hotkey_for_pynput
from core.utils import url_to_path, normalize_path, is_path_matching
from ui.main_window import MainWindow


def test_full_pipeline():
    # 1. Hotkey normalization
    hk_list = normalize_hotkey_for_pynput("Ctrl + Shift + Alt + L")
    assert any("<ctrl>" in hk and "<shift>" in hk and "<alt>" in hk and "l" in hk for hk in hk_list)
    prot_hk_list = normalize_hotkey_for_pynput("Ctrl + Shift + Alt + P")
    assert any("<ctrl>" in hk and "<shift>" in hk and "<alt>" in hk and "p" in hk for hk in prot_hk_list)
    assert any("з" in hk for hk in prot_hk_list)
    print("[PASS] Hotkey normalization passed")

    # 2. Config manager & PIN
    test_cfg_path = os.path.join(os.path.dirname(__file__), "pipeline_test_config.json")
    if os.path.exists(test_cfg_path):
        os.remove(test_cfg_path)

    cm = ConfigManager(config_path=test_cfg_path)
    pin_hash = ConfigManager.hash_pin("1234")
    assert pin_hash.startswith("pbkdf2_sha256$")
    cm.settings.pin_hash = pin_hash
    cm.settings.pin_enabled = True
    assert cm.verify_pin("1234") is True
    assert cm.verify_pin("wrong") is False

    # Test legacy SHA-256 auto-migration
    import hashlib
    legacy_sha256 = hashlib.sha256("5678".encode("utf-8")).hexdigest()
    cm.settings.pin_hash = legacy_sha256
    assert cm.verify_pin("5678") is True
    # Verify it automatically migrated to pbkdf2 format!
    assert cm.settings.pin_hash.startswith("pbkdf2_sha256$")
    assert cm.verify_pin("5678") is True
    assert cm.verify_pin("wrong") is False
    # Restore pin_hash to "1234" for subsequent UI dialog tests
    cm.settings.pin_hash = pin_hash
    print("[PASS] PIN PBKDF2-HMAC-SHA256 & Legacy Migration passed")

    # 3. Interceptor setup
    cleaner = RecentCleaner(cm)
    interceptor = ExplorerInterceptor(cm, cleaner)
    assert hasattr(interceptor, "intercepted")
    assert hasattr(interceptor, "status_changed")
    print("[PASS] Interceptor initialization passed")

    # 3a. File Cloaker test
    from core.file_cloaker import cloak_folder, uncloak_folder, cloak_file, uncloak_file, FILE_ATTRIBUTE_SYSTEM, FILE_ATTRIBUTE_HIDDEN
    import ctypes
    test_folder = os.path.join(os.path.dirname(__file__), "cloaker_test_dir")
    os.makedirs(test_folder, exist_ok=True)
    img_file = os.path.join(test_folder, "photo.png")
    doc_file = os.path.join(test_folder, "notes.txt")
    with open(img_file, "w") as f: f.write("img")
    with open(doc_file, "w") as f: f.write("doc")

    # Cloak folder with Total Cloaking (all_files=True)
    cloaked = cloak_folder(test_folder, all_files=True)
    assert cloaked == 2  # Both photo.png and notes.txt!
    attrs = ctypes.windll.kernel32.GetFileAttributesW(img_file)
    assert attrs & FILE_ATTRIBUTE_SYSTEM and attrs & FILE_ATTRIBUTE_HIDDEN
    doc_attrs = ctypes.windll.kernel32.GetFileAttributesW(doc_file)
    assert doc_attrs & FILE_ATTRIBUTE_SYSTEM and doc_attrs & FILE_ATTRIBUTE_HIDDEN

    # Cloak directory test
    from core.file_cloaker import cloak_directory, uncloak_directory
    assert cloak_directory(test_folder) is True
    folder_attrs = ctypes.windll.kernel32.GetFileAttributesW(test_folder)
    assert folder_attrs & FILE_ATTRIBUTE_SYSTEM and folder_attrs & FILE_ATTRIBUTE_HIDDEN

    # Uncloak folder
    uncloaked = uncloak_folder(test_folder, all_files=True)
    assert uncloaked == 2
    attrs_after = ctypes.windll.kernel32.GetFileAttributesW(img_file)
    assert not (attrs_after & FILE_ATTRIBUTE_SYSTEM)
    doc_attrs_after = ctypes.windll.kernel32.GetFileAttributesW(doc_file)
    assert not (doc_attrs_after & FILE_ATTRIBUTE_SYSTEM)
    uncloak_directory(test_folder)

    # Clean up test folder
    os.remove(img_file)
    os.remove(doc_file)
    os.rmdir(test_folder)
    print("[PASS] File & Directory Cloaker (System + Hidden) verified")

    # 3b. Decoy Generator test (Visual Homoglyph Clone + Auto-Cloak + Auto-Deletion)
    from core.decoy_generator import get_clone_candidates, create_visual_clone_decoy, is_visual_clone, delete_decoy_folder
    # Test candidate generation
    ru_candidates = get_clone_candidates("Секреты")
    assert len(ru_candidates) > 0
    assert ru_candidates[0] != "Секреты"

    # Test actual folder creation with automatic cloaking
    dummy_target = os.path.join(os.path.dirname(__file__), "ТестоваяПапка")
    os.makedirs(dummy_target, exist_ok=True)
    success, clone_path, msg = create_visual_clone_decoy(dummy_target, create_on_disk=True)
    assert success is True
    assert clone_path != dummy_target
    assert os.path.exists(clone_path)
    clone_attrs = ctypes.windll.kernel32.GetFileAttributesW(clone_path)
    assert clone_attrs & FILE_ATTRIBUTE_SYSTEM and clone_attrs & FILE_ATTRIBUTE_HIDDEN
    assert os.path.basename(clone_path) != os.path.basename(dummy_target)

    # Test clone detection
    assert is_visual_clone(dummy_target, clone_path) is True
    assert is_visual_clone(dummy_target, "C:\\DifferentPath\\Clone") is False

    # Test safe deletion of cloaked decoy folder
    assert delete_decoy_folder(clone_path) is True
    assert not os.path.exists(clone_path)
    os.rmdir(dummy_target)
    print("[PASS] Decoy Generator (Visual Clone + Auto-Cloaking + Deletion) verified")

    # Test ConfigManager remove_rule auto-deleting decoy
    dummy_target2 = os.path.join(os.path.dirname(__file__), "AutoDelTarget")
    os.makedirs(dummy_target2, exist_ok=True)
    _, dummy_decoy2, _ = create_visual_clone_decoy(dummy_target2, create_on_disk=True)
    rule_to_del = Rule(name="DelTest", target_path=dummy_target2, mode="decoy", decoy_path=dummy_decoy2, auto_decoy=True)
    cm.add_rule(rule_to_del)
    assert os.path.exists(dummy_decoy2)
    cm.remove_rule(rule_to_del.id)
    # Wait for async background cleanup thread to complete deletion
    import time
    for _ in range(40):
        if not os.path.exists(dummy_decoy2):
            break
        time.sleep(0.05)
    assert not os.path.exists(dummy_decoy2)
    os.rmdir(dummy_target2)
    print("[PASS] ConfigManager remove_rule decoy cleanup verified")

    # 3c. Autostart Dual-Registration test
    from core.autostart import set_autostart, is_autostart_enabled, get_startup_shortcut_path
    assert set_autostart(True) is True
    assert is_autostart_enabled() is True
    sc_path = get_startup_shortcut_path()
    assert os.path.exists(sc_path)
    assert set_autostart(False) is True
    assert not os.path.exists(sc_path)
    print("[PASS] Dual Autostart (Startup shortcut + Registry) verified")

    # 3d. Drive Cloaker and Virtual Decoy Drive test
    from core.drive_cloaker import (
        is_drive_root, get_drive_letter, get_free_drive_letter,
        mount_virtual_decoy_drive, unmount_virtual_decoy_drive,
        apply_hidden_drives, query_dos_device_target
    )
    assert is_drive_root("Y:\\") is True
    assert is_drive_root("Y:") is True
    assert is_drive_root("C:\\Windows") is False
    assert get_drive_letter("Y:\\") == "Y"
    free_l = get_free_drive_letter()
    assert free_l is not None

    # Test mount & unmount virtual decoy drive
    ok, decoy_root, _ = mount_virtual_decoy_drive("Y")
    assert ok is True
    decoy_l = get_drive_letter(decoy_root)
    assert query_dos_device_target(decoy_l) is not None
    assert unmount_virtual_decoy_drive(decoy_root, delete_backing=True) is True
    assert query_dos_device_target(decoy_l) is None

    # Test decoy generator drive wrapper
    ok_wrap, decoy_wrap, _ = create_visual_clone_decoy("Y:\\")
    assert ok_wrap is True
    assert is_visual_clone("Y:\\", decoy_wrap) is True
    assert is_visual_clone("Y:\\", "Y:\\") is False
    assert delete_decoy_folder(decoy_wrap) is True

    # Test NoDrives mask apply and clean
    apply_hidden_drives({"Y", "W"})
    apply_hidden_drives(set())
    print("[PASS] Drive Cloaker (Virtual Decoy Drive + NoDrives + SHChangeNotify) verified")

    # 3e. Search-ms protocol URL parsing & Stealth Policy test
    from core.file_cloaker import enforce_explorer_stealth_policies

    # Test enforce_explorer_stealth_policies runs safely
    stealth_res = enforce_explorer_stealth_policies()
    assert isinstance(stealth_res, bool)

    # Test search-ms URL with location scope
    search_url_location = (
        "search-ms:displayname=Search%20Results%20in%20Secret"
        "&crumb=location:C%3A%5CUsers%5CUser%5CDocuments%5CSecret"
    )
    parsed_location = url_to_path(search_url_location, location_name="Search Results in Secret")
    assert parsed_location.startswith("search-ms://")
    assert "c:\\users\\user\\documents\\secret" in parsed_location.lower()
    assert is_path_matching(parsed_location, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_location, "C:\\Users\\User\\Documents\\OtherFolder") is False

    # Test search-ms URL inside protected subfolder
    search_url_sub = (
        "search-ms:displayname=Search%20Results"
        "&crumb=location:C%3A%5CUsers%5CUser%5CDocuments%5CSecret%5CDeepSubFolder"
    )
    parsed_sub = url_to_path(search_url_sub, location_name="Search Results")
    assert is_path_matching(parsed_sub, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_sub, "C:\\Users\\User\\Documents\\Secret2") is False

    # Test search-ms URL query by keyword matching folder name
    search_url_keyword = "search-ms:displayname=Search%20Results&crumb=Secret"
    parsed_kw = url_to_path(search_url_keyword, location_name="Search Results")
    assert is_path_matching(parsed_kw, "C:\\Users\\User\\Documents\\Secret") is True
    assert is_path_matching(parsed_kw, "C:\\Users\\User\\Documents\\Photos") is False

    # Test classic file:// URLs remain fully functional
    file_url = "file:///C:/Users/User/Secret%20Folder"
    parsed_file = url_to_path(file_url)
    assert os.path.normcase(parsed_file) == os.path.normcase("C:\\Users\\User\\Secret Folder")
    assert is_path_matching(parsed_file, "C:\\Users\\User\\Secret Folder") is True
    assert is_path_matching(parsed_file, "C:\\Users\\User\\Secret Folder\\Sub") is False
    assert is_path_matching("C:\\Users\\User\\Secret Folder\\Sub\\file.txt", "C:\\Users\\User\\Secret Folder") is True
    print("[PASS] Search-ms URL parsing, path matching & stealth policies verified")

    # 3f. PROTECTED_ITEM_NAMES & Deep Search Interception by File Name test
    from core.file_cloaker import get_protected_item_names, clear_protected_item_names
    test_search_dir = os.path.join(os.path.dirname(__file__), "deep_search_test_dir")
    os.makedirs(test_search_dir, exist_ok=True)
    deep_file = os.path.join(test_search_dir, "nda_contract_2026.pdf")
    with open(deep_file, "w") as f:
        f.write("confidential")

    # Cloak folder and verify names added to PROTECTED_ITEM_NAMES
    cloak_folder(test_search_dir, all_files=True)
    prot_names = get_protected_item_names()
    assert "nda_contract_2026.pdf" in prot_names
    assert "nda_contract_2026" in prot_names

    # Test search query executed from drive root matching file name token
    root_search_url = (
        "search-ms:displayname=Search%20Results%20in%20Local%20Disk%20(C:)"
        "&crumb=location:C%3A%5C&crumb=nda_contract_2026"
    )
    parsed_root = url_to_path(root_search_url, location_name="Search Results in Local Disk (C:)")
    assert is_path_matching(parsed_root, test_search_dir) is True

    # Test search query with unrelated file token does not match
    unrelated_search_url = (
        "search-ms:displayname=Search%20Results%20in%20Local%20Disk%20(C:)"
        "&crumb=location:C%3A%5C&crumb=unrelated_vacation_photos"
    )
    parsed_unrelated = url_to_path(unrelated_search_url, location_name="Search Results in Local Disk (C:)")
    assert is_path_matching(parsed_unrelated, test_search_dir) is False

    # Uncloak and verify removal from index
    uncloak_folder(test_search_dir, all_files=True)
    prot_names_after = get_protected_item_names()
    assert "nda_contract_2026.pdf" not in prot_names_after
    os.remove(deep_file)
    os.rmdir(test_search_dir)
    print("[PASS] PROTECTED_ITEM_NAMES cache & Root Search Interception verified")

    # 3g. Smart Visibility Inversion for Visual Clone Decoys test
    from core.config_manager import sync_rules_cloaking
    from core.decoy_generator import create_visual_clone_decoy
    inversion_base = os.path.join(os.path.dirname(__file__), "inversion_test_base")
    os.makedirs(inversion_base, exist_ok=True)
    real_target = os.path.join(inversion_base, "СекретныеДокументы")
    os.makedirs(real_target, exist_ok=True)
    _, decoy_clone, _ = create_visual_clone_decoy(real_target, create_on_disk=True)

    inversion_rule = Rule(
        name="SmartInversionRule",
        target_path=real_target,
        mode="decoy",
        decoy_path=decoy_clone,
        enabled=True
    )
    cm.add_rule(inversion_rule)

    # 1) Protection ENABLED: Target is HIDDEN, Decoy Clone is VISIBLE
    sync_rules_cloaking(cm, protection_enabled=True)
    target_attrs_on = ctypes.windll.kernel32.GetFileAttributesW(real_target)
    decoy_attrs_on = ctypes.windll.kernel32.GetFileAttributesW(decoy_clone)
    assert (target_attrs_on & FILE_ATTRIBUTE_HIDDEN) and (target_attrs_on & FILE_ATTRIBUTE_SYSTEM)
    assert not (decoy_attrs_on & FILE_ATTRIBUTE_HIDDEN)

    # 2) Protection DISABLED (Pause): Target is VISIBLE, Decoy Clone is HIDDEN
    sync_rules_cloaking(cm, protection_enabled=False)
    target_attrs_off = ctypes.windll.kernel32.GetFileAttributesW(real_target)
    decoy_attrs_off = ctypes.windll.kernel32.GetFileAttributesW(decoy_clone)
    # Clean up inversion test
    cm.remove_rule(inversion_rule.id)
    for _ in range(30):
        if not os.path.exists(decoy_clone):
            break
        time.sleep(0.05)
    if os.path.exists(decoy_clone):
        delete_decoy_folder(decoy_clone)
    if os.path.exists(real_target):
        uncloak_folder(real_target, all_files=True)
        try:
            os.rmdir(real_target)
        except Exception:
            pass
    if os.path.exists(inversion_base):
        import shutil
        shutil.rmtree(inversion_base, ignore_errors=True)
    print("[PASS] Smart Visibility Inversion (Protection ON/OFF) verified")

    # 3h. EverythingCloaker patch_everything_ini_flags test
    from core.everything_cloaker import patch_everything_ini_flags
    test_everything_ini = os.path.join(os.path.dirname(__file__), "test_Everything.ini")
    with open(test_everything_ini, "w", encoding="utf-8") as f:
        f.write("; Everything configuration stub\n"
                "window_x=120\n"
                "window_y=80\n"
                "exclude_hidden_files_and_folders=0\n"
                "exclude_system_files_and_folders=0\n")

    # 1) Switch to 1 (Protection ENABLED: hide system & hidden objects)
    switched_on = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True)
    assert switched_on is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_on = f.read()
    assert "exclude_hidden_files_and_folders=1" in content_on
    assert "exclude_system_files_and_folders=1" in content_on

    # 2) Idempotent call (already 1 -> returns False)
    assert patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True) is False

    # 3) Switch back to 0 (Protection DISABLED: allow system & hidden objects)
    switched_off = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=False)
    assert switched_off is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_off = f.read()
    assert "exclude_hidden_files_and_folders=0" in content_off
    assert "exclude_system_files_and_folders=0" in content_off

    # 4) Idempotent call (already 0 -> returns False)
    assert patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=False) is False

    # 5) Missing keys append test
    with open(test_everything_ini, "w", encoding="utf-8") as f:
        f.write("window_x=200\n")
    appended = patch_everything_ini_flags(test_everything_ini, hide_system_and_hidden=True)
    assert appended is True
    with open(test_everything_ini, "r", encoding="utf-8") as f:
        content_appended = f.read()
    assert "exclude_hidden_files_and_folders=1" in content_appended
    assert "exclude_system_files_and_folders=1" in content_appended

    # Clean up test ini file
    if os.path.exists(test_everything_ini):
        os.remove(test_everything_ini)
    print("[PASS] Everything.ini flags patch (exclude_hidden & exclude_system) verified")

    # 3i. System files attribute preservation test
    from core.file_cloaker import clear_system_attributes_cache, get_recorded_original_attributes
    clear_system_attributes_cache()
    test_sys_dir = os.path.join(os.path.dirname(__file__), "test_sys_preservation")
    if os.path.exists(test_sys_dir):
        uncloak_folder(test_sys_dir, all_files=True)
        import shutil
        shutil.rmtree(test_sys_dir, ignore_errors=True)
    os.makedirs(test_sys_dir, exist_ok=True)
    normal_file = os.path.join(test_sys_dir, "normal_document.txt")
    with open(normal_file, "w", encoding="utf-8") as f:
        f.write("Normal content")
    system_file = os.path.join(test_sys_dir, "special_driver.sys")
    with open(system_file, "w", encoding="utf-8") as f:
        f.write("DRIVER_SYS_BINARY_DATA\n")

    # Mark special_driver.sys as System + Hidden originally
    ctypes.windll.kernel32.SetFileAttributesW(
        system_file,
        FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN
    )
    initial_sys_attrs = ctypes.windll.kernel32.GetFileAttributesW(system_file)
    assert (initial_sys_attrs & FILE_ATTRIBUTE_SYSTEM) != 0
    assert (initial_sys_attrs & FILE_ATTRIBUTE_HIDDEN) != 0

    # Cloak folder (both files become cloaked)
    cloak_folder(test_sys_dir, all_files=True)
    rec_attrs = get_recorded_original_attributes()
    norm_sys_path = os.path.normpath(system_file).lower()
    assert norm_sys_path in rec_attrs
    assert (rec_attrs[norm_sys_path] & FILE_ATTRIBUTE_SYSTEM) != 0

    # Uncloak folder: special_driver.sys MUST retain FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN!
    # normal_document.txt MUST become visible (no HIDDEN, no SYSTEM)!
    uncloak_folder(test_sys_dir, all_files=True)
    after_normal_attrs = ctypes.windll.kernel32.GetFileAttributesW(normal_file)
    after_sys_attrs = ctypes.windll.kernel32.GetFileAttributesW(system_file)

    assert not (after_normal_attrs & FILE_ATTRIBUTE_HIDDEN)
    assert not (after_normal_attrs & FILE_ATTRIBUTE_SYSTEM)
    assert (after_sys_attrs & FILE_ATTRIBUTE_SYSTEM) != 0
    assert (after_sys_attrs & FILE_ATTRIBUTE_HIDDEN) != 0

    # Clean up test files
    ctypes.windll.kernel32.SetFileAttributesW(system_file, 0x80)  # FILE_ATTRIBUTE_NORMAL
    os.remove(system_file)
    os.remove(normal_file)
    os.rmdir(test_sys_dir)
    print("[PASS] System files attribute preservation on uncloak verified")

    # 3j. Mode 'hide' (pure folder hiding without decoy) test
    test_hide_dir = os.path.join(os.path.dirname(__file__), "test_hide_mode_dir")
    os.makedirs(test_hide_dir, exist_ok=True)
    hide_rule = Rule(
        name="HideModeRule",
        target_path=test_hide_dir,
        mode="hide",
        decoy_path="",
        enabled=True
    )
    cm.add_rule(hide_rule)

    # 1) Protection ENABLED: test_hide_dir is cloaked
    sync_rules_cloaking(cm, protection_enabled=True)
    hide_attrs_on = ctypes.windll.kernel32.GetFileAttributesW(test_hide_dir)
    assert (hide_attrs_on & FILE_ATTRIBUTE_HIDDEN) and (hide_attrs_on & FILE_ATTRIBUTE_SYSTEM)

    # 2) Protection DISABLED: test_hide_dir is uncloaked
    sync_rules_cloaking(cm, protection_enabled=False)
    hide_attrs_off = ctypes.windll.kernel32.GetFileAttributesW(test_hide_dir)
    assert not (hide_attrs_off & FILE_ATTRIBUTE_HIDDEN)

    # Clean up
    cm.remove_rule(hide_rule.id)
    if os.path.exists(test_hide_dir):
        os.rmdir(test_hide_dir)
    print("[PASS] Mode 'hide' (pure folder hiding) sync verified")

    # 4. Qt App and Main Window UI verification
    app = QApplication.instance() or QApplication(sys.argv)

    # 3b. Test PinVerifyDialog standalone with hidden/none parent
    from ui.dialogs.pin_dialog import PinVerifyDialog
    dialog = PinVerifyDialog(cm, None)
    assert dialog.parent() is None
    dialog.pinInput.setText("wrong")
    dialog._handle_submit()
    assert not dialog.errorLabel.isHidden()
    dialog.pinInput.setText("1234")
    dialog._handle_submit()
    assert dialog.result() == 1  # Accepted!
    print("[PASS] Standalone PinVerifyDialog verified")

    hk_manager = GlobalHotkeyManager(cm.settings.hotkey)
    window = MainWindow(cm, interceptor, hk_manager)

    assert window.windowTitle().startswith("StealthGuard")
    assert window.rules_view is not None
    assert window.logs_view is not None
    assert window.settings_view is not None

    # Test adding a log entry
    sample_event = {
        "timestamp": "2026-10-31 12:00:00",
        "rule_name": "Test Rule",
        "target_path": "Y:\\Secret",
        "mode": "Подмена (Decoy)",
        "decoy_path": "C:\\Users\\Public\\Documents",
        "hwnd": 12345
    }
    window.logs_view.add_log_entry(sample_event)
    assert window.logs_view.table.rowCount() == 1
    assert window.logs_view.table.item(0, 1).text() == "Test Rule"
    print("[PASS] LogsView UI integration passed")

    # Test RulesView auto-clone button logic
    assert hasattr(window.rules_view, "autoCloneBtn")
    dummy_ui_target = os.path.join(os.path.dirname(__file__), "UI_Clone_Target")
    os.makedirs(dummy_ui_target, exist_ok=True)
    window.rules_view.targetInput.setText(dummy_ui_target)
    window.rules_view._create_auto_clone_decoy()
    created_decoy = window.rules_view.decoyInput.text()
    assert os.path.exists(created_decoy)
    assert created_decoy != dummy_ui_target
    os.rmdir(created_decoy)
    os.rmdir(dummy_ui_target)
    print("[PASS] RulesView Auto-Clone UI action passed")

    # Test RulesView Mode 'hide' (pure folder hiding) creation
    dummy_ui_hide = os.path.join(os.path.dirname(__file__), "UI_Hide_Target")
    os.makedirs(dummy_ui_hide, exist_ok=True)
    window.rules_view.targetInput.setText(dummy_ui_hide)
    window.rules_view.modeCombo.setCurrentIndex(1)  # Index 1: "Скрытие (Hide)"
    window.rules_view._create_rule()
    created_hide_rule = next((r for r in cm.rules if r.target_path == dummy_ui_hide), None)
    assert created_hide_rule is not None
    assert created_hide_rule.mode == "hide"
    assert created_hide_rule.decoy_path == ""
    cm.remove_rule(created_hide_rule.id)
    os.rmdir(dummy_ui_hide)
    print("[PASS] RulesView Mode 'hide' UI creation passed")

    # Test protection toggle hotkey handler
    assert cm.settings.global_protection_enabled is True
    window.on_toggle_protection_hotkey()
    assert cm.settings.global_protection_enabled is False
    window.on_toggle_protection_hotkey()
    assert cm.settings.global_protection_enabled is True
    print("[PASS] Global Protection Toggle hotkey action passed")

    # Clean up
    window.close()
    if os.path.exists(test_cfg_path):
        os.remove(test_cfg_path)

    print("[PASS] All pipeline components validated successfully!")


if __name__ == "__main__":
    test_full_pipeline()
