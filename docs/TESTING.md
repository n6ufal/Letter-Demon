# Testing Guide for Letter Demon

This guide explains how to run and understand the test suite, even if you're new to testing.

## What Are Tests?

Tests are small programs that verify Letter Demon works correctly. They check that:
- Words are found correctly
- Settings save and load properly
- Typing simulation works
- Error conditions are handled gracefully

When all tests pass, you know the code is working as intended.

## Running the Tests

### Quick Start

Open a command prompt in the Letter Demon folder and run:

```bash
python -m unittest discover -v
```

This will run all 105 tests and show you the results.

### What You Will See

The output will look like this:

```
test_load_and_find_word (test_integration.DictionaryLoadingIntegrationTest) ... ok
test_cache_speeds_up_loads (test_integration.DictionaryLoadingIntegrationTest) ... ok
test_word_engine_handles_no_matches (test_integration.ErrorRecoveryIntegrationTest) ... ok
...
Ran 105 tests in 2.3s

OK
```

- Each line represents one test
- "ok" means the test passed
- "FAILED" would mean something is broken
- At the end you see the total count and total time

### Running Specific Tests

To run just one test file:

```bash
python -m unittest tests.test_word_engine -v
```

To run just one test class:

```bash
python -m unittest tests.test_integration.DictionaryLoadingIntegrationTest -v
```

To run just one specific test:

```bash
python -m unittest tests.test_integration.DictionaryLoadingIntegrationTest.test_load_dict_and_find_word_end_to_end -v
```

## Understanding Test Results

### All Tests Pass (OK)

This is good. It means Letter Demon is working correctly and ready to use.

### Some Tests Fail (FAILED)

If you see FAILED, scroll up to see which test failed and the error message. Common reasons:

1. You modified code and broke something - read the error to see what went wrong
2. A required file is missing (e.g., a test dictionary)
3. A dependency is not installed - run `pip install -r requirements.txt`

### Example Error Message

```
FAIL: test_find_word_then_type_it (test_integration.TypingIntegrationTest)
...
AssertionError: 'apple' != 'banana'
```

This means the test expected 'apple' but got 'banana'. The error message tells you exactly what was wrong.

## Test Categories

Letter Demon has 105 tests organized into categories:

### Pure Logic Tests (70 tests)

These test the core algorithms with simple inputs and outputs.

- WordEngine tests: Does word selection work correctly?
- Dictionary tests: Can dictionaries load and cache properly?
- Config tests: Do settings save and load?
- Typer tests: Is the timing math correct?

These were the original tests and are very reliable.

### Integration Tests (35 new tests)

These test complete workflows, like a real user would do them.

#### Dictionary Loading (5 tests)
- Load a dictionary file and find a word
- Verify caching works
- Handle empty or invalid files

#### Word Searching (4 tests)
- Find words with trap endings
- Filter blacklisted words
- Reload settings and verify updates

#### Settings (2 tests)
- Save settings to file
- Load them back and verify

#### Typing (3 tests)
- Find a word and type it
- Handle typing failures
- Handle empty results

#### Used Words (3 tests)
- Don't repeat words
- Track history
- Clear the history

#### Error Recovery (3 tests)
- Typing works even if Roblox window is missing
- Handle prefixes with no matches
- Handle empty prefixes

#### Mode Switching (2 tests)
- Different modes pick different words
- Fallback mode works

#### Concurrency (2 tests)
- Multiple threads searching at once don't crash
- Thread safety works

#### Roblox Integration (13 tests)
- Window detection (found, not found, error handling)
- Window focus (normal, minimized, missing)
- Integration workflows

## What Each Test File Does

- `test_word_engine.py`: Tests word selection logic
- `test_dictionary.py`: Tests dictionary loading and caching
- `test_config.py`: Tests settings, trap endings, exceptions
- `test_typer.py`: Tests typing delays and keyboard simulation
- `test_modes.py`: Tests mode mapping (display names vs internal names)
- `test_integration.py`: Tests complete workflows end-to-end
- `test_roblox.py`: Tests Roblox window detection and focus
- `conftest.py`: Shared test infrastructure (fixtures, utilities)

## Why Tests Matter

1. **Confidence** - Know the code works before deploying
2. **Regression Detection** - If you change code, tests catch breakages immediately
3. **Documentation** - Test names describe what the code should do
4. **Safety** - Refactor with confidence that tests will catch mistakes

## Adding Your Own Tests

If you add new features to Letter Demon, add tests for them too.

The test structure is straightforward:

```python
def test_my_feature(self):
    # Setup
    engine = WordEngine(wordlist=["apple", "banana"], trap_endings=[], exceptions=set())
    
    # Action
    result = engine.find_full_word("app")
    
    # Verify
    self.assertEqual(result, "apple")
```

New tests can use the fixtures in `conftest.py` to avoid repetition.

## Troubleshooting Tests

### Tests take too long

Normal: 2-3 seconds for all 105 tests. If it takes longer, your computer might be busy.

### Tests fail with "No module named..."

Install dependencies:
```bash
pip install -r requirements.txt
```

If `ruff` is not found, install it separately:
```bash
pip install ruff
```

### Tests fail with FileNotFoundError

The test is trying to access a file that doesn't exist. This is usually not a problem - the test creates temporary files as needed. If it persists, clear the cache:

```bash
rmdir /s cache
```

Then re-run tests.

### One test fails but others pass

This usually indicates a specific bug in that feature. Read the error message to understand what failed, then look at the test to understand what behavior was expected.

## Continuous Integration

When you're ready to share code or deploy, you can set up automated testing:

1. Every commit runs the full test suite
2. If tests fail, the commit is rejected
3. Only green (passing) commits are merged

This prevents broken code from reaching users.

## Questions?

If a test fails and you don't understand why, look at the test file and read the test name and docstring. They describe what behavior is being tested.

Example:
```python
def test_trap_endings_prioritize_difficult_words(self):
    """Trap endings cause engine to prefer words ending with them."""
```

This test checks that trap endings make the engine prefer harder words. If it fails, trap ending prioritization is broken.
