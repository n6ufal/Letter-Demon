# widgets.py — fixed _split_grid_kwargs to handle int padx/pady with grid keys
"""Reusable widget constructors — eliminates copy-pasted slider/button code."""

import tkinter as tk
import tkinter.ttk as ttk

from .theme import (
    C_BG, C_BG_PANEL, C_TEXT, C_MUTED, C_ENTRY_BG, C_ENTRY_BD, C_ENTRY_FOCUS,
    C_PLAY_BG, C_PLAY_FG, C_PLAY_ACT, C_BTN_BG, C_BTN_FG,
    C_SEP, C_ACCENT_LIGHT, FONT_BTN, FONT_MAIN, FONT_MONO
)

# Keys that belong to .grid(), not to the widget constructor
_GRID_KEYS = {"row", "column", "rowspan", "columnspan", "sticky", "ipadx", "ipady"}


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_ttk_styles():
    """Configure the ttk theme once at startup."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TCombobox",
        fieldbackground=C_ENTRY_BG, background=C_BTN_BG,
        foreground=C_TEXT, bordercolor=C_ENTRY_BD,
        arrowcolor=C_TEXT, relief="flat",
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", C_ENTRY_BG)],
        foreground=[("readonly", C_TEXT)],
        bordercolor=[("focus", C_PLAY_BG), ("!focus", C_ENTRY_BD)],
        selectbackground=[("readonly", C_ENTRY_BG)],
        selectforeground=[("readonly", C_TEXT)],
    )

    style.configure("TCheckbutton",
        background=C_BG, foreground=C_TEXT, focuscolor=C_BG,
    )
    style.map("TCheckbutton", background=[("active", C_BG)])

    style.configure("TScrollbar",
        background=C_BTN_BG, troughcolor=C_BG_PANEL,
        bordercolor=C_BG_PANEL, arrowcolor=C_MUTED, relief="flat",
    )

    style.configure("TButton",
        background=C_BTN_BG, foreground=C_BTN_FG,
        bordercolor=C_ENTRY_BD, focuscolor=C_BG,
        relief="flat", padding=(8, 4),
    )
    style.map("TButton", background=[("active", C_ENTRY_BD)])

    style.configure("TFrame", background=C_BG)
    style.configure("TSeparator", background=C_SEP)

    # Styles for the new ttk.Scale sliders
    style.configure("Panel.Horizontal.TScale", background=C_BG_PANEL)
    style.configure("Bg.Horizontal.TScale", background=C_BG)


def _split_grid_kwargs(kwargs: dict) -> dict:
    """Separate grid layout options from widget constructor options.

    Extracts standard grid keys (row, column, sticky, etc.) AND padx/pady
    when grid keys are present (padx/pady are always grid options in that
    context, whether int or tuple).
    """
    grid_opts = {k: v for k, v in kwargs.items() if k in _GRID_KEYS}
    has_grid_keys = bool(grid_opts)
    for key in ("padx", "pady"):
        val = kwargs.get(key)
        if isinstance(val, tuple) or has_grid_keys:
            grid_opts[key] = val
    return grid_opts


# ---------------------------------------------------------------------------
# Slider helper
# ---------------------------------------------------------------------------

def make_slider(parent, label: str, variable, from_: int, to: int,
                resolution: int = 1, length: int = 180, bg=C_BG_PANEL,
                suffix: str = "ms", command=None):
    """Create a modern labeled slider row. Returns (slider, value_label).

    Uses ttk.Scale for a modern aesthetic, manually enforcing resolution snapping.
    """
    val_label = tk.Label(parent, text=f"{int(variable.get())}{suffix}",
                         font=FONT_MONO, bg=bg, fg=C_TEXT,
                         width=5, anchor="e")

    def _on_move(val):
        # Snap to exact resolution
        v = float(val)
        snapped = round(v / resolution) * resolution
        variable.set(snapped)
        val_label.config(text=f"{int(snapped)}{suffix}")

        # Fire secondary command if passed (useful for updating multiple UIs)
        if command:
            command(snapped)

    style_name = "Panel.Horizontal.TScale" if bg == C_BG_PANEL else "Bg.Horizontal.TScale"

    slider = ttk.Scale(
        parent, from_=from_, to=to, orient="horizontal",
        variable=variable, length=length,
        command=_on_move, style=style_name
    )

    return slider, val_label


# ---------------------------------------------------------------------------
# Button helpers
# ---------------------------------------------------------------------------

def make_primary_button(parent, text: str, command, **grid_kwargs):
    """Dark green accent button (Play round, Save)."""
    grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent, text=text, command=command,
        font=FONT_BTN, pady=6,
        bg=C_PLAY_BG, fg=C_PLAY_FG,
        activebackground=C_PLAY_ACT, activeforeground=C_PLAY_FG,
        relief="flat", bd=0, cursor="hand2",
    )
    if grid_opts:
        btn.grid(**grid_opts)
    btn.bind("<Enter>", lambda e: btn.config(bg=C_PLAY_ACT))
    btn.bind("<Leave>", lambda e: btn.config(bg=C_PLAY_BG))
    return btn


def make_secondary_button(parent, text: str, command, **grid_kwargs):
    """Light gray utility button."""
    grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent, text=text, command=command,
        font=FONT_MAIN, relief="flat", bd=0,
        padx=6, pady=3, cursor="hand2",
        bg=C_BTN_BG, fg=C_BTN_FG,
        activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
    )
    if grid_opts:
        btn.grid(**grid_opts)
    return btn


# ---------------------------------------------------------------------------
# Separator
# ---------------------------------------------------------------------------

def make_separator(parent, row: int, **grid_kwargs):
    """Thin horizontal separator line."""
    sep = tk.Frame(parent, height=1, bg=C_SEP)
    sep.grid(row=row, **grid_kwargs)
    return sep
