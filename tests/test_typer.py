"""Tests for system/typer.py — timing logic and keyboard simulation.

Actual SendInput calls are mocked; only the timing math is verified.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

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
        # At least some values should differ from the median
        self.assertGreater(len(set(round(d, 4) for d in delays)), 1)

    def test_jitter_scales_with_percentage(self):
        low_jitter = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=5.0)
        high_jitter = Typer(base_speed_ms=200.0, jitter_on=True, jitter_pct=100.0)
        low_delays = [low_jitter._next_delay() for _ in range(200)]
        high_delays = [high_jitter._next_delay() for _ in range(200)]
        # High jitter should have a larger variance
        low_var = __import__("statistics").variance(low_delays)
        high_var = __import__("statistics").variance(high_delays)
        self.assertGreater(high_var, low_var)

    def test_default_constructor(self):
        typer = Typer()
        self.assertEqual(typer.base_speed_ms, 170.0)
        self.assertTrue(typer.jitter_on)
        self.assertEqual(typer.jitter_pct, 75.0)


class TyperTypeTextTest(unittest.TestCase):
    def setUp(self):
        self.typer = Typer(base_speed_ms=50.0, jitter_on=False)
        self.typer._next_delay = MagicMock(return_value=0.001)

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_types_each_character(self, mock_send_char, mock_send_enter):
        success, msg = self.typer.type_text("abc", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        expected_calls = [call("a"), call("b"), call("c")]
        mock_send_char.assert_has_calls(expected_calls, any_order=False)
        mock_send_enter.assert_called_once_with()

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_returns_success_message(self, mock_send_char, mock_send_enter):
        success, msg = self.typer.type_text("hello", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        self.assertEqual(msg, "Typing successful")

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_empty_string_still_sends_enter(self, mock_send_char, mock_send_enter):
        success, msg = self.typer.type_text("", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertTrue(success)
        mock_send_char.assert_not_called()
        mock_send_enter.assert_called_once_with()

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_character_failure_returns_error(self, mock_send_char, mock_send_enter):
        mock_send_char.side_effect = Exception("mock fail")
        success, msg = self.typer.type_text("abc", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertFalse(success)
        self.assertIn("mock fail", msg)

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_enter_failure_returns_error(self, mock_send_char, mock_send_enter):
        mock_send_enter.side_effect = Exception("enter fail")
        success, msg = self.typer.type_text("a", pre_delay_s=0.01, post_delay_s=0.01)
        self.assertFalse(success)
        self.assertIn("enter fail", msg)

    @patch("system.typer._send_enter")
    @patch("system.typer._send_char_unicode")
    def test_pre_delay_respected(self, mock_send_char, mock_send_enter):
        import time
        typer = Typer(base_speed_ms=1000.0, jitter_on=False)
        typer._next_delay = MagicMock(return_value=0.001)
        start = time.perf_counter()
        typer.type_text("x", pre_delay_s=0.2, post_delay_s=0.01)
        elapsed = time.perf_counter() - start
        self.assertGreaterEqual(elapsed, 0.19)


if __name__ == "__main__":
    unittest.main()
