# Letter Demon 😈

> **The Demon knows every word your opponent doesn't.**

A pragmatic tool that searches 470k words in milliseconds, picks the hardest word your opponent can follow, and types it like a human. Built for a word game where every move builds from the last 2-4 letters.

> **No dictionary is included.** This tool expects you to supply your own word list.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Windows](https://img.shields.io/badge/platform-Windows-lightblue?style=flat-square)
![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)

<img src="screenshots/main-GUI.png" width="600" alt="Letter Demon main window">

## Features

- Finds the toughest words your opponent can play from 470k words in milliseconds
- Types naturally with human-like speed and pauses
- Auto-detects and focuses your game window
- Blocks unwanted words and customize difficulty settings
- Lightning-fast searches that adapt to your changes

## Installation

Windows, Python 3.10+. Run:

```bash
git clone https://github.com/n6ufal/Letter-Demon.git
cd letter-demon
pip install -r requirements.txt
python main.pyw       # normal use (no console)
python main.py        # debug (shows console)
```

## Quick Start

1. **Load a Dictionary** - Advanced > Load Dictionary, pick a .json or .txt file. Indexing takes 5-30s.
2. **Configure Typing** - Set speed (default 170ms), jitter/humanizer intensity (default 75%), pre/post delays (default 500ms each).
3. **Pick Strategy** - Trap Words (hardest), Long Words, Short Words, or Random. Choose a fallback.
4. **Play** - Type starting letters, press Play or Ctrl+Enter.

### Example Workflow

You type "ca" at the start of a game. The engine:

1. Searches all words starting with "ca" (cabinet, camera, capital, etc.)
2. Scores each by matching trap endings (suffix priority list)
3. Picks the highest-scoring word that's not in exceptions
4. Types it like a human with realistic keystroke delays

Result: "cabinet" gets typed with delays that look natural.

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
| `jitter_intensity` | 75 | jitter/humanizer intensity (0-100, 0 = off) |

<details>
<summary><b>Dictionary Format</b></summary>

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
</details>

<details>
<summary><b>Advanced Configuration</b></summary>

<img src="screenshots/advanced-window-GUI.png" width="600" alt="Advanced configuration window">

#### Custom Trap Endings

Trap endings are suffixes that are statistically hard to continue from. The engine scores each word by its longest matching suffix, prioritizing earlier entries in `trap_endings.txt`.

To load trap endings:

1. Click Advanced > Load (Trap Endings section)
2. Select `data/trap_endings.txt`
3. Changes take effect immediately

Format: one suffix per line, ordered by difficulty. Lines starting with # are ignored.

> **Note:** The `data/trap_endings.txt` in this repository is a minimal dummy for testing. Provide your own full trap endings file for real use.

```
# comment lines are ignored
ocy
loh
sz
osa
```

<img src="screenshots/editor-GUI.png" width="600" alt="Trap endings editor">

#### Word Exceptions

Stop the engine from suggesting certain words:

1. Click Advanced > Edit (Exceptions section)
2. Add one word per line
3. Useful for slurs, proper nouns, or anything you want blocked

#### UI Colors

Edit `ui/theme.py` and restart to customize colors.
</details>

## Testing

Run all 97 tests:

```bash
python -m unittest discover -v
```

See [TESTING.md](TESTING.md) for full details.

## Troubleshooting

- **"Game: off" indicator** - Open the game window before hitting Play
- **Dictionary won't load** - Check the file exists and is valid JSON or TXT
- **Typing fails** - Run `python main.py` to see errors, or check `logs/letter_demon.log`

## Learn More

- Full architecture and algorithms: [ARCHITECTURE.md](ARCHITECTURE.md)
- Test suite guide: [TESTING.md](TESTING.md)
- Blog post: [What Happens When You Take a Word Game Too Seriously](https://alifnaufal.me/posts/what-happens-when-you-take-a-word-game-too-seriously/)

## Disclaimer

This is a personal Python learning project for personal use only.

