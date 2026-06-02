# Letter Demon — Agent Guide

## Entry points
- `main.pyw` — release (double-click, no console). `main.py` — debug (shows console).
- Both insert project root into `sys.path` — no `pip install -e .` needed.

## Setup
```powershell
pip install keyboard
```

## Key facts
- **No tests, no CI, no linter/formatter/typechecker config.** Repo is code-only; agent should not assume any test framework.
- **Windows-only.** Uses `ctypes.windll`, WinAPI (`FindWindowW`, `ShowWindow`, `SetForegroundWindow`, `CreateToolhelp32Snapshot`), and `winsound`.
- **`keyboard` library** for keystroke simulation (`press_and_release`, `send("enter")`). Requires admin privileges on some Windows configs.
- **Pure tkinter** — no web framework, no async runtime.
- **Threading model:** dictionary loading and typing run on daemon threads; UI updates are marshalled via `root.after(0, ...)`.
- `WordEngine` (`core/word_engine.py`) is pure logic with no UI imports — the only unit-testable module.

## Architecture
```
core/           Pure logic (dictionary, word_engine)
config/         Settings persistence, trap endings, exceptions
system/         OS interaction (roblox process detection, keyboard typer)
ui/             tkinter GUI (app, dialogs, layout, theme, modes)
data/           Tracked data files (trap_endings.txt, exceptions.txt)
cache/          Gitignored. Dictionary cache (.txt + .hash companion files)
```

## Gotchas
- `.gitignore` excludes `settings.json`, `dictionaries/`, `cache/`, `validator/`, `testenv/`, `crash.log`.
- `main.pyw` catches top-level exceptions, writes `crash.log`, and shows a `tkinter.messagebox` — does not re-raise.
- No `pyproject.toml`, `setup.py`, `setup.cfg`, or `requirements.txt` — the only dependency is `keyboard`.
- `settings.json` is auto-created with defaults on first run.
