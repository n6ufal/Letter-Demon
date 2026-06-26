"""LookupView — all tkinter widgets, layout, and display updates.

Emits callbacks on user interaction; no knowledge of the controller.
"""

import logging
import tkinter as tk
from tkinter import ttk

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

FORMAT_GAP = " " * 2
COL_INDEX_W = 4
COL_WORD_W = 32
COL_LEN_W = 4
COL_EXC_W = 1

EXC_DEBOUNCE_MS = 200
TRAP_DEBOUNCE_MS = 200
FEEDBACK_MS_DEFAULT = 5000


def _format_row(index: int, word: str, in_exc: bool, col_width: int = COL_WORD_W) -> str:
    exc_mark = "\u2713" if in_exc else " "
    return (
        f"{index:>{COL_INDEX_W}}{FORMAT_GAP}"
        f"{word:<{col_width}}{FORMAT_GAP}"
        f"{len(word):>{COL_LEN_W}}{FORMAT_GAP}"
        f"{exc_mark}"
    )


class LookupView:
    """Owns all widgets, tkinter vars, and layout. Calls controller callbacks."""

    def __init__(self, root: tk.Tk, callbacks):
        self.root = root
        self._c = callbacks
        self._feedback_after_id = None
        self._exc_filter_after_id = None
        self._trap_filter_after_id = None
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
            command=self._c.load_dict,
            row=0, column=0, padx=(0, 6),
        )

        self.add_words_btn = make_secondary_button(
            frame, text="\u270e Add Words...",
            command=self._c.add_words,
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
        self.start_entry.bind("<KeyRelease>", self._c.search_debounced)
        self.start_entry.bind("<FocusIn>", lambda e: self.start_entry.config(
            highlightbackground=C_ENTRY_FOCUS, highlightthickness=2))
        self.start_entry.bind("<FocusOut>", lambda e: self.start_entry.config(
            highlightbackground=C_ENTRY_BD, highlightthickness=1))

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
        self.end_entry.bind("<KeyRelease>", self._c.search_debounced)
        self.end_entry.bind("<FocusIn>", lambda e: self.end_entry.config(
            highlightbackground=C_ENTRY_FOCUS, highlightthickness=2))
        self.end_entry.bind("<FocusOut>", lambda e: self.end_entry.config(
            highlightbackground=C_ENTRY_BD, highlightthickness=1))

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
        self.contains_entry.bind("<KeyRelease>", self._c.search_debounced)

        tk.Label(frame, text="Min:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).pack(side="left", padx=(0, 2))
        self._min_len_var = tk.IntVar(value=0)
        self.min_spin = tk.Spinbox(
            frame, from_=0, to=30, textvariable=self._min_len_var,
            width=3, font=FONT_MAIN, bg=C_ENTRY_BG, fg=C_TEXT,
            buttonbackground=C_BTN_BG, relief="solid", bd=1,
        )
        self.min_spin.pack(side="left", padx=(0, 14), ipady=1)
        self.min_spin.bind("<KeyRelease>", self._c.search_debounced)
        self._min_len_var.trace_add("write", lambda *_: self._c.search_immediate())

        tk.Label(frame, text="Max:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
                 ).pack(side="left", padx=(0, 2))
        self._max_len_var = tk.IntVar(value=0)
        self.max_spin = tk.Spinbox(
            frame, from_=0, to=30, textvariable=self._max_len_var,
            width=3, font=FONT_MAIN, bg=C_ENTRY_BG, fg=C_TEXT,
            buttonbackground=C_BTN_BG, relief="solid", bd=1,
        )
        self.max_spin.pack(side="left", padx=(0, 14), ipady=1)
        self.max_spin.bind("<KeyRelease>", self._c.search_debounced)
        self._max_len_var.trace_add("write", lambda *_: self._c.search_immediate())

        self._match_case_var = tk.BooleanVar(value=False)
        self.match_case_cb = tk.Checkbutton(
            frame, text="Match Case", variable=self._match_case_var,
            font=FONT_MAIN, bg=C_BG, fg=C_TEXT, selectcolor=C_BG,
            activebackground=C_BG, activeforeground=C_TEXT,
            command=self._c.search_immediate,
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
        self.remove_exc_btn = make_secondary_button(
            btn_frame, text="Remove Selected",
            command=self._on_remove_selected_exc,
        )
        self.remove_exc_btn.config(state="disabled")
        self.remove_exc_btn.pack(fill="x")

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

        trap_add_btn = make_secondary_button(
            add_frame, text="Add",
            command=self._on_trap_add,
        )
        trap_add_btn.pack(side="right", padx=(4, 0))

        btn_frame = tk.Frame(parent, bg=C_BG)
        btn_frame.grid(row=4, column=0, sticky="ew", padx=(5, 2))

        self.remove_trap_btn = make_secondary_button(
            btn_frame, text="Remove Selected",
            command=self._on_remove_selected_trap,
        )
        self.remove_trap_btn.config(state="disabled")
        self.remove_trap_btn.pack(fill="x", pady=(0, 4))

        edit_trap_btn = make_secondary_button(
            btn_frame, text="\u270e Edit File...",
            command=self._c.edit_trap_file,
        )
        edit_trap_btn.pack(fill="x")

    # ------------------------------------------------------------------
    # Trap Endings event handlers
    # ------------------------------------------------------------------

    def _on_trap_filter_change(self, event=None):
        if self._trap_filter_after_id:
            self.root.after_cancel(self._trap_filter_after_id)
        self._trap_filter_after_id = self.root.after(
            TRAP_DEBOUNCE_MS, self._c.refresh_trap_ui)

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
            self._c.add_trap_ending(ending)
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
        self._c.remove_trap_endings(endings)

    def _show_trap_context_menu(self, event):
        index = self.trap_listbox.nearest(event.y)
        if index < 0 or index >= self.trap_listbox.size():
            return
        text = self.trap_listbox.get(index)
        ending = text.split()[0] if text else ""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="Remove",
            command=lambda e=ending: self._c.remove_trap_endings([e]),
        )
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
        exc_count_label.bind("<Button-1>", lambda e: self._c.reload_exceptions())

        self.add_exc_btn = make_secondary_button(
            frame, text="+ Add to Exceptions",
            command=self._c.add_selected,
            row=0, column=2, padx=(0, 4),
        )
        self.add_exc_btn.config(state="disabled")

        self._trap_bottom_var = tk.StringVar(value="Trap Endings: 0")
        trap_bottom_label = tk.Label(
            frame, textvariable=self._trap_bottom_var,
            font=FONT_MAIN, bg=C_BG, fg=C_MUTED, cursor="hand2",
        )
        trap_bottom_label.grid(row=0, column=3, padx=(0, 4))
        trap_bottom_label.bind("<Button-1>", lambda e: self._c.reload_trap_endings())

        make_secondary_button(
            frame, text="\u2302 Clear",
            command=self._c.clear,
            row=0, column=4,
        )

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _wire_keyboard_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self._c.load_dict())
        self.root.bind("<Control-O>", lambda e: self._c.load_dict())
        self.root.bind("<Control-l>", lambda e: self._c.clear())
        self.root.bind("<Control-L>", lambda e: self._c.clear())
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
            words = [self._c.get_result_word(i) for i in selection]
            self._c.remove_from_exceptions(words)

    def _on_space_toggle_exception(self, event=None):
        selection = self.results_listbox.curselection()
        if selection:
            for i in selection:
                word = self._c.get_result_word(i)
                if self._c.is_exception(word):
                    self._c.remove_from_exceptions([word])
                else:
                    self._c.add_to_exceptions([word])
        return "break"

    def _on_delete_exc_selection(self, event=None):
        self._on_remove_selected_exc()

    # ------------------------------------------------------------------
    # Exception panel event handlers
    # ------------------------------------------------------------------

    def _on_exc_filter_change(self, event=None):
        if self._exc_filter_after_id:
            self.root.after_cancel(self._exc_filter_after_id)
        self._exc_filter_after_id = self.root.after(
            EXC_DEBOUNCE_MS, self._c.refresh_exception_list)

    def _on_exc_selection_changed(self, event=None):
        selection = self.exc_listbox.curselection()
        self.remove_exc_btn.config(state="normal" if selection else "disabled")

    def _on_exc_doubleclick(self, event=None):
        selection = self.exc_listbox.curselection()
        if not selection:
            return
        word = self.exc_listbox.get(selection[0])
        self._c.exception_click(word)

    def _show_exc_context_menu(self, event):
        index = self.exc_listbox.nearest(event.y)
        if index < 0 or index >= self.exc_listbox.size():
            return
        word = self.exc_listbox.get(index)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="Remove from Exceptions",
            command=lambda w=word: self._c.remove_from_exceptions([w]),
        )
        menu.add_command(
            label="Scroll to in Results",
            command=lambda w=word: self._c.exception_click(w),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_remove_selected_exc(self):
        selection = self.exc_listbox.curselection()
        if not selection:
            return
        words = [self.exc_listbox.get(i) for i in selection]
        self._c.remove_from_exceptions(words)

    def _on_listbox_doubleclick(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self._c.get_result_word(index)
        if self._c.is_exception(word):
            self._c.remove_from_exceptions([word])
        else:
            self._c.add_to_exceptions([word])

    def _show_exception_menu(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self._c.get_result_word(index)
        menu = tk.Menu(self.root, tearoff=0)
        if self._c.is_exception(word):
            menu.add_command(
                label="Remove from Exceptions",
                command=lambda w=word: self._c.remove_from_exceptions([w]),
            )
        else:
            menu.add_command(
                label="Add to Exceptions",
                command=lambda w=word: self._c.add_to_exceptions([w]),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_selection_changed(self, event=None):
        selection = self.results_listbox.curselection()
        self.add_exc_btn.config(state="normal" if selection else "disabled")

    # ------------------------------------------------------------------
    # Sash position
    # ------------------------------------------------------------------

    def _restore_sash(self, event=None):
        pos = self._c.get_setting("sash_pos")
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
        results_tuple = tuple(results)
        if results_tuple == self._prev_results_tuple and exceptions == self._prev_exceptions:
            return
        self._prev_results_tuple = results_tuple
        self._prev_exceptions = frozenset(exceptions)

        self.results_listbox.delete(0, tk.END)
        col_width = max((len(w) for w in results), default=0)
        col_width = max(COL_WORD_W, min(col_width + 2, 60))
        for i, word in enumerate(results):
            in_exc = word in exceptions
            display = _format_row(i + 1, word, in_exc, col_width)
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
        i = self._c.get_result_index(word)
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
