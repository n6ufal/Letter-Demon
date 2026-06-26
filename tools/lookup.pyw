"""Dictionary Lookup — standalone tkinter app for word list exploration.

Uses binary search (bisect) for O(log n) prefix/suffix lookup on
a sorted word list. Runs independently of the main Letter Demon app.
"""

import json
import logging
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
from config.exceptions import load_exceptions as _load_exc, save_exceptions as _save_exc
from config.trap_endings import TRAP_ENDINGS_FILE, load_trap_endings, save_trap_endings
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
from ui.widgets import setup_ttk_styles

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(_PROJECT_ROOT) / "data" / "runtime" / "lookup_settings.json"

FORMAT_GAP = " " * 2
COL_INDEX_W = 4
COL_WORD_W = 32
COL_LEN_W = 4
COL_EXC_W = 1

DEBOUNCE_MS = 300
EXC_DEBOUNCE_MS = 200
TRAP_DEBOUNCE_MS = 200
FEEDBACK_MS_DEFAULT = 5000
FEEDBACK_MS_ERROR = 6000
FEEDBACK_MS_DICT_ERROR = 8000


def _format_row(index: int, word: str, in_exc: bool) -> str:
    exc_mark = "\u2713" if in_exc else " "
    return f"{index:>{COL_INDEX_W}}{FORMAT_GAP}{word:<{COL_WORD_W}}{FORMAT_GAP}{len(word):>{COL_LEN_W}}{FORMAT_GAP}{exc_mark}"


