"""Keyboard simulation with humanized timing."""

import random
import time

import keyboard


class Typer:
    """Types text character-by-character with configurable speed and jitter.

    The Gaussian jitter model means most keystrokes land near the base
    speed, with rare deviations. Sigma is independent of base speed.
    """

    def __init__(self, base_speed_ms: float = 170.0,
                 jitter_on: bool = True, jitter_sigma_ms: float = 75.0):
        self.base_speed_ms = base_speed_ms
        self.jitter_on = jitter_on
        self.jitter_sigma_ms = jitter_sigma_ms

    def type_text(self, text: str, pre_delay_s: float = 0.5,
                  post_delay_s: float = 0.5) -> tuple[bool, str]:
        """Type *text* into the currently focused window.

        Returns (success: bool, message: str).
        Blocks the calling thread. Typically run on a daemon thread.
        """
        time.sleep(max(0.1, pre_delay_s))
        try:
            for i, ch in enumerate(text):
                try:
                    keyboard.press_and_release(ch)
                except Exception as e:
                    return False, f"Failed at char {i+1}/{len(text)}: '{ch}' — {e}"
                time.sleep(self._next_delay())
            try:
                keyboard.send("enter")
            except Exception as e:
                return False, f"Failed to send Enter key: {e}"
            time.sleep(max(0.1, post_delay_s))
            return True, "Typing successful"
        except Exception as e:
            return False, f"Unexpected error during typing: {e}"

    def _next_delay(self) -> float:
        base = max(0.005, self.base_speed_ms / 1000.0)
        if self.jitter_on:
            sigma = self.jitter_sigma_ms / 1000.0
            return max(0.005, random.gauss(base, sigma))
        return base
