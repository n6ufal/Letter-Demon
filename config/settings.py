"""Settings persistence — load/save settings.json."""

import json
import os
import sys


def get_project_root() -> str:
    """Resolve project root directory.

    Works both as a package (points to letter_demon/) and as a compiled exe.
    All config/data files live at the project root level.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # config/ is one level below project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SETTINGS_FILE = os.path.join(get_project_root(), "data", "settings.json")


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Failed to save settings:", e)
