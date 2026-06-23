# Release Notes

## v9.3.0 (2026-06-23)

### Features
- deliberate typo + auto-correct with QWERTY neighbor map
- typo toggle in Advanced dialog (master switch)
- typo intensity slider on main panel Row 3 (0–20%, per-character probability)
- info bar shows `● Typo: On` / `○ Typo: Off` indicator

### Bug Fixes
- widen slider value label from 4 to 7 chars to prevent clipping in Advanced timing sliders

### Documentation
- document typo engine in ARCHITECTURE.md typing simulation section
- update test counts 104→111 across all docs
- add typo_enabled/typo_intensity to settings.json example

### Chores
- bump v9.2.0 -> v9.3.0

## v9.2.0 (2026-06-21)


### Features
- add standalone dictionary lookup tool with exceptions integration
- burst typing and bigram fluency for more human-like rhythm
- scroll wheel support for sliders
- align speed and humanizer slider widths
- move info bar to top as toolbar, fix slider init position
- replace ms speed slider with real-world WPM values
- add Nord Light palette with live theme switching
- inline feedback in header, uniform slider bg
- add --dry-run flag to release script
- make play button load dictionary when none loaded
- replace winsound.Beep with custom error.wav
- make window title configurable via settings.json

### Bug Fixes
- reduce jitter burstiness and sync slider IntVar during drag
- use VK codes for letter characters instead of KEYEVENTF_UNICODE, fixes Roblox Raw Input compatibility
- compact slider value labels by reducing width and padx
- snap slider position on release to avoid callback recursion
- remove variable= from ttk.Scale to avoid command feedback loop
- correct UsedWordsDialog method name from _update_list to update_list
- widen slider value label from 5 to 8 chars
- stop false positive breaking detection from body text
- detect ! breaking notation and handle merge conflicts

### Chores
- add trap endings backup directory
- update exceptions and trap endings lists
- broaden data/runtime/ gitignore to whole directory
- bump v9.0.0 -> v9.1.0
- add release script, bump core/__init__.py to 9.0.0, update AGENTS.md

### Documentation
- update test count and add MVC architecture section
- remove error sound line from README
- overhaul TESTING.md, patch ARCHITECTURE.md and README.md
- restore personal disclaimer tone
- restructure README for better information flow
- trim redundant section 4 from README, tighten features
- add RELEASE_NOTES.md with v9.0.0 changelog

### Refactors
- tighten view/controller boundary, name magic constants, remove dead code
- overhaul lookup tool UI with MVC split, side panel, filters, and inline feedback
- replace keyboard library with SendInput via ctypes
- restructure main GUI layout for professional UX
- remove clickability from info bar, add theme constants
- trim controller to ~300 lines
- extract MainView from LetterDemonApp, class-based dialogs
- extract AppSession from LetterDemonApp god object
- migrate to pathlib, centralize project root, add SettingsManager
- declutter project root
- rename app class, clean stale comments

### Other
- enlarge lookup window to 1400x800
- update test files
- revert: restore keyboard library, SendInput incompatible with Roblox Raw Input
- Revert "feat: add Nord Light palette with live theme switching"
- Sync dev with main: release script, version bump
- Bump version 8.0.0 â†’ 9.0.0 to match v9 tag
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
