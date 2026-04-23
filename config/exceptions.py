"""Word exceptions — load/save exceptions.txt."""

import os

from .settings import get_project_root

EXCEPTIONS_FILE = os.path.join(get_project_root(), "data", "exceptions.txt")

DEFAULT_EXCEPTIONS: list[str] = []


def load_exceptions() -> set[str]:
    try:
        with open(EXCEPTIONS_FILE, "r") as f:
            words = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
        return words
    except Exception:
        pass
    save_exceptions(DEFAULT_EXCEPTIONS)
    return set()


def save_exceptions(words: list[str]) -> None:
    try:
        with open(EXCEPTIONS_FILE, "w") as f:
            f.write("# Word exceptions - one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# These words will never be chosen by the macro\n")
            f.write("# Case-insensitive. Edit this file and click Reload Exceptions in the app\n\n")
            for w in words:
                f.write(w + "\n")
    except Exception as ex:
        print("Failed to save exceptions:", ex)
