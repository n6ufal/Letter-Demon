# widgets.py — fixed _split_grid_kwargs to handle int padx/pady with grid keys
"""Reusable widget constructors — eliminates copy-pasted slider/button code."""

import tkinter as tk
import tkinter.ttk as ttk

from .theme import (
    C_BG,
    C_BG_PANEL,
    C_BTN_BG,
    C_BTN_FG,
    C_ENTRY_BD,
    C_ENTRY_BG,
    C_MUTED,
    C_PLAY_ACT,
    C_PLAY_BG,
    C_PLAY_FG,
    C_SEP,
    C_TEXT,
    C_TOOLTIP_BG,
    C_TOOLTIP_FG,
    FONT_BTN,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_MONO,
    FONT_MONO_M,
    FONT_SMALL,
)


class ToolTip:
    """Hover tooltip for any tkinter widget.

    Shows a small popup with explanatory text after a short delay.
    """

    def __init__(self, widget: tk.Widget, text: str, *, delay_ms: int = 500):
        self.widget = widget
        self.text = text
        self._delay_ms = delay_ms
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")

    def _enter(self, event=None) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
        self._after_id = self.widget.after(self._delay_ms, self._show)

    def _leave(self, event=None) -> None:
        self._cancel()
        self._hide()

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(
            tw,
            text=self.text,
            background=C_TOOLTIP_BG,
            foreground=C_TOOLTIP_FG,
            font=FONT_SMALL,
            padx=6,
            pady=3,
            wraplength=250,
        ).pack()

    def _hide(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


def add_tooltip(widget: tk.Widget, text: str, *, delay_ms: int = 500) -> ToolTip:
    return ToolTip(widget, text, delay_ms=delay_ms)


# Keys that belong to .grid(), not to the widget constructor
_GRID_KEYS = {"row", "column", "rowspan", "columnspan", "sticky", "ipadx", "ipady"}


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def _safe_configure(style, name, **opts):
    for key, val in opts.items():
        try:
            style.configure(name, **{key: val})
        except tk.TclError:
            pass


def _safe_map(style, name, **opts):
    for key, val in opts.items():
        try:
            style.map(name, **{key: val})
        except tk.TclError:
            pass


# The clam theme expresses slider and scrollbar sizes in points, so they grow
# with display DPI. Plain pixel values keep these controls compact.
_SLIM_SCALE = {"gripsize": 8, "sliderlength": 14, "troughheight": 4, "borderwidth": 0}
_SLIM_SCROLLBAR = {"gripsize": 9, "arrowsize": 13, "width": 11, "gripcount": 0, "borderwidth": 0}


def setup_ttk_styles():
    """Configure the ttk theme once at startup."""
    style = ttk.Style()
    style.theme_use("clam")

    _safe_configure(
        style,
        "TCombobox",
        fieldbackground=C_ENTRY_BG,
        background=C_ENTRY_BG,
        foreground=C_TEXT,
        bordercolor=C_ENTRY_BD,
        lightcolor=C_ENTRY_BD,
        darkcolor=C_ENTRY_BD,
        troughcolor=C_ENTRY_BG,
        arrowcolor=C_TEXT,
        arrowsize=13,
        borderwidth=1,
        padding=2,
        relief="flat",
    )
    _safe_map(
        style,
        "TCombobox",
        fieldbackground=[("readonly", C_ENTRY_BG)],
        foreground=[("readonly", C_TEXT)],
        bordercolor=[("focus", C_PLAY_BG), ("!focus", C_ENTRY_BD)],
        selectbackground=[("readonly", C_PLAY_BG)],
        selectforeground=[("readonly", C_PLAY_FG)],
    )

    _safe_configure(
        style,
        "TCheckbutton",
        background=C_BG,
        foreground=C_TEXT,
        focuscolor=C_BG,
        indicatorbackground=C_ENTRY_BG,
        indicatorforeground=C_TEXT,
        indicatorrelief="flat",
        bordercolor=C_ENTRY_BD,
        lightcolor=C_ENTRY_BD,
        darkcolor=C_ENTRY_BD,
        troughcolor=C_ENTRY_BG,
    )
    _safe_map(
        style,
        "TCheckbutton",
        background=[("active", C_BG)],
        foreground=[("disabled", C_MUTED)],
    )

    _safe_configure(
        style,
        "TScrollbar",
        background=C_BTN_BG,
        troughcolor=C_BG_PANEL,
        bordercolor=C_BG_PANEL,
        lightcolor=C_BTN_BG,
        darkcolor=C_ENTRY_BD,
        arrowcolor=C_MUTED,
        troughrelief="flat",
        relief="flat",
        **_SLIM_SCROLLBAR,
    )

    _safe_configure(
        style,
        "TButton",
        background=C_BTN_BG,
        foreground=C_BTN_FG,
        bordercolor=C_ENTRY_BD,
        lightcolor=C_ENTRY_BD,
        darkcolor=C_ENTRY_BD,
        troughcolor=C_BTN_BG,
        focuscolor=C_BG,
        relief="flat",
        borderwidth=0,
        padding=(8, 4),
    )
    _safe_map(
        style,
        "TButton",
        background=[("active", C_ENTRY_BD)],
        foreground=[("disabled", C_MUTED)],
    )

    _safe_configure(style, "TFrame", background=C_BG)
    _safe_configure(
        style,
        "TSeparator",
        background=C_SEP,
        troughcolor=C_SEP,
        bordercolor=C_SEP,
        lightcolor=C_SEP,
        darkcolor=C_SEP,
    )

    _safe_configure(
        style,
        "Treeview",
        background=C_ENTRY_BG,
        foreground=C_TEXT,
        fieldbackground=C_ENTRY_BG,
        bordercolor=C_BG,
        lightcolor=C_ENTRY_BG,
        darkcolor=C_ENTRY_BG,
        troughcolor=C_BG,
        font=FONT_MONO_M,
        rowheight=32,
        borderwidth=0,
    )
    _safe_map(
        style,
        "Treeview",
        background=[("selected", C_PLAY_BG)],
        foreground=[("selected", C_PLAY_FG)],
    )
    _safe_configure(
        style,
        "Treeview.Heading",
        background=C_BG_PANEL,
        foreground=C_TEXT,
        font=FONT_MAIN_BOLD,
        relief="flat",
        bordercolor=C_SEP,
        lightcolor=C_SEP,
        darkcolor=C_SEP,
        troughcolor=C_BG_PANEL,
        borderwidth=0,
        padding=(6, 4),
    )
    _safe_map(
        style,
        "Treeview.Heading",
        background=[("active", C_BTN_BG)],
    )

    _safe_configure(
        style,
        "Panel.Horizontal.TScale",
        background=C_ENTRY_BD,
        troughcolor=C_SEP,
        bordercolor=C_SEP,
        lightcolor=C_ENTRY_BG,
        darkcolor=C_ENTRY_BD,
        relief="flat",
        troughrelief="flat",
        **_SLIM_SCALE,
    )
    _safe_configure(
        style,
        "Bg.Horizontal.TScale",
        background=C_ENTRY_BD,
        troughcolor=C_BTN_BG,
        bordercolor=C_BTN_BG,
        lightcolor=C_ENTRY_BG,
        darkcolor=C_ENTRY_BD,
        relief="flat",
        troughrelief="flat",
        **_SLIM_SCALE,
    )


def _split_grid_kwargs(kwargs: dict) -> tuple[dict, dict]:
    """Separate grid layout options from widget constructor options.

    Extracts standard grid keys (row, column, sticky, etc.) AND padx/pady
    when grid keys are present (padx/pady are always grid options in that
    context, whether int or tuple).
    Returns (widget_opts, grid_opts).
    """
    grid_opts = {k: v for k, v in kwargs.items() if k in _GRID_KEYS}
    has_grid_keys = bool(grid_opts)
    for key in ("padx", "pady"):
        val = kwargs.get(key)
        if isinstance(val, tuple) or has_grid_keys:
            grid_opts[key] = val
    widget_opts = {k: v for k, v in kwargs.items() if k not in grid_opts}
    return widget_opts, grid_opts


# ---------------------------------------------------------------------------
# Slider helper
# ---------------------------------------------------------------------------


def make_slider(
    parent,
    label: str,
    variable,
    from_: int,
    to: int,
    resolution: int = 1,
    length: int = 180,
    bg=C_BG_PANEL,
    suffix: str = "ms",
    command=None,
):
    """Create a modern labeled slider row. Returns (slider, value_label).

    Uses ttk.Scale for a modern aesthetic, manually enforcing resolution snapping.
    """
    val_label = tk.Label(
        parent,
        text=f"{int(variable.get())}{suffix}",
        font=FONT_MONO,
        bg=bg,
        fg=C_TEXT,
        width=7,
        anchor="e",
    )

    style_name = (
        "Panel.Horizontal.TScale" if bg == C_BG_PANEL else "Bg.Horizontal.TScale"
    )

    slider = ttk.Scale(
        parent,
        from_=from_,
        to=to,
        orient="horizontal",
        length=length,
        style=style_name,
    )
    slider.set(variable.get())

    def _on_move(val):
        v = float(val)
        snapped = round(v / resolution) * resolution
        variable.set(snapped)
        val_label.config(text=f"{int(snapped)}{suffix}")
        if command:
            command(snapped)

    def _on_release(event):
        snapped = round(slider.get() / resolution) * resolution
        variable.set(snapped)
        slider.set(snapped)
        val_label.config(text=f"{int(snapped)}{suffix}")

    def _on_scroll(event):
        step = resolution if event.delta > 0 else -resolution
        snapped = round(slider.get() / resolution) * resolution
        new_val = max(from_, min(to, snapped + step))
        variable.set(new_val)
        slider.set(new_val)
        val_label.config(text=f"{int(new_val)}{suffix}")
        if command:
            command(new_val)

    slider.configure(command=_on_move)
    slider.bind("<ButtonRelease-1>", _on_release, add="+")
    slider.bind("<MouseWheel>", _on_scroll, add="+")

    return slider, val_label


# ---------------------------------------------------------------------------
# Button helpers
# ---------------------------------------------------------------------------


def make_primary_button(parent, text: str, command, **grid_kwargs):
    """Dark green accent button (Play round, Save)."""
    _, grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONT_BTN,
        pady=6,
        bg=C_PLAY_BG,
        fg=C_PLAY_FG,
        activebackground=C_PLAY_ACT,
        activeforeground=C_PLAY_FG,
        relief="flat",
        bd=0,
        cursor="hand2",
    )
    if grid_opts:
        btn.grid(**grid_opts)
    btn.bind("<Enter>", lambda e: btn.config(bg=C_PLAY_ACT))
    btn.bind("<Leave>", lambda e: btn.config(bg=C_PLAY_BG))
    return btn


def make_secondary_button(parent, text: str, command, **grid_kwargs):
    """Light gray utility button."""
    _, grid_opts = _split_grid_kwargs(grid_kwargs)

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONT_MAIN,
        relief="flat",
        bd=0,
        padx=6,
        pady=3,
        cursor="hand2",
        bg=C_BTN_BG,
        fg=C_BTN_FG,
        activebackground=C_ENTRY_BD,
        activeforeground=C_TEXT,
    )
    if grid_opts:
        btn.grid(**grid_opts)
    btn.bind("<Enter>", lambda e: btn.config(bg=C_ENTRY_BD))
    btn.bind("<Leave>", lambda e: btn.config(bg=C_BTN_BG))
    return btn


# ---------------------------------------------------------------------------
# Separator
# ---------------------------------------------------------------------------


def make_separator(parent, row: int, **grid_kwargs):
    """Thin horizontal separator line."""
    sep = tk.Frame(parent, height=1, bg=C_SEP)
    sep.grid(row=row, **grid_kwargs)
    return sep
