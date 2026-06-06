"""Shared test fixtures and utilities for Letter Demon tests."""

import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.word_engine import WordEngine
from core.dictionary import load_wordlist_from_dict
from config.settings import load_settings, save_settings
from config.trap_endings import load_trap_endings, save_trap_endings
from config.exceptions import load_exceptions, save_exceptions


# ============================================================================
# TEMPORARY FILE FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Temporary directory that exists for the duration of the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_dict_file(temp_dir):
    """Temporary dictionary file with known test words."""
    dict_path = os.path.join(temp_dir, "test_dict.txt")
    words = [
        "apple", "application", "appetizer",
        "banana", "bandana", "banshee",
        "cat", "caterpillar", "catalog",
        "dog", "dogmatic", "doge",
        "elephant", "elevator", "elite",
    ]
    with open(dict_path, "w") as f:
        f.write("\n".join(words) + "\n")
    return dict_path


@pytest.fixture
def temp_settings_dir(temp_dir):
    """Temporary directory for settings files."""
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


@pytest.fixture
def temp_trap_endings_file(temp_dir):
    """Temporary trap endings file."""
    trap_file = os.path.join(temp_dir, "trap_endings.txt")
    trap_endings = ["ing", "er", "le", "tion", "ly"]
    with open(trap_file, "w") as f:
        f.write("\n".join(trap_endings) + "\n")
    return trap_file


@pytest.fixture
def temp_exceptions_file(temp_dir):
    """Temporary exceptions (blacklist) file."""
    exceptions_file = os.path.join(temp_dir, "exceptions.txt")
    exceptions = ["banana", "dogmatic"]
    with open(exceptions_file, "w") as f:
        f.write("\n".join(exceptions) + "\n")
    return exceptions_file


# ============================================================================
# WORD ENGINE FIXTURES
# ============================================================================

@pytest.fixture
def word_engine_basic():
    """Basic WordEngine with small test wordlist."""
    wordlist = [
        "apple", "application", "appetizer",
        "banana", "bandana", "banshee",
        "cat", "caterpillar", "catalog",
        "dog", "dogmatic", "doge",
        "elephant", "elevator", "elite",
    ]
    trap_endings = ["ing", "er", "le"]
    exceptions = {"banana", "dogmatic"}
    return WordEngine(
        wordlist=wordlist,
        trap_endings=trap_endings,
        exceptions=exceptions,
    )


@pytest.fixture
def word_engine_from_dict(temp_dict_file, temp_trap_endings_file, temp_exceptions_file):
    """WordEngine loaded from temporary dictionary files."""
    # Load dictionary
    wordlist, _ = load_wordlist_from_dict(temp_dict_file)
    
    # Load trap endings and exceptions
    with patch("config.trap_endings.TRAP_ENDINGS_FILE", temp_trap_endings_file):
        trap_endings = load_trap_endings()
    
    with patch("config.exceptions.EXCEPTIONS_FILE", temp_exceptions_file):
        exceptions = load_exceptions()
    
    engine = WordEngine(
        wordlist=wordlist,
        trap_endings=trap_endings,
        exceptions=exceptions,
    )
    return engine


# ============================================================================
# MOCKING FIXTURES
# ============================================================================

@pytest.fixture
def mock_roblox_running():
    """Fixture that mocks Roblox detection as running."""
    with patch("system.roblox.is_roblox_running", return_value=True):
        yield


@pytest.fixture
def mock_roblox_not_running():
    """Fixture that mocks Roblox detection as not running."""
    with patch("system.roblox.is_roblox_running", return_value=False):
        yield


@pytest.fixture
def mock_focus_roblox():
    """Fixture that mocks focusing the Roblox window."""
    with patch("system.roblox.focus_roblox_window") as mock:
        yield mock


@pytest.fixture
def mock_keyboard():
    """Fixture that mocks keyboard library (press_and_release, send)."""
    with patch("system.typer.keyboard") as mock:
        yield mock


@pytest.fixture
def mock_winsound():
    """Fixture that mocks winsound library."""
    with patch("ui.app.winsound") as mock:
        yield mock


# ============================================================================
# SETTINGS FIXTURES
# ============================================================================

@pytest.fixture
def isolated_settings(temp_dir):
    """Context manager that isolates settings to a temporary directory."""
    settings_file = os.path.join(temp_dir, "data", "settings.json")
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    
    with patch("config.settings.SETTINGS_FILE", settings_file):
        yield settings_file


@pytest.fixture
def isolated_trap_endings(temp_dir):
    """Context manager that isolates trap_endings to a temporary directory."""
    trap_file = os.path.join(temp_dir, "data", "trap_endings.txt")
    os.makedirs(os.path.dirname(trap_file), exist_ok=True)
    
    with patch("config.trap_endings.TRAP_ENDINGS_FILE", trap_file):
        yield trap_file


@pytest.fixture
def isolated_exceptions(temp_dir):
    """Context manager that isolates exceptions to a temporary directory."""
    exceptions_file = os.path.join(temp_dir, "data", "exceptions.txt")
    os.makedirs(os.path.dirname(exceptions_file), exist_ok=True)
    
    with patch("config.exceptions.EXCEPTIONS_FILE", exceptions_file):
        yield exceptions_file


# ============================================================================
# UTILITY FUNCTIONS FOR TESTS
# ============================================================================

def assert_threads_clean(timeout=1.0):
    """Verify no daemon threads are hanging (they should complete quickly)."""
    daemon_threads = [t for t in threading.enumerate() if t.daemon]
    for t in daemon_threads:
        t.join(timeout=timeout)
        if t.is_alive():
            raise AssertionError(f"Daemon thread '{t.name}' did not complete within {timeout}s")


def get_cache_key_for_dict(dict_path: str) -> str:
    """Get the cache filename that would be generated for a dictionary."""
    import hashlib
    basename = os.path.basename(dict_path)
    hash_digest = hashlib.md5(dict_path.encode()).hexdigest()[:8]
    return f"cache_{hash_digest}_{basename}"
