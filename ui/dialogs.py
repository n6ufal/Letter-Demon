"""Secondary window classes: Advanced, About, Used Words."""

import tkinter as tk
import webbrowser

from .theme import (
    C_BG,
    C_BG_PANEL,
    C_ENTRY_BG,
    C_MUTED,
    C_PLAY_BG,
    C_PLAY_FG,
    C_SEP,
    C_TEXT,
    FONT_H1,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_MONO_M,
)
from .widgets import make_secondary_button, make_separator, make_slider, add_tooltip
from .window_utils import center_window
from core import version_string


class AboutDialog:
    """Stateless about window."""

    @staticmethod
    def show(root: tk.Misc) -> None:
        win = tk.Toplevel(root)
        win.title("About")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)

        f = tk.Frame(win, bg=C_BG, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        title_row = tk.Frame(f, bg=C_BG)
        title_row.pack(anchor="w", fill="x")
        tk.Label(title_row, text="Letter Demon \U0001f608", font=FONT_H1, bg=C_BG, fg=C_TEXT).pack(
            side="left"
        )
        tk.Label(
            f, text=version_string, font=FONT_MAIN, bg=C_BG, fg=C_MUTED
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

        tk.Label(f, text="Made by n6ufal with \U0001f49c", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
            anchor="w"
        )

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
            "<Button-1>", lambda e: webbrowser.open("mailto:boxcarr@proton.me")
        )

        gh_label = tk.Label(
            f,
            text="GitHub: n6ufal/Letter-Demon",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_TEXT,
            cursor="hand2",
        )
        gh_label.pack(anchor="w", pady=(2, 0))
        gh_label.bind(
            "<Button-1>",
            lambda e: webbrowser.open("https://github.com/n6ufal/Letter-Demon"),
        )

        center_window(win, root)


# ---------------------------------------------------------------------------
# Advanced dialog
# ---------------------------------------------------------------------------


class AdvancedDialog:
    """Advanced settings window — timing, dictionary, trap endings, exceptions."""

    def __init__(self, root: tk.Misc, controller, view) -> None:
        self._controller = controller
        self._view = view
        self._win: tk.Toplevel | None = None

    def show(self) -> None:
        if self._win is not None and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
            return
        self._build()

    def _build(self) -> None:
        win = tk.Toplevel(self._view.root)
        win.title("Advanced")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)
        self._win = win

        f = tk.Frame(win, padx=14, pady=12, bg=C_BG)
        f.pack(fill="both", expand=True)

        row = 0

        tk.Label(
            f, text="Dictionary", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        self._view.update_dict_label(self._controller.session.dict_path)
        tk.Label(
            f, textvariable=self._view.dict_label_var, fg=C_MUTED, font=FONT_MAIN,
            anchor="w", bg=C_BG,
        ).grid(row=row, column=0, sticky="w")
        load_btn = make_secondary_button(
            f, "Load Dictionary", self._controller.on_load_dict,
            row=row, column=1, sticky="e", padx=(12, 0),
        )
        add_tooltip(load_btn, "Open a .json or .txt word list file")
        row += 1
        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        tk.Label(
            f, text="Timing", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        tk.Label(
            f, text="Pre-type delay:", font=FONT_MAIN, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        def on_adv_pre_move(v):
            adv_pre_val.config(text=f"{int(v)}ms")

        adv_pre_slider, adv_pre_val = make_slider(
            f, "Pre-type", self._view.pre_delay_var,
            from_=100, to=2000, resolution=50, length=200, bg=C_BG,
            command=on_adv_pre_move,
        )
        adv_pre_slider.grid(row=row, column=0, sticky="we", pady=(0, 6))
        adv_pre_val.grid(row=row, column=1, sticky="e")
        add_tooltip(adv_pre_slider, "Pause before typing the first character")
        row += 1

        tk.Label(
            f, text="Post-type delay:", font=FONT_MAIN, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        def on_adv_post_move(v):
            adv_post_val.config(text=f"{int(v)}ms")

        adv_post_slider, adv_post_val = make_slider(
            f, "Post-type", self._view.post_delay_var,
            from_=100, to=2000, resolution=50, length=200, bg=C_BG,
            command=on_adv_post_move,
        )
        adv_post_slider.grid(row=row, column=0, sticky="we", pady=(0, 4))
        adv_post_val.grid(row=row, column=1, sticky="e")
        add_tooltip(adv_post_slider, "Pause after pressing Enter")
        row += 1

        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        tk.Label(
            f, text="Typing Mode", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        tk.Label(
            f, text="Auto Type Prefix:", font=FONT_MAIN, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, sticky="w")
        auto_type_combo = tk.ttk.Combobox(
            f,
            textvariable=self._view.auto_type_prefix_var,
            values=["On", "Off"],
            state="readonly",
            width=6,
        )
        auto_type_combo.grid(row=row, column=1, sticky="e")
        add_tooltip(
            auto_type_combo,
            "On: types only the ending / Off: types the full word",
        )
        row += 1

        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        tk.Label(
            f, text="Trap endings", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=0, sticky="nw", pady=(0, 2), padx=(0, 12))
        tk.Label(
            f, text="Exceptions", font=FONT_MAIN_BOLD, anchor="w", bg=C_BG, fg=C_TEXT
        ).grid(row=row, column=1, sticky="nw", pady=(0, 2))
        row += 1

        self._view.trap_status_var.set(
            f"{len(self._controller.session.engine.trap_endings)} loaded"
        )
        tk.Label(
            f, textvariable=self._view.trap_status_var, fg=C_TEXT, font=FONT_MAIN,
            anchor="w", bg=C_BG,
        ).grid(row=row, column=0, sticky="nw", padx=(0, 12))
        self._view.exceptions_status_var.set(
            f"{len(self._controller.session.engine.word_exceptions)} loaded"
        )
        tk.Label(
            f, textvariable=self._view.exceptions_status_var, fg=C_TEXT, font=FONT_MAIN,
            anchor="w", bg=C_BG,
        ).grid(row=row, column=1, sticky="nw")
        row += 1

        btn_row_trap = tk.Frame(f, bg=C_BG)
        btn_row_trap.grid(row=row, column=0, sticky="nw", pady=(4, 0), padx=(0, 12))
        trap_reload = make_secondary_button(
            btn_row_trap, "Reload", self._controller.reload_trap_endings
        )
        trap_reload.pack(side="left", padx=(0, 4))
        add_tooltip(trap_reload, "Reload trap endings from the file")
        trap_edit = make_secondary_button(
            btn_row_trap, "Edit", self._controller.edit_trap_endings
        )
        trap_edit.pack(side="left")
        add_tooltip(trap_edit, "Edit the trap endings list")

        btn_row_exc = tk.Frame(f, bg=C_BG)
        btn_row_exc.grid(row=row, column=1, sticky="nw", pady=(4, 0))
        exc_reload = make_secondary_button(
            btn_row_exc, "Reload", self._controller.reload_exceptions
        )
        exc_reload.pack(side="left", padx=(0, 4))
        add_tooltip(exc_reload, "Reload exceptions from the file")
        exc_edit = make_secondary_button(
            btn_row_exc, "Edit", self._controller.edit_exceptions
        )
        exc_edit.pack(side="left")
        add_tooltip(exc_edit, "Edit the word exceptions list")
        row += 1

        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        center_window(win, self._view.root)

        win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None


# ---------------------------------------------------------------------------
# Used Words dialog
# ---------------------------------------------------------------------------


class UsedWordsDialog:
    """Persistent window showing previously used words."""

    def __init__(self, root: tk.Misc, controller) -> None:
        self._controller = controller
        self._root = root
        self._win: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self._count_label: tk.Label | None = None

    def show(self) -> None:
        if self._win is not None and self._win.winfo_exists():
            self.update_list()
            self._win.lift()
            self._win.focus_force()
            return

        self._win = tk.Toplevel(self._root)
        self._win.title("Used Words")
        self._win.resizable(True, True)
        self._win.attributes("-topmost", True)
        self._win.configure(bg=C_BG)

        outer = tk.Frame(self._win, bg=C_BG, padx=8, pady=8)
        outer.pack(fill="both", expand=True)

        list_frame = tk.Frame(outer, bg=C_BG_PANEL, padx=1, pady=1)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(
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
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._listbox.yview)

        _, n_used = self._controller.session.used_words_for_display()
        self._count_label = tk.Label(
            outer,
            text=f"{n_used} words used",
            anchor="w",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_MUTED,
        )
        self._count_label.pack(fill="x", pady=(6, 4))

        make_secondary_button(outer, "Close", self.close).pack()

        center_window(self._win, self._root)
        self._win.protocol("WM_DELETE_WINDOW", self.close)

        self.update_list()

    def close(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
            self._listbox = None
            self._count_label = None

    def is_alive(self) -> bool:
        try:
            return self._win is not None and self._win.winfo_exists()
        except tk.TclError:
            self._win = None
            return False

    def update_list(self) -> None:
        if not self.is_alive():
            return
        words, n = self._controller.session.used_words_for_display()
        self._listbox.delete(0, tk.END)
        for word in words:
            self._listbox.insert(tk.END, word)
        if self._count_label is not None:
            self._count_label.config(text=f"{n} words used")
