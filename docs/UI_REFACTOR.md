# UI/UX Refactor: tkinter Port → Polished Qt

**Branch:** `migrate-qt` (continues after migration)
**Goal:** Transform the direct tkinter port into a polished Qt desktop app with depth, animations, system tray, hotkeys, and proper menu/status/dock architecture.

---

## Design Decisions

| Choice | Decision | Why |
|--------|----------|-----|
| Default theme | Light mode (keep current) | Familiar, readable during gameplay. Dark mode as optional toggle. |
| Advanced panel | QDockWidget | Tear-off, side-dock, or float freely. More flexible than modal dialog. |
| Drag-drop dict | Yes | A .json/.txt file onto the window loads it. Simple, natural. |
| System tray | Yes | Essential for a background gaming tool — app vanishes during typing. |
| Global hotkey | Yes | Summon window from anywhere. Reuse `keyboard` (already a dependency). |
| Compact mode | Yes | Minimal view during gameplay — entry + play button only. |
| Animations | Yes | Fade-in feedback, progress bar, window opacity transitions. |

---

## Phase A — Theme & Visual Depth (~2 days)

### File: `ui/theme.py` (rewrite)

Split single `QSS` into two stylesheets:

```python
LIGHT_QSS = """..."""   # current palette, enhanced
DARK_QSS = """..."""    # deep slate (#1e1e2e), green #16a34a, warm amber
```

**Light palette additions:**
- Card backgrounds: `QFrame#settingsCard { background: #f4f4f5; border-radius: 6px; padding: 8px; }`
- Drop shadow on entry: `QGraphicsDropShadowEffect(blurRadius=8, offset=0, color=#00000020)`
- Drop shadow on play button: same, slightly stronger on hover

**Dark palette (new):**
- `QMainWindow` background: `#1e1e2e`
- Card backgrounds: `#2a2a3e`
- Text: `#e4e4e7`
- Muted: `#9ca3af`
- Entry bg: `#3a3a4e`, border: `#4a4a5e`, focus: `#16a34a`
- Play button: same green, hover slightly lighter
- Tooltip bg: `#1f2937` (already dark, keep)

**Dynamic switching:**
```python
def apply_theme(self, is_dark: bool) -> None:
    qss = DARK_QSS if is_dark else LIGHT_QSS
    QApplication.instance().setStyleSheet(qss)
```

- Called from `MainWindow.on_toggle_dark()`
- Persisted in `settings.json` as `"dark_mode": bool`

### File: `ui/main_widget.py` (layout tweaks)

- Wrap slider/combo sections in `QFrame` with objectName `settingsCard`
- Remove `setFixedWidth()` on sliders — let them stretch with window resize
- Add `QGraphicsDropShadowEffect` to `self.entry` and `self.play_btn`

---

## Phase B — Menu Bar + Status Bar (~1 day)

### File: `ui/main_window.py` (additions)

**QMenuBar:**

```
File                        View                    Help
─────                       ─────                   ─────
Load Dictionary...  Ctrl+O  Compact Mode    Ctrl+M   About
Recent Dictionaries ▸       Dark Mode
  ─ item 1                  Always on Top           Quit   Ctrl+Q
  ─ item 2                  ─────
  ─ (empty)                 Status Bar
─────
Quit                Ctrl+Q
```

- `Recent Dictionaries` submenu populated dynamically from `settings["recent_dicts"]`
- On successful dict load: prepend path to `recent_dicts` (max 5), trim duplicates, save

**QStatusBar (replaces custom info bar in main_widget.py):**

```python
self.statusBar().addPermanentWidget(self._dict_status_widget)   # "● 12,340 words"
self.statusBar().addPermanentWidget(self._prefix_mode_widget)    # "● Suffix" / "● Full"
self.statusBar().addPermanentWidget(self._roblox_status_widget)  # "● Roblox"
```

- Remove `_build_info_bar()` from `MainWidget` — all that state moves into `MainWindow`-owned status bar widgets
- `MainWidget` still emits signals; `MainWindow` handles them and updates status bar
- Temporary messages (feedback, loading progress) via `statusBar().showMessage(msg, timeout_ms)`

**Removed from main_widget.py:**
- `_build_info_bar()` method
- `_dict_dot`, `dict_count_label`, `_auto_prefix_dot`, `auto_prefix_label`, `_roblox_dot`, `roblox_status_label`
- `set_roblox_indicator()`, `set_roblox_title()`, `update_dict_word_count()`, `_update_auto_prefix_indicator()`
- `_set_dot_color()`, `_set_label_color()`

**Signals added to MainWidget:**
```python
status_dict_changed = Signal(str, str)   # text, color
status_prefix_changed = Signal(str, str) # text, color
status_roblox_changed = Signal(str, str) # text, color
feedback_requested = Signal(str, int)    # message, timeout_ms
```

MainWindow connects these and updates status bar + tray icon tooltip.

---

## Phase C — Compact Mode (~1 day)

### File: `ui/main_widget.py` (additions)

