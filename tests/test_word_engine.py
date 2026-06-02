"""Tests for core/word_engine.py — pure logic, no UI dependencies."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.word_engine import WordEngine


class WordEngineTest(unittest.TestCase):
    def setUp(self):
        self.wordlist = [
            "apple", "application", "appetizer",
            "banana", "bandana", "banshee",
            "cat", "caterpillar", "catalog",
            "dog", "dogmatic", "doge",
            "elephant", "elevator", "elite",
        ]
        self.trap_endings = ["ing", "er", "le"]
        self.exceptions = {"banana", "dogmatic"}
        self.engine = WordEngine(
            wordlist=self.wordlist,
            trap_endings=self.trap_endings,
            exceptions=self.exceptions,
        )

    def test_find_completion_returns_suffix(self):
        suffix = self.engine.find_completion("app")
        self.assertIsNotNone(suffix)
        self.assertIn("app" + suffix, self.wordlist)

    def test_find_full_word_returns_full_word(self):
        full = self.engine.find_full_word("app")
        self.assertIn(full, self.wordlist)
        self.assertTrue(full.startswith("app"))

    def test_no_match_returns_none(self):
        self.assertIsNone(self.engine.find_completion("xyz"))

    def test_empty_wordlist_returns_none(self):
        engine = WordEngine(wordlist=[], trap_endings=self.trap_endings)
        self.assertIsNone(engine.find_completion("a"))

    def test_exceptions_are_excluded(self):
        engine = WordEngine(
            wordlist=["banana", "bananas"],
            trap_endings=[],
            exceptions={"banana"},
        )
        result = engine.find_full_word("b")
        self.assertEqual(result, "bananas")

    def test_trap_mode_prefers_scored_words(self):
        engine = WordEngine(
            wordlist=["apple", "ax"],
            trap_endings=["le"],
            exceptions=set(),
        )
        result = engine.find_full_word("a", mode="Trap Words")
        self.assertEqual(result, "apple")

    def test_short_mode_returns_shortest(self):
        engine = WordEngine(
            wordlist=["cat", "catalog", "caterpillar"],
            trap_endings=[],
        )
        result = engine.find_full_word("ca", mode="Short Words")
        self.assertEqual(result, "cat")

    def test_long_mode_returns_longest(self):
        engine = WordEngine(
            wordlist=["cat", "caterpillar", "catalog"],
            trap_endings=[],
        )
        result = engine.find_full_word("cat", mode="Long Words")
        self.assertEqual(result, "caterpillar")

    def test_fallback_when_trap_finds_nothing(self):
        engine = WordEngine(
            wordlist=["cat", "caterpillar"],
            trap_endings=["xyz"],
        )
        result = engine.find_full_word("ca", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result, "cat")

    def test_used_words_not_repeated(self):
        engine = WordEngine(
            wordlist=["apple", "application"],
            trap_endings=[],
        )
        first = engine.find_full_word("app")
        second = engine.find_full_word("app")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

    def test_clear_used_words(self):
        engine = WordEngine(
            wordlist=["apple", "application"],
            trap_endings=[],
        )
        self.assertIsNotNone(engine.find_full_word("app"))
        engine.clear_used_words()
        self.assertIsNotNone(engine.find_full_word("app"))

    def test_set_trap_endings_recalculates(self):
        engine = WordEngine(
            wordlist=["apple", "ax"],
            trap_endings=["le"],
        )
        result_before = engine.find_full_word("a", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result_before, "apple")

        engine.set_trap_endings(["xyz"])
        result_after = engine.find_full_word("a", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result_after, "ax")

    def test_set_exceptions_updates_filter(self):
        engine = WordEngine(
            wordlist=["apple", "application"],
            trap_endings=[],
            exceptions=set(),
        )
        result_before = engine.find_full_word("ap", mode="Short Words")
        self.assertEqual(result_before, "apple")

        engine.set_exceptions({"apple"})
        result_after = engine.find_full_word("ap", mode="Short Words")
        self.assertEqual(result_after, "application")

    def test_used_words_for_display(self):
        engine = WordEngine(
            wordlist=["apple", "banana"],
            trap_endings=[],
        )
        engine.find_full_word("a")
        engine.find_full_word("b")
        words, count = engine.used_words_for_display()
        self.assertEqual(count, 2)
        self.assertEqual(words, ["apple", "banana"])

    def test_case_insensitive_prefix(self):
        engine = WordEngine(
            wordlist=["apple", "application"],
            trap_endings=[],
        )
        result_upper = engine.find_full_word("APP")
        engine.clear_used_words()
        result_lower = engine.find_full_word("app")
        self.assertEqual(result_upper, result_lower)

    def test_set_wordlist_replaces_candidates(self):
        engine = WordEngine(
            wordlist=["apple"],
            trap_endings=[],
        )
        self.assertIsNotNone(engine.find_full_word("app"))
        engine.set_wordlist(["banana"])
        self.assertIsNone(engine.find_full_word("app"))
        self.assertIsNotNone(engine.find_full_word("ban"))


if __name__ == "__main__":
    unittest.main()
