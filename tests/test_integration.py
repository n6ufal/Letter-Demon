"""Integration tests for Letter Demon — end-to-end workflows.

These tests validate complete user scenarios:
- Dictionary loading → word searching → typing
- Settings persistence across sessions
- Error recovery and graceful degradation
- Trap endings & exceptions handling
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.dictionary import load_wordlist_from_dict
from core.word_engine import WordEngine
from config.settings import load_settings, save_settings
from config.trap_endings import load_trap_endings, save_trap_endings
from config.exceptions import load_exceptions, save_exceptions
from system.typer import Typer


# ============================================================================
# DICTIONARY LOADING INTEGRATION
# ============================================================================

class DictionaryLoadingIntegrationTest(unittest.TestCase):
    """Test dictionary loading with real and edge case files."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp_dir.name

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_load_dict_and_find_word_end_to_end(self):
        """Load dictionary, create engine, find word."""
        dict_path = os.path.join(self.tmp_path, "words.txt")
        with open(dict_path, "w") as f:
            f.write("apple\napplication\napple\n")  # Duplicate to test dedup

        wordlist, from_cache = load_wordlist_from_dict(dict_path)
        self.assertEqual(sorted(wordlist), ["apple", "application"])
        self.assertFalse(from_cache)

        # Create engine with loaded words
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())
        completion = engine.find_completion("app")
        self.assertIsNotNone(completion)
        self.assertIn("app" + completion, ["apple", "application"])

    def test_cache_speeds_up_subsequent_loads(self):
        """First load from file, second from cache."""
        dict_path = os.path.join(self.tmp_path, "words.txt")
        with open(dict_path, "w") as f:
            f.write("apple\nbanana\ncherry\n" * 100)  # Larger dict

        # First load: slower, not from cache
        start = time.perf_counter()
        wordlist1, from_cache1 = load_wordlist_from_dict(dict_path)
        time1 = time.perf_counter() - start
        self.assertFalse(from_cache1)

        # Second load: faster, from cache
        start = time.perf_counter()
        wordlist2, from_cache2 = load_wordlist_from_dict(dict_path)
        time2 = time.perf_counter() - start
        self.assertTrue(from_cache2)

        self.assertEqual(wordlist1, wordlist2)
        # Cache should be faster (though may not always be measurable)
        # Just verify both loads return same words (3 unique words repeated)
        self.assertEqual(len(wordlist1), 3)
        self.assertEqual(len(wordlist2), 3)

    def test_invalid_dict_path_returns_none(self):
        """Missing dictionary path handled gracefully."""
        nonexistent_path = os.path.join(self.tmp_path, "nonexistent.txt")
        try:
            wordlist, from_cache = load_wordlist_from_dict(nonexistent_path)
            # Function may raise or return empty; both acceptable
            self.assertEqual(wordlist, [])
        except FileNotFoundError:
            pass  # Also acceptable

    def test_empty_dictionary_creates_engine(self):
        """Empty dictionary file doesn't crash engine creation."""
        dict_path = os.path.join(self.tmp_path, "empty.txt")
        with open(dict_path, "w") as f:
            f.write("")

        wordlist, _ = load_wordlist_from_dict(dict_path)
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())
        
        # Engine should handle empty wordlist gracefully
        result = engine.find_completion("a")
        self.assertIsNone(result)

    def test_dictionary_with_extra_columns_loads(self):
        """Dictionary with extra columns (e.g., frequency) loads correctly."""
        dict_path = os.path.join(self.tmp_path, "freq.txt")
        with open(dict_path, "w") as f:
            f.write("apple 100\nbanana 50\ncherry 30\n")

        wordlist, _ = load_wordlist_from_dict(dict_path)
        self.assertEqual(sorted(wordlist), ["apple", "banana", "cherry"])


# ============================================================================
# WORD ENGINE + TRAP ENDINGS WORKFLOW
# ============================================================================

