"""Tests for system/typer.py — timing logic and keyboard simulation.

Actual keyboard calls are mocked; only the timing math is verified.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from system.typer import Typer


class TyperDelayTest(unittest.TestCase):
    def test_no_jitter_returns_base_speed(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=False)
        for _ in range(100):
            delay = typer._next_delay()
            self.assertAlmostEqual(delay, 0.2, places=4)

    def test_delay_never_below_30ms(self):
        typer = Typer(base_speed_ms=10.0, jitter_on=True, jitter_pct=100.0)
        for _ in range(1000):
            delay = typer._next_delay()
            self.assertGreaterEqual(delay, 0.03)

    def test_delay_never_below_30ms_no_jitter(self):
        typer = Typer(base_speed_ms=5.0, jitter_on=False)
        for _ in range(100):
            delay = typer._next_delay()
            self.assertGreaterEqual(delay, 0.03)

    def test_with_jitter_returns_varying_values(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=75.0)
        delays = [typer._next_delay() for _ in range(100)]
        self.assertGreater(len(set(round(d, 4) for d in delays)), 1)

    def test_jitter_scales_with_percentage(self):
        low_jitter = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=5.0)
        high_jitter = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=100.0)
        low_delays = [low_jitter._next_delay() for _ in range(200)]
        high_delays = [high_jitter._next_delay() for _ in range(200)]
        low_var = __import__("statistics").variance(low_delays)
        high_var = __import__("statistics").variance(high_delays)
        self.assertGreater(high_var, low_var)

    def test_default_constructor(self):
        typer = Typer()
        self.assertEqual(typer.base_speed_ms, 170.0)
        self.assertTrue(typer.jitter_on)
        self.assertEqual(typer.jitter_pct, 75.0)

    def test_rare_char_slower_than_common_no_jitter(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=False)
        e_delay = typer._next_delay("e", pos=1, total_len=5)
        z_delay = typer._next_delay("z", pos=1, total_len=5)
        self.assertGreater(z_delay, e_delay)

    def test_bigram_th_faster_than_zv_no_jitter(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=False)
        th_delay = typer._next_delay("h", prev="t", pos=1, total_len=5)
        zv_delay = typer._next_delay("v", prev="z", pos=1, total_len=5)
        self.assertGreater(zv_delay, th_delay)

    def test_micro_pause_fires_occasionally(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=0.0)
        max_delay = max(typer._next_delay("e", pos=1, total_len=5) for _ in range(500))
        self.assertGreater(max_delay, 0.15)

    def test_burst_splits_covers_full_word(self):
        typer = Typer()
        for _ in range(50):
            bursts = typer._split_bursts("hello")
            covered = set()
            for start, end in bursts:
                for j in range(start, end):
                    covered.add(j)
            self.assertEqual(covered, {0, 1, 2, 3, 4})

    def test_burst_gap_longer_than_internal_delay(self):
        typer = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=0.0)
        internal = typer._next_delay("e", pos=1, total_len=5, inside_burst=True)
        gap = typer._burst_gap_delay()
        self.assertGreater(gap, internal)

    def test_inside_burst_reduces_variance(self):
        low = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=100.0)
        high = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=100.0)
        lo_delays = [low._next_delay("e", pos=1, total_len=5, inside_burst=True)
                     for _ in range(200)]
        hi_delays = [high._next_delay("e", pos=1, total_len=5)
                     for _ in range(200)]
        lo_var = __import__("statistics").variance(lo_delays)
        hi_var = __import__("statistics").variance(hi_delays)
        self.assertGreater(hi_var, lo_var)

    @patch("system.typer.keyboard")
    def test_type_text_passes_burst_context(self, mock_kb):
        typer = Typer(base_speed_ms=200.0, jitter_on=True)
        original = typer._next_delay

        calls = []
        def tracking(char, prev, pos, total_len, inside_burst):
            calls.append((char, prev, pos, total_len, inside_burst))
            return original(char, prev, pos, total_len, inside_burst)

        typer._next_delay = tracking
        typer.type_text("cat", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertEqual(len(calls), 3)
        for char, prev, pos, total_len, inside_burst in calls:
            self.assertEqual(total_len, 3)
            self.assertTrue(inside_burst)
            self.assertIn(char, "cat")
        # prev is the char before within the same burst, or "" at burst start
        for i in range(1, len(calls)):
            if calls[i][1]:
                self.assertEqual(calls[i][1], calls[i - 1][0])


class TyperTypeTextTest(unittest.TestCase):
    def setUp(self):
        self.typer = Typer(base_speed_ms=50.0, jitter_on=False)
        self.typer._next_delay = MagicMock(return_value=0.001)

    @patch("system.typer.keyboard")
    def test_types_each_character(self, mock_kb):
        success, msg = self.typer.type_text("abc", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        expected_calls = [call.press_and_release("a"),
                          call.press_and_release("b"),
                          call.press_and_release("c")]
        mock_kb.assert_has_calls(expected_calls, any_order=False)
        mock_kb.send.assert_called_once_with("enter")

    @patch("system.typer.keyboard")
    def test_returns_success_message(self, mock_kb):
        success, msg = self.typer.type_text("hello", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        self.assertEqual(msg, "Typing successful")

    @patch("system.typer.keyboard")
    def test_empty_string_still_sends_enter(self, mock_kb):
        success, msg = self.typer.type_text("", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        mock_kb.send.assert_called_once_with("enter")

    @patch("system.typer.keyboard")
    def test_character_failure_returns_error(self, mock_kb):
        mock_kb.press_and_release.side_effect = Exception("mock fail")
        success, msg = self.typer.type_text("abc", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertFalse(success)
        self.assertIn("mock fail", msg)

    @patch("system.typer.keyboard")
    def test_enter_failure_returns_error(self, mock_kb):
        mock_kb.send.side_effect = Exception("enter fail")
        success, msg = self.typer.type_text("a", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertFalse(success)
        self.assertIn("enter fail", msg)

    @patch("system.typer.keyboard")
    def test_pre_delay_respected(self, mock_kb):
        import time
        typer = Typer(base_speed_ms=1000.0, jitter_on=False)
        typer._next_delay = MagicMock(return_value=0.001)
        start = time.perf_counter()
        typer.type_text("x", pre_delay_s=0.2, post_delay_s=0.01)
        elapsed = time.perf_counter() - start
        self.assertGreaterEqual(elapsed, 0.19)



class TyperTypoTest(unittest.TestCase):
    def setUp(self):
        self.typer = Typer(base_speed_ms=50.0, jitter_on=False, typo_rate=1.0)
        self.typer._next_delay = MagicMock(return_value=0.001)

    @patch("system.typer.keyboard")
    def test_typo_skips_first_character(self, mock_kb):
        self.typer.type_text("ab", pre_delay_s=0.01, post_delay_s=0.01)
        calls = [c for c in mock_kb.method_calls if c[0] == "press_and_release"]
        self.assertEqual(calls[0], call.press_and_release("a"))
        self.assertEqual(calls[1], call.press_and_release("b"))

    @patch("system.typer.keyboard")
    def test_typo_skips_words_two_letters_or_less(self, mock_kb):
        self.typer.type_text("hi", pre_delay_s=0.01, post_delay_s=0.01)
        calls = [c for c in mock_kb.method_calls if c[0] == "press_and_release"]
        self.assertEqual(len(calls), 2)

    @patch("system.typer.keyboard")
    def test_typo_picks_qwerty_neighbor(self, mock_kb):
        self.typer.type_text("cat", pre_delay_s=0.01, post_delay_s=0.01)
        calls = [c for c in mock_kb.method_calls if c[0] == "press_and_release"]
        typed = [c.args[0] for c in calls]
        self.assertIn("c", typed)
        self.assertIn("backspace", typed)

    def test_pick_typo_char_returns_valid_neighbor(self):
        wrong = self.typer._pick_typo_char("e")
        self.assertIn(wrong, ["w", "r", "s", "d", "f"])

    def test_pick_typo_char_fallback_to_same(self):
        wrong = self.typer._pick_typo_char("1")
        self.assertEqual(wrong, "1")

    @patch("system.typer.keyboard")
    def test_typo_zero_rate_disabled(self, mock_kb):
        typer = Typer(base_speed_ms=50.0, jitter_on=False, typo_rate=0.0)
        typer._next_delay = MagicMock(return_value=0.001)
        typer.type_text("test", pre_delay_s=0.01, post_delay_s=0.01)
        calls = [c for c in mock_kb.method_calls if c[0] == "press_and_release"]
        self.assertNotIn("backspace", [c.args[0] for c in calls])


if __name__ == "__main__":
    unittest.main()
