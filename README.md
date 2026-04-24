# Letter Demon 😈

> **The Demon knows every word your opponent doesn't.**

Automate the Last Letter word game on Roblox with smart word selection, trap ending detection, and human-like typing.

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

## Roadmap

- **Mode Profiles** — Separate profiles for Casual and Intermediate that automatically load the right dictionary and trap endings for each mode.
- **Auto-update** — Pull the latest trap endings list for each mode directly from GitHub.

---

## Features

- **Smart Word Engine** — Finds the best word for any starting letters in milliseconds. Words are ranked by how hard they are to follow; ties are broken by word length depending on your strategy. A separate exceptions list is checked before anything gets typed.

- **Human-like Typing** — Each keypress has its own timing, independently randomized. Occasional slow keypresses are mixed in naturally, matching how real people actually type. Speed, randomness, and delays are all configurable.

- **Roblox Integration**
  - Detects when Roblox is running automatically
  - Focuses the Roblox window before typing
  - Live status indicator (● on/off)

- **Advanced Configuration**
  - Load your own dictionary files (JSON or TXT)
  - Edit trap endings on the fly — changes take effect immediately
  - Manage a list of words to never suggest
  - Settings save automatically between sessions

- **Fast Lookups** — Word scores are preloaded when your dictionary is indexed. Searches are instant. Everything updates automatically when you change your dictionary or trap endings.

---

## Requirements

| Requirement | Details |
|-------------|----------|
| **OS** | Windows only |
| **Python** | 3.10 or higher |
| **Roblox** | Client must be installed and running |

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

3. **Run the application:**
   ```bash
   # Without console (normal use)
   python main.pyw
   
   # With console (for debugging)
   python main.py
   ```

---

## Usage

### Quick Start

1. **Load a Dictionary**
   - Click Advanced → Load Dictionary
   - Pick a `.json` or `.txt` word file
   - Wait for it to index (about 5–30 seconds depending on size)

2. **Configure Typing**
   - Set typing speed (default: 170ms per character)
   - Turn humanized jitter on or off (default: on, 75%)
   - Adjust pre/post delays (default: 500ms each)

3. **Set Game Strategy**
   - **Trap Words** — Go for words your opponent will struggle to follow
   - **Short Words** — Play it safe with shorter words
   - Pick a fallback in case your main strategy comes up empty

4. **Play**
   - Type the starting letters into the text field
   - Press PLAY or Ctrl+Enter
   - The window hides, the word gets typed, Roblox regains focus
   - The window comes back when it's done

### Advanced Features

#### Custom Trap Endings
Trap endings are word suffixes that are statistically hard for opponents to continue from. The default trap endings included in the config are **demonstration examples only** and show how the word engine prioritizes selected suffixes based on their order in `trap_endings.txt`:
- **Order matters** — First ending = hardest score, last ending = easiest score
- The engine finds the longest matching suffix in each word and assigns it a score accordingly
- Earlier endings in the file get higher priority scores

**Using Your Custom Trap Endings:**

This project includes a more comprehensive, handpicked collection of trap endings optimized for the Last Letter game:
1. Click **Advanced → Load** (Trap Endings section)
2. Navigate to the `data/` folder and select `trap_endings.txt`
3. The file contains one ending per line, ordered by difficulty
4. Lines starting with `#` are treated as comments and ignored
5. Changes take effect immediately

**Recommended Setup:**
- **Dictionary**: Load `mixed-old-complete-dict.txt` from the `dictionaries/` folder
- **Trap Endings**: Load `trap_endings.txt` from the `data/` folder (handpicked by the author)
- **Word Exceptions**: Edit from the **Advanced** menu to add any words you want to block

Example `trap_endings.txt` structure:
```
# Hardest endings first (highest priority)
-ness
-ment
-ing
-ion
# ... more suffixes ordered by difficulty
```

#### Word Exceptions
Stop the engine from ever suggesting certain words:
- Click **Advanced → Edit** (Exceptions section)
- Add one word per line
- Useful for slurs, proper nouns, slang, or anything else you want blocked

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

Settings save automatically to `settings.json`. All values are optional — sensible defaults are used if anything is missing:

```json
{
  // Path to your loaded dictionary (null if none loaded)
  "dict_path": "path/to/dictionary.json",
  
  // Typing speed in milliseconds per character (default: 170)
  "speed": 170,
  
  // Main strategy: "trap_words" or "short_words"
  "mode": "trap_words",
  
  // Backup strategy if the main one finds nothing
  "fallback": "short_words",
  
  // How long to wait before typing starts (milliseconds)
  "pre_delay": 500,
  
  // How long to wait after typing finishes (milliseconds)
  "post_delay": 500,
  
  // Turn humanized typing on or off
  "jitter_enabled": true,
  
  // How much randomness to add to typing speed (5–100%)
  "jitter_intensity": 75,
  
  // Window position (saved automatically)
  "win_x": 100,
  "win_y": 100
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Roblox: off" indicator | Make sure Roblox is open before hitting Play |
| Dictionary won't load | Check that the file exists and is valid JSON or TXT |
| Typing fails silently | Make sure the Roblox window is in focus; check `crash.log` |
| Words aren't matching the prefix | Double-check what you typed — matching is case-insensitive |
| Jitter slider is greyed out | Enable the "Jitter" checkbox first |

### Debug Mode

Run with a console to see errors as they happen:
```bash
python main.py
```

Crash logs are written to `crash.log` in the project folder.

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

Edit `ui/theme.py` to change how the app looks:

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

Colors use standard hex format. Changes apply on the next restart.

---

## Disclaimer

This tool is for **educational and research purposes only**. Use responsibly:

- The code is generated with AI, but the design, logic, and decisions are mine. This is a personal project for learning and experimentation
- This tool only uses publicly available data and standard Roblox interfaces. It does not modify the Roblox client or access private systems
- References to publicly shared word lists or community sources do not imply permission or endorsement from any game developer
- This tool may interact with game mechanics in ways that are not intended by the developers. Use of it may violate game rules or terms of service
- I do not guarantee accuracy, safety, or continued functionality. The tool may break, behave unexpectedly, or stop working at any time
- By using this tool, you accept all risks and agree that the creator is not liable for any damage, loss, or account actions

---

## License

MIT License — See LICENSE file for details
