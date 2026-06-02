# Letter Demon — Agent Guide

## Entry points
- `main.pyw` — release (double-click, no console). `main.py` — debug (shows console).
- Both insert project root into `sys.path` — no `pip install -e .` needed.

## Setup
```powershell
pip install -r requirements.txt
```

## Key facts
- **Tests** live in `tests/` — run with `python -m unittest discover`. Only `core/word_engine.py` is tested (pure logic, no UI deps).
- **No CI, no linter/formatter/typechecker config.** Repo is code-only.
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
- **Never touch `data/` or `dictionaries/`** — user-managed data files. Do not read, write, edit, or commit them.
- `.gitignore` excludes `settings.json`, `dictionaries/`, `cache/`, `validator/`, `testenv/`, `logs/`, `crash.log`.
- `main.pyw` does not show a console — logging goes to `logs/letter_demon.log`. Top-level exceptions are written there via `logging.exception()` and a `tkinter.messagebox` is shown.
- Only dependency: `keyboard` (in `requirements.txt`). No `pyproject.toml`, `setup.py`, or `setup.cfg`.
- `settings.json` is auto-created with defaults on first run.
- `.gitattributes` (`* text=auto`) normalizes line endings — commit will show CRLF warnings until it's in effect.
