"""Color palettes and fonts — single source of truth for all UI styling."""

# --- Color constants (module globals, updated by apply_theme()) ---
C_BG          = "#fafafa"
C_BG_PANEL    = "#f4f4f5"
C_TEXT        = "#18181b"
C_MUTED       = "#71717a"
C_ENTRY_BG    = "#ffffff"
C_ENTRY_BD    = "#d4d4d4"
C_ENTRY_FOCUS = "#16a34a"
C_PLAY_BG     = "#16a34a"
C_PLAY_FG     = "#ffffff"
C_PLAY_ACT    = "#15803d"
C_BTN_BG      = "#e4e4e7"
C_BTN_FG      = "#18181b"
C_SEP         = "#e4e4e7"
C_DOT_GREEN   = "#16a34a"
C_DOT_RED     = "#dc2626"
C_DOT_BLUE    = "#2563eb"
C_ACTIVE_BG   = "#e4e4e7"
C_ACTIVE_FG   = "#991b1b"
C_TOOLTIP_BG  = "#1f2937"
C_TOOLTIP_FG  = "#f9fafb"
C_FEEDBACK_WARN_BG  = "#fef3c7"
C_FEEDBACK_WARN_FG  = "#92400e"
C_FEEDBACK_ERR_BG   = "#fee2e2"
C_FEEDBACK_ERR_FG   = "#991b1b"
C_SEARCH_BG   = "#fef08a"
C_SEARCH_FG   = "#1a1a1a"

# --- Named palettes ---
PALETTES: dict[str, dict[str, str]] = {
    "Default": {
        "C_BG": "#fafafa",
        "C_BG_PANEL": "#f4f4f5",
        "C_TEXT": "#18181b",
        "C_MUTED": "#71717a",
        "C_ENTRY_BG": "#ffffff",
        "C_ENTRY_BD": "#d4d4d4",
        "C_ENTRY_FOCUS": "#16a34a",
        "C_PLAY_BG": "#16a34a",
        "C_PLAY_FG": "#ffffff",
        "C_PLAY_ACT": "#15803d",
        "C_BTN_BG": "#e4e4e7",
        "C_BTN_FG": "#18181b",
        "C_SEP": "#e4e4e7",
        "C_DOT_GREEN": "#16a34a",
        "C_DOT_RED": "#dc2626",
        "C_DOT_BLUE": "#2563eb",
        "C_ACTIVE_BG": "#e4e4e7",
        "C_ACTIVE_FG": "#991b1b",
        "C_TOOLTIP_BG": "#1f2937",
        "C_TOOLTIP_FG": "#f9fafb",
        "C_FEEDBACK_WARN_BG": "#fef3c7",
        "C_FEEDBACK_WARN_FG": "#92400e",
        "C_FEEDBACK_ERR_BG": "#fee2e2",
        "C_FEEDBACK_ERR_FG": "#991b1b",
        "C_SEARCH_BG": "#fef08a",
        "C_SEARCH_FG": "#1a1a1a",
    },
    "Nord Light": {
        "C_BG": "#eceff4",
        "C_BG_PANEL": "#e5e9f0",
        "C_TEXT": "#2e3440",
        "C_MUTED": "#4c566a",
        "C_ENTRY_BG": "#eceff4",
        "C_ENTRY_BD": "#d8dee9",
        "C_ENTRY_FOCUS": "#88c0d0",
        "C_PLAY_BG": "#5e81ac",
        "C_PLAY_FG": "#eceff4",
        "C_PLAY_ACT": "#81a1c1",
        "C_BTN_BG": "#d8dee9",
        "C_BTN_FG": "#2e3440",
        "C_SEP": "#d8dee9",
        "C_DOT_GREEN": "#a3be8c",
        "C_DOT_RED": "#bf616a",
        "C_DOT_BLUE": "#81a1c1",
        "C_ACTIVE_BG": "#d8dee9",
        "C_ACTIVE_FG": "#bf616a",
        "C_TOOLTIP_BG": "#4c566a",
        "C_TOOLTIP_FG": "#eceff4",
        "C_FEEDBACK_WARN_BG": "#ebcb8b",
        "C_FEEDBACK_WARN_FG": "#2e3440",
        "C_FEEDBACK_ERR_BG": "#bf616a",
        "C_FEEDBACK_ERR_FG": "#eceff4",
        "C_SEARCH_BG": "#ebcb8b",
        "C_SEARCH_FG": "#2e3440",
    },
}


def apply_theme(name: str) -> dict[str, str]:
    """Update module-level C_* globals to match a named palette.

    Returns the palette dict for callers that need to pass colors around.
    """
    palette = PALETTES[name]
    for key, value in palette.items():
        globals()[key] = value
    return palette


def palette_names() -> list[str]:
    return list(PALETTES.keys())


# --- Fonts ---
FONT_MAIN      = ("Segoe UI", 8)
FONT_MAIN_BOLD = ("Segoe UI", 8, "bold")
FONT_TITLE     = ("Segoe UI", 16)
FONT_H1        = ("Segoe UI", 13, "bold")
FONT_BTN       = ("Segoe UI", 10, "bold")
FONT_SMALL     = ("Segoe UI", 7)
FONT_MONO      = ("Consolas", 8)
FONT_MONO_M    = ("Consolas", 10)
