# Letter Demon 😈

> **The Demon knows every word your opponent doesn't.**

Searches 470k words in milliseconds, picks the hardest word your opponent can follow, and types it like a human would. Built for a word game where every move starts from the last 2, 3, or 4 letters of the previous word.

> ⚠️ **No dictionary is included.** This tool expects you to supply your own word list.  
> See [Usage](#usage) for the expected format.
> 
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Windows](https://img.shields.io/badge/platform-Windows-lightblue?style=flat-square)
![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Table of Contents

- [Roadmap and Current Status](#roadmap-and-current-status)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Customization](#customization)

---

## Roadmap and Current Status

### Roadmap
- **Mode Profiles** separate profiles for Casual and Pro that load the right dictionaries and trap endings automatically
- **Auto-update** pull the latest trap endings for each mode straight from GitHub

### Status (April 30, 2026)
This repository is code-only. I’ve excluded the 470k+ and 500k+ dictionaries, as well as the full trap_endings.txt. To run the engine, you’ll need to supply your own dictionary.
---

## Features

- **Smart Word Engine** finds the best word for any starting letters in milliseconds. Words are ranked by how hard they are to follow; ties broken by length depending on your strategy. An exceptions list is checked before anything gets typed.

- **Human-like Typing** gives each keypress its own independently randomized timing. Occasional slow keypresses are mixed in naturally, the way people actually type. Speed, randomness, and delays are all configurable.

- **Game Integration**
  - detects when the target window is running
  - focuses it before typing, returns focus when done
  - live status indicator (on/off)

- **Advanced Configuration**
  - load your own dictionary files (JSON or TXT)
  - edit trap endings on the fly, changes take effect immediately
  - maintain a list of words to never suggest
  - settings save automatically between sessions

- **Fast Lookups** preload word scores when your dictionary is indexed. Searches are instant. Everything updates automatically when you change your dictionary or trap endings.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | Windows only |
| **Python** | 3.10 or higher |

### Dependencies

```python
tkinter       # built-in with Python
keyboard      # pip install keyboard
ctypes        # built-in
```

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/n6ufal/Letter-Demon.git
   cd letter-demon
   ```

2. **Install dependencies:**
   ```bash
   pip install keyboard
   ```

3. **Run:**
   ```bash
   # Normal use (no console)
   python main.pyw

   # Debugging (shows console)
   python main.py
   ```

---

## Usage

### Quick Start

1. **Load a Dictionary**
   - Click Advanced > Load Dictionary
   - Pick a `.json` or `.txt` word file
   - Wait for indexing (5-30 seconds depending on size)

2. **Configure Typing**
   - Set typing speed (default: 170ms per character)
   - Toggle humanized jitter (default: on, 75%)
   - Adjust pre/post delays (default: 500ms each)

3. **Set Game Strategy**
   - **Trap Words** go for words your opponent will struggle to follow
   - **Long Words** go for the longest word available
   - **Short Words** play it safe with shorter words
   - Pick a fallback for when your main strategy comes up empty

4. **Play**
   - Type starting letters into the field
   - Press PLAY or Ctrl+Enter
   - The window hides, the word gets typed, the target window gets focus
   - Window comes back when it's done

---

### Custom Trap Endings

Trap endings are suffixes that are statistically hard to continue from. The engine scores each word by finding its longest matching suffix, prioritizing by position in `trap_endings.txt` where earlier means higher priority.

The default config ships with placeholder examples just to show the format. The real list is in `data/trap_endings.txt`.

**Loading the included trap endings:**

1. Click **Advanced > Load** (Trap Endings section)
2. Go to `data/` and select `trap_endings.txt`
3. Changes take effect immediately

One suffix per line, ordered by difficulty. Lines starting with `#` are ignored.

**Recommended setup:**
- Dictionary: `mixed-old-complete-dict.txt` from `dictionaries/`
- Trap Endings: `trap_endings.txt` from `data/`
- Exceptions: `exceptions.txt` from `data/`

**Example structure:**
```
# comment lines are ignored
ocy
loh
sz
osa
```

---

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

---

## Configuration

Settings save automatically to `settings.json`. All values are optional, defaults kick in if anything is missing:

```json
{
  "dict_path": "path/to/dictionary.json",
  "speed": 170,
  "mode": "trap_words",
  "fallback": "short_words",
  "pre_delay": 500,
  "post_delay": 500,
  "jitter_enabled": true,
  "jitter_intensity": 75,
  "win_x": 100,
  "win_y": 100
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `dict_path` | null | path to loaded dictionary |
| `speed` | 170 | ms per character |
| `mode` | trap_words | main strategy |
| `fallback` | short_words | backup strategy |
| `pre_delay` | 500 | ms before typing starts |
| `post_delay` | 500 | ms after typing finishes |
| `jitter_enabled` | true | humanized timing on/off |
| `jitter_intensity` | 75 | variance amount (5-100%) |

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| "Game: off" indicator | make sure the game window is open before hitting Play |
| Dictionary won't load | check the file exists and is valid JSON or TXT |
| Typing fails silently | check `crash.log` in the project folder |
| Words not matching prefix | matching is case-insensitive, double-check what you typed |
| Jitter slider greyed out | enable the "Jitter" checkbox first |

Run `python main.py` to see errors in the console as they happen. Crash logs go to `crash.log`.

---

## How It Works

### Word Selection Pipeline

From input to output, the engine follows a fixed sequence of steps.

#### 1. Trap Endings Index

When you load `trap_endings.txt`, the engine parses it line by line, skipping blanks and comments, trimming whitespace, lowercasing everything, then removes duplicates while preserving order.

Each ending gets a score based on its position:

```python
ending_scores = {
    ending: len(trap_endings) - index
    for index, ending in enumerate(trap_endings)
}
```

First entry gets the highest score. Last gets 1. Anything not in the list gets 0.

So a file with three endings gives you:

```
ocy  ->  score 3  (hardest to follow)
loh  ->  score 2
sz   ->  score 1
```

#### 2. Prefix Search

You type a prefix like "ca". The engine runs a bisect-based binary search on the sorted word list to find every word that starts with those letters. Binary search is O(log n), which on a 100k+ word dictionary is roughly 51x faster than scanning the list from the top.

Matching is case-insensitive, so "Ca", "CA", and "ca" all hit the same results.

#### 3. Scoring

For each candidate word, the engine checks what suffix it ends with and looks that up against `ending_scores`. It starts with the longest possible suffix and works down until it finds a match:

```
"happiness"   -> ends with "ness" -> score 3
"development" -> ends with "ment" -> score 2
"running"     -> ends with "ing"  -> score 1
"cat"         -> no match         -> score 0
```

The word with the highest trap score wins. If multiple words tie, the tiebreaker depends on your strategy:

- **Trap Words** picks the highest-scoring word, tiebroken by longest
- **Long Words** ignores trap scores entirely, just finds the longest match
- **Short Words** ignores trap scores entirely, just finds the shortest match

#### 4. Exception Filter

Before anything gets typed, the engine checks the exceptions set, a plain Python set of lowercase words. Set lookups are O(1) so this adds no noticeable overhead. Words on the list get skipped.

#### 5. Fallback

If no word is found for the prefix under your main strategy, the engine falls back to your backup strategy. If that's also empty, it returns None and shows an error state.

#### 6. Cache

When you load a dictionary, the engine precomputes scores for every word upfront and stores them in `_trap_score_cache`. That's where the 5-30 second wait on first load comes from. After that, lookups are instant.

The cache clears automatically when you load a new dictionary or change your trap endings.

---

### Typing Simulation

Keystroke delay is sampled from a log-normal distribution:

```
delay ~ LogNormal(μ, σ)
```

Log-normal means the distribution is right-skewed. Most keystrokes cluster around your base speed, but occasionally one takes longer, which is how people actually type. A uniform random distribution would feel robotic by comparison.

`μ` is derived from your configured base speed. `σ` scales with jitter intensity. Delays are clamped to [30ms, 500ms] to keep inputs physically plausible. Every character gets its own independently sampled delay with no pattern between keystrokes.

**Parameters:**
- **Base speed** (default: 170ms) is the median keystroke delay
- **Jitter intensity** (default: 75%) controls variance
- **Pre-delay** (default: 500ms) is the wait before the first keystroke
- **Post-delay** (default: 500ms) is the wait after the last keystroke and Enter

---

## Project Structure

```
letter_demon_tk/
├── main.py                 # debug entry point (shows console)
├── main.pyw                # release entry point (hidden console)
├── settings.json           # user configuration
│
├── core/
│   ├── dictionary.py       # word list loading & caching
│   └── word_engine.py      # scoring, bisect search & selection
│
├── config/
│   ├── settings.py         # settings persistence
│   ├── trap_endings.py     # trap ending management
│   └── exceptions.py       # exception word management
│
├── system/
│   ├── window.py           # target window detection
│   └── typer.py            # log-normal keystroke simulation
│
└── ui/
    ├── app.py              # main application class
    ├── dialogs.py          # advanced window & dialogs
    ├── main_layout.py      # UI widget tree
    ├── theme.py            # colors & typography
    ├── modes.py            # game mode definitions
    ├── widgets.py          # custom widget builders
    ├── window_utils.py     # window positioning
    └── file_editors.py     # file editing dialogs
```

---

## Customization

Edit `ui/theme.py` to change colors:

```python
C_BG = "#1a1a1a"           # main background
C_BG_PANEL = "#2a2a2a"     # panel background
C_TEXT = "#e0e0e0"         # primary text
C_MUTED = "#808080"        # secondary/disabled text
C_PLAY_BG = "#00d084"      # play button (green)
C_PLAY_FG = "#1a1a1a"      # play button text
C_DOT_GREEN = "#00d084"    # running indicator
C_DOT_RED = "#ff3333"      # stopped indicator
```

Changes apply on next restart.

---

## Disclaimer

This is a personal project built for learning. The code is AI-assisted but the design, logic, and decisions are mine.

The tool only uses publicly available data. It doesn't modify any game client or touch anything private. That said, it may interact with game mechanics in ways devs didn't intend, and using it could violate a game's terms of service. That's on you.

I don't guarantee it keeps working. Use it at your own risk.