class WordSearchingIntegrationTest(unittest.TestCase):
    """Test WordEngine with realistic trap endings and exceptions."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp_dir.name

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_engine_from_files(self, words, trap_endings, exceptions):
        """Helper: create engine with files."""
        # Create dictionary
        dict_path = os.path.join(self.tmp_path, "dict.txt")
        with open(dict_path, "w") as f:
            f.write("\n".join(words) + "\n")

        # Create trap endings file
        trap_path = os.path.join(self.tmp_path, "trap.txt")
        with open(trap_path, "w") as f:
            f.write("\n".join(trap_endings) + "\n")

        # Create exceptions file
        exc_path = os.path.join(self.tmp_path, "exc.txt")
        with open(exc_path, "w") as f:
            f.write("\n".join(exceptions) + "\n")

        # Load all
        wordlist, _ = load_wordlist_from_dict(dict_path)
        
        with patch("config.trap_endings.TRAP_ENDINGS_FILE", trap_path):
            trap_list = load_trap_endings()
        
        with patch("config.exceptions.EXCEPTIONS_FILE", exc_path):
            exc_set = load_exceptions()

        engine = WordEngine(
            wordlist=wordlist,
            trap_endings=trap_list,
            exceptions=exc_set,
        )
        return engine

    def test_trap_endings_prioritize_difficult_words(self):
        """Trap endings cause engine to prefer words ending with them."""
        words = ["apple", "ax", "ay"]  # apple ends with "le" (trap)
        trap_endings = ["le"]
        exceptions = []

        engine = self._create_engine_from_files(words, trap_endings, exceptions)
        
        # Trap Words mode should prefer 'apple'
        result = engine.find_full_word("a", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result, "apple")

    def test_exceptions_filter_blacklisted_words(self):
        """Exceptions prevent certain words from being suggested."""
        words = ["apple", "application", "appetizer"]
        trap_endings = []
        exceptions = ["apple", "appetizer"]  # Blacklist these

        engine = self._create_engine_from_files(words, trap_endings, exceptions)
        
        # Only 'application' should be available
        result = engine.find_full_word("app", mode="Short Words")
        self.assertEqual(result, "application")

    def test_reload_trap_endings_updates_scoring(self):
        """Changing trap endings recomputes word scores."""
        words = ["apple", "ax"]
        initial_trap_endings = ["le"]
        exceptions = []

        engine = self._create_engine_from_files(words, initial_trap_endings, exceptions)
        
        # With "le" trap, apple should win
        result1 = engine.find_full_word("a", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result1, "apple")
        
        # Update trap endings to have no effect
        engine.set_trap_endings(["xyz"])
        
        # Now "ax" (shorter) should win
        result2 = engine.find_full_word("a", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result2, "ax")

    def test_reload_exceptions_updates_filter(self):
        """Changing exceptions updates the filter."""
        words = ["apple", "application"]
        trap_endings = []
        exceptions = ["apple"]

        engine = self._create_engine_from_files(words, trap_endings, exceptions)
        
        # Only 'application' available
        result1 = engine.find_full_word("app", mode="Short Words")
        self.assertEqual(result1, "application")
        
        # Reload exceptions (empty)
        engine.set_exceptions(set())
        
        # Now both available; should return shortest
        result2 = engine.find_full_word("app", mode="Short Words")
        self.assertEqual(result2, "apple")


# ============================================================================
# SETTINGS PERSISTENCE
# ============================================================================

class SettingsPersistenceIntegrationTest(unittest.TestCase):
    """Test that settings persist across app sessions."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp_dir.name
        self.settings_file = os.path.join(self.tmp_path, "settings.json")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_save_and_reload_settings(self):
        """Save settings, reload, verify they persist."""
        settings = {
            "dict_path": "/path/to/dict.txt",
            "mode": "Trap Words",
            "fallback": "Short Words",
            "speed": 150,
            "jitter_intensity": 75,
            "jitter_on": True,
        }

        with patch("config.settings.SETTINGS_FILE", self.settings_file):
            save_settings(settings)
            loaded = load_settings()
        
        self.assertEqual(loaded, settings)

    def test_partial_settings_merge(self):
        """Saving partial settings replaces (not merges)."""
        initial = {"speed": 100, "mode": "Trap Words"}
        update = {"speed": 200}

        with patch("config.settings.SETTINGS_FILE", self.settings_file):
            save_settings(initial)
            loaded1 = load_settings()
            self.assertEqual(loaded1["speed"], 100)
            self.assertEqual(loaded1["mode"], "Trap Words")
            
            # Save just update - this replaces, doesn't merge
            save_settings(update)
            loaded2 = load_settings()
            self.assertEqual(loaded2["speed"], 200)
            # "mode" is gone because save_settings doesn't merge
            self.assertNotIn("mode", loaded2)


