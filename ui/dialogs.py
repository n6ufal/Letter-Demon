"""Secondary windows: Advanced, About, Used Words."""

import tkinter as tk

from .theme import (
    C_BG,
    C_BG_PANEL,
    C_ENTRY_BG,
    C_MUTED,
    C_PLAY_BG,
    C_PLAY_FG,
    C_SEP,
    C_TEXT,
    FONT_BTN,
    FONT_H1,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_MONO_M,
    FONT_SMALL,
)
from .widgets import make_secondary_button, make_separator, make_slider
from .window_utils import center_window


def show_about(app) -> None:
    win = tk.Toplevel(app.root)
    win.title("About")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.configure(bg=C_BG)

    f = tk.Frame(win, bg=C_BG, padx=24, pady=20)
    f.pack(fill="both", expand=True)

    title_row = tk.Frame(f, bg=C_BG)
    title_row.pack(anchor="w", fill="x")
    tk.Label(title_row, text="Letter Demon 😈", font=FONT_H1, bg=C_BG, fg=C_TEXT).pack(
        side="left"
    )
    tk.Label(
        f, text="v6 \u2022 April 2026", font=FONT_MAIN, bg=C_BG, fg=C_MUTED
    ).pack(anchor="w", pady=(2, 0))

    tk.Label(
        f,
        text="The Demon knows every word your opponent doesn't.",
        font=FONT_MAIN,
        bg=C_BG,
        fg=C_MUTED,
    ).pack(anchor="w", pady=(2, 12))

    sep = tk.Frame(f, height=1, bg=C_SEP)
    sep.pack(fill="x", pady=(0, 12))

    tk.Label(f, text="Made by n6ufal with 💜", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
        anchor="w"
    )
    import webbrowser
    email_label = tk.Label(
        f,
        text="Email: boxcarr@proton.me",
        font=FONT_MAIN,
        bg=C_BG,
        fg=C_TEXT,
        cursor="hand2",
    )
    email_label.pack(anchor="w", pady=(2, 0))
    email_label.bind(
        "<Button-1>",
        lambda e: webbrowser.open("mailto:boxcarr@proton.me")
    )

    center_window(win)


