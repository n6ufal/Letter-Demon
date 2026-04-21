# Letter Demon 😈

> **The Demon knows every word your opponent doesn't.**

Automate the Last Letter word game on Roblox with intelligent word selection, trap ending detection, and human-like typing simulation.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Windows](https://img.shields.io/badge/platform-Windows-lightblue?style=flat-square)
![MIT License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Customization](#customization)
- [License](#license)

---

## Update — April 20, 2026

Last Letter pushed a dictionary update across Casual, Intermediate, and Pro servers, removing a large portion of words sourced from Dwyl's English Dictionary. All three modes now share the same synchronized dictionary.

**Compatibility by mode:**

| Mode | Status | Notes |
|------|--------|-------|
| Casual | ⚠️ Degraded | Ships against a 470K-word legacy library. Partial overlap remains — some trap words still land. Use updated `trap_endings.txt`. |
| Intermediate | ✅ Functional | Legacy dictionary still aligns well. Use legacy `trap_endings.txt`. |
| Pro | ❌ Not viable | Enforces hyphenated compounds with a significantly wider suffix/prefix range. Current dictionary coverage is insufficient. |

---

## Roadmap

- **Mode Profiles** — Dedicated Casual and Intermediate profiles that automatically load the correct dictionary and trap endings per game mode.
- **Auto-update** — Fetch the latest trap endings list for each mode directly from GitHub.

---

## Features

- **Smart Word Engine** — Bisect-based prefix search with a scored trap ending index. Words ranked by suffix difficulty; ties broken by word length (mode-dependent). Separate exception filter runs as a set-membership check before output.

- **Anti-Detection Typing** — Per-keystroke delay sampled from a Log-Normal distribution, matching empirical human keystroke timing. Configurable base speed, jitter variance, and pre/post-action delays. Each character gets an independently sampled delay with no autocorrelation.

- **Roblox Integration**
  - Live process detection with 3-second polling
  - Automatic window focus via WinAPI
  - Status indicator (● on/off)

- **Advanced Configuration**
  - Load custom dictionary files (JSON or TXT)
  - Edit trap endings in real-time with live cache invalidation
  - Manage word exceptions
  - Persist settings across sessions

- **Cache Management** — Word scores are memoized per dictionary load. Cache invalidation is triggered by dictionary swap or trap ending mutation. Used-word tracking persists per session and is excluded from candidate selection at query time.

---

## Requirements

| Requirement | Details |
|-------------|----------|
| **OS** | Windows (uses WinAPI for process detection & keyboard control) |
| **Python** | 3.10 or higher |
| **Roblox** | Client must be installed and running |

### Dependencies

```python
tkinter       # built-in with Python
keyboard      # keyboard simulation — pip install keyboard
ctypes        # WinAPI integration — built-in
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

3. **Run the application:**
   ```bash
   # With GUI (no console)
   python main.pyw
   
   # With console (for debugging)
   python main.py
   ```

---

## Usage

### Quick Start

1. **Load a Dictionary**
   - Click Advanced → Load Dictionary
   - Select a `.json` or `.txt` word file
   - Wait for indexing (~5-30 seconds depending on size)

2. **Configure Typing**
   - Set typing speed (default: 170ms per character)
   - Enable/disable humanized jitter (default: on, 75%)
   - Adjust pre/post delays (default: 500ms each)

3. **Set Game Strategy**
   - **Trap Words** — Prioritize hard words
   - **Short Words** — Minimize character risk
   - Choose fallback mode if primary fails

4. **Play**
   - Enter the starting letters in the text field
   - Press PLAY or Ctrl+Enter
   - Window hides, word is typed, game window regains focus
   - Window reappears when done

### Advanced Features

#### Custom Trap Endings
Trap endings are word suffixes that are statistically hard for opponents to continue from:
- Click **Advanced → Load** (Trap Endings section)
- Select a `.txt` file with one ending per line
- Comments start with `#`
- **Order matters** — list endings from hardest to easiest

Example `trap_endings.txt`:
```
# Hardest endings first
-ness
-ment
-ing
-tion
```

#### Word Exceptions
Prevent the engine from suggesting certain words:
- Click **Advanced → Edit** (Exceptions section)
- Add one word per line
- Useful for: slurs, proper nouns, slang, offensive terms

#### Dictionary Format

**JSON** (`words_dictionary.json`):
```json
{
  "words": ["apple", "banana", "cherry", ...]
}
```

**Text** (one word per line):
```
apple
banana
cherry
```

---

## Configuration

Settings are auto-saved to `settings.json`. All values are optional and have sensible defaults:

```json
{
  // Path to loaded dictionary file (null if not loaded)
  "dict_path": "path/to/dictionary.json",
  
  // Typing speed in milliseconds per character (default: 170)
  "speed": 170,
  
  // Primary strategy: "trap_words" or "short_words"
  "mode": "trap_words",
  
  // Fallback strategy when primary fails
  "fallback": "short_words",
  
  // Delay before typing begins (milliseconds)
  "pre_delay": 500,
  
  // Delay after typing completes (milliseconds)
  "post_delay": 500,
  
  // Enable humanized typing jitter
  "jitter_enabled": true,
  
  // Jitter variance intensity (5-100%)
  "jitter_intensity": 75,
  
  // Window position (auto-saved)
  "win_x": 100,
  "win_y": 100
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Roblox: off" indicator | Ensure Roblox is running before playing |
| Dictionary won't load | Verify file exists and is valid JSON/TXT format |
| Typing fails silently | Check that Roblox window is focused; check `crash.log` |
| Words aren't matching prefix | Verify prefix is correct (case-insensitive) |
| Jitter slider disabled | Enable "Jitter" checkbox in main window |

### Debug Mode

Run with console output to see errors:
```bash
python main.py
```

Crash logs are saved to `crash.log` in the project directory.

---

## How It Works

### Word Selection Pipeline

The word engine follows a deterministic pipeline from user input to final word output:

#### 1. Trap Endings Index

When you load or reload a `trap_endings.txt` file, the engine:

1. **Parse the file line-by-line**
   - Skip empty lines
   - Skip comment lines (lines starting with `#`)
   - Trim whitespace
   - Convert to lowercase

2. **Remove duplicates** while preserving order (first occurrence wins)

3. **Build scoring map**
   ```python
   ending_scores = {
       ending: len(trap_endings) - index
       for index, ending in enumerate(trap_endings)
   }
   ```
   - First ending (hardest) gets highest score
   - Last ending (easiest) gets score = 1
   - Unlisted endings get score = 0

**Example:**
```
File content:          Index    Score
-ness                   0   →  3 - 0 = 3 (hardest)
-ment                   1   →  3 - 1 = 2
-ing                    2   →  3 - 2 = 1 (easiest)
```

#### 2. Prefix Search

When you enter a prefix (e.g., "ca"), the engine:

1. **Bisect-based binary search** on the sorted word dictionary
   - Finds all words starting with "ca"
   - O(log n) complexity per search
   - ~51x faster than linear scan on 100k+ word dictionaries

2. **Case-insensitive matching**
   - "Ca", "CA", "ca" all match the same words

#### 3. Scoring & Ranking

For each candidate word, compute trap score:

```python
score = max ending score found in word suffix
```

**Algorithm:**
- Extract last N characters (where N = max trap ending length)
- For each length from N down to 1, check if suffix exists in `ending_scores`
- Return the score of the first match found (longest suffix prioritized)

**Example with trap endings: [-ness, -ment, -ing]**
```
"happiness"     → check: "ness", "ness" found → score: 3 ✓
"development"   → check: "ment", "ment" found → score: 2
"running"       → check: "ning", "ing" found  → score: 1
"cat"           → check: "cat", "at", "t" → no match → score: 0 (fallback)
```

#### 4. Exception Filter

Before output, check if word is in the exceptions set:
- Exceptions are stored as lowercase
- Case-insensitive matching (`word.lower() in exceptions_set`)
- O(1) lookup via set membership check
- Rejected words are skipped

#### 5. Fallback Mode

If no trap word is found for the prefix:
- Switch to fallback strategy (e.g., "Short Words" mode)
- Find shortest matching word instead of highest-scoring
- If still no match, return None (error state)

#### 6. Cache Management

**Cache Precomputation:**
- When dictionary loads, all word scores are computed once
- Stored in `_trap_score_cache: dict[str, int]`
- ~5-30 seconds for 100k+ word dictionary (one-time)

**Cache Invalidation:**
- **Dictionary reload** → clear cache, precompute new scores
- **Trap endings change** → clear cache, precompute new scores
- **Word selection** → used words are tracked and excluded from future queries

### Typing Simulation

Inter-keystroke delay is sampled from a Log-Normal distribution:

```
delay ~ LogNormal(μ, σ)
```

where μ is derived from the configured base speed and σ scales with jitter intensity. Log-Normal was chosen because it's right-skewed — matching empirical human keystroke distributions where outlier-slow keystrokes are more common than outlier-fast ones. Delays are clamped to [30ms, 500ms] to prevent physically implausible inputs. Each character receives an independently sampled delay; no autocorrelation between keystrokes.

**Configuration parameters:**
- **Base speed** (default: 170ms) — anchors the median keystroke delay
- **Jitter intensity** (default: 75%) — controls variance (5–100%)
- **Pre-delay** (default: 500ms) — wait before first keystroke
- **Post-delay** (default: 500ms) — wait after last keystroke + Enter key

---

## Project Structure

```
letter_demon_tk/
├── main.py                 # Debug entry point (shows console)
├── main.pyw                # Release entry point (hidden console)
├── settings.json           # User configuration
├── crash.log              # Error logs (auto-generated)
│
├── core/
│   ├── dictionary.py      # Word list loading & caching
│   └── word_engine.py     # Scoring, bisect search & selection logic
│
├── config/
│   ├── settings.py        # Settings persistence
│   ├── trap_endings.py    # Trap ending management
│   └── exceptions.py      # Exception word management
│
├── system/
│   ├── roblox.py          # Roblox process detection
│   └── typer.py           # Log-Normal keystroke simulation
│
└── ui/
    ├── app.py             # Main application class
    ├── dialogs.py         # Advanced window & dialogs
    ├── main_layout.py     # UI widget tree
    ├── theme.py           # Colors & typography
    ├── modes.py           # Game mode definitions
    ├── widgets.py         # Custom widget builders
    ├── window_utils.py    # Window positioning
    └── file_editors.py    # File editing dialogs
```

---

## Customization

### Theme Colors

Edit `ui/theme.py` to customize application appearance:

```python
# Background colors
C_BG = "#1a1a1a"              # Main background
C_BG_PANEL = "#2a2a2a"        # Panel background

# Text colors
C_TEXT = "#e0e0e0"            # Primary text
C_MUTED = "#808080"           # Secondary/disabled text

# Button colors
C_PLAY_BG = "#00d084"         # Play button background (green)
C_PLAY_FG = "#1a1a1a"         # Play button text (dark)

# Status indicators
C_DOT_GREEN = "#00d084"       # Running indicator
C_DOT_RED = "#ff3333"         # Stopped indicator
```

Colors use standard hex format. Changes apply on next application restart.

---

## Disclaimer

This tool is for **educational and research purposes only**. Use responsibly:

- Written against public Roblox APIs only; no reverse engineering or client modification
- Respects game integrity and fair play principles
- Your account, your responsibility — use at your own risk
- By using this tool, you accept full responsibility for any consequences

---

## License

MIT License — See LICENSE file for details