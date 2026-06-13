# Architecture

## Project Overview

Letter Demon is a Windows desktop typing assistant for a Roblox word game. It searches a 470k+ word dictionary in milliseconds, picks the most difficult continuation for your opponent, and types it with human-like keystroke timing.

```
core/      pure logic (session.py, word_engine.py, dictionary.py — no UI/OS deps)
config/    file I/O for settings, trap endings, exceptions
system/    WinAPI (roblox.py), keystroke injection (typer.py via SendInput/ctypes)
ui/        tkinter: app.py (controller), view.py, dialogs.py, modes.py, theme.py, widgets.py, file_editors.py
data/      config files: settings.json, trap_endings.txt, exceptions.txt
data/runtime/   runtime data: cache, logs, dictionaries (gitignored)
docs/      ARCHITECTURE.md, TESTING.md, screenshots/
scripts/   release.py (automated dev -> main merge + versioning)
tests/     104 unittest.TestCase tests
```

## Entry Points

Two launch files, same core:

| File | Console | Log Level | Error Handling |
|------|---------|-----------|----------------|
| `main.py` | Visible | DEBUG (console + file) | Crash visible in terminal |
| `main.pyw` | Hidden | WARNING (file only) | Shows message box with log path |

Both insert the project root onto `sys.path`, enable DPI awareness via `ctypes.windll.shcore.SetProcessDpiAwareness(1)`, then start the tkinter `LetterDemonApp`.

## Module Layers

