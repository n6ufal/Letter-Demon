"""Binary-search dictionary lookup — finds words by prefix and/or suffix.

Standalone pure-logic module with zero UI imports. Used by tools/lookup.pyw.
"""

import bisect
import logging
import threading

logger = logging.getLogger(__name__)


class DictLookup:

    def __init__(self, wordlist=None):
        self._lock = threading.RLock()
        self._wordlist = wordlist or []
        self._reversed_pairs = None

    def set_wordlist(self, wordlist):
        with self._lock:
            self._wordlist = wordlist
            self._reversed_pairs = None

    def get_word_count(self):
        with self._lock:
            return len(self._wordlist)

    def has_wordlist(self):
        with self._lock:
            return len(self._wordlist) > 0

    def find_starting_with(self, prefix, limit=200):
        with self._lock:
            if not prefix or not self._wordlist:
                return []
            prefix = prefix.lower()
            left = bisect.bisect_left(self._wordlist, prefix)
            right = bisect.bisect_left(self._wordlist, prefix + '\xff')
            return self._wordlist[left:right][:limit]

    def find_ending_with(self, suffix, limit=200):
        with self._lock:
            if not suffix or not self._wordlist:
                return []
            self._ensure_reversed()
            suffix = suffix.lower()
            rev_suffix = suffix[::-1]
            left = bisect.bisect_left(self._reversed_pairs, (rev_suffix,))
            right = bisect.bisect_left(self._reversed_pairs, (rev_suffix + '\xff',))
            return [pair[1] for pair in self._reversed_pairs[left:right]][:limit]

    def find_starting_and_ending_with(self, prefix, suffix, limit=500):
        with self._lock:
            if not prefix and not suffix:
                return [], 0
            if prefix and not suffix:
                prefix = prefix.lower()
                left = bisect.bisect_left(self._wordlist, prefix)
                right = bisect.bisect_left(self._wordlist, prefix + '\xff')
                total = right - left
                return self._wordlist[left:right][:limit], total
            if suffix and not prefix:
                self._ensure_reversed()
                suffix = suffix.lower()
                rev_suffix = suffix[::-1]
                r_left = bisect.bisect_left(self._reversed_pairs, (rev_suffix,))
                r_right = bisect.bisect_left(self._reversed_pairs, (rev_suffix + '\xff',))
                total = r_right - r_left
                return [pair[1] for pair in self._reversed_pairs[r_left:r_right]][:limit], total

            prefix = prefix.lower()
            suffix = suffix.lower()

            left = bisect.bisect_left(self._wordlist, prefix)
            right = bisect.bisect_left(self._wordlist, prefix + '\xff')
            candidates = self._wordlist[left:right]
            if not candidates:
                return [], 0

            self._ensure_reversed()
            rev_suffix = suffix[::-1]
            r_left = bisect.bisect_left(self._reversed_pairs, (rev_suffix,))
            r_right = bisect.bisect_left(self._reversed_pairs, (rev_suffix + '\xff',))
            rev_set = {pair[0] for pair in self._reversed_pairs[r_left:r_right]}

            results = [w for w in candidates if w[::-1] in rev_set]
            total = len(results)
            return results[:limit], total

    def _ensure_reversed(self):
        if self._reversed_pairs is None:
            self._reversed_pairs = sorted((w[::-1], w) for w in self._wordlist)
