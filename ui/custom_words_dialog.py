"""Custom Words dialog — view, filter, remove, and add custom words."""

import logging
import tkinter as tk
from tkinter import ttk

from core.dictionary import save_custom_words
from ui.theme import (
    C_BG,
    C_ENTRY_BG,
    C_MUTED,
    C_PLAY_BG,
    C_PLAY_FG,
    C_TEXT,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_MONO,
    FONT_SMALL,
)
from ui.widgets import make_primary_button, make_secondary_button

logger = logging.getLogger(__name__)


class CustomWordsDialog:
    """Unified dialog to view, filter, remove, and add custom words."""

    FILTER_DEBOUNCE_MS = 200

    def __init__(self, parent, controller):
        self._controller = controller
        self._new_words = []
        self._filter_after_id = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Custom Words")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(480, 580)

        self._build_ui()
        self._refresh_custom_words_list()
        self._input_text.focus_set()

    def _build_ui(self):
        main = tk.Frame(self.dialog, bg=C_BG, padx=14, pady=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(8, weight=1)

        # Header
        header_frame = tk.Frame(main, bg=C_BG)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(header_frame, text="Custom Words", font=FONT_MAIN_BOLD,
                 bg=C_BG, fg=C_TEXT).pack(side="left")
        self._count_var = tk.StringVar(value="(0)")
        tk.Label(header_frame, textvariable=self._count_var,
                 font=FONT_MAIN, bg=C_BG, fg=C_MUTED
                 ).pack(side="left", padx=(4, 0))

        # Filter
        self._filter_var = tk.StringVar()
        filter_entry = tk.Entry(
            main, textvariable=self._filter_var, font=FONT_SMALL,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        filter_entry.grid(row=1, column=0, sticky="ew", pady=(0, 4), ipady=1)
        filter_entry.bind("<KeyRelease>", self._on_filter_change)

        # Custom words listbox
        list_frame = tk.Frame(main, bg=C_BG)
        list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_frame, font=FONT_MONO, activestyle="none",
            exportselection=False, selectmode=tk.EXTENDED,
            bg=C_ENTRY_BG, fg=C_TEXT, selectbackground=C_PLAY_BG,
            selectforeground=C_PLAY_FG, borderwidth=0,
            highlightthickness=0, relief="flat",
        )
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._listbox.bind("<<ListboxSelect>>", self._on_selection_changed)
        self._listbox.bind("<Delete>", self._on_delete)

        scroll = ttk.Scrollbar(list_frame, orient="vertical",
                                command=self._listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=scroll.set)

        # Remove button
        self._remove_btn = make_secondary_button(
            main, text="Remove Selected",
            command=self._on_remove,
            row=3, column=0, sticky="w", pady=(0, 8),
        )
        self._remove_btn.config(state="disabled")

        # Separator
        ttk.Separator(main, orient="horizontal").grid(
            row=4, column=0, sticky="ew", pady=(0, 8))

        # Input area
        tk.Label(main, text="Add words (one per line):", font=FONT_MAIN,
                 bg=C_BG, fg=C_TEXT, anchor="w"
                 ).grid(row=5, column=0, sticky="ew", pady=(0, 2))

        in_frame = tk.Frame(main, bg=C_BG)
        in_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 8))
        in_frame.columnconfigure(0, weight=1)
        in_frame.rowconfigure(0, weight=1)

        self._input_text = tk.Text(
            in_frame, font=FONT_MONO, height=6,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1, padx=4, pady=4, wrap="none",
        )
        self._input_text.grid(row=0, column=0, sticky="nsew")
        in_scroll = ttk.Scrollbar(in_frame, orient="vertical",
                                   command=self._input_text.yview)
        in_scroll.grid(row=0, column=1, sticky="ns")
        self._input_text.configure(yscrollcommand=in_scroll.set)
        self._input_text.bind("<KeyRelease>", self._on_input_changed)
        self._input_text.bind("<Control-Return>", lambda e: self._on_add())

        # Preview
        preview_header = tk.Frame(main, bg=C_BG)
        preview_header.grid(row=7, column=0, sticky="ew", pady=(0, 2))
        tk.Label(preview_header, text="Preview:",
                 font=FONT_MAIN_BOLD, bg=C_BG, fg=C_TEXT
                 ).pack(side="left")
        self._status_var = tk.StringVar()
        tk.Label(preview_header, textvariable=self._status_var,
                 font=FONT_SMALL, bg=C_BG, fg=C_MUTED
                 ).pack(side="left", padx=(8, 0))

        prev_frame = tk.Frame(main, bg=C_BG)
        prev_frame.grid(row=8, column=0, sticky="nsew", pady=(0, 10))
        prev_frame.columnconfigure(0, weight=1)
        prev_frame.rowconfigure(0, weight=1)

        self._preview_text = tk.Text(
            prev_frame, font=FONT_MONO, height=5,
            bg="#f0f0f0", fg=C_TEXT, relief="solid", bd=1,
            padx=4, pady=4, wrap="none", state=tk.DISABLED,
        )
        self._preview_text.grid(row=0, column=0, sticky="nsew")
        prev_scroll = ttk.Scrollbar(prev_frame, orient="vertical",
                                     command=self._preview_text.yview)
        prev_scroll.grid(row=0, column=1, sticky="ns")
        self._preview_text.configure(yscrollcommand=prev_scroll.set)

        # Bottom buttons
        btn_frame = tk.Frame(main, bg=C_BG)
        btn_frame.grid(row=9, column=0, sticky="ew")

        self._add_btn = make_primary_button(
            btn_frame, text="Add",
            command=self._on_add,
        )
        self._add_btn.config(state=tk.DISABLED)
        self._add_btn.pack(side="right", padx=(6, 0))

        close_btn = make_secondary_button(
            btn_frame, text="Close",
            command=self.dialog.destroy,
        )
        close_btn.pack(side="right")

    def _on_filter_change(self, event=None):
        if self._filter_after_id:
            self.dialog.after_cancel(self._filter_after_id)
        self._filter_after_id = self.dialog.after(
            self.FILTER_DEBOUNCE_MS, self._refresh_custom_words_list)

    def _refresh_custom_words_list(self):
        self._listbox.delete(0, tk.END)
        custom = sorted(self._controller.custom_words)
        filter_text = self._filter_var.get().strip().lower()
        if filter_text:
            custom = [w for w in custom if filter_text in w]
        for word in custom:
            self._listbox.insert(tk.END, word)
        self._count_var.set(f"({len(self._controller.custom_words)})")
        if not custom:
            self._listbox.insert(tk.END, "(no custom words)")

    def _on_selection_changed(self, event=None):
        sel = self._listbox.curselection()
        self._remove_btn.config(state="normal" if sel else "disabled")

    def _on_delete(self, event=None):
        self._on_remove()

    def _on_remove(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        words = [self._listbox.get(i) for i in sel]
        words = [w for w in words if w != "(no custom words)"]
        if not words:
            return
        self._controller.on_remove_custom_words(words)
        self._refresh_custom_words_list()
        self._remove_btn.config(state="disabled")

    def _on_input_changed(self, event=None):
        self._update_preview()

    def _update_preview(self):
        raw = self._input_text.get("1.0", tk.END)
        seen = set()
        all_words = []
        for line in raw.splitlines():
            w = line.strip().lower()
            if not w or not w.isalpha():
                continue
            if w not in seen:
                seen.add(w)
                all_words.append(w)

        all_words.sort()

        if not all_words:
            self._set_preview("(enter words above)", muted=True)
            self._status_var.set("")
            self._add_btn.config(state=tk.DISABLED, text="Add")
            return

        lookup = self._controller.lookup
        new_words = [w for w in all_words if not lookup.contains(w)]
        existing = len(all_words) - len(new_words)
        self._new_words = new_words

        if new_words:
            self._set_preview("\n".join(new_words), muted=False)
        else:
            self._set_preview("(all words already in dictionary)", muted=True)

        parts = []
        if new_words:
            parts.append(f"{len(new_words)} new")
        if existing:
            parts.append(f"{existing} already in dict")
        self._status_var.set(" \u00b7 ".join(parts))

        if new_words:
            n = len(new_words)
            self._add_btn.config(state=tk.NORMAL,
                                  text=f"Add {n} Word{'s' if n != 1 else ''}")
        else:
            self._add_btn.config(state=tk.DISABLED, text="Add")

    def _set_preview(self, text, muted=False):
        self._preview_text.config(state=tk.NORMAL)
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", text)
        self._preview_text.config(state=tk.DISABLED,
                                  fg=C_MUTED if muted else C_TEXT)

    def _on_add(self):
        if not self._new_words:
            return
        ctrl = self._controller
        try:
            ctrl.custom_words.update(self._new_words)
            save_custom_words(ctrl.custom_words)
            ctrl.lookup.add_words(self._new_words)
            ctrl._run_search()
            n = len(self._new_words)
            ctrl.view.set_status(
                f"Added {n} word{'s' if n != 1 else ''} to dictionary"
            )
            self._new_words = []
            self._input_text.delete("1.0", tk.END)
            self._update_preview()
            self._refresh_custom_words_list()
        except Exception as e:
            logger.exception("Failed to add words")
            self._status_var.set(f"Error: {e}")