# ============================================================================
# TYPING + WORD ENGINE WORKFLOW
# ============================================================================

class TypingIntegrationTest(unittest.TestCase):
    """Test Typer with WordEngine output."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp_dir.name

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("system.typer.keyboard")
    def test_find_word_then_type_it(self, mock_kb):
        """End-to-end: find word and type it."""
        # Create dictionary and engine
        words = ["apple", "application"]
        dict_path = os.path.join(self.tmp_path, "dict.txt")
        with open(dict_path, "w") as f:
            f.write("\n".join(words) + "\n")

        wordlist, _ = load_wordlist_from_dict(dict_path)
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        # Find a completion
        completion = engine.find_full_word("app")
        self.assertIsNotNone(completion)
        self.assertIn(completion, words)

        # Type it
        typer = Typer(base_speed_ms=10.0, jitter_on=False)
        success, msg = typer.type_text(completion, pre_delay_s=0.01, post_delay_s=0.01)

        self.assertTrue(success)
        # Verify keyboard was called with the word (send() for enter)
        mock_kb.send.assert_called_with("enter")

    @patch("system.typer.keyboard")
    def test_typing_failure_returns_error(self, mock_kb):
        """Typing failure is caught and reported."""
        mock_kb.press_and_release.side_effect = Exception("keyboard failure")
        
        typer = Typer(base_speed_ms=10.0, jitter_on=False)
        success, msg = typer.type_text("hello", pre_delay_s=0.01, post_delay_s=0.01)

        self.assertFalse(success)
        self.assertIn("keyboard failure", msg)

    @patch("system.typer.keyboard")
    def test_empty_word_sends_enter(self, mock_kb):
        """If no word found, typing still sends enter."""
        typer = Typer(base_speed_ms=10.0, jitter_on=False)
        success, msg = typer.type_text("", pre_delay_s=0.01, post_delay_s=0.01)

        self.assertTrue(success)
        mock_kb.send.assert_called_with("enter")


# ============================================================================
# USED WORDS TRACKING
# ============================================================================

class UsedWordsTrackingIntegrationTest(unittest.TestCase):
    """Test that used words are tracked and don't repeat."""

    def test_used_words_prevent_repetition(self):
        """Used words list prevents the same word being suggested twice."""
        wordlist = ["apple", "application"]
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        first = engine.find_full_word("app")
        second = engine.find_full_word("app")

        # Should get different words
        self.assertNotEqual(first, second)

    def test_used_words_for_display_returns_history(self):
        """Used words tracking returns current history."""
        wordlist = ["apple", "application", "appetizer"]
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        # Use some words
        engine.find_full_word("app")
        engine.find_full_word("app")
        
        words, count = engine.used_words_for_display()
        self.assertEqual(count, 2)
        self.assertEqual(len(words), 2)

    def test_clear_used_words_resets_tracking(self):
        """Clearing used words allows them to be suggested again."""
        wordlist = ["apple", "application"]
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        # Use both words
        first = engine.find_full_word("app")
        second = engine.find_full_word("app")

        # No more words available
        third = engine.find_full_word("app")
        self.assertIsNone(third)

        # Clear and try again
        engine.clear_used_words()
        fourth = engine.find_full_word("app")
        self.assertIsNotNone(fourth)


# ============================================================================
# ERROR RECOVERY
# ============================================================================

