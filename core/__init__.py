from .dictionary import load_wordlist_from_dict, get_cache_path
from .word_engine import WordEngine

__version__ = "6"


def version_string() -> str:
    """Human-readable version with auto-incrementing build number.

    Build comes from git commit count so it always goes up.
    Falls back to bare version if git is unavailable.
    """
    try:
        import subprocess
        build = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip()
        return f"v{__version__} (build {build})"
    except Exception:
        return f"v{__version__}"
