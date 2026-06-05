from .dictionary import load_wordlist_from_dict, get_cache_path
from .word_engine import WordEngine

__version__ = "6"

_version_string: str | None = None


def version_string() -> str:
    """Human-readable version with auto-incrementing build number.

    Build comes from git commit count so it always goes up.
    Falls back to bare version if git is unavailable.
    Result is cached after first call.
    """
    global _version_string
    if _version_string is not None:
        return _version_string
    try:
        import subprocess
        build = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip()
        _version_string = f"v{__version__} (build {build})"
    except Exception:
        _version_string = f"v{__version__}"
    return _version_string