```python
class MainWidget(QWidget):
    def set_compact_mode(self, enabled: bool) -> None:
        self._compact = enabled
        self._settings_panel.setVisible(not enabled)
        self._separator.setVisible(not enabled)
        self._action_buttons.setVisible(not enabled)
        self._bottom_row.setVisible(not enabled)
        # Status bar is outside MainWidget — always visible

    @property
    def is_compact(self) -> bool:
        return self._compact
```

- Settings panel: the `QVBoxLayout` containing speed/mode/human/fallback rows
- Separator: the `QFrame.HLine`
- Action buttons: Advanced + Clear Used row
- Bottom row: Used words + credit

**Window resize animation:**
```python
def _animate_compact(self, enabled: bool) -> None:
    target_height = 120 if enabled else 320  # approximate
    self._window().animation = QPropertyAnimation(self._window(), b"maximumHeight")
    self._window().animation.setDuration(200)
    self._window().animation.setStartValue(self._window().height())
    self._window().animation.setEndValue(target_height)
    self._window().animation.setEasingCurve(QEasingCurve.OutCubic)
    self._window().animation.start()
```

- Toggle via `QAction("Compact Mode", checkable=True)` in View menu
- Shortcut: `Ctrl+M`
- Persisted in settings as `"compact_mode": bool`

---

## Phase D — System Tray (~1 day)

### File: `ui/main_window.py` (additions)

```python
def _setup_tray(self) -> None:
    self._tray_icon = QSystemTrayIcon(self)
    self._tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
    self._tray_icon.setToolTip("Letter Demon")

    menu = QMenu()
    menu.addAction("Show/Hide", self._toggle_visibility)
    menu.addAction("Quick Type", self.on_play_round)
    menu.addSeparator()
    menu.addAction("Quit", self.close)
    self._tray_icon.setContextMenu(menu)

    self._tray_icon.activated.connect(self._on_tray_activated)
    self._tray_icon.show()

def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
    if reason == QSystemTrayIcon.DoubleClick:
        self._toggle_visibility()

def _toggle_visibility(self) -> None:
    if self.isVisible():
        self.hide()
    else:
        self.show()
        self.raise_()
        self.activateWindow()
```

**Tray notifications:**
```python
def _on_typing_finished(self, success, message):
    if self._tray_icon is not None:
        title = "Typing complete" if success else "Typing failed"
        icon = QSystemTrayIcon.Information if success else QSystemTrayIcon.Warning
        self._tray_icon.showMessage(title, message, icon, 4000)
```

**Tray icon asset:**
- For now: `self.style().standardIcon(QStyle.SP_ComputerIcon)` (built-in)
- Future: replace with custom `.ico` / `.png`

---

## Phase E — Global Hotkey (~0.5 day)

### File: `ui/main_window.py` (additions)

```python
def _setup_global_hotkey(self) -> None:
    combo = self.session.settings.get("global_hotkey", "win+shift+d")
    try:
        keyboard.add_hotkey(combo, self._summon_from_hotkey)
        self._hotkey_combo = combo
    except Exception:
        logger.warning("Could not register global hotkey %s", combo)

def _summon_from_hotkey(self) -> None:
    # Called from keyboard callback (any thread) → schedule on main thread
    QTimer.singleShot(0, self._show_from_tray)

def _show_from_tray(self) -> None:
    self.show()
    self.raise_()
    self.activateWindow()
    self.view.entry.setFocus()
```

- Uses `keyboard.add_hotkey()` from existing `keyboard` dependency
- Requires admin on Windows (same as the typing injection) — no new dependency
- Configurable via settings `"global_hotkey"` string
- Validation: ensure combo doesn't conflict with common shortcuts
- Unregister old combo before registering new one

---

## Phase F — Dockable Advanced Panel (~1.5 days)

### File: `ui/dialogs.py` (edit)

`AdvancedDialog` → `AdvancedPanel(QWidget)` — plain widget, no window flags:

```python
class AdvancedPanel(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main = main_window
        # Same tabs as current, but no setWindowFlags, no show/raise logic
        ...
```

- Remove `Qt.WindowStaysOnTopHint`, `setWindowTitle`, `setAttribute(Qt.WA_DeleteOnClose)`
- Keep all tab content, `refresh_dict_label()`, trap/exceptions methods
- Layout unchanged — `QVBoxLayout` + `QTabWidget`

### File: `ui/main_window.py` (additions)

```python
def _setup_advanced_dock(self) -> None:
    self._advanced_dock = QDockWidget("Advanced", self)
    self._advanced_panel = AdvancedPanel(self)
    self._advanced_dock.setWidget(self._advanced_panel)
    self._advanced_dock.setFeatures(
        QDockWidget.DockWidgetClosable |
        QDockWidget.DockWidgetMovable |
        QDockWidget.DockWidgetFloatable
    )
    self.addDockWidget(Qt.RightDockWidgetArea, self._advanced_dock)
    self._advanced_dock.hide()

    # View menu action
    self._advanced_action = self._view_menu.addAction("Advanced")
    self._advanced_action.setCheckable(True)
    self._advanced_action.setChecked(False)
    self._advanced_action.toggled.connect(self._advanced_dock.setVisible)
    self._advanced_dock.visibilityChanged.connect(
        self._advanced_action.setChecked
    )
```

- Replace singleton pattern (`show_advanced` → `_advanced_dock.show()`)
- Persistent state: `"advanced_dock_area"` (int), `"advanced_dock_floating"` (bool)
- On close: save dock state via `dockWidgetArea()` and `isFloating()`

---

## Phase G — Drag-and-Drop (~0.5 day)

### File: `ui/main_widget.py` (additions)

```python
class MainWidget(QWidget):
    def __init__(self, settings):
        ...
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith((".json", ".txt")):
                    event.acceptProposedAction()
                    self._show_drag_indicator(True)
                    return

    def dragLeaveEvent(self, event) -> None:
        self._show_drag_indicator(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._show_drag_indicator(False)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith((".json", ".txt")):
                self.dict_dropped.emit(path)   # new signal
                break

    def _show_drag_indicator(self, visible: bool) -> None:
        # Highlight border/background while dragging
        if visible:
            self.setStyleSheet(
                "QWidget#mainWidget { border: 2px dashed #16a34a; }"
            )
        else:
            self.setStyleSheet("")
```

- New signal: `dict_dropped = Signal(str)`
- Connected in `MainWindow._wire_view_signals()` → `on_load_dict_from_path(path)`
- `on_load_dict_from_path` follows same path as `on_load_dict` but skips file dialog

---

## Phase H — Animations & Polish (~1 day)

### Feedback animation (main_widget.py)

```python
def show_feedback(self, level, message, *, duration_ms=5000, beep=False):
    ...
    # Fade in
    self._feedback_label.setStyleSheet(...)  # set text + colors first
    self._feedback_anim = QPropertyAnimation(self._feedback_label, b"maximumHeight")
    self._feedback_anim.setDuration(150)
    self._feedback_anim.setStartValue(0)
    self._feedback_anim.setEndValue(20)
    self._feedback_anim.start()
```

Or simpler: use `QGraphicsOpacityEffect` and animate opacity from 0 to 1.

### Loading progress (main_window.py)

```python
def set_loading_state(self):
    self.play_btn.setText("Loading...")
    self.play_btn.setEnabled(False)
    self._progress_bar = QProgressBar()
    self._progress_bar.setRange(0, 0)  # indeterminate
    self.statusBar().addWidget(self._progress_bar)

def set_ready_state(self):
    self.play_btn.setEnabled(True)
    if self._progress_bar is not None:
        self.statusBar().removeWidget(self._progress_bar)
        self._progress_bar.deleteLater()
        self._progress_bar = None
```

### Window fade on hide/show (main_window.py)

```python
def _prepare_for_typing(self, completion):
    # Fade out
    self._fade_out = QPropertyAnimation(self, b"windowOpacity")
    self._fade_out.setDuration(100)
    self._fade_out.setStartValue(1.0)
    self._fade_out.setEndValue(0.0)
    self._fade_out.finished.connect(self.hide)  # hide after fade
    self._fade_out.start()
```

### Keyboard shortcuts review

| Shortcut | Wire to | Where |
|----------|---------|-------|
| `Ctrl+O` | `on_load_dict()` | `MainWindow._wire_shortcuts()` |
| `Ctrl+Q` | `close()` | same |
| `Ctrl+M` | `on_toggle_compact()` | same |
| `Escape` | `view.entry.clear()` / `entry.clearFocus()` | `MainWidget` key press |
| `Win+Shift+D` | `_summon_from_hotkey()` | `MainWindow._setup_global_hotkey()` |

---

## New Settings (added to `config/settings.py` schema)

```python
"dark_mode": (bool, False),
"compact_mode": (bool, False),
"always_on_top": (bool, True),
"global_hotkey": (str, "win+shift+d"),
"recent_dicts": (list, []),
"advanced_dock_area": (int, 2),     # Qt.RightDockWidgetArea
"advanced_dock_floating": (bool, False),
```

---

## Files Unchanged

- `ui/workers.py`
- `ui/file_editors.py` (minor: theme-aware search colors)
- `ui/modes.py`
- `ui/__init__.py`
- `core/` (all)
- `config/settings.py` (schema additions only)
- `config/trap_endings.py`
- `config/exceptions.py`
- `system/` (all)
- `tests/` (all 104)

---

## Estimated Timeline

| Phase | Days |
|-------|------|
| A — Theme & Depth | 2 |
| B — Menu Bar + Status Bar | 1 |
| C — Compact Mode | 1 |
| D — System Tray | 1 |
| E — Global Hotkey | 0.5 |
| F — Dockable Advanced | 1.5 |
| G — Drag-and-Drop | 0.5 |
| H — Animations & Polish | 1 |
| **Total** | **8.5** |
