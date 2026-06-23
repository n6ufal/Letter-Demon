"""Keyboard simulation with humanized timing.

Uses the `keyboard` library for keystroke injection,
which sends scan codes compatible with Raw Input (required by Roblox).
"""

import logging
import math
import random
import time

import keyboard

logger = logging.getLogger(__name__)

_MIN_KEYSTROKE_DELAY_S = 0.03

_CHAR_RARITY = {
    "e": 0.78, "t": 0.80, "a": 0.82, "o": 0.84, "i": 0.84,
    "n": 0.85, "s": 0.85, "h": 0.87, "r": 0.87, "d": 0.90, "l": 0.92,
    "c": 1.10, "f": 1.10, "g": 1.10, "m": 1.10, "w": 1.10,
    "y": 1.10, "p": 1.12, "b": 1.12, "v": 1.20, "k": 1.20,
    "j": 1.40, "q": 1.50, "x": 1.40, "z": 1.50,
}

_BIGRAM_SPEED = {
    "th": 0.75, "he": 0.78, "in": 0.80, "er": 0.82, "an": 0.82,
    "re": 0.84, "ed": 0.85, "on": 0.85, "es": 0.85, "st": 0.85,
    "en": 0.87, "at": 0.87, "to": 0.87, "nt": 0.87, "ha": 0.88,
    "nd": 0.88, "ou": 0.88, "ea": 0.88, "ng": 0.90, "al": 0.90,
    "it": 0.90, "as": 0.90, "is": 0.90, "hi": 0.90, "ar": 0.92,
    "zv": 1.50, "xq": 1.50, "wz": 1.50, "yj": 1.40, "qf": 1.40,
    "qz": 1.50, "qx": 1.50, "jv": 1.40, "zj": 1.40, "xz": 1.40,
}

_MICRO_PAUSE_CHANCE = 0.03

_BURST_SIZES = [2, 3, 4]
_BURST_WEIGHTS = [3, 5, 2]
_BURST_GAP_RANGE = (1.5, 3.0)
_BURST_SCALE_RATIO = 0.6

_TYPO_NEIGHBORS = {
    "q": ["w", "a", "s"],
    "w": ["q", "e", "a", "s", "d"],
    "e": ["w", "r", "s", "d", "f"],
    "r": ["e", "t", "d", "f", "g"],
    "t": ["r", "y", "f", "g", "h"],
    "y": ["t", "u", "g", "h", "j"],
    "u": ["y", "i", "h", "j", "k"],
    "i": ["u", "o", "j", "k", "l"],
    "o": ["i", "p", "k", "l"],
    "p": ["o", "l"],
    "a": ["q", "w", "s", "z", "x"],
    "s": ["a", "w", "e", "d", "x", "z"],
    "d": ["s", "e", "r", "f", "x", "c"],
    "f": ["d", "r", "t", "g", "c", "v"],
    "g": ["f", "t", "y", "h", "v", "b"],
    "h": ["g", "y", "u", "j", "b", "n"],
    "j": ["h", "u", "i", "k", "n", "m"],
    "k": ["j", "i", "o", "l", "m"],
    "l": ["k", "o", "p"],
    "z": ["a", "s", "x"],
    "x": ["z", "s", "d", "c"],
    "c": ["x", "d", "f", "v"],
    "v": ["c", "f", "g", "b"],
    "b": ["v", "g", "h", "n"],
    "n": ["b", "h", "j", "m"],
    "m": ["n", "j", "k"],
}

_TYPO_KEY_POSITION = {
    "q": (0, 0), "w": (0, 1), "e": (0, 2), "r": (0, 3), "t": (0, 4),
    "y": (0, 5), "u": (0, 6), "i": (0, 7), "o": (0, 8), "p": (0, 9),
    "a": (1, 0), "s": (1, 1), "d": (1, 2), "f": (1, 3), "g": (1, 4),
    "h": (1, 5), "j": (1, 6), "k": (1, 7), "l": (1, 8),
    "z": (2, 0), "x": (2, 1), "c": (2, 2), "v": (2, 3), "b": (2, 4),
    "n": (2, 5), "m": (2, 6),
}


