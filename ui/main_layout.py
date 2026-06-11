"""Main window widget tree for Letter Demon."""

import tkinter as tk

from .modes import FALLBACK_DISPLAY, MODE_DISPLAY
from .theme import (
    C_BG,
    C_ENTRY_BD,
    C_ENTRY_BG,
    C_ENTRY_FOCUS,
    C_MUTED,
    C_DOT_GREEN,
    C_DOT_RED,
    C_PLAY_FG,
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
    add_tooltip,
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
        selectbackground=C_ENTRY_FOCUS,
        selectforeground=C_PLAY_FG,
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=C_ENTRY_BD,
        highlightcolor=C_ENTRY_FOCUS,
        validate="key",
        validatecommand=(app._validate_prefix_cmd, "%P"),
    )
    app.entry.grid(row=1, column=0, columnspan=4, sticky="we", ipady=6, ipadx=8, pady=(0, 6))
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
    )
    app.feedback_label.pack(fill="x")
    app.feedback_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(0, 4))
    app.feedback_frame.grid_remove()

    info_bar = tk.Frame(f, bg=C_BG)
    info_bar.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 4))
    for col in range(3):
        info_bar.grid_columnconfigure(col, weight=1)

    app.status_var = tk.StringVar(value="")
    app.status_label = tk.Label(
        info_bar,
        textvariable=app.status_var,
        fg=C_TEXT,
        anchor="w",
        font=FONT_MAIN,
        bg=C_BG,
    )
    app.status_label.grid(row=0, column=0, sticky="w")

    app.auto_prefix_var = tk.StringVar(value="")
    app.auto_prefix_label = tk.Label(
        info_bar,
        textvariable=app.auto_prefix_var,
        fg=C_DOT_GREEN,
        font=FONT_MAIN,
        bg=C_BG,
    )
    app.auto_prefix_label.grid(row=0, column=1)

    app.roblox_status_var = tk.StringVar(value="Roblox")
    app.roblox_status_label = tk.Label(
        info_bar,
        textvariable=app.roblox_status_var,
        fg=C_DOT_RED,
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG,
    )
    app.roblox_status_label.grid(row=0, column=2, sticky="e")

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

    panel = tk.Frame(f, bg=C_BG)
    panel.grid(row=5, column=0, columnspan=4, sticky="we", pady=(0, 6))
    panel.grid_columnconfigure(0, weight=1)

    speed_frame = tk.Frame(panel, bg=C_BG)
    speed_frame.grid(row=0, column=0, sticky="we")
    speed_frame.columnconfigure(1, weight=1)

    tk.Label(
        speed_frame,
        text="Speed:",
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG,
        fg=C_TEXT,
        width=12,
    ).grid(row=0, column=0, sticky="e", padx=(0, 8))

    app.speed_var = tk.DoubleVar(value=settings.get("speed", 170.0))
    app.speed_slider, app.speed_val_label = make_slider(
        speed_frame,
        "Speed",
        app.speed_var,
        from_=10,
        to=250,
        resolution=5,
        length=160,
        suffix="",
    )
    app.speed_slider.grid(row=0, column=1, sticky="ew", pady=(0, 2))
    app.speed_val_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

    humanizer_frame = tk.Frame(panel, bg=C_BG)
    humanizer_frame.grid(row=1, column=0, sticky="we", pady=(4, 0))
    humanizer_frame.columnconfigure(1, weight=1)

    app.humanizer_label = tk.Label(
        humanizer_frame,
        text="Humanizer:",
        anchor="e",
        font=FONT_MAIN,
        bg=C_BG,
        fg=C_TEXT,
        width=12,
    )
    app.humanizer_label.grid(row=0, column=0, sticky="e", padx=(0, 8))

    app.humanizer_slider, app.humanizer_val_label = make_slider(
        humanizer_frame,
        "Humanizer",
        app.jitter_intensity,
        from_=0,
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

    app.advanced_btn = make_secondary_button(
        btn_row,
        "Advanced",
        app.show_advanced,
        row=0,
        column=0,
        sticky="we",
        padx=2,
        pady=(0, 2),
    )
    app.clear_used_btn = make_secondary_button(
        btn_row,
        "Clear Used",
        app.on_clear_used_words,
        row=0,
        column=1,
        sticky="we",
        padx=2,
        pady=(0, 2),
    )
    app.used_words_btn = make_secondary_button(
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

    add_tooltip(app.auto_prefix_label, "Suffix: types only the ending / Full: types the complete word")
    add_tooltip(app.roblox_status_label, f"Green: {app._window_title} running / Red: {app._window_title} not found")
    app.play_btn_tip = add_tooltip(app.play_btn, "Type the word into Roblox (Ctrl+Enter)", delay_ms=200)
    add_tooltip(app.speed_slider, "Average keystroke delay in ms (actual delays vary around this)")
    add_tooltip(app.humanizer_slider, "Human-like timing variation (0 = robotic)")
    add_tooltip(app.mode_combobox, "Primary strategy for picking the word")
    add_tooltip(app.fallback_combobox, "Backup strategy when primary mode finds nothing")
    add_tooltip(app.advanced_btn, "Dictionary, timing, trap endings, exceptions")
    add_tooltip(app.clear_used_btn, "Reset used words for a new game")
    add_tooltip(app.used_words_btn, "Show words played this session")
