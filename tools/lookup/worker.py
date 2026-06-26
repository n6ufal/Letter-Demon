"""Queue-based search worker — one thread, no pileup."""
import queue
import sys
import threading


class SearchWorker:
    """Background worker that drains a queue, discarding stale searches.

    Only the most recently submitted search runs to completion; earlier
    submissions are skipped as soon as a newer generation arrives.
    """

    RESULT_LIMIT = 1000

    def __init__(self, lookup):
        self._lookup = lookup
        self._queue = queue.Queue()
        self._generation = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, prefix, suffix, contains, min_len, max_len,
               match_case, on_result, on_error):
        self._generation += 1
        gen = self._generation
        self._queue.put((gen, prefix, suffix, contains, min_len,
                         max_len, match_case, on_result, on_error))

    def _run(self):
        while True:
            item = self._queue.get()
            gen, prefix, suffix, contains, min_len, max_len, \
                match_case, on_result, on_error = item
            if gen != self._generation:
                continue
            try:
                has_secondary = bool(contains) or bool(min_len) or bool(max_len)
                limit = sys.maxsize if has_secondary else self.RESULT_LIMIT
                results, total = self._lookup.find_starting_and_ending_with(
                    prefix, suffix, limit=limit,
                )
                filtered = self._apply_filters(
                    results, contains, min_len, max_len, match_case,
                )
                if has_secondary and len(filtered) > self.RESULT_LIMIT:
                    filtered = filtered[:self.RESULT_LIMIT]
                on_result(filtered, total)
            except Exception as e:
                on_error(str(e))

    @staticmethod
    def _apply_filters(results, contains, min_len, max_len, match_case):
        if not contains and not min_len and not max_len:
            return results
        filtered = []
        for word in results:
            w = word if match_case else word.lower()
            if contains:
                needle = contains if match_case else contains.lower()
                if needle not in w:
                    continue
            if min_len and len(word) < min_len:
                continue
            if max_len and len(word) > max_len:
                continue
            filtered.append(word)
        return filtered