class Typer:
    """Types text with humanized burst + bigram timing."""

    def __init__(self, base_speed_ms: float = 170.0,
                 jitter_on: bool = True, jitter_pct: float = 75.0,
                 typo_rate: float = 0.0, typo_pause_s: float = 0.3):
        self.base_speed_ms = base_speed_ms
        self.jitter_on = jitter_on
        self.jitter_pct = min(jitter_pct, 100.0)
        self.typo_rate = max(0.0, typo_rate)
        self.typo_pause_s = max(0.05, typo_pause_s)

    def type_text(self, text: str, pre_delay_s: float = 0.5,
                  post_delay_s: float = 0.5) -> tuple[bool, str]:
        time.sleep(max(0.1, pre_delay_s))
        try:
            if self.jitter_on:
                bursts = self._split_bursts(text)
                for start, end in bursts:
                    for i in range(start, end):
                        ch = text[i]
                        prev = text[i - 1] if i > start else ""
                        typo_err = self._maybe_typo(ch, i, len(text))
                        if typo_err:
                            return typo_err
                        try:
                            keyboard.press_and_release(ch)
                        except Exception as e:
                            return (False,
                                    f"Failed at char {i+1}/{len(text)}: '{ch}' — {e}")
                        time.sleep(self._next_delay(ch, prev, i, len(text), True))
                    if end < len(text):
                        time.sleep(self._burst_gap_delay())
            else:
                for i, ch in enumerate(text):
                    typo_err = self._maybe_typo(ch, i, len(text))
                    if typo_err:
                        return typo_err
                    try:
                        keyboard.press_and_release(ch)
                    except Exception as e:
                        return (False,
                                f"Failed at char {i+1}/{len(text)}: '{ch}' — {e}")
                    time.sleep(self._next_delay(ch))
            try:
                keyboard.send("enter")
            except Exception as e:
                return False, f"Failed to send Enter key: {e}"
            time.sleep(max(0.1, post_delay_s))
            return True, "Typing successful"
        except Exception as e:
            return False, f"Unexpected error during typing: {e}"

    def _maybe_typo(self, ch: str, i: int, total_len: int
                    ) -> tuple[bool, str] | None:
        """If conditions are met, type a wrong char + backspace + pause.
        Returns an error tuple on failure, or None on success/no-typo."""
        if not (self.typo_rate > 0 and i > 0 and total_len > 2
                and random.random() < self.typo_rate):
            return None
        wrong = self._pick_typo_char(ch)
        try:
            keyboard.press_and_release(wrong)
        except Exception as e:
            return (False, f"Typo failed at char {i+1}/{total_len}: '{wrong}' — {e}")
        time.sleep(self.typo_pause_s)
        try:
            keyboard.press_and_release("backspace")
        except Exception as e:
            return (False, f"Backspace after typo failed — {e}")
        time.sleep(self.typo_pause_s * 0.3)
        return None

    @staticmethod
    def _pick_typo_char(correct: str) -> str:
        neighbors = _TYPO_NEIGHBORS.get(correct.lower(), [])
        if neighbors:
            return random.choice(neighbors)
        return correct

    @staticmethod
    def _split_bursts(text: str) -> list[tuple[int, int]]:
        bursts = []
        i = 0
        n = len(text)
        while i < n:
            size = min(random.choices(_BURST_SIZES, _BURST_WEIGHTS)[0], n - i)
            bursts.append((i, i + size))
            i += size
        return bursts

    def _burst_gap_delay(self) -> float:
        base_s = max(_MIN_KEYSTROKE_DELAY_S, self.base_speed_ms / 1000.0)
        return base_s * random.uniform(*_BURST_GAP_RANGE)

    def _next_delay(self, char: str = "", prev: str = "",
                    pos: int = 0, total_len: int = 0,
                    inside_burst: bool = False) -> float:
        base_s = max(_MIN_KEYSTROKE_DELAY_S, self.base_speed_ms / 1000.0)
        adjusted = base_s

        if char:
            if prev:
                adjusted *= _BIGRAM_SPEED.get((prev + char).lower(), 1.0)
            else:
                adjusted *= _CHAR_RARITY.get(char.lower(), 1.0)

            if total_len > 2 and pos >= total_len - 2:
                adjusted *= 1.15

        if not self.jitter_on:
            return max(_MIN_KEYSTROKE_DELAY_S, adjusted)

        scale = (self.jitter_pct / 100.0) * 0.5
        if inside_burst:
            scale *= _BURST_SCALE_RATIO
        mu = math.log(adjusted) - 0.5 * scale ** 2
        delay = random.lognormvariate(mu, scale)

        if char and random.random() < _MICRO_PAUSE_CHANCE:
            delay += random.uniform(0.1, 0.4)

        _floor = max(_MIN_KEYSTROKE_DELAY_S, adjusted * 0.25)
        return max(_floor, delay)
