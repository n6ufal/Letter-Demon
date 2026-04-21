"""Modal text editors for trap endings and exceptions files."""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from .theme import (
    C_BG,
    C_ENTRY_BG,
    C_PLAY_ACT,
    C_PLAY_BG,
    C_PLAY_FG,
    C_TEXT,
    FONT_MAIN,
    FONT_MONO_M,
)
from .widgets import make_secondary_button
from .window_utils import center_window


def open_file_editor(app, title, file_path, reload_callback, status_var, default_content):
    win = tk.Toplevel(app.root)
    win.title(title)
    win.resizable(True, True)
    win.attributes("-topmost", True)
    win.configure(bg=C_BG)

    frame = tk.Frame(win, padx=12, pady=12, bg=C_BG)
    frame.pack(fill="both", expand=True)

    text_widget = ScrolledText(
        frame,
        font=FONT_MONO_M,
        width=60,
        height=20,
        bg=C_ENTRY_BG,
        fg=C_TEXT,
        insertbackground=C_TEXT,
        undo=True,
        maxundo=-1,
    )
    text_widget.pack(fill="both", expand=True, pady=(0, 8))

    try:
        with open(file_path, "r", encoding="utf-8") as f_in:
            content = f_in.read()
    except FileNotFoundError:
        content = default_content
    text_widget.insert("1.0", content)

    def save_and_close(event=None):
        save_editor_content(
            app, win, text_widget, file_path, reload_callback, status_var
        )

    def cancel(event=None):
        win.destroy()

    text_widget.bind("<Control-s>", save_and_close)
    text_widget.bind("<Control-S>", save_and_close)
    text_widget.bind("<Escape>", cancel)

    btn_frame = tk.Frame(frame, bg=C_BG)
    btn_frame.pack(fill="x")
    make_secondary_button(btn_frame, "Cancel", cancel).pack(side="right", padx=(4, 0))

    save_btn = tk.Button(
        btn_frame,
        text="Save",
        command=save_and_close,
        font=FONT_MAIN,
        bg=C_PLAY_BG,
        fg=C_PLAY_FG,
        activebackground=C_PLAY_ACT,
        relief="flat",
        bd=0,
        padx=10,
        pady=3,
        cursor="hand2",
    )
    save_btn.pack(side="right")

    center_window(win)
    text_widget.focus_set()


def save_editor_content(app, win, text_widget, file_path, reload_callback, status_var):
    content = text_widget.get("1.0", tk.END).strip()
    try:
        with open(file_path, "w", encoding="utf-8") as f_out:
            f_out.write(content)
            if content and not content.endswith("\n"):
                f_out.write("\n")
        reload_callback()
        if "trap" in file_path:
            count = len(app.engine.trap_endings)
        else:
            count = len(app.engine.word_exceptions)
        status_var.set(f"{count} loaded")
        win.destroy()
    except Exception as e:
        app.notify("error", f"Could not save file: {e}", duration_ms=8000)
