"""Application session — coordinates engine, typer, settings, and play state."""

import threading
from pathlib import Path

from core.dictionary import load_wordlist_from_dict
from core.word_engine import WordEngine
from config.settings import SettingsManager, SETTINGS_FILE
from config.trap_endings import load_trap_endings
from config.exceptions import load_exceptions
from system.typer import Typer


class AppSession:
    """Holds all business-logic state: engine, typer, settings, play guard.

    Knows nothing about tkinter. All callbacks run in the caller's thread.
    """

    def __init__(self, settings: SettingsManager | None = None) -> None:
        self.settings = settings or SettingsManager(SETTINGS_FILE)
        self.engine = WordEngine(
            wordlist=[],
            trap_endings=load_trap_endings(),
            exceptions=load_exceptions(),
        )
        self.typer = Typer()

        self._is_playing = False
        self._playing_lock = threading.RLock()

        self.dict_path: str | None = self.settings.get("dict_path", None)  # type: ignore[assignment]
        self.window_title: str = self.settings.get("window_title", "Roblox")  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Dictionary
    # ------------------------------------------------------------------

    def has_wordlist(self) -> bool:
        return self.engine.has_wordlist()

    def load_dictionary(self, path: str) -> tuple[list[str], bool]:
        """Load synchronously. Returns (wordlist, from_cache)."""
        wordlist, from_cache = load_wordlist_from_dict(path)
        self.engine.set_wordlist(wordlist)
        self.dict_path = path
        return wordlist, from_cache

    # ------------------------------------------------------------------
    # Play round
    # ------------------------------------------------------------------

    def prepare_play_round(
        self,
        prefix: str,
        mode: str,
        fallback: str,
        auto_type_prefix: bool,
    ) -> str | None:
        """Thread-safe: find the word and mark the session as playing.

        Returns the text to type, or None if no match / already playing.
        """
        with self._playing_lock:
            if self._is_playing:
                return None
            if auto_type_prefix:
                word = self.engine.find_completion(prefix, mode, fallback)
            else:
                word = self.engine.find_full_word(prefix, mode, fallback)
            if word is not None:
                self._is_playing = True
            return word

    def finish_play_round(self) -> None:
        with self._playing_lock:
            self._is_playing = False

    def configure_typer(
        self,
        speed_ms: float,
        jitter_intensity: int,
        pre_delay_s: float,
        post_delay_s: float,
    ) -> None:
        self.typer.base_speed_ms = speed_ms
        self.typer.jitter_on = jitter_intensity > 0
        self.typer.jitter_pct = jitter_intensity
        self._pre_delay = max(0.1, pre_delay_s)
        self._post_delay = max(0.1, post_delay_s)

    @property
    def pre_delay(self) -> float:
        return getattr(self, "_pre_delay", 0.5)

    @property
    def post_delay(self) -> float:
        return getattr(self, "_post_delay", 0.5)

    # ------------------------------------------------------------------
    # Trap endings / exceptions
    # ------------------------------------------------------------------

    def reload_trap_endings(self) -> None:
        endings = load_trap_endings()
        self.engine.set_trap_endings(endings)

    def reload_exceptions(self) -> None:
        exceptions = load_exceptions()
        self.engine.set_exceptions(exceptions)

    # ------------------------------------------------------------------
    # Used words
    # ------------------------------------------------------------------

    def clear_used_words(self) -> None:
        self.engine.clear_used_words()

    def used_words_for_display(self) -> tuple[list[str], int]:
        return self.engine.used_words_for_display()

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def persist_settings(self, ui_state: dict[str, object]) -> None:
        """Write current session + UI state to settings file."""
        self.settings.set("dict_path", self.dict_path)
        self.settings.set("window_title", self.window_title)
        self.settings.update(ui_state)
        self.settings.save()

    def try_load_dict_at_startup(self) -> str | None:
        """Return dict_path if it exists on disk, else None."""
        if self.dict_path and Path(self.dict_path).exists():
            return self.dict_path
        self.dict_path = None
        return None
