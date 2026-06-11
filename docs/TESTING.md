# Testing Guide

## Quick Start

```bash
python -m unittest discover -v      # all 97 tests
python -m unittest tests.test_word_engine -v   # single file
python -m unittest tests.test_integration.DictionaryLoadingIntegrationTest -v  # single class
python -m unittest tests.test_integration.TypingIntegrationTest.test_find_word_then_type_it -v  # single test
```

Also run the linter before committing:

```bash
ruff check .
```

## Test Layout

```
tests/
  test_word_engine.py    16 tests   word selection, trap scoring, used words
  test_dictionary.py     16 tests   loading, caching, file formats
  test_config.py         18 tests   settings, trap endings, exceptions
  test_typer.py          12 tests   delay math, character typing
  test_modes.py           1 test    display name <-> internal name mapping
  test_integration.py    24 tests   end-to-end workflows
  test_roblox.py         11 tests   WinAPI detection + focus
                         --
                         97 total
```

All tests use `unittest.TestCase`. A `conftest.py` exists but is unused — the runner is `unittest`, not pytest.

## Key Testing Patterns

### CACHE_DIR patching

The dictionary disk cache path (`core.dictionary.CACHE_DIR`) is patched per test class to prevent cache files leaking into the real `data/runtime/cache/` directory:

```python
@classmethod
def setUpClass(cls):
    cls.cache_dir = tempfile.mkdtemp()
    cls.cache_patcher = patch("core.dictionary.CACHE_DIR", cls.cache_dir)
    cls.cache_patcher.start()
```

### Temp dictionaries

Integration tests create temporary `.txt` dictionary files:

```python
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
    f.write("apple\nbanana\ncherry\n")
    dict_path = f.name
```

### WinAPI mocking

`system.roblox.py` functions are mocked so tests don't depend on the actual Roblox window:

```python
@patch("system.roblox._user32")
def test_is_roblox_running_returns_true_when_found(self, mock_user32_fn):
    mock_user32 = MagicMock()
    mock_user32.FindWindowW.return_value = 12345
    mock_user32_fn.return_value = mock_user32
    result = is_roblox_running()
    self.assertTrue(result)
```

### Thread safety

Concurrency tests verify the engine's `RLock` protects shared state under `threading.Thread`:

```python
def test_concurrent_searches_are_thread_safe(self):
    errors = []
    def search():
        try:
            for _ in range(50):
                self.engine.find_full_word("app")
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=search) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    self.assertEqual(errors, [])
```

## Writing Tests

Follow the existing patterns:

- One test class per logical concern
- Descriptive method names prefixed with `test_`
- Docstrings on test methods explaining the expected behavior
- Use `setUp` / `setUpClass` for shared setup
- Use `@patch` for external dependencies (WinAPI, keyboard, filesystem)

```python
def test_trap_mode_prefers_scored_words(self):
    """Trap endings cause engine to prefer words ending with them."""
    engine = WordEngine(
        wordlist=["apple", "appley"],
        trap_endings=["ey"],
        exceptions=set(),
    )
    result = engine.find_full_word("app", mode="trap")
    self.assertEqual(result, "appley")
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tests fail with "No module named..." | `pip install -r requirements.txt` |
| Ruff not found | `pip install ruff` |
| Tests fail with FileNotFoundError | Clear cache: `rmdir /s data\runtime\cache` |
| Single test fails, others pass | Read the error message — specific bug in that feature |

## Notes

- No CI configured — run tests manually before every commit
- All tests run in ~2.5 seconds on a modern machine
- Keep the test count at 97 when adding features — write tests for new code
