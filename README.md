# Letter Demon 🎮

> **The Demon knows every word your opponent doesn't.**

Automate the Last Letter word game on Roblox with intelligent word selection, trap ending detection, and human-like typing simulation.

---

## ✨ Features

- **Smart Word Engine** — Analyzes your dictionary and finds optimal words based on:
  - Trap endings (hard-to-continue words ranked by difficulty)
  - Word exceptions (blacklisted words to avoid)
  - Game mode strategies (Trap Words, Short Words, or custom fallback)

- **Anti-Detection Typing** — Human-like keyboard simulation with:
  - Configurable typing speed (ms per character)
  - Realistic jitter/variance (Log-Normal distribution)
  - Pre/post-delay customization
  - Character-by-character keystroke simulation

- **Roblox Integration**
  - Live process detection with 3-second polling
  - Automatic window focus
  - Status indicator (● on/off)

- **Advanced Configuration**
  - Load custom dictionary files (JSON or TXT)
  - Edit trap endings in real-time
  - Manage word exceptions
  - Persist settings across sessions

- **Cache Management**
  - Built-in word scoring cache
  - Track used words during gameplay
  - Clear cache with one click

---

## 📋 Requirements

- **Windows** (uses WinAPI for Roblox detection & keyboard control)
- **Python 3.10+**
- **Roblox** (obviously!)

### Dependencies
```
tkinter       (built-in with Python)
keyboard      (keyboard simulation)
ctypes        (WinAPI integration)
```

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/letter-demon.git
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

## 🎯 Usage

### Quick Start

1. **Load a Dictionary**
   - Click **Advanced → Load Dictionary**
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
   - Press **PLAY** or **Ctrl+Enter**
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

## ⚙️ Configuration

Settings are auto-saved to `settings.json`:

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

---

## 🛠️ Troubleshooting

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

## 📊 How It Works

### Word Scoring Algorithm

Each word receives a **trap score** based on its ending:

1. Extract the last N characters of the word (N = max trap ending length)
2. Check if it matches any trap ending
3. Return the score: `total_endings - rank` (higher = harder)
4. Words with higher scores are suggested first

Example:
```
Trap endings: [-ness, -ment, -ing]

Word: "happiness"
- Ends with "-ness" (rank 0)
- Score: 3 - 0 = 3 ✓ (best)

Word: "development"
- Ends with "-ment" (rank 1)
- Score: 3 - 1 = 2 (good)

Word: "running"
- Ends with "-ing" (rank 2)
- Score: 3 - 2 = 1 (okay)
```

### Typing Simulation

Uses Log-Normal distribution for realistic delays:
- **Base speed**: anchored median delay
- **Jitter%**: controls variance (higher = more erratic)
- **Min/Max**: capped at 30ms–500ms per character

---

## 📁 Project Structure

```
letter_demon_tk/
├── main.py                 # Debug entry point (shows console)
├── main.pyw                # Release entry point (hidden console)
├── settings.json           # User configuration
├── crash.log              # Error logs (auto-generated)
│
├── core/
│   ├── dictionary.py      # Word list loading & caching
│   └── word_engine.py     # Core scoring & selection logic
│
├── config/
│   ├── settings.py        # Settings persistence
│   ├── trap_endings.py    # Trap ending management
│   └── exceptions.py      # Exception word management
│
├── system/
│   ├── roblox.py          # Roblox process detection
│   └── typer.py           # Humanized keyboard simulation
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

## 🎨 Customization

### Theme Colors

Edit `ui/theme.py` to customize:
- Background colors
- Text colors
- Button styles
- Accent colors

Example:
```python
C_BG = "#1a1a1a"           # Dark background
C_TEXT = "#e0e0e0"         # Light text
C_PLAY_BG = "#00d084"      # Play button green
```

---

## ⚠️ Disclaimer

This tool is for **educational purposes**. Use responsibly:
- Follows Roblox Terms of Service (uses public APIs only)
- Respects game integrity
- Your account is your responsibility
- Use at your own risk

---

## 📝 License

MIT License — See LICENSE file for details

---

## 👤 Author

**n6ufal**
- Discord: `b6xy`
- Email: `boxcarr@proton.me`

---

## 🙏 Acknowledgments

- Inspired by word game theory and adaptive algorithms
- Built with Python, Tkinter, and ❤️

---

**v6 • April 2026**
