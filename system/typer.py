"""Keyboard simulation with humanized timing."""

import math
import random
import time
import keyboard


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
        # Convert ms to seconds for time.sleep()
        base_s = max(0.03, self.base_speed_ms / 1000.0)

        if not self.jitter_on:
            return base_s

        # Map the 5-100 UI slider to a log-normal sigma.
        # 0.0 = perfectly robotic. 0.75 = highly erratic/drunk.
        scale = (self.jitter_pct / 100.0) * 0.75

        # Log-Normal magic:
        # By setting mu = log(base_s), the MEDIAN of the distribution
        # is guaranteed to be exactly base_s, keeping it anchored to the speed slider.
        mu = math.log(base_s)

        delay = random.lognormvariate(mu, scale)

        # Absolute physical limit: Even the fastest human twitch + OS input lag
        # takes about 30ms. Never go below this to prevent robotic spam.
        return max(0.03, delay)
