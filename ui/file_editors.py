"""Modal text editors for trap endings and exceptions files."""

import shutil
import tkinter as tk
from pathlib import Path
from tkinter.scrolledtext import ScrolledText

from .theme import (
    C_BG,
    C_ENTRY_BG,
    C_MUTED,
    C_PLAY_ACT,
    C_PLAY_BG,
    C_PLAY_FG,
    C_SEARCH_BG,
    C_SEARCH_FG,
    C_TEXT,
    FONT_MAIN,
    FONT_MONO_M,
)
from .widgets import make_secondary_button
from .window_utils import center_window


class EditorDialog:
    """Modal text editor window for trap endings / exceptions files."""

    def __init__(
        self,
        controller,
        *,
        title: str,
        file_path: str,
        reload_callback,
        status_var: tk.StringVar,
        default_content: str,
    ) -> None:
        self._controller = controller
        self._file_path = file_path
        self._reload_callback = reload_callback
        self._status_var = status_var
        self._default_content = default_content
        self._build(title)

    def _build(self, title: str) -> None:
        win = tk.Toplevel(self._controller.root)
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
            with open(self._file_path, "r", encoding="utf-8") as f_in:
                content = f_in.read()
        except FileNotFoundError:
            content = self._default_content
        text_widget.insert("1.0", content)
        text_widget.tag_configure("search", background=C_SEARCH_BG, foreground=C_SEARCH_FG)

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
            search_frame, text="\u25c0", command=_go_prev,
            font=FONT_MAIN, relief="flat", bd=0, padx=4, pady=1, cursor="hand2",
            bg=C_BG, fg=C_TEXT, activebackground=C_ENTRY_BG, state=tk.DISABLED,
        )
        prev_btn.pack(side="left", padx=(2, 0))

        next_btn = tk.Button(
            search_frame, text="\u25b6", command=_go_next,
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
            self._save(text_widget, win)

        def cancel(event=None):
            win.destroy()

        text_widget.bind("<Control-s>", save_and_close)
        text_widget.bind("<Control-S>", save_and_close)
        text_widget.bind("<Escape>", cancel)

        btn_frame = tk.Frame(frame, bg=C_BG)
        btn_frame.pack(fill="x")
        make_secondary_button(btn_frame, "Cancel", cancel).pack(
            side="right", padx=(4, 0)
        )

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

        center_window(win, self._controller.root)
        text_widget.focus_set()

    def _save(self, text_widget: ScrolledText, win: tk.Toplevel) -> None:
        content = text_widget.get("1.0", tk.END).strip()
        try:
            fp = Path(self._file_path)
            if fp.exists():
                shutil.copy2(fp, fp.with_suffix(".bak"))
            with open(fp, "w", encoding="utf-8") as f_out:
                f_out.write(content)
                if content and not content.endswith("\n"):
                    f_out.write("\n")
            self._reload_callback()
            basename = fp.name.lower()
            if basename == "trap_endings.txt":
                count = len(self._controller.session.engine.trap_endings)
            elif basename == "exceptions.txt":
                count = len(self._controller.session.engine.word_exceptions)
            else:
                count = 0
            self._status_var.set(f"{count} loaded")
            win.destroy()
        except Exception as e:
            self._controller.view.show_feedback(
                "error", f"Could not save file: {e}", duration_ms=8000
            )
