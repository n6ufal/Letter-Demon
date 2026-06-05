"""Modal text editors for trap endings and exceptions files."""

import os
import shutil
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from .theme import (
    C_BG,
    C_ENTRY_BG,
    C_MUTED,
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
    text_widget.tag_configure("search", background="yellow", foreground="black")

    search_var = tk.StringVar()
    search_frame = tk.Frame(frame, bg=C_BG)

    tk.Label(search_frame, text="Find:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
        side="left", padx=(0, 4)
    )
    search_entry = tk.Entry(
        search_frame, textvariable=search_var, font=FONT_MAIN, width=25,
        bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
        relief="solid", bd=1,
    )
    search_entry.pack(side="left", padx=(0, 6))

    match_label = tk.Label(search_frame, text="", font=FONT_MAIN, bg=C_BG, fg=C_MUTED)
    match_label.pack(side="left")

    search_matches: list[str] = []
    search_index = 0

    def _go_prev():
        nonlocal search_index
        if not search_matches:
            return
        search_index = (search_index - 1) % len(search_matches)
        text_widget.see(search_matches[search_index])
        match_label.config(text=f"{search_index + 1}/{len(search_matches)}")

    def _go_next():
        nonlocal search_index
        if not search_matches:
            return
        search_index = (search_index + 1) % len(search_matches)
        text_widget.see(search_matches[search_index])
        match_label.config(text=f"{search_index + 1}/{len(search_matches)}")

    prev_btn = tk.Button(
        search_frame, text="◀", command=_go_prev,
        font=FONT_MAIN, relief="flat", bd=0, padx=4, pady=1, cursor="hand2",
        bg=C_BG, fg=C_TEXT, activebackground=C_ENTRY_BG, state=tk.DISABLED,
    )
    prev_btn.pack(side="left", padx=(2, 0))

    next_btn = tk.Button(
        search_frame, text="▶", command=_go_next,
        font=FONT_MAIN, relief="flat", bd=0, padx=4, pady=1, cursor="hand2",
        bg=C_BG, fg=C_TEXT, activebackground=C_ENTRY_BG, state=tk.DISABLED,
    )
    next_btn.pack(side="left")

    search_frame.pack(fill="x", pady=(0, 6))

    def _on_search(*args):
        nonlocal search_matches, search_index
        text_widget.tag_remove("search", "1.0", tk.END)
        query = search_var.get()
        if not query:
            match_label.config(text="")
            prev_btn.config(state=tk.DISABLED)
            next_btn.config(state=tk.DISABLED)
            search_matches = []
            return

        search_matches = []
        pos = "1.0"
        query_lower = query.lower()
        while True:
            pos = text_widget.search(query_lower, pos, tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            text_widget.tag_add("search", pos, end)
            search_matches.append(pos)
            pos = end

        if search_matches:
            search_index = 0
            text_widget.see(search_matches[0])
            match_label.config(text=f"1/{len(search_matches)}")
            prev_btn.config(state=tk.NORMAL)
            next_btn.config(state=tk.NORMAL)
        else:
            match_label.config(text="0 matches")
            prev_btn.config(state=tk.DISABLED)
            next_btn.config(state=tk.DISABLED)

    search_var.trace_add("write", _on_search)

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

    center_window(win, app.root)
    text_widget.focus_set()


def save_editor_content(app, win, text_widget, file_path, reload_callback, status_var):
    content = text_widget.get("1.0", tk.END).strip()
    try:
        if os.path.exists(file_path):
            shutil.copy2(file_path, file_path + ".bak")
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
