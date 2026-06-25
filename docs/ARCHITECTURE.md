# Architecture

## Project Overview

Letter Demon is a Windows desktop typing assistant for a Roblox word game. It searches a 470k+ word dictionary in milliseconds, picks the most difficult continuation for your opponent, and types it with human-like keystroke timing.

```
core/      pure logic (session.py, word_engine.py, dictionary.py, dict_lookup.py — no UI/OS deps)
config/    file I/O for settings, trap endings, exceptions
system/    WinAPI (roblox.py), keystroke injection (typer.py via `keyboard` library)
ui/        tkinter: app.py (controller), view.py, dialogs.py, modes.py, theme.py, widgets.py, file_editors.py
tools/     standalone tools: lookup.pyw (dictionary explorer)
data/      config files: settings.json, trap_endings.txt, exceptions.txt, custom_words.txt
data/runtime/   runtime data: cache, logs, dictionaries, lookup_settings.json (all gitignored)
docs/      ARCHITECTURE.md, TESTING.md, screenshots/
scripts/   release.py (automated dev -> main merge + versioning)
tests/     151 unittest.TestCase tests
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
| **system/** | OS-specific operations | WinAPI window detection, keystroke injection via `keyboard` library |
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

**Format support.** The parser handles two formats:
- **.txt**: one word per line, optional extra columns (frequency, etc.) are split off. Lines starting with `#` are comments. Blank lines are skipped. Words are lowercased.
- **.json**: a flat JSON object `{word: count, ...}` — dictionary keys are extracted as words.

**Atomic cache writes.** Cache files are written atomically via a temp file + `replace()` to prevent corruption from partial writes:

```python
tmp_path = cache_path.with_suffix(".txt.tmp")
try:
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(wordlist))
    tmp_path.replace(cache_path)
except Exception as ex:
    logger.warning("Could not save cache: %s", ex)
```

**Cache validation** is purely mtime-based:

```python
def _cache_is_valid(cache_path, dict_path):
    if not cache_path.exists():
        return False
    return cache_path.stat().st_mtime >= Path(dict_path).stat().st_mtime
```

No content hashing, no hash files. If the cache file is newer than the dictionary, it's valid. An empty cache file also triggers a full re-parse.

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

Keystrokes are injected via the `keyboard` library, which uses scan-code-based `SendInput` calls compatible with both legacy and Raw Input applications (required by Roblox).

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
| Typo rate | 0–20% | Per-character probability of deliberate typo (0 = off) |

The `mu = log(base_s) - 0.5 * sigma^2` shift anchors the distribution's **mean** (not median) to the configured speed, so the slider is an honest average even at high jitter levels. The `max(0.03, delay)` clamp prevents sub-30ms intervals that would look inhuman. There is no upper-bound clamp — the log-normal distribution naturally makes very long delays rare.

Every character gets its own independently sampled delay with no pattern between keystrokes.

### Deliberate Typos

When typo mode is enabled, the typer can insert a wrong character, backspace it, and retype the correct one — simulating a real player's fat-finger mistake.

The typo engine uses a QWERTY adjacency map (`system/typer.py`):

```python
_TYPO_NEIGHBORS = {
    "q": ["w", "a", "s"],
    "w": ["q", "e", "a", "s", "d"],
    # ... every letter maps to its physical keyboard neighbors
}
```

Before typing each character, the typer rolls per-character probability (`typo_rate = N / 100`). If the roll hits:

1. A random neighbor is picked from `_TYPO_NEIGHBORS[char]`
2. The wrong character is typed immediately
3. A short pause (`typo_pause_s`, ~30ms) simulates the user noticing the mistake
4. Backspace is pressed
5. The correct character is typed

**Constraints:**
- Only alphabetical QWERTY neighbors (no number homoglyphs like `e→3`, `i→1`)
- Never typo the first character of a word
- Never typo on words ≤ 2 letters
- Typo only triggers when `typo_rate > 0`

### Burst Typing & Bigram Fluency

Human typing isn't uniform — people type in quick bursts with pauses between groups, common letter pairs are faster than rare ones, and occasional micro-pauses break the rhythm. The typer simulates all three.

