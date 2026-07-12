"""Dictionary Lookup — standalone tkinter app for word list exploration.

Uses binary search (bisect) for O(log n) prefix/suffix lookup on
a sorted word list. Runs independently of the main Letter Demon app.
"""

import json
import logging
import queue
import sys
import threading
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

log_dir = Path(_PROJECT_ROOT) / "data" / "runtime" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(log_dir / "lookup.log"), mode="a", encoding="utf-8"),
    ],
)

import tkinter as tk
from tkinter import filedialog, ttk

from core import __version__
from core.dict_lookup import DictLookup
from core.dictionary import load_custom_words, load_wordlist_from_dict, save_custom_words
from config.exceptions import EXCEPTIONS_FILE, load_exceptions as _load_exc, save_exceptions as _save_exc
from config.trap_endings import TRAP_ENDINGS_FILE
from config.spam_suffixes import SPAM_SUFFIXES_FILE, load_spam_suffixes
from ui.custom_words_dialog import CustomWordsDialog
from ui.file_editors import EditorDialog
from ui.theme import (
    C_BG,
    C_BG_PANEL,
    C_BTN_BG,
    C_DOT_GREEN,
    C_ENTRY_BD,
    C_ENTRY_BG,
    C_ENTRY_FOCUS,
    C_FEEDBACK_ERR_BG,
    C_FEEDBACK_ERR_FG,
    C_FEEDBACK_WARN_BG,
    C_FEEDBACK_WARN_FG,
    C_MUTED,
    C_PLAY_BG,
    C_PLAY_FG,
    C_SEP,
    C_TEXT,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_MONO,
    FONT_MONO_M,
    FONT_SMALL,
)
from ui.widgets import make_secondary_button, setup_ttk_styles

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(_PROJECT_ROOT) / "data" / "runtime" / "lookup_settings.json"

DEBOUNCE_MS = 300
FEEDBACK_MS_DEFAULT = 5000
FEEDBACK_MS_ERROR = 6000
FEEDBACK_MS_DICT_ERROR = 8000