| Layer | Description | Examples |
|-------|-------------|---------|
| **core/** | Pure logic, testable without any OS/UI | `WordEngine`, dictionary parsing |
| **config/** | File I/O for user-editable configs | `settings.json`, `trap_endings.txt` |
| **system/** | OS-specific operations | WinAPI window detection, keystroke injection via SendInput |
| **ui/** | tkinter application | Main window, dialogs, modes, theme, tooltips, file editors |

Data flows **down**: ui → system/config → core. The `WordEngine` has no knowledge of tkinter, keystroke injection, or Roblox.

## MVC Architecture

The app follows a lightweight Model-View-Controller pattern:

### Model — `core/session.py` (`AppSession`)

Owns `WordEngine`, `Typer`, `SettingsManager`, play guard lock, dict path, and window title. No tkinter imports. Thread-safe via `RLock` on play state.

```python
session = AppSession()
session.load_dictionary("words.txt")
word = session.prepare_play_round(prefix, mode, fallback, auto_type_prefix)
session.configure_typer(speed_ms=170, jitter_intensity=75, pre_delay_s=0.5, post_delay_s=0.5)
session.finish_play_round()
```

### View — `ui/view.py` (`MainView`)

Owns all widgets and tkinter variables. The controller constructs one instance, then reads/writes state through properties and update methods. Dialogs manage their own `Toplevel` windows.

```python
view = MainView(root, controller, window_title, settings)
view.prefix             # reads entry text
view.speed_ms           # reads slider
view.show_feedback("error", "No match found")
view.set_roblox_indicator(running)
view.update_play_button(has_wordlist)
```

### Controller — `ui/app.py` (`LetterDemonApp`, ~300 lines)

Creates session + view, wires event handlers, owns thread creation and Roblox polling. Pure orchestration — no direct widget access, no engine access, no typer access.

```python
class LetterDemonApp:
    def __init__(self, root: tk.Tk, session: AppSession | None = None):
        self.session = session or AppSession()
        self.view = MainView(root, self, ...)
        # ... wire bindings, start polling
```

## Word Selection Pipeline

From prefix input to typed word, the engine follows this sequence:

```
Prefix → [Prefix Search] → [Score Candidates] → [Filter Exceptions] → [Fallback?] → Return word + type
```

### 1. Dictionary Loading & Disk Cache

Loading 500k words from scratch takes ~1 second. A disk cache drops this to ~50ms.

The cache file path is deterministic — `data/runtime/cache/cache_{md5[:10]}.txt` where the hash is derived from the dictionary's absolute path.

```python
def load_wordlist_from_dict(dict_path):
    cache_path = get_cache_path(dict_path)

    if _cache_is_valid(cache_path, dict_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            wordlist = f.read().splitlines()
        return wordlist, True  # from cache

    words_set = _load_dict_file(dict_path)
    wordlist = sorted(words_set)

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write("\n".join(wordlist))

    return wordlist, False  # fresh parse
```

**Cache validation** is purely mtime-based:

```python
def _cache_is_valid(cache_path, dict_path):
    if not os.path.exists(cache_path):
        return False
    return os.path.getmtime(cache_path) >= os.path.getmtime(dict_path)
```

No content hashing, no hash files. If the cache file is newer than the dictionary, it's valid.

### 2. Trap Endings Index

When the engine loads `trap_endings.txt`, it parses line by line — skipping blanks, comments, trimming whitespace, lowercasing, deduplicating while preserving order.

Each ending gets a score based on its position in the file:

```python
self._ending_scores = {
    ending: len(trap_endings) - index
    for index, ending in enumerate(trap_endings)
}
```

First entry gets the highest score. Last gets 1. Anything not in the list gets 0.

```
ocy  ->  score 3  (hardest to follow)
loh  ->  score 2
sz   ->  score 1
```

The maximum ending length is tracked to bound suffix searches:

```python
self._max_ending_len = max((len(e) for e in trap_endings), default=8)
```

### 3. Prefix Search

Binary search (bisect) on the sorted word list. On a 100k+ dictionary, this is ~51x faster than linear scan.

```python
def _get_candidates_bisect(self, prefix):
    lower_prefix = prefix.lower()
    start_idx = bisect.bisect_left(self.wordlist, lower_prefix)
    upper_prefix = lower_prefix + "~"        # "~" sorts after any letter
    end_idx = bisect.bisect_left(self.wordlist, upper_prefix)

    return [
        w for w in itertools.islice(self.wordlist, start_idx, end_idx)
        if w not in self.used_words          # skip already-played
        and w not in self.word_exceptions     # skip blacklisted
        and len(w) > len(prefix)             # must be longer than prefix
    ]
```

Case-insensitive — "Ca", "CA", "ca" all hit the same results.

### 4. Score Candidates

Each candidate word is checked against the trap list. The check walks backward from the longest possible suffix down to 2 characters:

```python
def _trap_score(self, word):
    lower = word.lower()
    for length in range(min(len(lower), max_len), 1, -1):
        if lower[-length:] in ending_scores:
            return ending_scores[lower[-length:]]
    return 0
```

Scores are computed **lazily** — only for candidate words at query time. This eliminates the 5–30 second wait on dictionary load entirely. For typical candidate sets (100–2,000 words), scoring adds ~1–50ms per query, imperceptible during gameplay.

### 5. Strategy & Selection

The engine selects the best word based on the active strategy:

```python
def _select(self, candidates, mode, fallback):
    if mode == "Trap Words":
        trap_scored = [
            (s, w) for w in candidates
            if (s := self._trap_score(w)) > 0
        ]
        if trap_scored:
            best_score = max(s for s, _ in trap_scored)
            top = [w for s, w in trap_scored if s == best_score]
            return random.choice(top)  # random among highest scorers
        return self._pick_by_strategy(candidates, fallback)

    return self._pick_by_strategy(candidates, mode)
```

| Strategy | Behavior |
|----------|----------|
| **Trap Words** | Highest trap score wins; ties broken **randomly** |
| **Short Words** | Ignores trap scores — picks shortest match |
| **Long Words** | Ignores trap scores — picks longest match |
| **Random Words** | Picks arbitrarily from candidates |

Trap Words uses random tiebreaking so the same suffix doesn't always produce the same word.

### 6. Exception Filter

Before any word is typed, the engine checks the exceptions set (a plain Python `set` of lowercase words). Set lookups are O(1). Words on the list get skipped entirely.

### 7. Fallback

If the primary strategy finds no candidates, the engine falls back to the secondary strategy. If that also returns nothing, it returns `None` and the UI shows an error.

### 8. Used Words Tracking

The engine tracks every word it plays in `self.used_words` (a `set`). Words in this set are filtered out of subsequent searches — they never repeat.

```python
def clear_used_words(self):
    with self._lock:
        self.used_words.clear()

def used_words_for_display(self):
    with self._lock:
        return sorted(self.used_words, key=str.lower), len(self.used_words)
```

Reset via the "Clear Used" button in the UI — not to be confused with the disk cache.

### 9. Scoring Lifecycle

Trap scores are computed lazily at query time in `_select`. The scoring index (`_ending_scores` and `_max_ending_len`) is rebuilt when trap endings change via `set_trap_endings`. No per-word cache is maintained — scores are computed fresh for each query's candidate set.

The disk cache (`data/runtime/cache/cache_*.txt`) is only invalidated when the dictionary file's mtime changes.

## Mode System

Display names are mapped to internal names via `ui/modes.py`:

| Display Name | Internal Name |
|--------------|---------------|
| Trap | Trap Words |
| Short | Short Words |
| Long | Long Words |
| Random | Random Words |

Fallback only uses Short, Long, and Random (not Trap).

## Window Focus & Typing Sequence

The full "play a round" flow:

1. User enters a prefix and presses **Play** (or Ctrl+Enter)
2. Engine finds a completion word
3. App window hides (`root.withdraw()`)
4. Roblox window is detected and focused via WinAPI
5. A background daemon thread types the word character by character
6. The Enter key is pressed to submit
7. App window reappears (`root.deiconify()`)

```python
def focus_roblox_window(window_title: str = "Roblox") -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.FindWindowW(None, window_title)
    if hwnd:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)   # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
```

The key trick: hiding the app window **before** calling `SetForegroundWindow` eliminates focus competition with Windows, raising success rate from ~80% to near 100%.

A 15-second timer polls `is_roblox_running()` to update the UI indicator (green dot = running, red = not found).

## Typing Simulation

Keystrokes are injected via the Windows `SendInput` API using the `KEYEVENTF_UNICODE` flag, which bypasses keyboard layout mapping and directly inserts the correct Unicode character. The Enter key is sent as a virtual-key (`VK_RETURN`) keystroke.

Keystroke delay is sampled from a **log-normal distribution**. Log-normal is right-skewed: most keystrokes cluster around the base speed, but occasionally one takes much longer — exactly how people actually type. A uniform distribution would feel robotic.

```python
def _next_delay(self):
    base_s = max(0.03, self.base_speed_ms / 1000.0)

    if not self.jitter_on:
        return base_s

    scale = (self.jitter_pct / 100.0) * 0.75
    mu = math.log(base_s) - 0.5 * scale ** 2
    delay = random.lognormvariate(mu, scale)

    return max(0.03, delay)   # 30ms floor — no upper bound
```

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| Base speed | 170ms | Median keystroke delay |
| Jitter/Humanizer | 75% | Controls distribution spread (0 = robotic, 100 = erratic) |
| Pre-delay | 500ms | Pause before first keystroke |
| Post-delay | 500ms | Pause after Enter |

The `mu = log(base_s) - 0.5 * sigma^2` shift anchors the distribution's **mean** (not median) to the configured speed, so the slider is an honest average even at high jitter levels. The `max(0.03, delay)` clamp prevents sub-30ms intervals that would look inhuman. There is no upper-bound clamp — the log-normal distribution naturally makes very long delays rare.

Every character gets its own independently sampled delay with no pattern between keystrokes.

## Threading Model

Two separate locks serve different purposes:

### 1. WordEngine's Internal RLock

```python
# core/word_engine.py
self._lock = threading.RLock()  # Reentrant — same thread can re-acquire
```

All public methods (`find_completion`, `find_full_word`, `set_trap_endings`, `set_wordlist`, etc.) acquire this lock. Reentrant (`RLock`) means methods that call into each other won't deadlock.

### 2. Session's Play Guard Lock

```python
# core/session.py
self._playing_lock = threading.RLock()  # Reentrant — prevents double-fire
```

Acquired at the start of `session.prepare_play_round()`, released in `session.finish_play_round()`. The controller delegates play state management to `AppSession` — no lock lives in the controller.

### Daemon Thread Pattern

All blocking operations run on daemon threads so the UI stays responsive:

```python
threading.Thread(
    target=self._type_and_return,
    args=(completion,),
    daemon=True
).start()
```

### Cross-Thread UI

Tkinter requires all UI operations on the main thread. The `root.after(0, ...)` pattern schedules work back to the main thread:

```python
def _type_and_return(self, completion) -> None:
    try:
        success, message = self.session.typer.type_text(
            completion,
            pre_delay_s=self.session.pre_delay,
            post_delay_s=self.session.post_delay,
        )
        if not success:
            logger.warning("Typing failed: %s", message)
    finally:
        self.session.finish_play_round()
        self.root.after(0, self.root.deiconify)
```

Dictionary loading also happens on a background thread with `after(0)` callbacks for status updates and UI re-enable.

## Persistence

Three files live in `data/`:

### settings.json

Saved on quit, loaded on start. Includes dict path, speed, mode, fallback, jitter/humanizer intensity, pre/post delays, and window position.

```json
{
  "dict_path": "C:/dicts/english.txt",
  "speed": 170,
  "mode": "Trap Words",
  "fallback": "Short Words",
  "jitter_intensity": 75,
  "pre_delay": 500,
  "post_delay": 500,
  "auto_type_prefix": true,
  "window_title": "Roblox",
  "win_x": 100,
  "win_y": 200
}
```

### trap_endings.txt

One per line, hardest first. Lines starting with `#` are comments. On missing file, defaults are written automatically.

Comments and blank lines are skipped. Lowercased on load. Duplicates removed while preserving first-occurrence order.

### exceptions.txt

Words never chosen by the engine. On missing file, an empty set is used.

## Style Notes

- Encoding `utf-8` on all file I/O (avoids Windows cp1252 defaults with non-ASCII)
- EditorConfig: CRLF, 4-space indent, UTF-8
- No docstrings on private methods
- Minimal type annotations (no mypy/pyright configured — bare Python project)
- Ruff linter with F + E4 rules (no E402) — run `ruff check .` before committing
