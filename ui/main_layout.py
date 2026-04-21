"""Main window widget tree for Letter Demon."""

import tkinter as tk

from .modes import FALLBACK_DISPLAY, MODE_DISPLAY
from .theme import (
    C_BG,
    C_BG_PANEL,
    C_ENTRY_BD,
    C_ENTRY_BG,
    C_ENTRY_FOCUS,
    C_MUTED,
    C_DOT_RED,
    C_TEXT,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_SMALL,
    FONT_TITLE,
)
from .widgets import (
    make_primary_button,
    make_secondary_button,
    make_separator,
    make_slider,
    setup_ttk_styles,
)


def build_main_layout(app, settings: dict) -> None:
    f = app.main_frame

    setup_ttk_styles()

    header_frame = tk.Frame(f, bg=C_BG)
    header_frame.grid(row=0, column=0, columnspan=4, sticky="we", pady=(0, 2))

    tk.Label(
        header_frame,
        text="Starting letters:",
        anchor="w",
        font=FONT_MAIN_BOLD,
        bg=C_BG,
        fg=C_TEXT,
    ).pack(side="left")

    app.entry = tk.Entry(
        f,
        textvariable=app.prefix_var,
        font=FONT_TITLE,
        width=18,
        bg=C_ENTRY_BG,
        fg=C_TEXT,
        insertbackground=C_TEXT,
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=C_ENTRY_BD,
        highlightcolor=C_ENTRY_FOCUS,
    )
    app.entry.grid(row=1, column=0, columnspan=4, sticky="we", ipady=6, pady=(0, 6))
    app.entry.focus_set()

    app.entry.bind(
        "<FocusIn>",
        lambda e: app.entry.config(highlightbackground=C_ENTRY_FOCUS, highlightthickness=2),
    )
    app.entry.bind(
        "<FocusOut>",
        lambda e: app.entry.config(highlightbackground=C_ENTRY_BD, highlightthickness=1),
    )

    app.feedback_frame = tk.Frame(f, bg=C_BG)
    app.feedback_label = tk.Label(
        app.feedback_frame,
        text="",
        anchor="w",
        justify="left",
        font=FONT_MAIN,
        bg=C_BG,
        fg=C_BG,
        padx=8,
        pady=5,
        wraplength=300,
    )
    app.feedback_label.pack(fill="x")
    app.feedback_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(0, 4))
    app.feedback_frame.grid_remove()

    info_bar = tk.Frame(f, bg=C_BG)
    info_bar.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 4))
    app.status_var = tk.StringVar(value="No dictionary loaded")
    tk.Label(
        info_bar,
        textvariable=app.status_var,
        fg=C_MUTED,
        anchor="w",
        font=FONT_MAIN,
        bg=C_BG,
    ).pack(side="left")
    app.roblox_status_var = tk.StringVar(value="○ Roblox: off")
    app.roblox_status_label = tk.Label(
        info_bar,
        textvariable=app.roblox_status_var,
        fg=C_DOT_RED,
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG,
    )
    app.roblox_status_label.pack(side="right")

    app.play_btn = make_primary_button(
        f,
        "Start (Ctrl+Enter)",
        app.on_play_round,
        row=4,
        column=0,
        columnspan=4,
        sticky="we",
        pady=(4, 8),
    )

    panel = tk.Frame(f, bg=C_BG_PANEL, padx=8, pady=6)
    panel.grid(row=5, column=0, columnspan=4, sticky="we", pady=(0, 6))
    panel.grid_columnconfigure(0, weight=1)

    speed_frame = tk.Frame(panel, bg=C_BG_PANEL)
    speed_frame.grid(row=0, column=0, sticky="we")
    speed_frame.columnconfigure(1, weight=1)

    tk.Label(
        speed_frame,
        text="Speed:",
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG_PANEL,
        fg=C_TEXT,
        width=12,
    ).grid(row=0, column=0, sticky="e", padx=(0, 8))

    app.speed_var = tk.DoubleVar(value=settings.get("speed", 170.0))
    app.speed_slider, app.speed_val_label = make_slider(
        speed_frame,
        "Speed",
        app.speed_var,
        from_=10,
        to=200,
        resolution=5,
        length=160,
        suffix="",
    )
    app.speed_slider.grid(row=0, column=1, sticky="ew", pady=(0, 2))
    app.speed_val_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

    humanizer_frame = tk.Frame(panel, bg=C_BG_PANEL)
    humanizer_frame.grid(row=1, column=0, sticky="we", pady=(4, 0))
    humanizer_frame.columnconfigure(1, weight=1)

    tk.Label(
        humanizer_frame,
        text="Humanizer:",
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG_PANEL,
        fg=C_TEXT,
        width=12,
    ).grid(row=0, column=0, sticky="e", padx=(0, 8))

    app.humanizer_slider, app.humanizer_val_label = make_slider(
        humanizer_frame,
        "Humanizer",
        app.jitter_intensity,
        from_=5,
        to=100,
        resolution=5,
        length=160,
        suffix="%",
    )
    app.humanizer_slider.grid(row=0, column=1, sticky="ew", pady=(0, 2))
    app.humanizer_val_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

    combo_row = tk.Frame(f, bg=C_BG)
    combo_row.grid(row=6, column=0, columnspan=4, sticky="we", pady=(0, 4))

    tk.Label(combo_row, text="Mode:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
        side="left", padx=(0, 8)
    )
    app.mode_combobox = tk.ttk.Combobox(
        combo_row,
        textvariable=app.mode_var,
        values=MODE_DISPLAY,
        state="readonly",
        width=8,
    )
    app.mode_combobox.pack(side="left", padx=(0, 12))

    tk.Label(combo_row, text="Fallback:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
        side="left", padx=(0, 8)
    )
    app.fallback_combobox = tk.ttk.Combobox(
        combo_row,
        textvariable=app.fallback_var,
        values=FALLBACK_DISPLAY,
        state="readonly",
        width=8,
    )
    app.fallback_combobox.pack(side="left")

    make_separator(f, 7, column=0, columnspan=4, sticky="we", pady=(4, 6))

    btn_row = tk.Frame(f, bg=C_BG)
    btn_row.grid(row=8, column=0, columnspan=4, sticky="we", pady=(0, 2))
    btn_row.grid_columnconfigure(0, weight=1)
    btn_row.grid_columnconfigure(1, weight=1)
    btn_row.grid_columnconfigure(2, weight=1)

    make_secondary_button(
        btn_row,
        "Advanced",
        app.show_advanced,
        row=0,
        column=0,
        sticky="we",
        padx=2,
        pady=(0, 2),
    )
    make_secondary_button(
        btn_row,
        "Clear",
        app.on_clear_cache,
        row=0,
        column=1,
        sticky="we",
        padx=2,
        pady=(0, 2),
    )
    make_secondary_button(
        btn_row,
        "Used Words",
        app.show_used_words,
        row=0,
        column=2,
        sticky="we",
        padx=2,
        pady=(0, 2),
    )

    credit = tk.Label(
        f, text="Made by n6ufal", fg=C_MUTED, font=FONT_SMALL, bg=C_BG, cursor="hand2"
    )
    credit.grid(row=9, column=0, columnspan=4, sticky="e", pady=(2, 0))
    credit.bind("<Button-1>", lambda e: app.show_about())
    credit.bind("<Enter>", lambda e: credit.config(fg=C_TEXT))
    credit.bind("<Leave>", lambda e: credit.config(fg=C_MUTED))

    for col in range(4):
        f.grid_columnconfigure(col, weight=1)
