import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import url_to_path, normalize_path, is_path_matching
from core.config_manager import ConfigManager, Rule


def test_utils():
    # URL to Path tests
    assert url_to_path("file:///C:/Users/ADI/Documents") == "C:\\Users\\ADI\\Documents"
    assert url_to_path("file:///Y:/Secret%20Folder") == "Y:\\Secret Folder"
    assert url_to_path("file:///Y:/%D0%96%D0%BC%D0%B0%D1%82%D1%8c") == "Y:\\Жмать"
    assert url_to_path("file://myserver/share/folder") == "\\\\myserver\\share\\folder"

    # Normalize path tests
    assert normalize_path("C:\\Users\\ADI\\Documents\\") == "c:\\users\\adi\\documents"
    assert normalize_path("y:/SecretFolder") == "y:\\secretfolder"

    # Subpath matching
    assert is_path_matching("y:\\SecretFolder", "Y:\\SecretFolder")
    assert is_path_matching("y:\\SecretFolder\\file.txt", "Y:\\SecretFolder")
    assert is_path_matching("y:\\SecretFolder\\Sub\\Deep", "Y:\\SecretFolder")
    assert not is_path_matching("y:\\SecretFolderOther", "Y:\\SecretFolder")
    assert not is_path_matching("c:\\Other", "Y:\\SecretFolder")
    print("[PASS] Utils tests passed!")


def test_config():
    test_config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

    cm = ConfigManager(config_path=test_config_path)
    assert cm.settings.global_protection_enabled is True

    # Add rule
    r = Rule(name="Test Rule", target_path="Y:\\Test", mode="decoy", decoy_path="C:\\Decoy")
    cm.add_rule(r)
    assert len(cm.rules) >= 1

    # Reload from disk
    cm2 = ConfigManager(config_path=test_config_path)
    found = any(x.target_path == "Y:\\Test" for x in cm2.rules)
    assert found

    # Clean up
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
    print("[PASS] ConfigManager tests passed!")


if __name__ == "__main__":
    test_utils()
    test_config()
    print("All smoke tests completed successfully!")
