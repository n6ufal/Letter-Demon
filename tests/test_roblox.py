"""Tests for system/roblox.py — Roblox window detection and focus."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from system.roblox import is_roblox_running, focus_roblox_window


class RobloxDetectionTest(unittest.TestCase):
    """Test Roblox window detection via WinAPI."""

    @patch("system.roblox._user32")
    def test_is_roblox_running_returns_true_when_found(self, mock_user32_fn):
        """FindWindowW returns non-zero when Roblox window exists."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 12345  # Non-zero = found
        mock_user32_fn.return_value = mock_user32

        result = is_roblox_running()

        self.assertTrue(result)
        mock_user32.FindWindowW.assert_called_once_with(None, "Roblox")

    @patch("system.roblox._user32")
    def test_is_roblox_running_returns_false_when_not_found(self, mock_user32_fn):
        """FindWindowW returns 0 when Roblox window not found."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 0  # Zero = not found
        mock_user32_fn.return_value = mock_user32

        result = is_roblox_running()

        self.assertFalse(result)
        mock_user32.FindWindowW.assert_called_once_with(None, "Roblox")

    @patch("system.roblox._user32")
    def test_is_roblox_running_handles_exception(self, mock_user32_fn):
        """Exception in WinAPI call returns False gracefully."""
        mock_user32_fn.side_effect = Exception("WinAPI error")

        result = is_roblox_running()

        self.assertFalse(result)

    @patch("system.roblox._user32")
    def test_is_roblox_running_handles_access_denied(self, mock_user32_fn):
        """Access denied (permission error) returns False gracefully."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.side_effect = OSError("Access denied")
        mock_user32_fn.return_value = mock_user32

        result = is_roblox_running()

        self.assertFalse(result)


class RobloxFocusTest(unittest.TestCase):
    """Test bringing Roblox window to foreground."""

    @patch("system.roblox._user32")
    def test_focus_roblox_window_found_and_visible(self, mock_user32_fn):
        """Focus normal (not minimized) Roblox window."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 12345
        mock_user32.IsIconic.return_value = False  # Not minimized
        mock_user32_fn.return_value = mock_user32

        focus_roblox_window()

        # Verify FindWindowW called
        mock_user32.FindWindowW.assert_called_once_with(None, "Roblox")
        # Verify IsIconic checked (window not minimized)
        mock_user32.IsIconic.assert_called_once_with(12345)
        # Verify SetForegroundWindow called
        mock_user32.SetForegroundWindow.assert_called_once_with(12345)
        # Verify ShowWindow NOT called (already visible)
        mock_user32.ShowWindow.assert_not_called()

    @patch("system.roblox._user32")
    def test_focus_roblox_window_minimized(self, mock_user32_fn):
        """Restore and focus minimized Roblox window."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 12345
        mock_user32.IsIconic.return_value = True  # Minimized
        mock_user32_fn.return_value = mock_user32

        focus_roblox_window()

        # Verify ShowWindow called to restore
        mock_user32.ShowWindow.assert_called_once_with(12345, 9)  # 9 = SW_RESTORE
        # Verify SetForegroundWindow called
        mock_user32.SetForegroundWindow.assert_called_once_with(12345)

    @patch("system.roblox._user32")
    def test_focus_roblox_window_not_found(self, mock_user32_fn):
        """If Roblox window not found, no error raised."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 0  # Not found
        mock_user32_fn.return_value = mock_user32

        # Should not raise
        focus_roblox_window()

        # FindWindowW called, but no other calls made
        mock_user32.FindWindowW.assert_called_once()
        mock_user32.SetForegroundWindow.assert_not_called()

    @patch("system.roblox._user32")
    def test_focus_roblox_window_handles_exception(self, mock_user32_fn):
        """Exception in focus operation is silently caught."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.side_effect = Exception("WinAPI error")
        mock_user32_fn.return_value = mock_user32

        # Should not raise
        focus_roblox_window()

    @patch("system.roblox._user32")
    def test_focus_roblox_window_handles_setforeground_failure(self, mock_user32_fn):
        """If SetForegroundWindow fails, error is silently caught."""
        mock_user32 = MagicMock()
        mock_user32.FindWindowW.return_value = 12345
        mock_user32.IsIconic.return_value = False
        mock_user32.SetForegroundWindow.side_effect = Exception("Focus failed")
        mock_user32_fn.return_value = mock_user32

        # Should not raise
        focus_roblox_window()


class RobloxIntegrationTest(unittest.TestCase):
    """Integration tests for Roblox detection and focus workflow."""

    @patch("system.roblox._user32")
    def test_detect_then_focus_workflow(self, mock_user32_fn):
        """Typical workflow: detect Roblox, then focus it."""
        mock_user32 = MagicMock()
        # First call (detect): found
        # Second call (focus): found
        mock_user32.FindWindowW.side_effect = [12345, 12345]
        mock_user32.IsIconic.return_value = False
        mock_user32_fn.return_value = mock_user32

        # Detect
        is_running = is_roblox_running()
        self.assertTrue(is_running)

        # Focus
        focus_roblox_window()
        self.assertEqual(mock_user32.FindWindowW.call_count, 2)

    @patch("system.roblox._user32")
    def test_resilient_to_intermittent_failures(self, mock_user32_fn):
        """Roblox detection/focus resilient to occasional WinAPI failures."""
        mock_user32 = MagicMock()
        
        # First call fails, second succeeds
        mock_user32.FindWindowW.side_effect = [
            Exception("Temporary failure"),
            12345,
        ]
        mock_user32_fn.return_value = mock_user32

        # First detection: exception → returns False
        result1 = is_roblox_running()
        self.assertFalse(result1)

        # Second detection: succeeds
        result2 = is_roblox_running()
        self.assertTrue(result2)


if __name__ == "__main__":
    unittest.main()
