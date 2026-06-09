"""Dictionary loading and caching — parses .txt/.json word lists."""

import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def get_cache_path(dict_path: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path_hash = hashlib.md5(os.path.abspath(dict_path).encode()).hexdigest()[:10]
    return os.path.join(CACHE_DIR, f"cache_{path_hash}.txt")


def _cache_is_valid(cache_path: str, dict_path: str) -> bool:
    if not os.path.exists(cache_path):
        return False
    try:
        return os.path.getmtime(cache_path) >= os.path.getmtime(dict_path)
    except OSError:
        return False


def _load_dict_file(dict_path: str) -> set[str]:
    ext = os.path.splitext(dict_path)[1].lower()
    if ext == ".json":
        with open(dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower() for k in data.keys()}
    else:
        with open(dict_path, "r", encoding="utf-8") as f:
            # OPTIMIZATION: maxsplit=1 stops splitting after the first word.
            # Much faster and uses less memory than .split() if your txt
            # file has extra data per line (e.g., "word frequency").
            return {
                line.split(maxsplit=1)[0].lower()
                for line in f
                if line.strip() and not line.startswith("#")
            }


def load_wordlist_from_dict(dict_path: str) -> tuple[list[str], bool]:
    """Load and sort a word list from disk. Returns (wordlist, from_cache)."""
    cache_path = get_cache_path(dict_path)

    if _cache_is_valid(cache_path, dict_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                wordlist = f.read().splitlines()
            if len(wordlist) > 0:
                return wordlist, True
        except Exception:
            pass

    words_set = _load_dict_file(dict_path)
    wordlist = sorted(words_set)

    tmp_path = cache_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(wordlist))
        os.replace(tmp_path, cache_path)
    except Exception as ex:
        logger.warning("Could not save cache: %s", ex)
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return wordlist, False