#### Burst Grouping

Characters are typed in random-size bursts with a gap between each group:

```python
_BURST_SIZES = [2, 3, 4]
_BURST_WEIGHTS = [3, 5, 2]
_BURST_GAP_RANGE = (1.5, 3.0)        # multiplier of base delay
_BURST_SCALE_RATIO = 0.6             # reduce jitter inside bursts
```

At typing time, the word is split into bursts via `_split_bursts()`:

```python
def _split_bursts(text: str) -> list[tuple[int, int]]:
    bursts = []
    i = 0
    n = len(text)
    while i < n:
        size = min(random.choices(_BURST_SIZES, _BURST_WEIGHTS)[0], n - i)
        bursts.append((i, i + size))
        i += size
    return bursts
```

Between bursts, a longer gap (`_burst_gap_delay`) produces:
```python
base_s * random.uniform(1.5, 3.0)
```

Inside a burst, the jitter scale is reduced by `_BURST_SCALE_RATIO` (0.6), making within-burst keystrokes tighter and more rhythmic.

#### Bigram Speed Map

Every adjacent letter pair adjusts the delay. Common digraphs like `th`, `he`, `in` are faster (multiplier < 1), rare pairs like `zv`, `xq`, `qz` are slower (multiplier > 1):

```python
_BIGRAM_SPEED = {
    "th": 0.75, "he": 0.78, "in": 0.80, ...    # fast
    "zv": 1.50, "xq": 1.50, "qz": 1.50, ...    # slow
}
```

If no bigram applies (e.g. first character of a word or after a burst boundary), per-character rarity is used instead:

```python
_CHAR_RARITY = {
    "e": 0.78, "t": 0.80, ...  # common → faster
    "z": 1.50,                  # rare → slower
}
```

Characters in the last two positions of the word get a 1.15× slowdown — simulating people slowing down as they finish a word.

#### Micro-Pauses

A 3% chance per keystroke adds an extra 100–400ms pause, simulating the user briefly hesitating mid-word:

```python
if char and random.random() < _MICRO_PAUSE_CHANCE:
    delay += random.uniform(0.1, 0.4)
```

#### Updated `_next_delay` signature

The method now accepts contextual parameters to enable all the above adjustments:

```python
def _next_delay(self, char="", prev="",
                pos=0, total_len=0,
                inside_burst=False) -> float:
```

When jitter is off, only the bigram/rarity multipliers apply (no burst effects). When jitter is on, the burst scale reduction and log-normal sampling combine with all the above.

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

Configuration files live in `data/`:

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
  "typo_enabled": false,
  "typo_intensity": 4,
  "window_title": "Roblox",
  "win_x": 100,
  "win_y": 200
}
```

#### SettingsManager — `config/settings.py`

The `SettingsManager` class provides schema-driven persistence with validation, migration, and merge-on-save:

```python
class SettingsManager:
    SCHEMA: dict[str, tuple[type | tuple[type, ...], object]] = {
        "dict_path": ((str, type(None)), None),
        "mode": (str, "Trap Words"),
        "wpm": (int, 70),
        "jitter_intensity": (int, 75),
        "typo_intensity": (int, 4),
        ...
    }

    RANGES: dict[str, tuple[int | float, int | float]] = {
        "wpm": (50, 200),
        "jitter_intensity": (0, 100),
        "typo_intensity": (0, 20),
        ...
    }
```

| Feature | Behavior |
|---------|----------|
| **Type validation** | Values not matching the expected type fall back to the default |
| **Range clamping** | Numeric values are clamped to `RANGES` bounds on load |
| **Self-healing** | Missing schema keys are filled with defaults |
| **Merge-on-save** | Unknown keys from the file are preserved when writing |

The raw `load_settings`/`save_settings` functions provide unvalidated direct access for simpler use cases.

### trap_endings.txt

One per line, hardest first. Lines starting with `#` are comments. On missing file, defaults are written automatically.

Comments and blank lines are skipped. Lowercased on load. Duplicates removed while preserving first-occurrence order.

