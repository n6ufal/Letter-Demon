"""Roblox window detection and focus via WinAPI."""

import ctypes

_SW_RESTORE = 9  # WinAPI SW_RESTORE


def _user32() -> ctypes.WinDLL:
    return ctypes.WinDLL("user32", use_last_error=True)


def is_roblox_running() -> bool:
    """Check whether a Roblox window exists (via FindWindowW)."""
    try:
        return _user32().FindWindowW(None, "Roblox") != 0
    except Exception:
        return False


def focus_roblox_window() -> None:
    """Bring the Roblox window to the foreground (restore if minimized)."""
    try:
        user32 = _user32()
        hwnd = user32.FindWindowW(None, "Roblox")
        if hwnd:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, _SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass



