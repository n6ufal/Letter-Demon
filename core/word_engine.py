"""Word selection engine — pure logic, no UI dependencies."""

import bisect
import itertools
import random
import threading


class WordEngine:
    """Finds the best word given a prefix, dictionary, and game strategy.

    Knows nothing about tkinter, keyboard, or Roblox.
    Fully testable in isolation.
    """

    def __init__(self, wordlist: list[str], trap_endings: list[str],
                 exceptions: set[str] | None = None):
        self.wordlist: list[str] = wordlist
        self.used_words: set[str] = set()
        self.word_exceptions: set[str] = {e.lower() for e in (exceptions or set())}
        self.trap_endings: list[str] = trap_endings
        self._lock = threading.RLock()
        self._build_trap_scores()

        self._trap_score_cache: dict[str, int] = {}
        if self.wordlist:
            self._precompute_trap_scores()

    def _build_trap_scores(self) -> None:
        self._ending_scores: dict[str, int] = {
            ending: len(self.trap_endings) - i
            for i, ending in enumerate(self.trap_endings)
        }
        self._max_ending_len: int = max(
            (len(e) for e in self.trap_endings), default=8
        )

    def _precompute_trap_scores(self) -> None:
        self._trap_score_cache = {word: self._trap_score(word) for word in self.wordlist}

    def _trap_score(self, word: str) -> int:
        lower = word.lower()
        ending_scores = self._ending_scores
        max_len = self._max_ending_len

        for length in range(min(len(lower), max_len), 1, -1):
            if lower[-length:] in ending_scores:
                return ending_scores[lower[-length:]]
        return 0

    def _get_candidates_bisect(self, prefix: str) -> list[str]:
        lower_prefix = prefix.lower()

        start_idx = bisect.bisect_left(self.wordlist, lower_prefix)

        upper_prefix = lower_prefix + "~"
        end_idx = bisect.bisect_left(self.wordlist, upper_prefix)

        used = self.used_words
        exc = self.word_exceptions
        prefix_len = len(prefix)

        return [
            w for w in itertools.islice(self.wordlist, start_idx, end_idx)
            if w not in used
            and w not in exc
            and len(w) > prefix_len
        ]

    def find_completion(self, prefix: str, mode: str = "Trap Words",
                        fallback: str = "Short Words") -> str | None:
        with self._lock:
            if not self.wordlist:
                return None

            candidates = self._get_candidates_bisect(prefix)
            if not candidates:
                return None

            chosen = self._select(candidates, mode, fallback)
            self.used_words.add(chosen)
            return chosen[len(prefix):]

    def find_full_word(self, prefix: str, mode: str = "Trap Words",
                       fallback: str = "Short Words") -> str | None:
        with self._lock:
            if not self.wordlist:
                return None

            candidates = self._get_candidates_bisect(prefix)
            if not candidates:
                return None

            chosen = self._select(candidates, mode, fallback)
            self.used_words.add(chosen)
            return chosen

    def _select(self, candidates: list[str], mode: str,
                fallback: str) -> str:
        if mode == "Trap Words":
            trap_scored = [
                (s, w) for w in candidates
                if (s := self._trap_score_cache.get(w, 0)) > 0
            ]

            if trap_scored:
                best_score = max(s for s, _ in trap_scored)
                top = [w for s, w in trap_scored if s == best_score]
                return random.choice(top)
            else:
                return self._apply_fallback(candidates, fallback)

        elif mode == "Short Words":
            return min(candidates, key=len)
        elif mode == "Long Words":
            return max(candidates, key=len)
        else:
            return random.choice(candidates)

    @staticmethod
    def _apply_fallback(candidates: list[str], fallback: str) -> str:
        if fallback == "Short Words":
            return min(candidates, key=len)
        elif fallback == "Long Words":
            return max(candidates, key=len)
        else:
            return random.choice(candidates)

    def clear_used_words(self) -> None:
        with self._lock:
            self.used_words.clear()

    def used_words_for_display(self) -> tuple[list[str], int]:
        """Sorted words and count for UI; consistent under concurrent updates."""
        with self._lock:
            return sorted(self.used_words, key=str.lower), len(self.used_words)

    def has_wordlist(self) -> bool:
        with self._lock:
            return bool(self.wordlist)

    def set_trap_endings(self, endings: list[str]) -> None:
        with self._lock:
            self.trap_endings = endings
            self._build_trap_scores()
            if self.wordlist:
                self._precompute_trap_scores()

    def set_exceptions(self, exceptions: set[str]) -> None:
        with self._lock:
            self.word_exceptions = {e.lower() for e in exceptions}

    def set_wordlist(self, wordlist: list[str]) -> None:
        with self._lock:
            self.wordlist = wordlist
            if self.wordlist:
                self._precompute_trap_scores()
