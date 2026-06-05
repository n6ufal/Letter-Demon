"""Tests for core/dictionary.py — dictionary loading, caching, hashing."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.dictionary import (
    get_cache_path,
    _cache_is_valid,
    _load_dict_file,
    load_wordlist_from_dict,
    CACHE_DIR,
)


class GetCachePathTest(unittest.TestCase):
    def test_returns_path_in_cache_dir(self):
        path = get_cache_path(r"C:\dicts\words.txt")
        self.assertIn(CACHE_DIR, path)
        self.assertTrue(path.endswith(".txt"))
        self.assertIn("cache_", path)

    def test_differs_for_different_paths(self):
        p1 = get_cache_path(r"C:\dicts\words.txt")
        p2 = get_cache_path(r"C:\dicts\other.txt")
        self.assertNotEqual(p1, p2)


class CacheIsValidTest(unittest.TestCase):
    def test_no_cache_file_returns_false(self):
        self.assertFalse(_cache_is_valid(r"C:\nonexistent\cache.txt", r"C:\nonexistent\dict.txt"))

    def test_cached_newer_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = os.path.join(tmp, "dict.txt")
            cache_path = os.path.join(tmp, "cache.txt")
            with open(dict_path, "w") as f:
                f.write("hello")
            with open(cache_path, "w") as f:
                f.write("hello")
            # Modify cache mtime to be newer than dict
            cache_mtime = os.path.getmtime(dict_path) + 100
            os.utime(cache_path, (cache_mtime, cache_mtime))
            self.assertTrue(_cache_is_valid(cache_path, dict_path))

    def test_cached_older_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = os.path.join(tmp, "dict.txt")
            cache_path = os.path.join(tmp, "cache.txt")
            with open(dict_path, "w") as f:
                f.write("hello")
            with open(cache_path, "w") as f:
                f.write("hello")
            dict_mtime = os.path.getmtime(dict_path) + 100
            os.utime(dict_path, (dict_mtime, dict_mtime))
            self.assertFalse(_cache_is_valid(cache_path, dict_path))


class LoadDictFileTest(unittest.TestCase):
    def test_txt_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("apple\nbanana\ncherry\n")
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana", "cherry"})
        finally:
            os.unlink(tmp)

    def test_txt_lowercase(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Apple\nBANANA\nCherry\n")
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana", "cherry"})
        finally:
            os.unlink(tmp)

    def test_txt_skips_comments(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("# this is a comment\napple\n# another comment\nbanana\n")
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana"})
        finally:
            os.unlink(tmp)

    def test_txt_skips_blank_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("apple\n\nbanana\n  \ncherry\n")
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana", "cherry"})
        finally:
            os.unlink(tmp)

    def test_txt_with_extra_columns(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("apple 42\nbanana 17\ncherry 99\n")
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana", "cherry"})
        finally:
            os.unlink(tmp)

    def test_txt_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, set())
        finally:
            os.unlink(tmp)

    def test_json_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({"Apple": 1, "Banana": 2}, f)
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, {"apple", "banana"})
        finally:
            os.unlink(tmp)

    def test_json_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({}, f)
            tmp = f.name
        try:
            result = _load_dict_file(tmp)
            self.assertEqual(result, set())
        finally:
            os.unlink(tmp)


class LoadWordlistFromDictTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dict_path = os.path.join(self.tmp_dir.name, "words.txt")
        with open(self.dict_path, "w") as f:
            f.write("cherry\napple\nbanana\n")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _patch_cache_dir(self, func):
        cache_dir = os.path.join(self.tmp_dir.name, "cache")
        with patch("core.dictionary.CACHE_DIR", cache_dir):
            return func()

    def test_loads_and_sorts(self):
        def test():
            wordlist, from_cache = load_wordlist_from_dict(self.dict_path)
            self.assertEqual(wordlist, ["apple", "banana", "cherry"])
            self.assertFalse(from_cache)
        self._patch_cache_dir(test)

    def test_loads_from_cache_on_subsequent_call(self):
        def test():
            # First call: loads fresh
            wordlist1, from_cache1 = load_wordlist_from_dict(self.dict_path)
            self.assertEqual(wordlist1, ["apple", "banana", "cherry"])
            self.assertFalse(from_cache1)
            # Second call: should use cache
            wordlist2, from_cache2 = load_wordlist_from_dict(self.dict_path)
            self.assertEqual(wordlist2, ["apple", "banana", "cherry"])
            self.assertTrue(from_cache2)
        self._patch_cache_dir(test)

    def test_falls_back_when_cache_invalid(self):
        def test():
            load_wordlist_from_dict(self.dict_path)
            # Make dict newer than cache
            os.utime(self.dict_path, (os.path.getmtime(self.dict_path) + 200,
                                       os.path.getmtime(self.dict_path) + 200))
            wordlist, from_cache = load_wordlist_from_dict(self.dict_path)
            self.assertEqual(wordlist, ["apple", "banana", "cherry"])
            self.assertFalse(from_cache)
        self._patch_cache_dir(test)


if __name__ == "__main__":
    unittest.main()