### exceptions.txt

Words never chosen by the engine. On missing file, an empty set is used.

### custom_words.txt

Extra words merged into the dictionary at load time. Both the main app and the lookup tool union these with the loaded wordlist before use. Managed via the lookup tool's Add Words dialog or manually edited. Sorted alphabetically on save.

## Dictionary Lookup Tool — `tools/lookup.pyw`

A standalone tkinter application for dictionary exploration, independent of the main Letter Demon app. It shares the same `core/` modules and `data/` config files.

### Architecture

```
tools/lookup.pyw
  LookupView     — owns all widgets, tkinter vars, layout
  LookupApp      — controller, owns DictLookup, threading, settings
  AddWordsDialog — toplevel for bulk-adding words to dictionary

core/dict_lookup.py
  DictLookup     — pure logic, thread-safe binary search via bisect
```

Data flows follow the same pattern as the main app: view → controller → core logic.

### DictLookup — `core/dict_lookup.py`

A thread-safe, bi-sect-based dictionary index supporting prefix, suffix, and combined queries.

**Prefix search** uses bisect to find the range of words starting with a given prefix:

```python
def find_starting_with(self, prefix, limit=200):
    with self._lock:
        left = bisect.bisect_left(self._wordlist, prefix)
        right = bisect.bisect_left(self._wordlist, prefix + '\xff')
        return self._wordlist[left:right][:limit]
```

**Suffix search** maintains a lazily-built reversed-word index (`_reversed_pairs`):

```python
def _ensure_reversed(self):
    if self._reversed_pairs is None:
        self._reversed_pairs = sorted((w[::-1], w) for w in self._wordlist)
```

Reversed pairs are invalidated (`set None`) on `set_wordlist` or `add_word`.

**Combined prefix + suffix** queries intersect both sets for O(log n) performance.

**Word management:** `add_word`/`add_words` insert into the sorted list and invalidate the reversed cache. `contains` uses bisect for O(log n) membership checks.

### Lookup UI Features

| Feature | Description |
|---------|-------------|
| **Prefix filter** | Find words starting with text |
| **Suffix filter** | Find words ending with text |
| **Contains filter** | Substring match within results |
| **Min/Max length** | Spinbox range filters |
| **Match Case** | Toggle case-sensitive search |
| **Results list** | Displays #, word, length, exception status ; color-coded rows |
| **Exceptions panel** | Live filterable list, add/remove words via double-click, right-click context menu, Space key, or Delete key |
| **Trap Endings panel** | Collapsible, filterable, add/edit/remove trap endings inline, Edit File button opens system editor |
| **Add Words dialog** | Bulk-insert words via text area with preview of new vs already-present |
| **Keyboard shortcuts** | Ctrl+O (load dict), Ctrl+L (clear), Ctrl+F (focus prefix), Escape (cycle focus), Delete/Space on results |

### Lookup Settings

Lookup tool persists its own settings to `data/runtime/lookup_settings.json`:

```json
{
  "dict_path": "C:/dicts/words.txt",
  "win_w": 1400,
  "win_h": 800,
  "sash_pos": 300
}
```

### Custom Words — `data/custom_words.txt`

A user-editable file of extra words merged into the dictionary at load time. Both the main app and the lookup tool call `load_custom_words()` after `load_wordlist_from_dict()` and union the sets.

```python
def load_custom_words() -> set[str]:
    if not CUSTOM_WORDS_PATH.exists():
        return set()
    with open(CUSTOM_WORDS_PATH, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}
```

Persistence is handled by `save_custom_words()` which writes alphabetically sorted to the file. The lookup tool's Add Words dialog calls this after bulk-adding words.

## Style Notes

- Encoding `utf-8` on all file I/O (avoids Windows cp1252 defaults with non-ASCII)
- EditorConfig: CRLF, 4-space indent, UTF-8
- No docstrings on private methods
- Minimal type annotations (no mypy/pyright configured — bare Python project)
- Ruff linter with F + E4 rules (no E402) — run `ruff check .` before committing
