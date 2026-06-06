# Letter Demon 😈

> **The Demon knows every word your opponent doesn't.**

A pragmatic tool that searches 470k words in milliseconds, picks the hardest word your opponent can follow, and types it like a human. Built for a word game where every move builds from the last 2-4 letters.

> ⚠️ **No dictionary is included.** This tool expects you to supply your own word list.  
> See [Usage](#usage) for the expected format.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Windows](https://img.shields.io/badge/platform-Windows-lightblue?style=flat-square)
![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [How It Works](#how-it-works)

## Features

- **Smart Word Engine** finds the hardest-to-follow word for any starting letters in milliseconds. An exceptions list blocks unwanted suggestions.

- **Human-like Typing** randomized per-keystroke delays from a log-normal distribution. Speed, jitter, and pre/post delays are all configurable.

- **Game Integration** detects the target window, focuses it before typing, and restores focus when done, with a live on/off status indicator.

- **Advanced Configuration** load custom dictionaries (JSON or TXT), edit trap endings live, maintain an exceptions list, and save settings automatically.

- **Fast Lookups** precomputes scores on index, so searches are instant. Automatically recaches on config changes.

## Requirements

Windows, Python 3.10+, `keyboard` library (`pip install -r requirements.txt`).

## Installation

```bash
git clone https://github.com/n6ufal/Letter-Demon.git
cd letter-demon
pip install -r requirements.txt
python main.pyw       # normal use (no console)
python main.py        # debug (shows console)
```

## Testing

Letter Demon has a comprehensive test suite with 105 tests covering the word engine, dictionary caching, settings persistence, typing simulation, and complete end-to-end workflows.

### Running Tests

To run all tests:

```bash
python -m unittest discover -v
```

This runs all 105 tests in about 2-3 seconds. You should see "OK" at the end if all tests pass.

### What the Tests Cover

- Word engine logic: Does word selection work correctly?
- Dictionary loading and caching: Can dictionaries load fast?
- Settings persistence: Do settings save and load properly?
- Typing simulation: Is the timing correct?
- End-to-end workflows: Can you load a dictionary, find a word, and type it?
- Error recovery: Does the app handle errors gracefully?
- System integration: Does Roblox window detection work?

Tests use synthetic word lists and temporary directories, so your data files are never touched. The keyboard library is mocked during tests to avoid actual keystroke injection.

### Learning More

For a beginner-friendly guide to running and understanding tests, see TESTING.md.

## Usage

### Quick Start

1. **Load a Dictionary** — Advanced > Load Dictionary, pick a `.json` or `.txt` file. Indexing takes 5-30s.
2. **Configure Typing**
   - Set typing speed (default: 170ms per keystroke)
   - Set humanizer intensity (default: 75%, 0 = off)
   - Adjust pre/post delays (default: 500ms each)
3. **Set Strategy** — Trap Words (hard for opponent), Random Words, Long Words, or Short Words. Pick a fallback.
4. **Play** — type starting letters, press Play or Ctrl+Enter. Window hides, word gets typed.

### Custom Trap Endings

Trap endings are suffixes that are statistically hard to continue from. The engine scores each word by finding its longest matching suffix, prioritizing by position in `trap_endings.txt` where earlier means higher priority.

The default config ships with placeholder examples just to show the format. The real list is in `data/trap_endings.txt`.

**Loading the included trap endings:**

1. Click **Advanced > Load** (Trap Endings section)
2. Go to `data/` and select `trap_endings.txt`
3. Changes take effect immediately

One suffix per line, ordered by difficulty. Lines starting with `#` are ignored.

**Example structure:**
```
# comment lines are ignored
ocy
loh
sz
osa
```

### Word Exceptions

Stop the engine from ever suggesting certain words:

- Click **Advanced > Edit** (Exceptions section)
- Add one word per line
- Useful for slurs, proper nouns, or anything else you want blocked

### Dictionary Format

**JSON:**
```json
{
  "words": ["apple", "banana", "cherry"]
}
```

**Text (one word per line):**
```
apple
banana
cherry
```

## Configuration

Settings save automatically to `settings.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `dict_path` | null | path to loaded dictionary |
| `speed` | 170 | ms per keystroke |
| `mode` | "Trap Words" | main strategy |
| `fallback` | "Short Words" | backup strategy |
| `pre_delay` | 500 | ms before typing starts |
| `post_delay` | 500 | ms after typing finishes |
| `jitter_intensity` | 75 | humanizer intensity (0-100, 0 = off) |

To customize UI colors, edit `ui/theme.py` and restart.

## Troubleshooting

- **"Game: off" indicator** — open the game window before hitting Play
- **Dictionary won't load** — check the file exists and is valid JSON or TXT
- **Typing fails** — run `python main.py` to see errors, or check `logs/letter_demon.log`

## How It Works

See [ARCHITECTURE.md](ARCHITECTURE.md) for details on the word selection pipeline and typing simulation.

## Disclaimer

This is a personal Python learning project for personal use only.

