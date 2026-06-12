# Migration: tkinter → PySide6 (Qt Widgets)

**Branch:** `migrate-qt`
**Target:** Replace `ui/` (tkinter) with PySide6 (Qt Widgets). Core logic (`core/`, `config/`, `system/`) stays untouched.

---

## Motivation

- **Visual polish**: Native Windows 11 look via Fusion style + QSS stylesheets
- **Performance**: No tkinter Tcl/Tk overhead; QThread signals replace `root.after(0,)` callbacks
- **Maintainability**: ~500 fewer lines of custom widget code (tooltips, sliders, button factories)

---

## Dependency Change

```
# requirements.txt — before
keyboard>=0.13.5

# requirements.txt — after
keyboard>=0.13.5
PySide6>=6.5
```

Add `PySide6>=6.5` to `pyproject.toml` as well. No other new deps — Qt has built-in tooltips, sliders, validators, stylesheets, scrollable text areas, and file dialogs.

---

## Architecture (After)

```
main.py / main.pyw
  └─ QApplication
       └─ MainWindow (QMainWindow)    ← was LetterDemonApp
            ├─ MainWidget (QWidget)   ← was MainView (view.py)
            ├─ AdvancedDialog (QDialog)
            ├─ UsedWordsDialog (QDialog)
            ├─ EditorDialog (QDialog)
            ├─ AboutDialog (QDialog)
            ├─ QTimer (Roblox polling)
            ├─ QThread (typing worker)
            └─ QThreadPool (dict loading)
```

---

## Phases

### Phase 1 — Entry points + skeleton

**Files:** `main.py`, `main.pyw`, `ui/__init__.py`

Replace tkinter bootstrap with Qt:

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from ui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

- Remove `ctypes` DPI-awareness call (Qt handles it natively)
- `MainWindow` imports and creates the session, but has no widgets yet
- Verify the app launches and shows a blank QMainWindow

### Phase 2 — Main widget layout

**Files:** `ui/main_widget.py` (new), `ui/view.py` (delete after)

- Replace `MainView` with `MainWidget(QWidget)`
- Layout: `QVBoxLayout` containing:
  - Header: `QLabel("Starting letters:")` + `QLabel` (feedback)
  - Entry: `QLineEdit` + `QRegularExpressionValidator("[A-Za-z]*")`
  - Play button: `QPushButton` with objectName `playBtn`
  - Settings row 1: `QLabel("Speed:")` + `QSlider` + `QLabel(value)` | `QLabel("Mode:")` + `QComboBox`
  - Settings row 2: `QLabel("Human:")` + `QSlider` + `QLabel(value)` | `QLabel("Fall:")` + `QComboBox`
  - Separator: `QFrame` with `QFrame.HLine`
  - Action buttons: 2x `QPushButton` ("Advanced", "Clear Used")
  - Info bar: 3x `QLabel` (dict status, suffix/full, Roblox status)
  - Bottom row: `QLabel("Used words")` + `QLabel("Made by n6ufal")`

- All tooltips via `setToolTip()` — no custom ToolTip class
- WPM/slider logic identical (12000 / wpm conversion)
- Mode/fallback combobox values from `modes.py` (unchanged)

### Phase 3 — Theme (QSS stylesheet)

**Files:** `ui/theme.py` (rewrite)

- Replace 22 color constants + 8 font constants with one QSS string
- Apply via `app.setStyleSheet(stylesheet)` at startup
- Use objectName selectors for specific widgets (`#playBtn`, `#dictDot`, etc.)
- Key styles: entry focus border, button hover, tooltip dark theme, feedback colors

### Phase 4 — Controller signals/slots

**Files:** `ui/app.py` → `ui/main_window.py`

- `LetterDemonApp` becomes `MainWindow(QMainWindow)`
- Widget signals connect to slot methods:
  - `play_btn.clicked.connect(self.on_play_round)`
  - `entry.returnPressed.connect(self.on_play_round)`
  - `advanced_btn.clicked.connect(self.show_advanced)`
  - `clear_used_btn.clicked.connect(self.on_clear_used_words)`
  - `used_words_label.linkActivated.connect(self.show_used_words)`

- `QShortcut(Qt.CTRL | Qt.Key_Return, self).activated.connect(on_ctrl_enter)`
- Window position: save in `QSettings` on close, restore on open
- `QTimer(15000)` for Roblox polling

### Phase 5 — Threading

**Files:** `ui/main_window.py`, `ui/workers.py` (new)

- Dictionary loading: `QRunnable` + `QThreadPool.globalInstance().start()`
  - Signal wordlist_loaded(word_count) back to main thread