def show_advanced(app) -> None:
    if app._advanced_window is not None and app._advanced_window.winfo_exists():
        app._advanced_window.lift()
        app._advanced_window.focus_force()
        return

    win = tk.Toplevel(app.root)
    win.title("Advanced")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.configure(bg=C_BG)
    app._advanced_window = win

    f = tk.Frame(win, padx=14, pady=12, bg=C_BG)
    f.pack(fill="both", expand=True)

    row = 0

    tk.Label(f, text="Dictionary", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    row += 1
    app.dict_label_var = tk.StringVar(value=app._dict_display_name())
    tk.Label(f, textvariable=app.dict_label_var, fg=C_MUTED, font=FONT_MAIN, anchor="w", bg=C_BG).grid(
        row=row, column=0, sticky="w"
    )
    make_secondary_button(
        f, "Load Dictionary", app.on_load_dict, row=row, column=1, sticky="e", padx=(12, 0)
    )
    row += 1
    make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
    row += 1

    tk.Label(f, text="Timing", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    row += 1

    tk.Label(f, text="Pre-type delay:", font=FONT_MAIN, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, columnspan=2, sticky="w"
    )
    row += 1

    def on_adv_pre_move(v):
        adv_pre_val.config(text=f"{int(v)}ms")

    adv_pre_slider, adv_pre_val = make_slider(
        f,
        "Pre-type",
        app.pre_delay_var,
        from_=100,
        to=2000,
        resolution=50,
        length=200,
        bg=C_BG,
        command=on_adv_pre_move,
    )
    adv_pre_slider.grid(row=row, column=0, sticky="we", pady=(0, 6))
    adv_pre_val.grid(row=row, column=1, sticky="e")
    row += 1

    tk.Label(f, text="Post-type delay:", font=FONT_MAIN, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, columnspan=2, sticky="w"
    )
    row += 1

    def on_adv_post_move(v):
        adv_post_val.config(text=f"{int(v)}ms")

    adv_post_slider, adv_post_val = make_slider(
        f,
        "Post-type",
        app.post_delay_var,
        from_=100,
        to=2000,
        resolution=50,
        length=200,
        bg=C_BG,
        command=on_adv_post_move,
    )
    adv_post_slider.grid(row=row, column=0, sticky="we", pady=(0, 4))
    adv_post_val.grid(row=row, column=1, sticky="e")
    row += 1

    make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
    row += 1

    tk.Label(f, text="Trap endings", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, sticky="nw", pady=(0, 2), padx=(0, 12)
    )
    tk.Label(f, text="Exceptions", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=1, sticky="nw", pady=(0, 2)
    )
    row += 1

    app.trap_status_var = tk.StringVar(value=f"{len(app.engine.trap_endings)} loaded")
    tk.Label(f, textvariable=app.trap_status_var, fg=C_MUTED, font=FONT_MAIN, anchor="w", bg=C_BG).grid(
        row=row, column=0, sticky="nw", padx=(0, 12)
    )
    app.exceptions_status_var = tk.StringVar(
        value=f"{len(app.engine.word_exceptions)} loaded"
    )
    tk.Label(
        f, textvariable=app.exceptions_status_var, fg=C_MUTED, font=FONT_MAIN, anchor="w", bg=C_BG
    ).grid(row=row, column=1, sticky="nw")
    row += 1

    btn_row_trap = tk.Frame(f, bg=C_BG)
    btn_row_trap.grid(row=row, column=0, sticky="nw", pady=(4, 0), padx=(0, 12))
    make_secondary_button(btn_row_trap, "Reload", app.reload_trap_endings).pack(
        side="left", padx=(0, 4)
    )
    make_secondary_button(btn_row_trap, "Edit", app.edit_trap_endings).pack(side="left")

    btn_row_exc = tk.Frame(f, bg=C_BG)
    btn_row_exc.grid(row=row, column=1, sticky="nw", pady=(4, 0))
    make_secondary_button(btn_row_exc, "Reload", app.reload_exceptions).pack(
        side="left", padx=(0, 4)
    )
    make_secondary_button(btn_row_exc, "Edit", app.edit_exceptions).pack(side="left")
    row += 1

    make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
    row += 1

    tk.Label(f, text="Humanizer", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    row += 1

    app.humanizer_check = tk.Checkbutton(
        f,
        text="Enable Humanizer",
        variable=app.jitter_enabled,
        command=app._on_jitter_toggle,
        font=FONT_BTN,
        bg=C_BG,
        fg=C_TEXT,
        activebackground=C_BG,
        activeforeground=C_TEXT,
        selectcolor=C_ENTRY_BG,
        padx=4,
        pady=6,
    )
    app.humanizer_check.grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1

    f.grid_columnconfigure(0, weight=1)
    f.grid_columnconfigure(1, weight=1)
    center_window(win)

    def _on_adv_close():
        app._advanced_window = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_adv_close)


def used_words_window_alive(app) -> bool:
    try:
        return app.used_words_window is not None and app.used_words_window.winfo_exists()
    except tk.TclError:
        return False


def show_used_words(app) -> None:
    if not used_words_window_alive(app):
        app.used_words_window = tk.Toplevel(app.root)
        app.used_words_window.title("Used Words")
        app.used_words_window.resizable(True, True)
        app.used_words_window.attributes("-topmost", True)
        app.used_words_window.configure(bg=C_BG)

        outer = tk.Frame(app.used_words_window, bg=C_BG, padx=8, pady=8)
        outer.pack(fill="both", expand=True)

        list_frame = tk.Frame(outer, bg=C_BG_PANEL, padx=1, pady=1)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        app.used_words_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=FONT_MONO_M,
            width=28,
            height=15,
            bg=C_ENTRY_BG,
            fg=C_TEXT,
            selectbackground=C_PLAY_BG,
            selectforeground=C_PLAY_FG,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        app.used_words_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=app.used_words_listbox.yview)

        _, n_used = app.engine.used_words_for_display()
        app.used_words_count = tk.Label(
            outer,
            text=f"{n_used} words used",
            anchor="w",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_MUTED,
        )
        app.used_words_count.pack(fill="x", pady=(6, 4))

        make_secondary_button(outer, "Close", lambda: close_used_words(app)).pack()

        center_window(app.used_words_window)
        app.used_words_window.protocol(
            "WM_DELETE_WINDOW", lambda: close_used_words(app)
        )

    update_used_words_list(app)
    app.used_words_window.lift()
    app.used_words_window.focus_force()


def close_used_words(app) -> None:
    app.used_words_window.destroy()
    app.used_words_window = None


def update_used_words_list(app) -> None:
    if used_words_window_alive(app):
        words, n = app.engine.used_words_for_display()
        app.used_words_listbox.delete(0, tk.END)
        for word in words:
            app.used_words_listbox.insert(tk.END, word)
        app.used_words_count.config(text=f"{n} words used")
