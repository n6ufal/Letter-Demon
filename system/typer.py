"""Keyboard simulation with humanized timing.

Uses Windows SendInput API directly instead of the `keyboard` library
for reliable keystroke injection without admin rights.
"""

import ctypes
import ctypes.wintypes
import logging
import math
import random
import threading
import time

logger = logging.getLogger(__name__)

_MIN_KEYSTROKE_DELAY_S = 0.03  # 30ms — absolute human+OS input lag floor

# ---------------------------------------------------------------------------
# SendInput constants & structures
# ---------------------------------------------------------------------------

INPUT_KEYBOARD = 1
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("u", INPUT_UNION),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_SendInput = _user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint

_PeekMessageW = _user32.PeekMessageW
_PeekMessageW.argtypes = [
    ctypes.POINTER(ctypes.wintypes.MSG),
    ctypes.wintypes.HWND,
    ctypes.c_uint,
    ctypes.c_uint,
    ctypes.c_uint,
]
_PeekMessageW.restype = ctypes.c_bool

_thread_local = threading.local()


def _ensure_message_queue() -> None:
    """Ensure the calling thread has a Windows message queue.

    SendInput silently fails on threads that have never called
    PeekMessage / GetMessage.  Call this once per thread before
    the first SendInput call.
    """
    if not getattr(_thread_local, "_has_msg_queue", False):
        msg = ctypes.wintypes.MSG()
        _PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        _thread_local._has_msg_queue = True


def _make_input(dwFlags: int, wVk: int = 0, wScan: int = 0) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(wVk=wVk, wScan=wScan, dwFlags=dwFlags, time=0, dwExtraInfo=None),
    )


def _send_char_unicode(char: str) -> None:
    """Send a single character via KEYEVENTF_UNICODE."""
    code = ord(char)
    down = _make_input(KEYEVENTF_UNICODE, wScan=code)
    up = _make_input(KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, wScan=code)
    inputs = (INPUT * 2)(down, up)
    sent = _SendInput(2, inputs, ctypes.sizeof(INPUT))
    if sent == 0:
        err = ctypes.get_last_error()
        raise RuntimeError(
            f"SendInput returned 0 for U+{code:04X} "
            f"(last_error={err})"
        )


def _send_enter() -> None:
    """Send an Enter (VK_RETURN) keystroke."""
    down = _make_input(KEYEVENTF_KEYDOWN, wVk=VK_RETURN, wScan=0x1C)
    up = _make_input(KEYEVENTF_KEYUP, wVk=VK_RETURN, wScan=0x1C)
    inputs = (INPUT * 2)(down, up)
    sent = _SendInput(2, inputs, ctypes.sizeof(INPUT))
    if sent == 0:
        err = ctypes.get_last_error()
        raise RuntimeError(
            f"SendInput returned 0 for VK_RETURN "
            f"(last_error={err})"
        )


# ---------------------------------------------------------------------------
# Typer
# ---------------------------------------------------------------------------


class Typer:
    """Types text character-by-character with configurable speed and jitter.

    Uses a Log-Normal distribution to model human typing.
    The median typing speed is always anchored to base_speed_ms.
    The jitter_pct slider controls the "erraticness" (variance).
    """

    def __init__(self, base_speed_ms: float = 170.0,
                 jitter_on: bool = True, jitter_pct: float = 75.0):
        self.base_speed_ms = base_speed_ms
        self.jitter_on = jitter_on
        self.jitter_pct = jitter_pct  # Expects 5.0 to 100.0

    def type_text(self, text: str, pre_delay_s: float = 0.5,
                  post_delay_s: float = 0.5) -> tuple[bool, str]:
        """Type *text* into the currently focused window.

        Returns (success: bool, message: str).
        Blocks the calling thread. Typically run on a daemon thread.
        """
        _ensure_message_queue()
        time.sleep(max(0.1, pre_delay_s))
        try:
            for i, ch in enumerate(text):
                try:
                    _send_char_unicode(ch)
                except Exception as e:
                    return False, f"Failed at char {i+1}/{len(text)}: '{ch}' — {e}"
                time.sleep(self._next_delay())
            try:
                _send_enter()
            except Exception as e:
                return False, f"Failed to send Enter key: {e}"
            time.sleep(max(0.1, post_delay_s))
            return True, "Typing successful"
        except Exception as e:
            return False, f"Unexpected error during typing: {e}"

    def _next_delay(self) -> float:
        # Convert ms to seconds for time.sleep()
        base_s = max(_MIN_KEYSTROKE_DELAY_S, self.base_speed_ms / 1000.0)

        if not self.jitter_on:
            return base_s

        # Map the 5-100 UI slider to a log-normal sigma.
        # 0.0 = perfectly robotic. 0.75 = highly erratic/drunk.
        scale = (self.jitter_pct / 100.0) * 0.75

        # Shift mu so the MEAN of the distribution equals base_s
        # (exp(mu + sigma^2/2) = base_s), making the slider an honest average.
        mu = math.log(base_s) - 0.5 * scale ** 2

        delay = random.lognormvariate(mu, scale)

        # Absolute physical limit: Even the fastest human twitch + OS input lag
        # takes about 30ms. Never go below this to prevent robotic spam.
        return max(_MIN_KEYSTROKE_DELAY_S, delay)
