# Release Notes

## v9.1.0 (2026-06-12)

### Features
- add --dry-run flag to release script
- make play button load dictionary when none loaded
- replace winsound.Beep with custom error.wav
- make window title configurable via settings.json

### Bug Fixes
- stop false positive breaking detection from body text
- detect ! breaking notation and handle merge conflicts

### Chores
- add release script, bump core/__init__.py to 9.0.0, update AGENTS.md

### Documentation
- remove error sound line from README
- overhaul TESTING.md, patch ARCHITECTURE.md and README.md
- restore personal disclaimer tone
- restructure README for better information flow
- trim redundant section 4 from README, tighten features
- add RELEASE_NOTES.md with v9.0.0 changelog

### Refactors
- declutter project root
- rename app class, clean stale comments

### Other
- Sync dev with main: release script, version bump
- Bump version 8.0.0 → 9.0.0 to match v9 tag

## v9.0.0 (2026-06-11)

### Features
- Speed slider now uses average-based delay (the number you set is the actual average keystroke delay)
- Speed slider range extended from 10-200ms to 10-250ms
- Add Auto Type Prefix toggle to type suffix-only or full word
- Add hover tooltips to all main GUI widgets and Advanced dialog
- Replace trap score precomputation with lazy scoring for faster dictionary loading

### Bug Fixes
- Fix tooltips appearing behind the main window
- Clean up info bar layout and status indicator wiring

### Chores
- Integrate ruff linter for code quality enforcement
- Consolidate development and runtime dependencies
- Remove dead code across 6 files for a leaner codebase
- Bump version to 9.0.0 and add automated release script
