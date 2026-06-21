"""Settings persistence — load/save settings.json with schema validation."""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Resolve project root directory.

    Works both as a package (points to letter_demon/) and as a compiled exe.
    All config/data files live at the project root level.
    Returns a pathlib.Path.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


SETTINGS_FILE = get_project_root() / "data" / "settings.json"


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)


# ---------------------------------------------------------------------------
# SettingsManager — schema-driven, validates ranges, merges on save
# ---------------------------------------------------------------------------

class SettingsManager:
    """Schema-driven settings persistence with validation and migration.

    Unlike the raw load_settings/save_settings functions, this class:
    - Validates types and clamps numeric ranges on load
    - Merges missing keys with defaults (self-healing on schema changes)
    - Preserves unknown keys in the file (future-proof)
    """

    SCHEMA: dict[str, tuple[type | tuple[type, ...], object]] = {
        "dict_path": ((str, type(None)), None),
        "window_title": (str, "Roblox"),
        "mode": (str, "Trap Words"),
        "fallback": (str, "Short Words"),
        "wpm": (int, 70),
        "jitter_intensity": (int, 75),
        "pre_delay": (int, 500),
        "post_delay": (int, 500),
        "auto_type_prefix": (bool, True),
        "win_x": ((int, type(None)), None),
        "win_y": ((int, type(None)), None),
    }

    RANGES: dict[str, tuple[int | float, int | float]] = {
        "wpm": (50, 200),
        "jitter_intensity": (0, 100),
        "pre_delay": (100, 5000),
        "post_delay": (100, 5000),
    }

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else SETTINGS_FILE
        self._data: dict[str, object] = self._load()

    def _load(self) -> dict[str, object]:
        raw: dict[str, object] = {}
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text("utf-8"))
        except Exception:
            raw = {}

        merged: dict[str, object] = {}
        for key, (expected_type, default) in self.SCHEMA.items():
            val = raw.get(key, default)
            merged[key] = self._clamp(key, val, default, expected_type)
        return merged

    @staticmethod
    def _clamp(
        key: str,
        val: object,
        default: object,
        expected_type: type | tuple[type, ...],
    ) -> object:
        if not isinstance(val, expected_type):
            return default
        lo_hi = SettingsManager.RANGES.get(key)
        if lo_hi is not None and isinstance(val, (int, float)):
            lo, hi = lo_hi
            val = max(lo, min(hi, val))
        return val

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def set(self, key: str, value: object) -> None:
        self._data[key] = value

    def update(self, data: dict[str, object]) -> None:
        self._data.update(data)

    def save(self) -> None:
        """Write to disk, merging with any existing keys in the file."""
        existing: dict[str, object] = {}
        try:
            if self.path.exists():
                existing = json.loads(self.path.read_text("utf-8"))
        except Exception:
            pass
        existing.update(self._data)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(existing, indent=2), "utf-8")
        except Exception as e:
            logger.warning("Failed to save settings: %s", e)

    def as_dict(self) -> dict[str, object]:
        return dict(self._data)
