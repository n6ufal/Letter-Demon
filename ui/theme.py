"""Color palette and fonts — single source of truth for all UI styling."""

# --- Colors ---
C_BG          = "#fafafa"   # main background
C_BG_PANEL    = "#f0f1f3"   # subtle inset panel for controls
C_TEXT        = "#1a1a1a"   # primary text
C_MUTED       = "#888888"   # labels, hints, secondary text
C_ENTRY_BG    = "#ffffff"   # entry field background
C_ENTRY_BD    = "#adadad"   # entry border (unfocused) — subtle but visible
C_ENTRY_FOCUS = "#2d6a4f"   # entry border (focused) — matches Play button green
C_PLAY_BG     = "#2d6a4f"   # Play round button — dark green
C_PLAY_FG     = "#ffffff"   # Play round text
C_PLAY_ACT    = "#245a42"   # Play round hover/active
C_BTN_BG      = "#e8e8e8"   # secondary button background
C_BTN_FG      = "#1a1a1a"   # secondary button text
C_SEP         = "#dedede"   # separator color
C_DOT_GREEN   = "#27ae60"   # Roblox found dot
C_DOT_RED     = "#e74c3c"   # Roblox not found dot

# Inline feedback strip (no modal dialogs)
C_FEEDBACK_WARN_BG  = "#fff3e0"   # light amber panel
C_FEEDBACK_WARN_FG  = "#b45309"   # amber-brown text
C_FEEDBACK_ERR_BG   = "#fdecea"   # light red panel
C_FEEDBACK_ERR_FG   = "#c0392b"   # red text

# --- Fonts ---
FONT_MAIN      = ("Segoe UI", 8)
FONT_MAIN_BOLD = ("Segoe UI", 8, "bold")
FONT_TITLE     = ("Segoe UI", 16)
FONT_H1        = ("Segoe UI", 13, "bold")
FONT_BTN       = ("Segoe UI", 10, "bold")
FONT_SMALL     = ("Segoe UI", 7)
FONT_MONO      = ("Consolas", 8)
FONT_MONO_M    = ("Consolas", 10)
