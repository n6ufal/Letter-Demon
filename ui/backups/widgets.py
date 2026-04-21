"""Reusable widget constructors — eliminates copy-pasted slider/button code."""

import tkinter as tk
import tkinter.ttk as ttk

from .theme import (
    C_BG, C_BG_PANEL, C_TEXT, C_MUTED, C_ENTRY_BG, C_ENTRY_BD, C_ENTRY_FOCUS,
    C_PLAY_BG, C_PLAY_FG, C_PLAY_ACT, C_BTN_BG, C_BTN_FG,
    C_SEP,
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


def _split_grid_kwargs(kwargs: dict) -> tuple[dict, dict]:
    """Separate grid layout options from widget constructor options.

    Grid keys (row, column, sticky, etc.) go to .grid().
    Tuple-valued padx/pady also go to .grid() (single ints stay as widget padding).
    Everything else goes to the widget constructor.
    """
    grid_opts = {k: v for k, v in kwargs.items() if k in _GRID_KEYS}
    for key in ("padx", "pady"):
        val = kwargs.get(key)
        if isinstance(val, tuple):
            grid_opts[key] = val
    return grid_opts


# ---------------------------------------------------------------------------
# Slider helper
# ---------------------------------------------------------------------------

def make_slider(parent, label: str, variable, from_: int, to: int,
                resolution: int, length: int, bg=C_BG_PANEL):
    """Create a labeled slider row. Returns (slider, value_label).

    The value_label auto-updates when the slider moves.
    """
    val_label = tk.Label(parent, text=f"{int(variable.get())}ms",
                         font=("Segoe UI", 8), bg=bg, fg=C_MUTED,
                         width=5, anchor="e")

    slider = tk.Scale(
        parent, from_=from_, to=to, orient="horizontal",
        variable=variable, showvalue=False,
        length=length, resolution=resolution, sliderlength=14, width=12,
        bg=bg, fg=C_TEXT, troughcolor=C_ENTRY_BD,
        highlightthickness=0, bd=0,
        command=lambda v: val_label.config(text=f"{int(float(v))}ms"),
    )
    return slider, val_label


# ---------------------------------------------------------------------------
# Button helpers
# ---------------------------------------------------------------------------

def make_primary_button(parent, text: str, command, **grid_kwargs):
    """Dark green accent button (Play round, Save).

    Accepts grid layout kwargs (row, column, sticky, padx as tuple, etc.)
    which are applied via .grid(). Widget styling is fixed.
    """
    grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent, text=text, command=command,
        font=("Segoe UI", 10, "bold"), pady=6,
        bg=C_PLAY_BG, fg=C_PLAY_FG,
        activebackground=C_PLAY_ACT, activeforeground=C_PLAY_FG,
        relief="flat", bd=0, cursor="hand2",
    )
    if grid_opts:
        btn.grid(**grid_opts)
    # Hover effects
    btn.bind("<Enter>", lambda e: btn.config(bg=C_PLAY_ACT))
    btn.bind("<Leave>", lambda e: btn.config(bg=C_PLAY_BG))
    return btn


def make_secondary_button(parent, text: str, command, **grid_kwargs):
    """Light gray utility button.

    Accepts grid layout kwargs (row, column, sticky, padx as tuple, etc.)
    which are applied via .grid(). Widget styling is fixed.
    """
    grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent, text=text, command=command,
        font=("Segoe UI", 8), relief="flat", bd=0,
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