class LookupView:
    """Owns all widgets, tkinter vars, and layout. Delegates actions to controller."""

    def __init__(self, root: tk.Tk, controller):
        self.root = root
        self._controller = controller
        self._feedback_after_id = None
        self._prev_results_tuple = None
        self._prev_exceptions = None

        setup_ttk_styles()
        self._build_ui()
        self._wire_keyboard_shortcuts()

    # ------------------------------------------------------------------
    # Build layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.root.configure(bg=C_BG)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = tk.Frame(self.root, bg=C_BG, padx=15, pady=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        self._build_dict_bar(main, 0)
        self._build_filter_row1(main, 1)
        self._build_filter_row2(main, 2)
        self._build_paned_results(main, 3)
        self._build_bottom_bar(main, 4)

    def _build_dict_bar(self, parent, row):
        frame = tk.Frame(parent, bg=C_BG)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(3, weight=1)

        self.dict_button = make_secondary_button(
            frame, text="\U0001f4c2 Load Dictionary...",
            command=self._controller.on_load_dict,
            row=0, column=0, padx=(0, 6),
        )

        self.add_words_btn = make_secondary_button(
            frame, text="\u270e Add Words...",
            command=self._controller.on_add_words,
            row=0, column=1, padx=(0, 6),
        )
        self.add_words_btn.config(state="disabled")

        self._dict_dot = tk.Label(frame, text="\u25cf", fg=C_MUTED, font=FONT_MAIN, bg=C_BG)
        self._dict_dot.grid(row=0, column=2, padx=(0, 4))

        self._dict_label_var = tk.StringVar(value="No dictionary loaded")
        self.dict_label = tk.Label(
            frame, textvariable=self._dict_label_var,
            font=FONT_MAIN, bg=C_BG, fg=C_MUTED,
        )
        self.dict_label.grid(row=0, column=3, sticky="w")

    def _build_filter_row1(self, parent, row):
        frame = tk.Frame(parent, bg=C_BG)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        frame.columnconfigure((1, 3), weight=1)

        tk.Label(frame, text="Starts With:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).grid(row=0, column=0, padx=(0, 4))
        self._start_var = tk.StringVar()
        self.start_entry = tk.Entry(
            frame, textvariable=self._start_var, font=FONT_MAIN,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1, highlightthickness=1,
            highlightbackground=C_ENTRY_BD, highlightcolor=C_ENTRY_FOCUS,
        )
        self.start_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16), ipady=2)
        self.start_entry.bind("<KeyRelease>", self._controller.on_search_debounced)
        self.start_entry.bind("<FocusIn>", lambda e: self.start_entry.config(highlightbackground=C_ENTRY_FOCUS, highlightthickness=2))
        self.start_entry.bind("<FocusOut>", lambda e: self.start_entry.config(highlightbackground=C_ENTRY_BD, highlightthickness=1))

        tk.Label(frame, text="Ends With:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).grid(row=0, column=2, padx=(0, 4))
        self._end_var = tk.StringVar()
        self.end_entry = tk.Entry(
            frame, textvariable=self._end_var, font=FONT_MAIN,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1, highlightthickness=1,
            highlightbackground=C_ENTRY_BD, highlightcolor=C_ENTRY_FOCUS,
        )
        self.end_entry.grid(row=0, column=3, sticky="ew", ipady=2)
        self.end_entry.bind("<KeyRelease>", self._controller.on_search_debounced)
        self.end_entry.bind("<FocusIn>", lambda e: self.end_entry.config(highlightbackground=C_ENTRY_FOCUS, highlightthickness=2))
        self.end_entry.bind("<FocusOut>", lambda e: self.end_entry.config(highlightbackground=C_ENTRY_BD, highlightthickness=1))

    def _build_filter_row2(self, parent, row):
        frame = tk.Frame(parent, bg=C_BG)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))

        tk.Label(frame, text="Contains:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).pack(side="left", padx=(0, 4))
        self._contains_var = tk.StringVar()
        self.contains_entry = tk.Entry(
            frame, textvariable=self._contains_var, font=FONT_MAIN,
            width=16, bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        self.contains_entry.pack(side="left", padx=(0, 14), ipady=2)
        self.contains_entry.bind("<KeyRelease>", self._controller.on_search_debounced)

        tk.Label(frame, text="Min:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).pack(side="left", padx=(0, 2))
        self._min_len_var = tk.IntVar(value=0)
        self.min_spin = tk.Spinbox(
            frame, from_=0, to=30, textvariable=self._min_len_var,
            width=3, font=FONT_MAIN, bg=C_ENTRY_BG, fg=C_TEXT,
            buttonbackground=C_BTN_BG, relief="solid", bd=1,
        )
        self.min_spin.pack(side="left", padx=(0, 14), ipady=1)
        self.min_spin.bind("<KeyRelease>", self._controller.on_search_debounced)
        self._min_len_var.trace_add("write", lambda *_: self._controller.on_search_immediate())

        tk.Label(frame, text="Max:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).pack(side="left", padx=(0, 2))
        self._max_len_var = tk.IntVar(value=0)
        self.max_spin = tk.Spinbox(
            frame, from_=0, to=30, textvariable=self._max_len_var,
            width=3, font=FONT_MAIN, bg=C_ENTRY_BG, fg=C_TEXT,
            buttonbackground=C_BTN_BG, relief="solid", bd=1,
        )
        self.max_spin.pack(side="left", padx=(0, 14), ipady=1)
        self.max_spin.bind("<KeyRelease>", self._controller.on_search_debounced)
        self._max_len_var.trace_add("write", lambda *_: self._controller.on_search_immediate())

        self._match_case_var = tk.BooleanVar(value=False)
        self.match_case_cb = tk.Checkbutton(
            frame, text="Match Case", variable=self._match_case_var,
            font=FONT_MAIN, bg=C_BG, fg=C_TEXT, selectcolor=C_BG,
            activebackground=C_BG, activeforeground=C_TEXT,
            command=self._controller.on_search_immediate,
        )
        self.match_case_cb.pack(side="left")

    def _build_paned_results(self, parent, row):
        main = tk.Frame(parent, bg=C_BG)
        main.grid(row=row, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        results_frame = tk.Frame(main, bg=C_BG)
        results_frame.grid(row=0, column=0, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        self._build_result_count_bar(results_frame, 0)
        self._build_result_tree(results_frame, 1)

    def _build_result_tree(self, parent, row):
        tree_frame = tk.Frame(parent, bg=C_BG)
        tree_frame.grid(row=row, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("#", "Word", "Len", "Exc", "Spm")
        self._result_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
        )
        for col in columns:
            self._result_tree.heading(
                col, text=col,
                command=lambda c=col: self._sort_tree(c, False),
            )
        self._result_tree.column("#", width=50, minwidth=30, anchor="e", stretch=False)
        self._result_tree.column("Word", width=300, minwidth=100, anchor="w", stretch=True)
        self._result_tree.column("Len", width=55, minwidth=40, anchor="e", stretch=False)
        self._result_tree.column("Exc", width=40, minwidth=30, anchor="center", stretch=False)
        self._result_tree.column("Spm", width=40, minwidth=30, anchor="center", stretch=False)

        self._result_tree.grid(row=0, column=0, sticky="nsew")
        self._result_tree.bind("<Double-Button-1>", self._on_tree_doubleclick)
        self._result_tree.bind("<Button-3>", self._show_tree_context_menu)
        self._result_tree.bind("<<TreeviewSelect>>", self._on_tree_selection_changed)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._result_tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._result_tree.configure(yscrollcommand=scrollbar.set)

    def _sort_tree(self, col, reverse):
        tree = self._result_tree
        items = [(tree.set(item, col), item) for item in tree.get_children('')]
        if col in ("#", "Len"):
            items.sort(key=lambda x: int(x[0]) if x[0] else 0, reverse=reverse)
        else:
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for index, (_, item) in enumerate(items):
            tree.move(item, '', index)
        tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    def _build_result_count_bar(self, parent, row):
        self._count_var = tk.StringVar(value="")
        self.count_label = tk.Label(
            parent, textvariable=self._count_var,
            font=FONT_SMALL, bg=C_BG_PANEL, fg=C_MUTED, anchor="e",
        )
        self.count_label.grid(row=row, column=0, sticky="ew", pady=(1, 0), ipady=1)




    def _build_bottom_bar(self, parent, row):
        frame = tk.Frame(parent, bg=C_BG)
        frame.grid(row=row, column=0, sticky="ew", pady=(10, 0))
        frame.columnconfigure(0, weight=1)

        self._feedback_var = tk.StringVar(value="Load a dictionary to begin")
        self.feedback_label = tk.Label(
            frame, textvariable=self._feedback_var,
            font=FONT_MAIN, bg=C_BG, fg=C_TEXT, anchor="w",
        )
        self.feedback_label.grid(row=0, column=0, sticky="w")

        self.add_exc_btn = make_secondary_button(
            frame, text="+ Add to Exceptions",
            command=self._controller.on_add_selected,
            row=0, column=2, padx=(0, 4),
        )
        self.add_exc_btn.config(state="disabled")

        make_secondary_button(
            frame, text="\u270e Exceptions...",
            command=self._controller.edit_exceptions_file,
            row=0, column=3, padx=(0, 4),
        )

        make_secondary_button(
            frame, text="\u270e Trap Endings...",
            command=self._controller.edit_trap_endings_file,
            row=0, column=4, padx=(0, 4),
        )

        make_secondary_button(
            frame, text="\u270e Spam Suffixes...",
            command=self._controller.edit_spam_suffixes_file,
            row=0, column=5, padx=(0, 4),
        )

        make_secondary_button(
            frame, text="\u2302 Clear",
            command=self._controller.on_clear,
            row=0, column=6,
        )

        self._help_btn = make_secondary_button(
            frame, text="\u24d8",
            command=self._show_shortcuts_help,
            row=0, column=7, padx=(12, 0),
        )

    def _show_shortcuts_help(self):
        msg = (
            "Keyboard Shortcuts\n\n"
            "Ctrl+O    Load dictionary\n"
            "Ctrl+F    Focus filter\n"
            "Ctrl+L    Clear filters\n"
            "Escape    Cycle focus\n"
            "Delete    Remove selected from Exceptions\n"
            "Space     Toggle exception on selected\n\n"
            "Results\n"
            "Double-click  Toggle exception\n"
            "Right-click   Context menu (Copy, Exception)\n"
            "Column header Sort by column"
        )
        tk.messagebox.showinfo("Help", msg, parent=self.root)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _wire_keyboard_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self._controller.on_load_dict())
        self.root.bind("<Control-O>", lambda e: self._controller.on_load_dict())
        self.root.bind("<Control-l>", lambda e: self._controller.on_clear())
        self.root.bind("<Control-L>", lambda e: self._controller.on_clear())
        self.root.bind("<Control-f>", lambda e: self.start_entry.focus_set())
        self.root.bind("<Control-F>", lambda e: self.start_entry.focus_set())
        self.root.bind("<Escape>", self._on_escape)
        self._result_tree.bind("<Delete>", self._on_delete_results_selection)
        self._result_tree.bind("<space>", self._on_space_toggle_exception)
        self.root.bind("<Control-c>", self._on_copy_selected)
        self.root.bind("<Control-C>", self._on_copy_selected)

    def _on_escape(self, event=None):
        focused = self.root.focus_get()
        if focused in (self.start_entry, self.end_entry):
            self._result_tree.focus_set()
        else:
            self.start_entry.focus_set()

    def _on_delete_results_selection(self, event=None):
        sel = self._result_tree.selection()
        if sel:
            words = [self._result_tree.item(item, "values")[1] for item in sel]
            self._controller.on_remove_from_exceptions(words)

    def _on_space_toggle_exception(self, event=None):
        sel = self._result_tree.selection()
        if sel:
            for item in sel:
                word = self._result_tree.item(item, "values")[1]
                if self._controller.is_exception(word):
                    self._controller.on_remove_from_exceptions([word])
                else:
                    self._controller.on_add_to_exceptions([word])
        return "break"

    def _on_copy_selected(self, event=None):
        sel = self._result_tree.selection()
        if not sel:
            return
        words = [self._result_tree.item(item, "values")[1] for item in sel]
        text = "\n".join(words)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _on_tree_doubleclick(self, event):
        tree = self._result_tree
        item = tree.identify_row(event.y)
        if not item:
            return
        word = tree.item(item, "values")[1]
        if self._controller.is_exception(word):
            self._controller.on_remove_from_exceptions([word])
        else:
            self._controller.on_add_to_exceptions([word])

    def _show_tree_context_menu(self, event):
        tree = self._result_tree
        item = tree.identify_row(event.y)
        if not item:
            return
        word = tree.item(item, "values")[1]
        sel = tree.selection()
        if item in sel and len(sel) > 1:
            words = [tree.item(i, "values")[1] for i in sel]
            label = f"Copy {len(words)} Words"
        else:
            words = [word]
            label = "Copy Word"
        menu = tk.Menu(self.root, tearoff=0)
        if self._controller.is_exception(word):
            menu.add_command(
                label="Remove from Exceptions",
                command=lambda w=word: self._controller.on_remove_from_exceptions([w])
            )
        else:
            menu.add_command(
                label="Add to Exceptions",
                command=lambda w=word: self._controller.on_add_to_exceptions([w])
            )
        menu.add_command(
            label=label,
            command=lambda ws=words: (self.root.clipboard_clear(), self.root.clipboard_append("\n".join(ws)))
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_tree_selection_changed(self, event=None):
        sel = self._result_tree.selection()
        self.add_exc_btn.config(state="normal" if sel else "disabled")

    # ------------------------------------------------------------------
    # Properties (read by controller)
    # ------------------------------------------------------------------

    @property
    def prefix(self):
        return self._start_var.get().strip()

    @property
    def suffix(self):
        return self._end_var.get().strip()

    @property
    def contains(self):
        return self._contains_var.get().strip()

    @property
    def min_len(self):
        return self._min_len_var.get()

    @property
    def max_len(self):
        return self._max_len_var.get()

    @property
    def match_case(self):
        return self._match_case_var.get()

    # ------------------------------------------------------------------
    # Update methods (called by controller from main thread)
    # ------------------------------------------------------------------

    def set_status(self, text, level=None):
        if level == "error":
            self.feedback_label.config(text=text, bg=C_FEEDBACK_ERR_BG, fg=C_FEEDBACK_ERR_FG)
        elif level == "warn":
            self.feedback_label.config(text=text, bg=C_FEEDBACK_WARN_BG, fg=C_FEEDBACK_WARN_FG)
        else:
            self.feedback_label.config(text=text, bg=C_BG, fg=C_TEXT)
        self._feedback_var.set(text)

    def show_feedback(self, level, message, duration_ms=FEEDBACK_MS_DEFAULT):
        if self._feedback_after_id:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None
        bg = C_FEEDBACK_ERR_BG if level == "error" else C_FEEDBACK_WARN_BG
        fg = C_FEEDBACK_ERR_FG if level == "error" else C_FEEDBACK_WARN_FG
        self.feedback_label.config(text=message, bg=bg, fg=fg)
        self._feedback_after_id = self.root.after(duration_ms, self._clear_feedback)

    def _clear_feedback(self):
        self._feedback_after_id = None
        try:
            self.feedback_label.config(text="", bg=C_BG, fg=C_TEXT)
        except tk.TclError:
            pass

    def set_dict_loaded(self, filename, word_count):
        self._dict_label_var.set(f"Dict: {filename}  ({word_count:,} words)")
        self._dict_dot.config(fg=C_DOT_GREEN)
        self.dict_label.config(fg=C_TEXT)

    def set_dict_empty(self):
        self._dict_label_var.set("No dictionary loaded")
        self._dict_dot.config(fg=C_MUTED)
        self.dict_label.config(fg=C_MUTED)

    def update_results(self, results, total, exceptions, spam_suffixes=None):
        results_tuple = tuple(results)
        if results_tuple == self._prev_results_tuple and exceptions == self._prev_exceptions:
            return
        self._prev_results_tuple = results_tuple
        self._prev_exceptions = frozenset(exceptions)

        tree = self._result_tree
        tree.delete(*tree.get_children())

        tag_configs = {
            "r0": {"background": "#ffffff"},
            "r1": {"background": "#f4f4f5"},
            "rx0": {"background": "#ffffff", "foreground": C_MUTED},
            "rx1": {"background": "#f4f4f5", "foreground": C_MUTED},
        }
        for tag, cfg in tag_configs.items():
            tree.tag_configure(tag, **cfg)

        for i, word in enumerate(results):
            parity = i % 2
            in_exc = word in exceptions
            is_spam = spam_suffixes and any(word.endswith(s) for s in spam_suffixes)
            tag = f"rx{parity}" if in_exc else f"r{parity}"
            tree.insert(
                "", tk.END,
                values=(i + 1, word, len(word), "\u2713" if in_exc else "", "\u2713" if is_spam else ""),
                tags=(tag,),
            )

        n = len(results)
        if n == 0:
            self._count_var.set("")
        elif n < total:
            self._count_var.set(f"Showing {n:,} of {total:,} words")
        elif n == 1:
            self._count_var.set("1 word found")
        else:
            self._count_var.set(f"{n:,} words found")

    def scroll_to_word(self, word):
        tree = self._result_tree
        for item in tree.get_children(''):
            if tree.item(item, "values")[1] == word:
                tree.selection_set(item)
                tree.see(item)
                tree.focus(item)
                return True
        return False

    def reset_filters(self):
        self._start_var.set("")
        self._end_var.set("")
        self._contains_var.set("")
        self._min_len_var.set(0)
        self._max_len_var.set(0)

    def enable_dict_button(self, enabled):
        self.dict_button.config(state="normal" if enabled else "disabled")

    def enable_add_words_btn(self, enabled):
        self.add_words_btn.config(state="normal" if enabled else "disabled")

    def focus_start_entry(self):
        self.start_entry.focus_set()




class SearchWorker:
    """Background worker — one thread, queue-based, discards stale searches."""

    RESULT_LIMIT = 1000

    def __init__(self, lookup):
        self._lookup = lookup
        self._queue = queue.Queue()
        self._generation = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, prefix, suffix, contains, min_len, max_len,
               match_case, on_result, on_error):
        self._generation += 1
        gen = self._generation
        self._queue.put((gen, prefix, suffix, contains, min_len,
                         max_len, match_case, on_result, on_error))

    def _run(self):
        while True:
            item = self._queue.get()
            gen, prefix, suffix, contains, min_len, max_len, \
                match_case, on_result, on_error = item
            if gen != self._generation:
                continue
            try:
                has_secondary = bool(contains) or bool(min_len) or bool(max_len)
                if not prefix and not suffix and not has_secondary:
                    on_result([], 0)
                    continue
                if not prefix and not suffix and has_secondary:
                    all_words = self._lookup.get_all_words()
                    filtered = self._apply_filters(
                        all_words, contains, min_len, max_len, match_case,
                    )
                    on_result(filtered[:self.RESULT_LIMIT], len(all_words))
                    continue
                limit = sys.maxsize if has_secondary else self.RESULT_LIMIT
                results, total = self._lookup.find_starting_and_ending_with(
                    prefix, suffix, limit=limit,
                )
                filtered = self._apply_filters(
                    results, contains, min_len, max_len, match_case,
                )
                if has_secondary and len(filtered) > self.RESULT_LIMIT:
                    filtered = filtered[:self.RESULT_LIMIT]
                on_result(filtered, total)
            except Exception as e:
                on_error(str(e))

    @staticmethod
    def _apply_filters(results, contains, min_len, max_len, match_case):
        if not contains and not min_len and not max_len:
            return results
        filtered = []
        for word in results:
            w = word if match_case else word.lower()
            if contains:
                needle = contains if match_case else contains.lower()
                if needle not in w:
                    continue
            if min_len and len(word) < min_len:
                continue
            if max_len and len(word) > max_len:
                continue
            filtered.append(word)
        return filtered


class LookupApp:
    """Controller — owns DictLookup, exceptions, settings, threading."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"Dictionary Lookup v{__version__}")
        self.root.minsize(1100, 650)

        self.dict_path = None
        self.lookup = DictLookup()
        self.exceptions = set()
        self._search_after_id = None
        self._result_word_list = []
        self._settings = {}
        self.custom_words = load_custom_words()
        self._base_wordlist = None

        self._worker = SearchWorker(self.lookup)

        self.view = LookupView(root, self)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_settings()
        self._center_window()
        self.spam_suffixes = load_spam_suffixes()
        self._load_exceptions()

        if self.dict_path and Path(self.dict_path).is_file():
            self._load_dictionary(self.dict_path)

    def _center_window(self):
        self.root.update_idletasks()
        w = self._settings.get("win_w", 1400)
        h = self._settings.get("win_h", 800)
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Dictionary loading
    # ------------------------------------------------------------------

    def on_load_dict(self):
        path = filedialog.askopenfilename(
            title="Select Dictionary File",
            filetypes=[
                ("Word lists", "*.txt *.json"),
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._load_dictionary(path)

    def _load_dictionary(self, path):
        self.view.set_status("Loading dictionary...")
        self.view.enable_dict_button(False)
        self.view.set_dict_empty()
        t = threading.Thread(target=self._load_thread, args=(path,), daemon=True)
        t.start()

    def _load_thread(self, path):
        try:
            wordlist, from_cache = load_wordlist_from_dict(path)
            self.root.after(0, self._on_dict_loaded, path, wordlist, from_cache)
        except Exception as e:
            logger.exception("Failed to load dictionary")
            self.root.after(0, self._on_dict_error, str(e))

    def _on_dict_loaded(self, path, wordlist, from_cache):
        self.dict_path = path
        self._base_wordlist = wordlist
        if self.custom_words:
            wordlist = sorted(set(wordlist) | self.custom_words)  # type: ignore[arg-type]
        self.lookup.set_wordlist(wordlist)
        self.view.set_dict_loaded(Path(path).name, len(wordlist))
        cache_hint = " (from cache)" if from_cache else ""
        extra = f" + {len(self.custom_words)} custom" if self.custom_words else ""
        self.view.set_status(f"{len(wordlist):,} words loaded{cache_hint}{extra}")
        self.view.enable_dict_button(True)
        self.view.enable_add_words_btn(True)

    def _on_dict_error(self, error):
        self.view.show_feedback("error", f"Failed to load dictionary: {error}", duration_ms=FEEDBACK_MS_DICT_ERROR)
        self.view.set_dict_empty()
        self.view.enable_dict_button(True)

    def on_add_words(self):
        if not self.lookup.has_wordlist():
            self.view.show_feedback("warn", "Load a dictionary first")
            return
        CustomWordsDialog(self.root, self)

    def on_remove_custom_words(self, words):
        before = len(self.custom_words)
        self.custom_words -= set(words)
        removed = before - len(self.custom_words)
        if not removed:
            self.view.set_status("Words not in custom words")
            return
        save_custom_words(self.custom_words)
        if self._base_wordlist is not None:
            merged = sorted(set(self._base_wordlist) | self.custom_words)
            self.lookup.set_wordlist(merged)
        self._run_search()
        s = "s" if removed != 1 else ""
        self.view.set_status(f"Removed {removed} custom word{s}")

    def edit_exceptions_file(self):
        EditorDialog(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=lambda: (self._load_exceptions(),
                                      self.view.set_status("Exceptions reloaded")),
            status_var=tk.StringVar(),
            default_content="# Exceptions - one per line\n",
        )

    def edit_trap_endings_file(self):
        EditorDialog(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=lambda: self.view.set_status("Trap endings saved"),
            status_var=tk.StringVar(),
            default_content="# Trap endings - one per line, hardest first\n",
        )

    def edit_spam_suffixes_file(self):
        EditorDialog(
            self,
            title="Edit Spam Suffixes",
            file_path=SPAM_SUFFIXES_FILE,
            reload_callback=lambda: (setattr(self, 'spam_suffixes', load_spam_suffixes()),
                                     self._refresh_result_colors(),
                                     self.view.set_status("Spam suffixes reloaded")),
            status_var=tk.StringVar(),
            default_content="# Spam suffixes - one per line\n",
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def on_search_debounced(self, event=None):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(DEBOUNCE_MS, self._run_search)

    def on_search_immediate(self):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._run_search()

    def _run_search(self):
        self._search_after_id = None
        if not self.lookup.has_wordlist():
            return
        prefix = self.view.prefix
        suffix = self.view.suffix
        contains = self.view.contains
        has_filter = bool(contains) or bool(self.view.min_len) or bool(self.view.max_len)
        if not prefix and not suffix and not has_filter:
            self.view.update_results([], 0, self.exceptions, self.spam_suffixes)
            self.view.set_status(
                f"{self.lookup.get_word_count():,} words available "
                "\u2014 type a prefix, suffix, or filter"
            )
            return
        self.view.set_status("Searching...")
        self._worker.submit(
            prefix, suffix, self.view.contains, self.view.min_len,
            self.view.max_len, self.view.match_case,
            on_result=lambda results, total: self.root.after(
                0, self._update_results, results, total),
            on_error=lambda error: self.root.after(0, self._on_search_error, error),
        )

    def _update_results(self, results, total):
        self._result_word_list = list(results)
        self.view.update_results(results, total, self.exceptions, self.spam_suffixes)
        n = len(results)
        if n == 0:
            self.view.set_status("No words found")
        else:
            self.view.set_status("Ready")

    def _on_search_error(self, error):
        self.view.show_feedback("error", f"Search failed: {error}", duration_ms=FEEDBACK_MS_ERROR)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def on_clear(self):
        self.view.reset_filters()
        self._result_word_list = []
        self.view.update_results([], 0, self.exceptions, self.spam_suffixes)
        if self.lookup.has_wordlist():
            self.view.set_status(f"{self.lookup.get_word_count():,} words available")
        else:
            self.view.set_status("Load a dictionary to begin")

    # ------------------------------------------------------------------
    # Query helpers (public interface for view, no direct attr access)
    # ------------------------------------------------------------------

    def is_exception(self, word):
        return word in self.exceptions

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    # ------------------------------------------------------------------
    # Exception management
    # ------------------------------------------------------------------

    def _load_exceptions(self):
        self.exceptions = _load_exc()
        self.refresh_exception_ui()

    def reload_exceptions(self):
        self._load_exceptions()
        self.view.set_status("Exceptions reloaded")

    def refresh_exception_ui(self):
        self._refresh_result_colors()

    def on_add_to_exceptions(self, words):
        before = len(self.exceptions)
        self.exceptions.update(w.lower() for w in words)
        added = len(self.exceptions) - before
        if added:
            _save_exc(sorted(self.exceptions))
            self.refresh_exception_ui()
            s = "s" if added != 1 else ""
            self.view.set_status(f"Added {added} word{s} to exceptions")
        else:
            self.view.set_status("Words already in exceptions")

    def on_remove_from_exceptions(self, words):
        before = len(self.exceptions)
        for w in words:
            self.exceptions.discard(w.lower())
        removed = before - len(self.exceptions)
        if removed:
            _save_exc(sorted(self.exceptions))
            self.refresh_exception_ui()
            s = "s" if removed != 1 else ""
            self.view.set_status(f"Removed {removed} word{s} from exceptions")
        else:
            self.view.set_status("Words not in exceptions")

    def on_add_selected(self):
        sel = self.view._result_tree.selection()
        if not sel:
            return
        words = [self.view._result_tree.item(item, "values")[1] for item in sel]
        self.on_add_to_exceptions(words)

    def on_exception_click(self, word):
        found = self.view.scroll_to_word(word)
        if not found:
            self.view.set_status(f"'{word}' not in current results \u2014 try searching")

    def _refresh_result_colors(self):
        self.view.update_results(self._result_word_list, len(self._result_word_list), self.exceptions, self.spam_suffixes)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text("utf-8"))
                self._settings = data
                self.dict_path = data.get("dict_path") or None
        except Exception:
            self._settings = {}

    def on_paste_exceptions_from_clipboard(self):
        try:
            raw = self.root.clipboard_get()
        except tk.TclError:
            self.view.show_feedback("warn", "Clipboard is empty")
            return
        words = []
        for line in raw.splitlines():
            for token in line.split():
                w = token.strip(",.!?;:()[]{}'\"-").lower()
                if w and w.isalpha():
                    words.append(w)
        if words:
            self.on_add_to_exceptions(words)
        else:
            self.view.show_feedback("warn", "No valid words in clipboard")

    def _save_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "dict_path": self.dict_path or "",
                "win_w": self.root.winfo_width(),
                "win_h": self.root.winfo_height(),
            }
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")
        except Exception as e:
            logger.warning("Failed to save lookup settings: %s", e)

    def _on_close(self):
        self._save_settings()
        self.root.destroy()


def main():
    try:
        root = tk.Tk()
        LookupApp(root)
        root.mainloop()
    except Exception:
        import traceback
        error_msg = traceback.format_exc()
        logger.critical("Startup crash:\n%s", error_msg)
        try:
            tk.Tk().withdraw()
            import tkinter.messagebox as mb
            mb.showerror("Startup Error", error_msg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
