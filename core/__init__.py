from .dictionary import load_wordlist_from_dict, get_cache_path
from .word_engine import WordEngine

__version__ = "6"


def _compute_version_string() -> str:
    try:
        import subprocess
        build = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip()
        return f"v{__version__} (build {build})"
    except Exception:
        return f"v{__version__}"


version_string = _compute_version_string()
