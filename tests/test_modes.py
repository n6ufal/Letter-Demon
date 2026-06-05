"""Tests for ui/modes.py — display-to-internal mode mapping."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.modes import (
    to_display_mode,
    to_internal_mode,
    to_display_fallback,
    to_internal_fallback,
)


class ModeMappingTest(unittest.TestCase):
    def test_to_display_mode_map(self):
        cases = [
            ("Trap Words", "Trap"),
            ("Random Words", "Random"),
            ("Short Words", "Short"),
            ("Long Words", "Long"),
        ]
        for internal, display in cases:
            self.assertEqual(to_display_mode(internal), display)

    def test_to_internal_mode_map(self):
        cases = [
            ("Trap", "Trap Words"),
            ("Random", "Random Words"),
            ("Short", "Short Words"),
            ("Long", "Long Words"),
        ]
        for display, internal in cases:
            self.assertEqual(to_internal_mode(display), internal)

    def test_to_display_fallback_map(self):
        cases = [
            ("Short Words", "Short"),
            ("Random Words", "Random"),
            ("Long Words", "Long"),
        ]
        for internal, display in cases:
            self.assertEqual(to_display_fallback(internal), display)

    def test_to_internal_fallback_map(self):
        cases = [
            ("Short", "Short Words"),
            ("Random", "Random Words"),
            ("Long", "Long Words"),
        ]
        for display, internal in cases:
            self.assertEqual(to_internal_fallback(display), internal)

    def test_unknown_mode_returns_default(self):
        self.assertEqual(to_display_mode("Unknown"), "Trap")
        self.assertEqual(to_internal_mode("Unknown"), "Trap Words")
        self.assertEqual(to_display_fallback("Unknown"), "Short")
        self.assertEqual(to_internal_fallback("Unknown"), "Short Words")

    def test_round_trip_modes(self):
        for display in ["Trap", "Random", "Short", "Long"]:
            internal = to_internal_mode(display)
            back = to_display_mode(internal)
            self.assertEqual(back, display)

    def test_round_trip_fallbacks(self):
        for display in ["Short", "Random", "Long"]:
            internal = to_internal_fallback(display)
            back = to_display_fallback(internal)
            self.assertEqual(back, display)


if __name__ == "__main__":
    unittest.main()