class LookupView:
    """Owns all widgets, tkinter vars, and layout. Delegates actions to controller."""

    def __init__(self, root: tk.Tk, controller):
        self.root = root
        self._controller = controller
        self._feedback_after_id = None
        self._exc_filter_after_id = None
        self._trap_filter_after_id = None

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

        self.dict_button = tk.Button(
            frame,
            text="\U0001f4c2 Load Dictionary...",
            command=self._controller.on_load_dict,
            font=FONT_MAIN,
            relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        self.dict_button.grid(row=0, column=0, padx=(0, 6))
        self.dict_button.bind("<Enter>", lambda e: self.dict_button.config(bg=C_ENTRY_BD))
        self.dict_button.bind("<Leave>", lambda e: self.dict_button.config(bg=C_BTN_BG))

        self.add_words_btn = tk.Button(
            frame,
            text="\u270e Add Words...",
            command=self._controller.on_add_words,
            font=FONT_MAIN,
            relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
            state="disabled",
        )
        self.add_words_btn.grid(row=0, column=1, padx=(0, 6))
        self.add_words_btn.bind("<Enter>", lambda e: self.add_words_btn.config(bg=C_ENTRY_BD))
        self.add_words_btn.bind("<Leave>", lambda e: self.add_words_btn.config(bg=C_BTN_BG))

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
        paned_frame = tk.Frame(parent, bg=C_BG)
        paned_frame.grid(row=row, column=0, sticky="nsew")
        paned_frame.columnconfigure(0, weight=1)
        paned_frame.rowconfigure(0, weight=1)

        self.paned = ttk.PanedWindow(paned_frame, orient=tk.HORIZONTAL)
        self.paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(self.paned)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        self._build_result_header(left, 0)
        self._build_result_listbox(left, 2)
        self._build_result_count_bar(left, 1)
        self.paned.add(left, weight=3)

        right = ttk.Frame(self.paned)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        container = tk.Frame(right, bg=C_BG)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        self._exc_frame = tk.Frame(container, bg=C_BG)
        self._exc_frame.pack(fill="both", expand=True)
        self._exc_frame.columnconfigure(0, weight=1)
        self._exc_frame.rowconfigure(2, weight=1)
        self._build_exception_panel(self._exc_frame)

        tk.Frame(container, height=1, bg=C_SEP).pack(fill="x", padx=(5, 2), pady=(0, 0))

        self._build_trap_toggle_header(container)

        self._trap_frame = tk.Frame(container, bg=C_BG)
        self._trap_frame.columnconfigure(0, weight=1)
        self._trap_frame.rowconfigure(1, weight=1)
        self._build_trap_panel(self._trap_frame)

        self.paned.add(right, weight=1)
        self.paned.bind("<Map>", self._restore_sash, add="+")

    def _build_result_header(self, parent, row):
        header = tk.Frame(parent, bg=C_BG_PANEL, height=24)
        header.grid(row=row, column=0, sticky="ew")
        header.grid_propagate(False)

        tk.Label(header, text="#", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT,
                 width=5, anchor="w").pack(side="left", padx=(4, 0))
        tk.Label(header, text="Word", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT,
                 anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(header, text="Len", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT,
                 width=5, anchor="e").pack(side="right", padx=(0, 28))
        tk.Label(header, text="Exc", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT,
                 width=3, anchor="center").pack(side="right")
        tk.Frame(header, height=1, bg=C_SEP).pack(side="bottom", fill="x")

        sep = tk.Frame(parent, height=1, bg=C_SEP)
        sep.grid(row=row + 1, column=0, sticky="ew")

    def _build_result_listbox(self, parent, row):
        list_frame = tk.Frame(parent, bg=C_BG)
        list_frame.grid(row=row, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.results_listbox = tk.Listbox(
            list_frame,
            font=FONT_MONO_M,
            activestyle="none",
            exportselection=False,
            selectmode=tk.EXTENDED,
            bg=C_ENTRY_BG,
            fg=C_TEXT,
            selectbackground=C_PLAY_BG,
            selectforeground=C_PLAY_FG,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.results_listbox.grid(row=0, column=0, sticky="nsew")
        self.results_listbox.bind("<Double-Button-1>", self._on_listbox_doubleclick)
        self.results_listbox.bind("<Button-3>", self._show_exception_menu)
        self.results_listbox.bind("<<ListboxSelect>>", self._on_selection_changed)

        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.results_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_listbox.configure(yscrollcommand=scrollbar.set)

    def _build_result_count_bar(self, parent, row):
        self._count_var = tk.StringVar(value="")
        self.count_label = tk.Label(
            parent, textvariable=self._count_var,
            font=FONT_SMALL, bg=C_BG_PANEL, fg=C_MUTED, anchor="e",
        )
        self.count_label.grid(row=row, column=0, sticky="ew", pady=(1, 0), ipady=1)

    def _build_exception_panel(self, parent):
        sep = tk.Frame(parent, width=1, bg=C_SEP)
        sep.grid(row=0, column=0, rowspan=5, sticky="ns")

        header = tk.Frame(parent, bg=C_BG_PANEL, height=24)
        header.grid(row=0, column=0, sticky="ew", padx=(1, 0))
        header.grid_propagate(False)
        tk.Label(header, text="Exceptions", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT
                 ).pack(side="left", padx=(6, 0))
        self._exc_count_label = tk.Label(
            header, text="0", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_MUTED,
        )
        self._exc_count_label.pack(side="left", padx=(2, 0))
        tk.Frame(header, height=1, bg=C_SEP).pack(side="bottom", fill="x")

        self._exc_filter_var = tk.StringVar()
        exc_filter_entry = tk.Entry(
            parent, textvariable=self._exc_filter_var, font=FONT_SMALL,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        exc_filter_entry.grid(row=1, column=0, sticky="ew", padx=(5, 2), pady=(4, 4), ipady=1)
        exc_filter_entry.bind("<KeyRelease>", self._on_exc_filter_change)

        exc_list_frame = tk.Frame(parent, bg=C_BG)
        exc_list_frame.grid(row=2, column=0, sticky="nsew", padx=(5, 2))
        exc_list_frame.columnconfigure(0, weight=1)
        exc_list_frame.rowconfigure(0, weight=1)

        self.exc_listbox = tk.Listbox(
            exc_list_frame,
            font=FONT_MONO,
            activestyle="none",
            exportselection=False,
            bg=C_ENTRY_BG,
            fg=C_TEXT,
            selectbackground=C_PLAY_BG,
            selectforeground=C_PLAY_FG,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.exc_listbox.grid(row=0, column=0, sticky="nsew")
        self.exc_listbox.bind("<<ListboxSelect>>", self._on_exc_selection_changed)
        self.exc_listbox.bind("<Double-Button-1>", self._on_exc_doubleclick)
        self.exc_listbox.bind("<Button-3>", self._show_exc_context_menu)

        exc_scroll = ttk.Scrollbar(
            exc_list_frame, orient="vertical", command=self.exc_listbox.yview
        )
        exc_scroll.grid(row=0, column=1, sticky="ns")
        self.exc_listbox.configure(yscrollcommand=exc_scroll.set)

        btn_frame = tk.Frame(parent, bg=C_BG)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=(5, 2), pady=(6, 0))
        self.remove_exc_btn = tk.Button(
            btn_frame,
            text="Remove Selected",
            command=self._on_remove_selected_exc,
            font=FONT_SMALL,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
            state="disabled",
        )
        self.remove_exc_btn.pack(fill="x")
        self.remove_exc_btn.bind("<Enter>", lambda e: self.remove_exc_btn.config(bg=C_ENTRY_BD))
        self.remove_exc_btn.bind("<Leave>", lambda e: self.remove_exc_btn.config(bg=C_BTN_BG))

        self._exc_all_count = 0

    # ------------------------------------------------------------------
    # Trap Endings — collapsible panel
    # ------------------------------------------------------------------

    def _build_trap_toggle_header(self, parent):
        self._trap_header = tk.Frame(parent, bg=C_BG_PANEL, height=26, cursor="hand2")
        self._trap_header.pack(fill="x")
        self._trap_header.pack_propagate(False)

        self._trap_arrow_var = tk.StringVar(value="\u25b6")
        arrow_label = tk.Label(self._trap_header, textvariable=self._trap_arrow_var,
                               font=FONT_MAIN, bg=C_BG_PANEL, fg=C_TEXT)
        arrow_label.pack(side="left", padx=(6, 2))
        arrow_label.bind("<Button-1>", lambda e: self._toggle_trap_panel())

        tk.Label(self._trap_header, text="Trap Endings",
                 font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT
                 ).pack(side="left")

        self._trap_count_header = tk.Label(self._trap_header, text="0",
                                            font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_MUTED)
        self._trap_count_header.pack(side="left", padx=(2, 0))
        self._trap_count_header.bind("<Button-1>", lambda e: self._toggle_trap_panel())

        tk.Frame(self._trap_header, height=1, bg=C_SEP).pack(side="bottom", fill="x")

        self._trap_header.bind("<Button-1>", lambda e: self._toggle_trap_panel())
        self._trap_expanded = False

    def _toggle_trap_panel(self, event=None):
        if getattr(self, "_trap_expanded", False):
            self._trap_frame.pack_forget()
            self._trap_arrow_var.set("\u25b6")
            self._trap_expanded = False
        else:
            self._trap_frame.pack(fill="both", expand=True, after=self._trap_header)
            self._trap_arrow_var.set("\u25bc")
            self._trap_expanded = True

    def _build_trap_panel(self, parent):
        sep = tk.Frame(parent, width=1, bg=C_SEP)
        sep.grid(row=0, column=0, rowspan=5, sticky="ns")

        header = tk.Frame(parent, bg=C_BG_PANEL, height=24)
        header.grid(row=0, column=0, sticky="ew", padx=(1, 0))
        header.grid_propagate(False)
        tk.Label(header, text="Trap Endings", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_TEXT
                 ).pack(side="left", padx=(6, 0))
        self._trap_count_label = tk.Label(
            header, text="0", font=FONT_MAIN_BOLD, bg=C_BG_PANEL, fg=C_MUTED,
        )
        self._trap_count_label.pack(side="left", padx=(2, 0))
        tk.Frame(header, height=1, bg=C_SEP).pack(side="bottom", fill="x")

        self._trap_filter_var = tk.StringVar()
        trap_filter_entry = tk.Entry(
            parent, textvariable=self._trap_filter_var, font=FONT_SMALL,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        trap_filter_entry.grid(row=1, column=0, sticky="ew", padx=(5, 2), pady=(4, 4), ipady=1)
        trap_filter_entry.bind("<KeyRelease>", self._on_trap_filter_change)

        trap_list_frame = tk.Frame(parent, bg=C_BG)
        trap_list_frame.grid(row=2, column=0, sticky="nsew", padx=(5, 2))
        trap_list_frame.columnconfigure(0, weight=1)
        trap_list_frame.rowconfigure(0, weight=1)

        self.trap_listbox = tk.Listbox(
            trap_list_frame,
            font=FONT_MONO,
            activestyle="none",
            exportselection=False,
            bg=C_ENTRY_BG,
            fg=C_TEXT,
            selectbackground=C_PLAY_BG,
            selectforeground=C_PLAY_FG,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.trap_listbox.grid(row=0, column=0, sticky="nsew")
        self.trap_listbox.bind("<<ListboxSelect>>", self._on_trap_selection_changed)
        self.trap_listbox.bind("<Double-Button-1>", self._on_trap_doubleclick_copy)
        self.trap_listbox.bind("<Button-3>", self._show_trap_context_menu)

        trap_scroll = ttk.Scrollbar(
            trap_list_frame, orient="vertical", command=self.trap_listbox.yview
        )
        trap_scroll.grid(row=0, column=1, sticky="ns")
        self.trap_listbox.configure(yscrollcommand=trap_scroll.set)

        add_frame = tk.Frame(parent, bg=C_BG)
        add_frame.grid(row=3, column=0, sticky="ew", padx=(5, 2), pady=(6, 4))

        self._trap_add_var = tk.StringVar()
        trap_add_entry = tk.Entry(
            add_frame, textvariable=self._trap_add_var, font=FONT_SMALL,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        trap_add_entry.pack(side="left", fill="x", expand=True, ipady=1)
        trap_add_entry.bind("<Return>", self._on_trap_add)

        trap_add_btn = tk.Button(
            add_frame,
            text="Add",
            command=self._on_trap_add,
            font=FONT_SMALL,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        trap_add_btn.pack(side="right", padx=(4, 0))
        trap_add_btn.bind("<Enter>", lambda e: trap_add_btn.config(bg=C_ENTRY_BD))
        trap_add_btn.bind("<Leave>", lambda e: trap_add_btn.config(bg=C_BTN_BG))

        btn_frame = tk.Frame(parent, bg=C_BG)
        btn_frame.grid(row=4, column=0, sticky="ew", padx=(5, 2))

        self.remove_trap_btn = tk.Button(
            btn_frame,
            text="Remove Selected",
            command=self._on_remove_selected_trap,
            font=FONT_SMALL,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
            state="disabled",
        )
        self.remove_trap_btn.pack(fill="x", pady=(0, 4))
        self.remove_trap_btn.bind("<Enter>", lambda e: self.remove_trap_btn.config(bg=C_ENTRY_BD))
        self.remove_trap_btn.bind("<Leave>", lambda e: self.remove_trap_btn.config(bg=C_BTN_BG))

        edit_trap_btn = tk.Button(
            btn_frame,
            text="\u270e Edit File...",
            command=self._controller.edit_trap_endings_file,
            font=FONT_SMALL,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        edit_trap_btn.pack(fill="x")
        edit_trap_btn.bind("<Enter>", lambda e: edit_trap_btn.config(bg=C_ENTRY_BD))
        edit_trap_btn.bind("<Leave>", lambda e: edit_trap_btn.config(bg=C_BTN_BG))

    # ------------------------------------------------------------------
    # Trap Endings event handlers
    # ------------------------------------------------------------------

    def _on_trap_filter_change(self, event=None):
        if self._trap_filter_after_id:
            self.root.after_cancel(self._trap_filter_after_id)
        self._trap_filter_after_id = self.root.after(TRAP_DEBOUNCE_MS,
                                                      self._controller.refresh_trap_ui)

    def _on_trap_selection_changed(self, event=None):
        selection = self.trap_listbox.curselection()
        self.remove_trap_btn.config(state="normal" if selection else "disabled")

    def _on_trap_doubleclick_copy(self, event=None):
        selection = self.trap_listbox.curselection()
        if selection:
            text = self.trap_listbox.get(selection[0])
            ending = text.split()[0] if text else ""
            if ending:
                self._trap_add_var.set(ending)
                for child in self._trap_frame.winfo_children():
                    if isinstance(child, tk.Entry) and child.winfo_ismapped():
                        child.focus_set()
                        child.icursor(tk.END)
                        break

    def _on_trap_add(self, event=None):
        ending = self._trap_add_var.get().strip()
        if ending:
            self._controller.on_add_trap_ending(ending)
            self._trap_add_var.set("")
            self._trap_add_entry_focus()

    def _on_remove_selected_trap(self):
        selection = self.trap_listbox.curselection()
        if not selection:
            return
        endings = []
        for i in selection:
            text = self.trap_listbox.get(i)
            ending = text.split()[0] if text else ""
            if ending:
                endings.append(ending)
        self._controller.on_remove_trap_endings(endings)

    def _show_trap_context_menu(self, event):
        index = self.trap_listbox.nearest(event.y)
        if index < 0 or index >= self.trap_listbox.size():
            return
        text = self.trap_listbox.get(index)
        ending = text.split()[0] if text else ""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Remove",
                         command=lambda e=ending: self._controller.on_remove_trap_endings([e]))
        menu.tk_popup(event.x_root, event.y_root)

    def _on_delete_trap_selection(self, event=None):
        self._on_remove_selected_trap()

    def _trap_add_entry_focus(self):
        for child in self._trap_frame.winfo_children():
            if isinstance(child, tk.Entry):
                child.focus_set()
                break

    def update_trap_panel(self, endings, filter_text=""):
        self.trap_listbox.delete(0, tk.END)
        total = len(endings)
        filtered = [
            (i, e) for i, e in enumerate(endings)
            if not filter_text or filter_text.lower() in e.lower()
        ]
        for orig_idx, ending in filtered:
            score = total - orig_idx
            display = f"{ending:<20} ({score})"
            self.trap_listbox.insert(tk.END, display)
        n = len(filtered)
        self._trap_count_label.config(text=str(total))
        self._trap_count_header.config(text=str(total))

    @property
    def trap_filter_text(self):
        return self._trap_filter_var.get()

    @property
    def trap_add_text(self):
        return self._trap_add_var.get()

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

        self._exc_count_var = tk.StringVar(value="Exceptions: 0")
        exc_count_label = tk.Label(
            frame, textvariable=self._exc_count_var,
            font=FONT_MAIN, bg=C_BG, fg=C_MUTED, cursor="hand2",
        )
        exc_count_label.grid(row=0, column=1, padx=(8, 4))
        exc_count_label.bind("<Button-1>", lambda e: self._controller.reload_exceptions())

        self.add_exc_btn = tk.Button(
            frame,
            text="+ Add to Exceptions",
            command=self._controller.on_add_selected,
            font=FONT_MAIN,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT, state="disabled",
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        self.add_exc_btn.grid(row=0, column=2, padx=(0, 4))
        self.add_exc_btn.bind("<Enter>", lambda e: self.add_exc_btn.config(bg=C_ENTRY_BD))
        self.add_exc_btn.bind("<Leave>", lambda e: self.add_exc_btn.config(bg=C_BTN_BG))

        self._trap_bottom_var = tk.StringVar(value="Trap Endings: 0")
        trap_bottom_label = tk.Label(
            frame, textvariable=self._trap_bottom_var,
            font=FONT_MAIN, bg=C_BG, fg=C_MUTED, cursor="hand2",
        )
        trap_bottom_label.grid(row=0, column=3, padx=(0, 4))
        trap_bottom_label.bind("<Button-1>", lambda e: self._controller.reload_trap_endings())

        clear_btn = tk.Button(
            frame,
            text="\u2302 Clear",
            command=self._controller.on_clear,
            font=FONT_MAIN,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT,
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        clear_btn.grid(row=0, column=4)
        clear_btn.bind("<Enter>", lambda e: clear_btn.config(bg=C_ENTRY_BD))
        clear_btn.bind("<Leave>", lambda e: clear_btn.config(bg=C_BTN_BG))

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
        self.results_listbox.bind("<Delete>", self._on_delete_results_selection)
        self.results_listbox.bind("<space>", self._on_space_toggle_exception)
        self.exc_listbox.bind("<Delete>", self._on_delete_exc_selection)
        self.trap_listbox.bind("<Delete>", self._on_delete_trap_selection)

    def _on_escape(self, event=None):
        focused = self.root.focus_get()
        if focused in (self.start_entry, self.end_entry):
            self.results_listbox.focus_set()
        else:
            self.start_entry.focus_set()

    def _on_delete_results_selection(self, event=None):
        selection = self.results_listbox.curselection()
        if selection:
            words = [self._controller.get_result_word(i) for i in selection]
            self._controller.on_remove_from_exceptions(words)

    def _on_space_toggle_exception(self, event=None):
        selection = self.results_listbox.curselection()
        if selection:
            for i in selection:
                word = self._controller.get_result_word(i)
                if self._controller.is_exception(word):
                    self._controller.on_remove_from_exceptions([word])
                else:
                    self._controller.on_add_to_exceptions([word])
        return "break"

    def _on_delete_exc_selection(self, event=None):
        self._on_remove_selected_exc()

    # ------------------------------------------------------------------
    # Exception panel event handlers
    # ------------------------------------------------------------------

    def _on_exc_filter_change(self, event=None):
        if self._exc_filter_after_id:
            self.root.after_cancel(self._exc_filter_after_id)
        self._exc_filter_after_id = self.root.after(EXC_DEBOUNCE_MS, self._controller.refresh_exception_list)

    def _on_exc_selection_changed(self, event=None):
        selection = self.exc_listbox.curselection()
        self.remove_exc_btn.config(state="normal" if selection else "disabled")

    def _on_exc_doubleclick(self, event=None):
        selection = self.exc_listbox.curselection()
        if not selection:
            return
        word = self.exc_listbox.get(selection[0])
        self._controller.on_exception_click(word)

    def _show_exc_context_menu(self, event):
        index = self.exc_listbox.nearest(event.y)
        if index < 0 or index >= self.exc_listbox.size():
            return
        word = self.exc_listbox.get(index)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Remove from Exceptions",
                         command=lambda w=word: self._controller.on_remove_from_exceptions([w]))
        menu.add_command(label="Scroll to in Results",
                         command=lambda w=word: self._controller.on_exception_click(w))
        menu.tk_popup(event.x_root, event.y_root)

    def _on_remove_selected_exc(self):
        selection = self.exc_listbox.curselection()
        if not selection:
            return
        words = [self.exc_listbox.get(i) for i in selection]
        self._controller.on_remove_from_exceptions(words)

    def _on_listbox_doubleclick(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self._controller.get_result_word(index)
        if self._controller.is_exception(word):
            self._controller.on_remove_from_exceptions([word])
        else:
            self._controller.on_add_to_exceptions([word])

    def _show_exception_menu(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self._controller.get_result_word(index)
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
        menu.tk_popup(event.x_root, event.y_root)

    def _on_selection_changed(self, event=None):
        selection = self.results_listbox.curselection()
        self.add_exc_btn.config(state="normal" if selection else "disabled")

    # ------------------------------------------------------------------
    # Sash position
    # ------------------------------------------------------------------

    def _restore_sash(self, event=None):
        pos = self._controller.get_setting("sash_pos")
        if pos is not None:
            try:
                self.paned.sashpos(0, pos)
            except Exception:
                pass

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
        self._dict_label_var.set(f"Dict: {filename}")
        self._dict_dot.config(fg=C_DOT_GREEN)
        self.dict_label.config(fg=C_TEXT)

    def set_dict_empty(self):
        self._dict_label_var.set("No dictionary loaded")
        self._dict_dot.config(fg=C_MUTED)
        self.dict_label.config(fg=C_MUTED)

    def update_results(self, results, total, exceptions):
        self.results_listbox.delete(0, tk.END)
        for i, word in enumerate(results):
            in_exc = word in exceptions
            display = _format_row(i + 1, word, in_exc)
            self.results_listbox.insert(tk.END, display)
            bg = "#ffffff" if i % 2 == 0 else "#f4f4f5"
            self.results_listbox.itemconfig(i, bg=bg)
            if in_exc:
                self.results_listbox.itemconfig(i, fg=C_MUTED)

        n = len(results)
        if n == 0:
            self._count_var.set("")
        elif n < total:
            self._count_var.set(f"Showing {n:,} of {total:,} words")
        elif n == 1:
            self._count_var.set("1 word found")
        else:
            self._count_var.set(f"{n:,} words found")

    def update_exception_panel(self, exceptions, filter_text=""):
        self.exc_listbox.delete(0, tk.END)
        filtered = sorted(
            w for w in exceptions
            if not filter_text or filter_text.lower() in w.lower()
        )
        for word in filtered:
            self.exc_listbox.insert(tk.END, word)
        n = len(exceptions)
        self._exc_count_var.set(f"Exceptions: {n}")
        self._exc_count_label.config(text=str(n))

    def set_exception_count_label(self, count):
        self._exc_count_var.set(f"Exceptions: {count}")

    def get_exception_listbox_selection(self):
        return [(self.exc_listbox.get(i), i) for i in self.exc_listbox.curselection()]

    def scroll_to_word(self, word):
        i = self._controller.get_result_index(word)
        if i < 0:
            return False
        self.results_listbox.selection_clear(0, tk.END)
        self.results_listbox.selection_set(i)
        self.results_listbox.see(i)
        self.results_listbox.activate(i)
        return True

    def reset_filters(self):
        self._start_var.set("")
        self._end_var.set("")
        self._contains_var.set("")
        self._min_len_var.set(0)
        self._max_len_var.set(0)

    @property
    def exc_filter_text(self):
        return self._exc_filter_var.get()

    def enable_dict_button(self, enabled):
        self.dict_button.config(state="normal" if enabled else "disabled")

    def enable_add_words_btn(self, enabled):
        self.add_words_btn.config(state="normal" if enabled else "disabled")

    def focus_start_entry(self):
        self.start_entry.focus_set()


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

        # ── Header ──
        header_frame = tk.Frame(main, bg=C_BG)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(header_frame, text="Custom Words", font=FONT_MAIN_BOLD,
                 bg=C_BG, fg=C_TEXT).pack(side="left")
        self._count_var = tk.StringVar(value="(0)")
        tk.Label(header_frame, textvariable=self._count_var,
                 font=FONT_MAIN, bg=C_BG, fg=C_MUTED
                 ).pack(side="left", padx=(4, 0))

        # ── Filter ──
        self._filter_var = tk.StringVar()
        filter_entry = tk.Entry(
            main, textvariable=self._filter_var, font=FONT_SMALL,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1,
        )
        filter_entry.grid(row=1, column=0, sticky="ew", pady=(0, 4), ipady=1)
        filter_entry.bind("<KeyRelease>", self._on_filter_change)

        # ── Custom words listbox ──
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

        # ── Remove button ──
        self._remove_btn = tk.Button(
            main, text="Remove Selected",
            command=self._on_remove, font=FONT_SMALL,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            bg=C_BTN_BG, fg=C_TEXT, state="disabled",
            activebackground=C_ENTRY_BD, activeforeground=C_TEXT,
        )
        self._remove_btn.grid(row=3, column=0, sticky="w", pady=(0, 8))
        self._remove_btn.bind("<Enter>",
                              lambda e: self._remove_btn.config(bg=C_ENTRY_BD))
        self._remove_btn.bind("<Leave>",
                              lambda e: self._remove_btn.config(bg=C_BTN_BG))

        # ── Separator ──
        ttk.Separator(main, orient="horizontal").grid(
            row=4, column=0, sticky="ew", pady=(0, 8))

        # ── Input area ──
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

        # ── Preview ──
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

        # ── Bottom buttons ──
        btn_frame = tk.Frame(main, bg=C_BG)
        btn_frame.grid(row=9, column=0, sticky="ew")

        self._add_btn = tk.Button(
            btn_frame, text="Add", command=self._on_add,
            font=FONT_MAIN_BOLD, relief="flat", bd=0,
            padx=14, pady=4, state=tk.DISABLED,
            bg=C_PLAY_BG, fg=C_PLAY_FG, cursor="hand2",
        )
        self._add_btn.pack(side="right", padx=(6, 0))

        close_btn = tk.Button(
            btn_frame, text="Close", command=self.dialog.destroy,
            font=FONT_MAIN, relief="flat", bd=0, padx=12, pady=4,
            bg=C_BTN_BG, fg=C_TEXT, cursor="hand2",
        )
        close_btn.pack(side="right")

    # ── Filter ──

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

    # ── Remove ──

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

    # ── Add (from AddWordsDialog) ──

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


class LookupApp:
    """Controller — owns DictLookup, exceptions, settings, threading."""

    RESULT_LIMIT = 1000

    def __init__(self, root):
        self.root = root
        self.root.title(f"Dictionary Lookup v{__version__}")
        self.root.minsize(1100, 650)

        self.dict_path = None
        self.lookup = DictLookup()
        self.exceptions = set()
        self._search_after_id = None
        self._current_results = []
        self._result_word_list = []
        self._settings = {}
        self.custom_words = load_custom_words()
        self._base_wordlist = None
        self.trap_endings = load_trap_endings()

        class _Engine:
            pass
        class _Session:
            pass
        self._editor_engine = _Engine()
        self._editor_engine.trap_endings = self.trap_endings
        self.session = _Session()
        self.session.engine = self._editor_engine

        self.view = LookupView(root, self)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_settings()
        self._center_window()
        self._load_exceptions()
        self.refresh_trap_ui()

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
        self._current_results = []
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

    # ------------------------------------------------------------------
    # Trap Endings
    # ------------------------------------------------------------------

    def reload_trap_endings(self):
        self.trap_endings = load_trap_endings()
        self._editor_engine.trap_endings = self.trap_endings
        self.refresh_trap_ui()
        self.view.set_status(f"Trap endings reloaded ({len(self.trap_endings)})")

    def refresh_trap_ui(self):
        self.view.update_trap_panel(self.trap_endings, self.view.trap_filter_text)
        self.view._trap_bottom_var.set(f"Trap Endings: {len(self.trap_endings)}")

    def on_add_trap_ending(self, ending):
        ending = ending.strip().lower()
        if not ending or not ending.isalpha():
            self.view.show_feedback("warn", "Ending must be alphabetic")
            return
        if ending in self.trap_endings:
            self.view.show_feedback("warn", f"'{ending}' already in trap endings")
            return
        self.trap_endings.append(ending)
        save_trap_endings(self.trap_endings)
        self.reload_trap_endings()
        self.view.set_status(f"Added '{ending}' to trap endings")

    def on_remove_trap_endings(self, endings):
        before = len(self.trap_endings)
        self.trap_endings = [e for e in self.trap_endings if e not in set(endings)]
        removed = before - len(self.trap_endings)
        if removed:
            save_trap_endings(self.trap_endings)
            self.reload_trap_endings()
            s = "s" if removed != 1 else ""
            self.view.set_status(f"Removed {removed} ending{s}")
        else:
            self.view.set_status("Endings not in list")

    def edit_trap_endings_file(self):
        EditorDialog(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=tk.StringVar(),
            default_content="# Trap endings - one per line, hardest first\n",
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
        if not prefix and not suffix:
            self.view.update_results([], 0, self.exceptions)
            self.view.set_status(
                f"{self.lookup.get_word_count():,} words available "
                "\u2014 type a prefix or suffix"
            )
            return
        self.view.set_status("Searching...")
        t = threading.Thread(
            target=self._search_thread,
            args=(prefix, suffix, self.view.contains, self.view.min_len,
                  self.view.max_len, self.view.match_case),
            daemon=True,
        )
        t.start()

    def _search_thread(self, prefix, suffix, contains, min_len, max_len, match_case):
        try:
            results, total = self.lookup.find_starting_and_ending_with(
                prefix, suffix, limit=self.RESULT_LIMIT
            )
            filtered = self._apply_filters(results, contains, min_len, max_len, match_case)
            self.root.after(0, self._update_results, filtered, total)
        except Exception as e:
            logger.exception("Search failed")
            self.root.after(0, self._on_search_error, str(e))

    def _apply_filters(self, results, contains, min_len, max_len, match_case):
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

    def _update_results(self, results, total):
        self._current_results = list(enumerate(results))
        self._result_word_list = list(results)
        self.view.update_results(results, total, self.exceptions)
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
        self._current_results = []
        self._result_word_list = []
        self.view.update_results([], 0, self.exceptions)
        if self.lookup.has_wordlist():
            self.view.set_status(f"{self.lookup.get_word_count():,} words available")
        else:
            self.view.set_status("Load a dictionary to begin")

    # ------------------------------------------------------------------
    # Query helpers (public interface for view, no direct attr access)
    # ------------------------------------------------------------------

    def get_result_word(self, index):
        return self._current_results[index][1]

    def is_exception(self, word):
        return word in self.exceptions

    def get_result_index(self, word):
        try:
            return self._result_word_list.index(word)
        except ValueError:
            return -1

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
        self.view.update_exception_panel(self.exceptions, self.view.exc_filter_text)
        self.view.set_exception_count_label(len(self.exceptions))
        self._refresh_result_colors()

    def refresh_exception_list(self):
        self.view.update_exception_panel(self.exceptions, self.view.exc_filter_text)

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
        selection = self.view.results_listbox.curselection()
        if not selection:
            return
        words = [self.get_result_word(i) for i in selection]
        self.on_add_to_exceptions(words)

    def on_exception_click(self, word):
        found = self.view.scroll_to_word(word)
        if not found:
            self.view.set_status(f"'{word}' not in current results \u2014 try searching")

    def _refresh_result_colors(self):
        self.view.update_results(self._result_word_list, len(self._result_word_list), self.exceptions)

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

    def _save_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "dict_path": self.dict_path or "",
                "win_w": self.root.winfo_width(),
                "win_h": self.root.winfo_height(),
            }
            try:
                data["sash_pos"] = self.view.paned.sashpos(0)
            except Exception:
                pass
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
