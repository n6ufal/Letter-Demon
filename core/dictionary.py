"""Dictionary loading and caching — parses .txt/.json word lists."""

import hashlib
import json
import logging
from pathlib import Path

from config.settings import get_project_root

logger = logging.getLogger(__name__)

CACHE_DIR = get_project_root() / "data" / "runtime" / "cache"


def get_cache_path(dict_path: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path_hash = hashlib.md5(Path(dict_path).absolute().as_posix().encode()).hexdigest()[:10]
    return CACHE_DIR / f"cache_{path_hash}.txt"


def _cache_is_valid(cache_path: Path, dict_path: str) -> bool:
    if not cache_path.exists():
        return False
    try:
        dict_mtime = Path(dict_path).stat().st_mtime
        return cache_path.stat().st_mtime >= dict_mtime
    except OSError:
        return False


def _load_dict_file(dict_path: str) -> set[str]:
    p = Path(dict_path)
    if p.suffix.lower() == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower() for k in data.keys()}
    else:
        with open(p, "r", encoding="utf-8") as f:
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

    tmp_path = cache_path.with_suffix(".txt.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(wordlist))
        tmp_path.replace(cache_path)
    except Exception as ex:
        logger.warning("Could not save cache: %s", ex)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    return wordlist, False
