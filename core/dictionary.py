"""Dictionary loading and caching — parses .txt/.json word lists."""

import hashlib
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def get_cache_path(dict_path: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path_hash = hashlib.md5(os.path.abspath(dict_path).encode()).hexdigest()[:10]
    # SECURITY FIX: Use .txt instead of dangerous .pkl
    return os.path.join(CACHE_DIR, f"cache_{path_hash}.txt")


def _cache_is_valid(cache_path: str, dict_path: str) -> bool:
    if not os.path.exists(cache_path):
        return False
    try:
        return os.path.getmtime(cache_path) >= os.path.getmtime(dict_path)
    except Exception:
        return False


def _compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of file content."""
    sha = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return ""


def _verify_cache_hash(cache_hash_path: str, expected_hash: str) -> bool:
    """Verify stored cache hash matches expected hash."""
    try:
        with open(cache_hash_path, "r") as f:
            stored_hash = f.read().strip()
        return stored_hash == expected_hash and stored_hash != ""
    except Exception:
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
    cache_hash_path = cache_path.replace('.txt', '.hash')

    # OPTIMIZATION: Check the fast, free OS file-stamp first.
    # If the cache is older than the dictionary, skip the heavy SHA256 hash entirely.
    if _cache_is_valid(cache_path, dict_path) and os.path.exists(cache_hash_path):
        dict_hash = _compute_file_hash(dict_path)

        if _verify_cache_hash(cache_hash_path, dict_hash):
            try:
                # SECURITY FIX: Safely read from a plain text file
                with open(cache_path, "r", encoding="utf-8") as f:
                    wordlist = f.read().splitlines()
                return wordlist, True
            except Exception:
                pass  # Fall through to rebuild cache if reading fails

    # If no cache exists or is outdated, read from the raw dictionary file
    words_set = _load_dict_file(dict_path)
    wordlist = sorted(words_set)

    try:
        # SECURITY FIX: Save safely as a plain text file, separated by newlines
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("\n".join(wordlist))
        # Only compute the hash when we actually need to save the new cache
        dict_hash = _compute_file_hash(dict_path)
        with open(cache_hash_path, "w") as f:
            f.write(dict_hash)
    except Exception as ex:
        print("Warning: could not save cache:", ex)

    return wordlist, False
