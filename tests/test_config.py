"""Tests for config/ — settings, trap_endings, exceptions persistence."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import get_project_root, load_settings, save_settings
from config.trap_endings import (
    load_trap_endings,
    save_trap_endings,
    DEFAULT_TRAP_ENDINGS,
)
from config.exceptions import load_exceptions, save_exceptions


class GetProjectRootTest(unittest.TestCase):
    def test_returns_absolute_path(self):
        root = get_project_root()
        self.assertTrue(os.path.isabs(root))

    def test_contains_core_directory(self):
        root = get_project_root()
        self.assertTrue(os.path.isdir(os.path.join(root, "core")))


class SettingsRoundTripTest(unittest.TestCase):
    def setUp(self):
        import config.settings as cs
        self.tmp_dir = tempfile.TemporaryDirectory()
        data_dir = os.path.join(self.tmp_dir.name, "data")
        os.makedirs(data_dir, exist_ok=True)
        self._orig_settings_file = cs.SETTINGS_FILE
        cs.SETTINGS_FILE = os.path.join(data_dir, "settings.json")

    def tearDown(self):
        import config.settings as cs
        cs.SETTINGS_FILE = self._orig_settings_file
        self.tmp_dir.cleanup()

    def test_load_missing_returns_empty(self):
        result = load_settings()
        self.assertEqual(result, {})

    def test_save_and_load_round_trip(self):
        data = {"speed": 150, "mode": "Trap Words", "jitter_on": True}
        save_settings(data)
        loaded = load_settings()
        self.assertEqual(loaded, data)

    def test_save_updates_existing(self):
        save_settings({"speed": 100})
        save_settings({"speed": 200, "mode": "Short"})
        loaded = load_settings()
        self.assertEqual(loaded["speed"], 200)
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


if __name__ == "__main__":
    unittest.main()
