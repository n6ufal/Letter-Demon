"""Word exceptions — load/save exceptions.txt."""

import logging

from .settings import get_project_root

logger = logging.getLogger(__name__)

EXCEPTIONS_FILE = get_project_root() / "data" / "exceptions.txt"

DEFAULT_EXCEPTIONS: list[str] = []


def load_exceptions() -> set[str]:
    try:
        with open(EXCEPTIONS_FILE, "r", encoding="utf-8") as f:
            words = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
        return words
    except Exception:
        pass
    save_exceptions(DEFAULT_EXCEPTIONS)
    return set()


def add_exception(word: str) -> bool:
    """Add a single word to exceptions.txt. Returns True if added, False if already present."""
    word = word.strip().lower()
    current = load_exceptions()
    if word in current:
        return False
    current.add(word)
    save_exceptions(sorted(current))
    return True


def save_exceptions(words: list[str]) -> None:
    try:
        with open(EXCEPTIONS_FILE, "w", encoding="utf-8") as f:
            f.write("# Word exceptions - one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# These words will never be chosen by the macro\n")
            f.write("# Case-insensitive. Edit this file and click Reload Exceptions in the app\n\n")
            for w in words:
                f.write(w + "\n")
    except Exception as ex:
        logger.warning("Failed to save exceptions: %s", ex)
