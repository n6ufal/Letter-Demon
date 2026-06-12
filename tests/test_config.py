"""Tests for config/ — settings, trap_endings, exceptions persistence."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import get_project_root, load_settings, save_settings, SettingsManager
from config.trap_endings import (
    load_trap_endings,
    save_trap_endings,
    DEFAULT_TRAP_ENDINGS,
)
from config.exceptions import load_exceptions, save_exceptions


class GetProjectRootTest(unittest.TestCase):
    def test_returns_absolute_path(self):
        root = get_project_root()
        self.assertTrue(root.is_absolute())

    def test_contains_core_directory(self):
        root = get_project_root()
        self.assertTrue((root / "core").is_dir())


class SettingsRoundTripTest(unittest.TestCase):
    def setUp(self):
        import config.settings as cs
        self.tmp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self.tmp_dir.name) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._orig_settings_file = cs.SETTINGS_FILE
        cs.SETTINGS_FILE = data_dir / "settings.json"

    def tearDown(self):
        import config.settings as cs
        cs.SETTINGS_FILE = self._orig_settings_file
        self.tmp_dir.cleanup()

    def test_load_missing_returns_empty(self):
        result = load_settings()
        self.assertEqual(result, {})

    def test_save_and_load_round_trip(self):
        data = {"wpm": 70, "mode": "Trap Words", "jitter_on": True}
        save_settings(data)
        loaded = load_settings()
        self.assertEqual(loaded, data)

    def test_save_updates_existing(self):
        save_settings({"wpm": 80})
        save_settings({"wpm": 120, "mode": "Short"})
        loaded = load_settings()
        self.assertEqual(loaded["wpm"], 120)
        self.assertEqual(loaded["mode"], "Short")


class TrapEndingsRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.tmp_dir.name, "trap_endings.txt")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _patch_file(self, func):
        with patch("config.trap_endings.TRAP_ENDINGS_FILE", self.file_path):
            return func()

    def test_load_missing_returns_defaults(self):
        def test():
            result = load_trap_endings()
            self.assertEqual(result, DEFAULT_TRAP_ENDINGS)
        self._patch_file(test)

    def test_save_and_load_round_trip(self):
        def test():
            data = ["ing", "er", "le", "tion"]
            save_trap_endings(data)
            loaded = load_trap_endings()
            self.assertEqual(loaded, data)
        self._patch_file(test)

    def test_load_ignores_comments_and_blanks(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("# comment line\n\ning\n  \n# another comment\ner\n  \nle\n")
            loaded = load_trap_endings()
            self.assertEqual(loaded, ["ing", "er", "le"])
        self._patch_file(test)

    def test_load_ignores_blank_lines(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("ing\n\n\n\ner\n")
            loaded = load_trap_endings()
            self.assertEqual(loaded, ["ing", "er"])
        self._patch_file(test)

    def test_load_deduplicates(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("ing\ner\ning\ner\n")
            loaded = load_trap_endings()
            self.assertEqual(loaded, ["ing", "er"])
        self._patch_file(test)

    def test_defaults_have_no_duplicates(self):
        self.assertEqual(len(DEFAULT_TRAP_ENDINGS), len(set(DEFAULT_TRAP_ENDINGS)))

    def test_load_lowercases(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("ING\nEr\nle\n")
            loaded = load_trap_endings()
            self.assertEqual(loaded, ["ing", "er", "le"])
        self._patch_file(test)

    def test_missing_file_creates_default_file(self):
        def test():
            load_trap_endings()
            self.assertTrue(os.path.exists(self.file_path))
            with open(self.file_path) as f:
                content = f.read()
            for e in DEFAULT_TRAP_ENDINGS:
                self.assertIn(e, content)
        self._patch_file(test)


class ExceptionsRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.tmp_dir.name, "exceptions.txt")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _patch_file(self, func):
        with patch("config.exceptions.EXCEPTIONS_FILE", self.file_path):
            return func()

    def test_load_missing_returns_empty_set(self):
        def test():
            result = load_exceptions()
            self.assertEqual(result, set())
        self._patch_file(test)

    def test_save_and_load_round_trip(self):
        def test():
            words = ["badword1", "badword2"]
            save_exceptions(words)
            loaded = load_exceptions()
            self.assertEqual(loaded, {"badword1", "badword2"})
        self._patch_file(test)

    def test_load_ignores_comments_and_blanks(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("# comment\nbadword1\n\n  \nbadword2\n")
            loaded = load_exceptions()
            self.assertEqual(loaded, {"badword1", "badword2"})
        self._patch_file(test)

    def test_load_lowercases(self):
        def test():
            with open(self.file_path, "w") as f:
                f.write("BadWord\nANOTHER\n")
            loaded = load_exceptions()
            self.assertEqual(loaded, {"badword", "another"})
        self._patch_file(test)

    def test_missing_file_creates_default_file(self):
        def test():
            result = load_exceptions()
            self.assertEqual(result, set())
            self.assertTrue(os.path.exists(self.file_path))
        self._patch_file(test)


class SettingsManagerTest(unittest.TestCase):
    """Tests for the SettingsManager class."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp_dir.name) / "settings.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_load_missing_returns_defaults(self):
        mgr = SettingsManager(self.path)
        self.assertEqual(mgr.get("mode"), "Trap Words")
        self.assertEqual(mgr.get("wpm"), 70)
        self.assertEqual(mgr.get("jitter_intensity"), 75)

    def test_save_and_reload(self):
        mgr = SettingsManager(self.path)
        mgr.set("wpm", 120)
        mgr.set("mode", "Short Words")
        mgr.save()

        mgr2 = SettingsManager(self.path)
        self.assertEqual(mgr2.get("wpm"), 120)
        self.assertEqual(mgr2.get("mode"), "Short Words")

    def test_merge_preserves_unknown_keys(self):
        self.path.write_text(json.dumps({"unknown_key": "hello"}), "utf-8")
        mgr = SettingsManager(self.path)
        mgr.set("wpm", 90)
        mgr.save()

        saved = json.loads(self.path.read_text("utf-8"))
        self.assertEqual(saved["unknown_key"], "hello")
        self.assertEqual(saved["wpm"], 90)

    def test_range_clamps_int(self):
        self.path.write_text(json.dumps({"wpm": 999}), "utf-8")
        mgr = SettingsManager(self.path)
        self.assertEqual(mgr.get("wpm"), 200)

    def test_range_clamps_low(self):
        self.path.write_text(json.dumps({"jitter_intensity": -5}), "utf-8")
        mgr = SettingsManager(self.path)
        self.assertEqual(mgr.get("jitter_intensity"), 0)

    def test_wrong_type_falls_back_to_default(self):
        self.path.write_text(json.dumps({"wpm": "fast"}), "utf-8")
        mgr = SettingsManager(self.path)
        self.assertEqual(mgr.get("wpm"), 70)

    def test_update_and_as_dict(self):
        mgr = SettingsManager(self.path)
        mgr.set("mode", "Long Words")
        mgr.set("jitter_intensity", 50)
        self.assertEqual(mgr.get("mode"), "Long Words")
        self.assertEqual(mgr.get("jitter_intensity", 50), 50)

        d = mgr.as_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["mode"], "Long Words")
        self.assertEqual(d["jitter_intensity"], 50)


if __name__ == "__main__":
    unittest.main()