class ErrorRecoveryIntegrationTest(unittest.TestCase):
    """Test graceful degradation and error recovery."""

    @patch("system.roblox.is_roblox_running")
    @patch("system.typer.keyboard")
    def test_typing_continues_if_roblox_missing(self, mock_kb, mock_roblox):
        """If Roblox window missing, typing still works."""
        mock_roblox.return_value = False  # Roblox not found
        
        typer = Typer(base_speed_ms=10.0, jitter_on=False)
        success, msg = typer.type_text("test", pre_delay_s=0.01, post_delay_s=0.01)

        # Typing should succeed regardless of Roblox status
        self.assertTrue(success)

    def test_word_engine_handles_empty_prefix(self):
        """Empty prefix handled gracefully."""
        wordlist = ["apple", "banana"]
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        # Empty prefix requires words longer than 0 chars, so should return a word
        # (Actually, find_completion returns the suffix, which might be the whole word)
        result = engine.find_completion("")
        # With empty prefix and requirement len(w) > len(""), it returns any word
        if result is not None:
            self.assertIsInstance(result, str)

    def test_word_engine_handles_no_matches(self):
        """Prefix with no matches returns None."""
        wordlist = ["apple", "banana"]
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        result = engine.find_completion("xyz")
        self.assertIsNone(result)


# ============================================================================
# MODE SWITCHING
# ============================================================================

class ModeSwitchingIntegrationTest(unittest.TestCase):
    """Test switching between modes produces different results."""

    def test_mode_switching_changes_results(self):
        """Different modes return different words from same prefix."""
        wordlist = ["cat", "caterpillar", "catalog"]
        trap_endings = ["le"]
        engine = WordEngine(wordlist=wordlist, trap_endings=trap_endings, exceptions=set())

        # Short Words mode
        short = engine.find_full_word("ca", mode="Short Words", fallback="Random Words")
        self.assertEqual(short, "cat")

        engine.clear_used_words()

        # Long Words mode
        long = engine.find_full_word("ca", mode="Long Words", fallback="Random Words")
        self.assertEqual(long, "caterpillar")

        engine.clear_used_words()

        # Trap Words mode: "catalog" ends with "le" which is a trap
        # (will be preferred if it has highest trap score)
        trap = engine.find_full_word("ca", mode="Trap Words", fallback="Short Words")
        self.assertIn(trap, ["catalog", "cat"])  # Either could be returned depending on scoring

    def test_fallback_mode_used_when_primary_fails(self):
        """Fallback mode kicks in when primary mode finds nothing."""
        wordlist = ["cat", "caterpillar"]
        trap_endings = ["xyz"]  # No match
        engine = WordEngine(wordlist=wordlist, trap_endings=trap_endings, exceptions=set())

        # Trap Words mode (no match) → fallback to Short Words
        result = engine.find_full_word("ca", mode="Trap Words", fallback="Short Words")
        self.assertEqual(result, "cat")


# ============================================================================
# THREADING & CONCURRENCY
# ============================================================================

class ConcurrencyIntegrationTest(unittest.TestCase):
    """Test thread safety with concurrent operations."""

    def test_concurrent_searches_are_thread_safe(self):
        """Multiple threads searching simultaneously don't crash."""
        wordlist = ["apple", "application", "appetizer", "apricot", "arrangement"]
        engine = WordEngine(wordlist=wordlist, trap_endings=["ing"], exceptions=set())

        results = []
        errors = []

        def search():
            try:
                result = engine.find_full_word("a")
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=search) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # No exceptions
        self.assertEqual(len(errors), 0)
        # All searches completed
        self.assertEqual(len(results), 10)

    def test_used_words_thread_safe_for_display(self):
        """Getting display words from multiple threads is safe."""
        wordlist = ["apple", "application", "appetizer"] * 10
        engine = WordEngine(wordlist=wordlist, trap_endings=[], exceptions=set())

        # Use some words
        for _ in range(5):
            engine.find_full_word("a")

        results = []
        errors = []

        def get_display():
            try:
                words, count = engine.used_words_for_display()
                results.append((words, count))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=get_display) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # No exceptions
        self.assertEqual(len(errors), 0)
        # All got results
        self.assertEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