- Typing: `QObject` worker moved to `QThread`
  - Signals: `typing_finished(success, message)`, `typing_complete()`
  - `worker.moveToThread(thread)` pattern
- Roblox polling: `QTimer(interval=15000)` — runs on main thread, no thread needed
- No more `root.after(0, lambda: ...)` — signals deliver to main thread automatically
- No more `tk.TclError` guards

### Phase 6 — Dialogs

**Files:** `ui/dialogs.py` (rewrite), `ui/file_editors.py` (rewrite)

- **AboutDialog**: `QDialog` with rich-text `QLabel` for clickable links
- **AdvancedDialog**: `QDialog` with `QTabWidget`:
  - Tab 1: Dictionary (path label + load button)
  - Tab 2: Timing (pre-delay / post-delay `QSpinBox` pairs)
  - Tab 3: Typing (auto-prefix combo + mode/fallback read-only display)
  - Tab 4: Trap Endings & Exceptions (status + reload/edit buttons)
- **UsedWordsDialog**: `QDialog` with `QListWidget + QLabel + QPushButton`
- **EditorDialog**: `QDialog` with `QPlainTextEdit`:
  - `Ctrl+S` / `Escape` via `QShortcut`
  - Search bar: `QLineEdit` + prev/next buttons + match counter
  - Save writes to file, creates `.bak`, calls reload callback

### Phase 7 — Cleanup

- Delete `ui/view.py`, `ui/widgets.py`, `ui/window_utils.py`, `ui/main_layout.py`
- Remove unused tkinter imports
- Update `ui/__init__.py` exports
- Update `tests/` if any test imports from deleted modules
- Run existing 97 tests to confirm core untouched

---

## Widget Mapping

| tkinter | Qt Widget |
|---------|-----------|
| `tk.Tk` | `QApplication` |
| `tk.Toplevel` | `QDialog` |
| `tk.Frame` | `QWidget` or `QFrame` |
| `tk.Label` | `QLabel` |
| `tk.Entry` + validate | `QLineEdit` + `QRegularExpressionValidator` |
| `tk.Button` + hover | `QPushButton` + QSS `:hover` |
| `ttk.Scale` | `QSlider` (horizontal, snapped) |
| `ttk.Combobox` | `QComboBox` |
| `tk.Listbox` + Scrollbar | `QListWidget` |
| `ScrolledText` | `QPlainTextEdit` |
| `StringVar` / `IntVar` | Direct property reads |
| `root.after()` | `QTimer.singleShot()` |
| `threading.Thread` + `after(0,)` | `QThread` + signals |
| `tkinter.filedialog` | `QFileDialog.getOpenFileName()` |
| `winsound` | `QSoundEffect` |
| `ctypes DPI` | Qt built-in (automatic) |

---

## Files to Create

- `ui/main_window.py` — MainWindow (QMainWindow), controller
- `ui/main_widget.py` — MainWidget (QWidget), all main-window widgets
- `ui/workers.py` — TypeWorker (QObject), DictLoader (QRunnable)

## Files to Delete

- `ui/view.py`
- `ui/widgets.py`
- `ui/window_utils.py`
- `ui/main_layout.py`

## Files to Rewrite

- `main.py` — QApplication bootstrap
- `main.pyw` — same, no console
- `ui/app.py` → merged into `main_window.py`
- `ui/dialogs.py` — QDialog subclasses
- `ui/file_editors.py` — QPlainTextEdit version
- `ui/theme.py` — QSS stylesheet

## Files to Edit

- `requirements.txt` — add PySide6
- `pyproject.toml` — add PySide6 dep
- `ui/__init__.py` — export MainWindow

## Files Unchanged

- `core/` (all)
- `config/` (all — SettingsManager kept as-is, no QSettings)
- `system/` (all)
- `data/` (all)
- `scripts/` (all)
- `tests/test_word_engine.py`
- `tests/test_dictionary.py`
- `tests/test_config.py`
- `tests/test_integration.py`
- `tests/test_roblox.py`
- `tests/test_typer.py`

---

## Threading Model (After)

| Work | Mechanism | Runs On |
|------|-----------|---------|
| UI events | Qt event loop | Main thread |
| Roblox polling | `QTimer(15000)` | Main thread |
| Dictionary loading | `QRunnable` → `QThreadPool` | Pool thread |
| Typing injection | `QObject` → `QThread` | Dedicated thread |
| Signal delivery | Qt auto-queued | Main thread |

---

## Rollback

Keep the old `dev` branch. The `migrate-qt` branch is a workspace; old code remains untouched on `dev` and `main`.
