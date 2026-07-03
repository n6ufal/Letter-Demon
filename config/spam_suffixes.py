"""Spam suffixes — load/save spam_suffixes.txt."""

import logging

from .settings import get_project_root

logger = logging.getLogger(__name__)

SPAM_SUFFIXES_FILE = get_project_root() / "data" / "spam_suffixes.txt"

DEFAULT_SPAM_SUFFIXES = [
    "ing",
    "ed",
    "tion",
    "sion",
    "ment",
    "ly",
    "ness",
    "able",
    "ible",
    "ful",
    "less",
    "er",
    "est",
    "ance",
    "ence",
    "ity",
    "ous",
    "ious",
    "al",
    "ial",
    "ical",
    "ive",
    "ative",
    "ize",
    "ise",
    "en",
    "ate",
    "ify",
    "ee",
    "dom",
    "ship",
    "ward",
    "wise",
    "like",
    "ward",
    "fold",
    "ish",
    "y",
]


def load_spam_suffixes() -> list[str]:
    try:
        with open(SPAM_SUFFIXES_FILE, "r", encoding="utf-8") as f:
            suffixes = [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]
        if suffixes:
            return list(dict.fromkeys(suffixes))
    except Exception:
        pass
    save_spam_suffixes(DEFAULT_SPAM_SUFFIXES)
    return DEFAULT_SPAM_SUFFIXES


def save_spam_suffixes(suffixes: list[str]) -> None:
    try:
        with open(SPAM_SUFFIXES_FILE, "w", encoding="utf-8") as f:
            f.write("# Spam suffixes - one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# These are common English suffixes used by Spam mode.\n")
            f.write("# Edit this file and click Reload Spam in the app\n\n")
            for s in suffixes:
                f.write(s + "\n")
    except Exception as ex:
        logger.warning("Failed to save spam suffixes: %s", ex)
