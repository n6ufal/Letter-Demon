# Release Notes

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
