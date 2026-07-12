"""Modal text editors for trap endings and exceptions files.

Also exports InlineFileEditor for embedding in the lookup tool.
"""

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
    FONT_BTN,
    FONT_MAIN,
    FONT_MONO_M,
    FONT_TITLE,
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
            try:
                if basename == "trap_endings.txt":
                    count = len(self._controller.session.engine.trap_endings)
                elif basename == "exceptions.txt":
                    count = len(self._controller.session.engine.word_exceptions)
                else:
                    count = 0
            except AttributeError:
                count = 0
            self._status_var.set(f"{count} loaded")
            win.destroy()
        except Exception as e:
            self._controller.view.show_feedback(
                "error", f"Could not save file: {e}", duration_ms=8000
            )


class InlineFileEditor(tk.Frame):
    """Inline text editor with search/highlight, embedded in a parent frame.

    Replacement for EditorDialog when popup windows are undesirable.
    Builds inside a given parent frame; call ``open()`` to load content.
    """

    def __init__(self, parent, on_close):
        super().__init__(parent, bg=C_BG)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._file_path = None
        self._reload_callback = None
        self._on_close = on_close

        # Row 0: title
        self._title_label = tk.Label(
            self, font=FONT_TITLE, bg=C_BG, fg=C_TEXT, anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        # Row 1: search bar
        search_frame = tk.Frame(self, bg=C_BG)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        tk.Label(search_frame, text="Find:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
            side="left", padx=(0, 4),
        )
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame, textvariable=self._search_var, font=FONT_MAIN, width=25,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        search_entry.pack(side="left", padx=(0, 6))

        self._match_label = tk.Label(
            search_frame, text="", font=FONT_MAIN, bg=C_BG, fg=C_MUTED,
        )
        self._match_label.pack(side="left")

        self._search_matches = []
        self._search_index = 0

        self._prev_btn = tk.Button(
            search_frame, text="\u25c0", command=self._go_prev,
            font=FONT_MAIN, relief="flat", bd=0, padx=4, pady=1, cursor="hand2",
            bg=C_BG, fg=C_TEXT, activebackground=C_ENTRY_BG, state=tk.DISABLED,
        )
        self._prev_btn.pack(side="left", padx=(2, 0))

        self._next_btn = tk.Button(
            search_frame, text="\u25b6", command=self._go_next,
            font=FONT_MAIN, relief="flat", bd=0, padx=4, pady=1, cursor="hand2",
            bg=C_BG, fg=C_TEXT, activebackground=C_ENTRY_BG, state=tk.DISABLED,
        )
        self._next_btn.pack(side="left")

        self._search_var.trace_add("write", self._on_search)

        # Row 2: text widget
        self._text = ScrolledText(
            self,
            font=FONT_MONO_M,
            width=60, height=20,
            bg=C_ENTRY_BG, fg=C_TEXT,
            insertbackground=C_TEXT,
            undo=True, maxundo=-1,
        )
        self._text.grid(row=2, column=0, sticky="nsew")
        self._text.tag_configure("search", background=C_SEARCH_BG, foreground=C_SEARCH_FG)
        self._text.bind("<Control-s>", lambda e: self._save())
        self._text.bind("<Control-S>", lambda e: self._save())
        self._text.bind("<Escape>", lambda e: self._cancel())

        # Row 3: buttons
        btn_frame = tk.Frame(self, bg=C_BG)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        tk.Button(
            btn_frame, text="Save",
            command=self._save,
            font=FONT_BTN,
            bg=C_PLAY_BG, fg=C_PLAY_FG,
            activebackground=C_PLAY_ACT, activeforeground=C_PLAY_FG,
            relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
        ).pack(side="right")

        make_secondary_button(btn_frame, "Cancel", command=self._cancel).pack(
            side="right", padx=(4, 0),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self, title, file_path, reload_callback, default_content):
        """Load a file into the editor."""
        self._file_path = file_path
        self._reload_callback = reload_callback
        self._title_label.config(text=title)
        self._text.delete("1.0", tk.END)
        try:
            content = Path(file_path).read_text("utf-8")
        except FileNotFoundError:
            content = default_content
        self._text.insert("1.0", content)
        self._text.edit_reset()
        self._search_var.set("")
        self._match_label.config(text="")
        self._text.focus_set()

    def close(self):
        """Dismiss the editor (user-facing Cancel)."""
        self._on_close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self):
        content = self._text.get("1.0", tk.END).strip()
        try:
            fp = Path(self._file_path)
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
                if content and not content.endswith("\n"):
                    f.write("\n")
            self._reload_callback()
        except Exception as e:
            self._match_label.config(text=f"Save error: {e}")
            return
        self._on_close()

    def _cancel(self):
        self._on_close()

    def _on_search(self, *args):
        self._text.tag_remove("search", "1.0", tk.END)
        query = self._search_var.get()
        if not query:
            self._match_label.config(text="")
            self._prev_btn.config(state=tk.DISABLED)
            self._next_btn.config(state=tk.DISABLED)
            self._search_matches = []
            return

        self._search_matches = []
        pos = "1.0"
        query_lower = query.lower()
        while True:
            pos = self._text.search(query_lower, pos, tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self._text.tag_add("search", pos, end)
            self._search_matches.append(pos)
            pos = end

        if self._search_matches:
            self._search_index = 0
            self._text.see(self._search_matches[0])
            self._match_label.config(
                text=f"1/{len(self._search_matches)}",
            )
            self._prev_btn.config(state=tk.NORMAL)
            self._next_btn.config(state=tk.NORMAL)
        else:
            self._match_label.config(text="0 matches")
            self._prev_btn.config(state=tk.DISABLED)
            self._next_btn.config(state=tk.DISABLED)

    def _go_prev(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._text.see(self._search_matches[self._search_index])
        self._match_label.config(
            text=f"{self._search_index + 1}/{len(self._search_matches)}",
        )

    def _go_next(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._text.see(self._search_matches[self._search_index])
        self._match_label.config(
            text=f"{self._search_index + 1}/{len(self._search_matches)}",
        )
