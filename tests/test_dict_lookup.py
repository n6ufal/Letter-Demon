"""Tests for core/dict_lookup.py — binary-search dictionary lookup."""

import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.dict_lookup import DictLookup


class DictLookupStartingWithTest(unittest.TestCase):
    def setUp(self):
        self.wordlist = [
            "apple", "application", "appetizer",
            "banana", "bandana", "banshee",
            "cat", "caterpillar", "catalog",
        ]
        self.lookup = DictLookup(self.wordlist)

    def test_find_starting_with_returns_matches(self):
        results = self.lookup.find_starting_with("app")
        self.assertEqual(len(results), 3)
        for w in results:
            self.assertTrue(w.startswith("app"))

    def test_find_starting_with_empty_prefix_returns_empty(self):
        results = self.lookup.find_starting_with("")
        self.assertEqual(results, [])

    def test_find_starting_with_no_match_returns_empty(self):
        results = self.lookup.find_starting_with("xyz")
        self.assertEqual(results, [])

    def test_find_starting_with_case_insensitive(self):
        results = self.lookup.find_starting_with("APP")
        self.assertEqual(len(results), 3)

    def test_find_starting_with_respects_limit(self):
        results = self.lookup.find_starting_with("b", limit=2)
        self.assertLessEqual(len(results), 2)

    def test_find_starting_with_empty_wordlist(self):
        lookup = DictLookup([])
        results = lookup.find_starting_with("a")
        self.assertEqual(results, [])


class DictLookupEndingWithTest(unittest.TestCase):
    def setUp(self):
        self.wordlist = [
            "apple", "ax", "ay",
            "banana", "bandana",
            "cat", "catalog",
        ]
        self.lookup = DictLookup(self.wordlist)

    def test_find_ending_with_returns_matches(self):
        results = self.lookup.find_ending_with("le")
        self.assertEqual(results, ["apple"])

    def test_find_ending_with_empty_suffix_returns_empty(self):
        results = self.lookup.find_ending_with("")
        self.assertEqual(results, [])

    def test_find_ending_with_no_match_returns_empty(self):
        results = self.lookup.find_ending_with("zzz")
        self.assertEqual(results, [])

    def test_find_ending_with_case_insensitive(self):
        results = self.lookup.find_ending_with("LE")
        self.assertEqual(results, ["apple"])


class DictLookupCombinedTest(unittest.TestCase):
    def setUp(self):
        self.wordlist = [
            "apple", "application", "appetizer",
            "cat", "caterpillar",
        ]
        self.lookup = DictLookup(self.wordlist)

    def test_find_starting_and_ending_with_prefix_only(self):
        results, total = self.lookup.find_starting_and_ending_with("app", "")
        self.assertEqual(total, 3)

    def test_find_starting_and_ending_with_suffix_only(self):
        results, total = self.lookup.find_starting_and_ending_with("", "ar")
        self.assertEqual(total, 1)

    def test_find_starting_and_ending_with_both(self):
        results, total = self.lookup.find_starting_and_ending_with("a", "le")
        self.assertEqual(results, ["apple"])
        self.assertEqual(total, 1)

    def test_find_starting_and_ending_with_no_match(self):
        results, total = self.lookup.find_starting_and_ending_with("xyz", "")
        self.assertEqual(results, [])

    def test_find_starting_and_ending_with_both_empty(self):
        results, total = self.lookup.find_starting_and_ending_with("", "")
        self.assertEqual(results, [])

    def test_find_starting_and_ending_respects_limit(self):
        wordlist = [f"ab{i}" for i in range(200)]
        lookup = DictLookup(wordlist)
        results, total = lookup.find_starting_and_ending_with("ab", "", limit=50)
        self.assertEqual(len(results), 50)
        self.assertEqual(total, 200)


class DictLookupContainsTest(unittest.TestCase):
    def setUp(self):
        self.lookup = DictLookup(["apple", "banana", "cherry"])

    def test_contains_exact_word(self):
        self.assertTrue(self.lookup.contains("apple"))

    def test_contains_missing_word(self):
        self.assertFalse(self.lookup.contains("apricot"))

    def test_contains_empty_wordlist(self):
        lookup = DictLookup([])
        self.assertFalse(lookup.contains("a"))


class DictLookupAddWordTest(unittest.TestCase):
    def setUp(self):
        self.lookup = DictLookup(["apple", "cherry"])

    def test_add_new_word(self):
        self.assertTrue(self.lookup.add_word("banana"))
        self.assertTrue(self.lookup.contains("banana"))

    def test_add_duplicate_word(self):
        self.assertFalse(self.lookup.add_word("apple"))

    def test_add_words_multiple(self):
        added = self.lookup.add_words(["banana", "date", "apple"])
        self.assertEqual(added, 2)

    def test_add_words_maintains_sorted_order(self):
        self.lookup.add_word("banana")
        results = self.lookup.find_starting_with("b")
        self.assertEqual(results, ["banana"])

    def test_add_word_invalidates_reversed_cache(self):
        self.lookup.find_ending_with("le")
        self.lookup.add_word("axle")
        results = self.lookup.find_ending_with("le")
        self.assertIn("axle", results)


class DictLookupSetWordlistTest(unittest.TestCase):
    def setUp(self):
        self.lookup = DictLookup(["apple", "banana"])

    def test_set_wordlist_replaces_words(self):
        self.lookup.set_wordlist(["cherry", "date"])
        self.assertFalse(self.lookup.contains("apple"))
        self.assertTrue(self.lookup.contains("cherry"))

    def test_set_wordlist_invalidates_reversed_cache(self):
        self.lookup.find_ending_with("na")
        self.lookup.set_wordlist(["apple", "axle"])
        results = self.lookup.find_ending_with("le")
        self.assertEqual(results, ["apple", "axle"])


class DictLookupThreadSafetyTest(unittest.TestCase):
    def setUp(self):
        self.lookup = DictLookup([f"word{i}" for i in range(1000)])

    def test_concurrent_search_and_add(self):
        errors = []

        def search():
            try:
                for _ in range(50):
                    self.lookup.find_starting_with("w")
                    self.lookup.contains("word500")
            except Exception as e:
                errors.append(e)

        def add():
            try:
                for i in range(500, 600):
                    self.lookup.add_word(f"new{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=search) for _ in range(5)
        ] + [
            threading.Thread(target=add) for _ in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(errors, [])


class DictLookupHasWordlistTest(unittest.TestCase):
    def test_has_wordlist_true(self):
        lookup = DictLookup(["apple"])
        self.assertTrue(lookup.has_wordlist())

    def test_has_wordlist_false(self):
        lookup = DictLookup([])
        self.assertFalse(lookup.has_wordlist())

    def test_get_word_count(self):
        lookup = DictLookup(["a", "b", "c"])
        self.assertEqual(lookup.get_word_count(), 3)


if __name__ == "__main__":
    unittest.main()
