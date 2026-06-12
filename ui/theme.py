"""Color palette and fonts — single source of truth for all UI styling."""

# --- Colors ---
C_BG          = "#fafafa"   # main background
C_BG_PANEL    = "#f4f4f5"   # subtle inset panel for controls
C_TEXT        = "#18181b"   # primary text
C_MUTED       = "#71717a"   # labels, hints, secondary text
C_ENTRY_BG    = "#ffffff"   # entry field background
C_ENTRY_BD    = "#d4d4d4"   # entry border (unfocused) — subtle but visible
C_ENTRY_FOCUS = "#16a34a"   # entry border (focused) — matches Play button green
C_PLAY_BG     = "#16a34a"   # Play round button — green
C_PLAY_FG     = "#ffffff"   # Play round text
C_PLAY_ACT    = "#15803d"   # Play round hover/active
C_BTN_BG      = "#e4e4e7"   # secondary button background
C_BTN_FG      = "#18181b"   # secondary button text
C_SEP         = "#e4e4e7"   # separator color
C_DOT_GREEN   = "#16a34a"   # connected / suffix / dict loaded
C_DOT_RED     = "#dc2626"   # disconnected
C_DOT_BLUE    = "#2563eb"   # full-word mode
C_ACTIVE_BG   = "#e4e4e7"   # button active / pressed background
C_ACTIVE_FG   = "#991b1b"   # button active foreground (error variant)
C_TOOLTIP_BG  = "#1f2937"   # tooltip popup background
C_TOOLTIP_FG  = "#f9fafb"   # tooltip popup foreground

# Inline feedback strip (no modal dialogs)
C_FEEDBACK_WARN_BG  = "#fef3c7"   # light amber panel
C_FEEDBACK_WARN_FG  = "#92400e"   # amber-brown text
C_FEEDBACK_ERR_BG   = "#fee2e2"   # light red panel
C_FEEDBACK_ERR_FG   = "#991b1b"   # red text

# Search highlight in text editors
C_SEARCH_BG = "#fef08a"   # soft yellow
C_SEARCH_FG = "#1a1a1a"   # black text on yellow

# --- Fonts ---
FONT_MAIN      = ("Segoe UI", 8)
FONT_MAIN_BOLD = ("Segoe UI", 8, "bold")
FONT_TITLE     = ("Segoe UI", 16)
FONT_H1        = ("Segoe UI", 13, "bold")
FONT_BTN       = ("Segoe UI", 10, "bold")
FONT_SMALL     = ("Segoe UI", 7)
FONT_MONO      = ("Consolas", 8)
FONT_MONO_M    = ("Consolas", 10)
