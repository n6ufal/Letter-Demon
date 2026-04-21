"""Main application window — thin tkinter layer that wires UI to engines."""

import os
import sys
import threading
import winsound

import tkinter as tk
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText

from core.dictionary import load_wordlist_from_dict
from core.word_engine import WordEngine
from config.settings import load_settings, save_settings
from config.trap_endings import load_trap_endings, save_trap_endings
from config.exceptions import load_exceptions, save_exceptions
from system.roblox import is_roblox_running, focus_roblox_window
from system.typer import Typer

from .theme import *
from .widgets import (
    setup_ttk_styles, make_slider, make_primary_button,
    make_secondary_button, make_separator,
)


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class LastLetterApp:
    """Tkinter application — handles widgets, user input, and threading.
    Delegates all game logic to WordEngine, all typing to Typer,
    and all system interaction to the roblox module.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Letter Demon")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        try:
            self.root.iconbitmap(resource_path("LastLetter.ico"))
        except Exception as e:
            print("Icon load error:", e)

        # --- Engines (no UI dependency) ---
        self.engine = WordEngine(
            wordlist=[],
            trap_endings=load_trap_endings(),
            exceptions=load_exceptions(),
        )
        self.typer = Typer()

        # --- State ---
        self._is_playing = False
        self._playing_lock = threading.Lock()
        self._wordlist_lock = threading.Lock()
        self._dict_path: str | None = None
        self._flash_after_id = None
        self._advanced_window = None
        self.used_words_window = None

        # --- Load persisted settings ---
        settings = load_settings()
        self._dict_path = settings.get("dict_path", None)

        # --- Tkinter variables ---
        self.prefix_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=settings.get("mode", "Trap Words"))
        self.fallback_var = tk.StringVar(value=settings.get("fallback", "Short Words"))
        self.jitter_enabled = tk.BooleanVar(value=settings.get("jitter_enabled", True))
        self.jitter_intensity = tk.IntVar(value=settings.get("jitter_intensity", 75))
        self.timing_expanded = tk.BooleanVar(value=settings.get("timing_expanded", False))

        # --- Build UI ---
        self.root.configure(bg=C_BG)
        self.main_frame = tk.Frame(self.root, padx=12, pady=10, bg=C_BG)
        self.main_frame.pack(fill="both", expand=True)

        setup_ttk_styles()
        self._build_ui(settings)

        # --- Restore window position ---
        if "win_x" in settings and "win_y" in settings:
            self.root.geometry(f"+{settings['win_x']}+{settings['win_y']}")

        # --- Post-init setup ---
        self.root.after(50, self._on_jitter_toggle)
        self.root.after(10, self._apply_timing_state)
        self.root.bind("<FocusIn>", lambda event: self.entry.focus_set())
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.entry.bind("<Control-Return>", self.on_ctrl_enter)

        self._poll_roblox()

        if self._dict_path and os.path.exists(self._dict_path):
            threading.Thread(
                target=self._load_wordlist_thread,
                args=(self._dict_path,),
                daemon=True,
            ).start()
        else:
            self._dict_path = None
            self.status_var.set("No dictionary loaded")

    # ==================================================================
    # Main UI
    # ==================================================================

    def _build_ui(self, settings: dict) -> None:
        f = self.main_frame

        # --- Starting letters ---
        tk.Label(f, text="Starting letters:", anchor="w",
                 font=("Segoe UI", 8), bg=C_BG, fg=C_MUTED
                 ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 2))

        self.entry = tk.Entry(
            f, textvariable=self.prefix_var,
            font=("Segoe UI", 16), width=18,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            relief="solid", bd=1, highlightthickness=1,
            highlightbackground=C_ENTRY_BD, highlightcolor=C_ENTRY_FOCUS,
        )
        self.entry.grid(row=1, column=0, columnspan=4, sticky="we", ipady=6, pady=(0, 6))
        self.entry.focus_set()
        self.entry.bind("<FocusIn>",  lambda e: self.entry.config(
            highlightbackground=C_ENTRY_FOCUS, highlightthickness=2))
        self.entry.bind("<FocusOut>", lambda e: self.entry.config(
            highlightbackground=C_ENTRY_BD, highlightthickness=1))

        # --- Info bar: status (left) + Roblox (right) on one row ---
        info_bar = tk.Frame(f, bg=C_BG)
        info_bar.grid(row=2, column=0, columnspan=4, sticky="we", pady=(0, 4))
        self.status_var = tk.StringVar(value="No dictionary loaded")
        tk.Label(info_bar, textvariable=self.status_var, fg=C_MUTED, anchor="w",
                 font=("Segoe UI", 8), bg=C_BG,
                 ).pack(side="left")
        self.roblox_status_var = tk.StringVar(value="Roblox: off")
        self.roblox_status_label = tk.Label(
            info_bar, textvariable=self.roblox_status_var,
            fg=C_DOT_RED, anchor="e", font=("Segoe UI", 8), bg=C_BG,
        )
        self.roblox_status_label.pack(side="right")

        # --- Play round button ---
        self.play_btn = make_primary_button(
            f, "Play round", self.on_play_round,
            row=3, column=0, columnspan=4, sticky="we", pady=(4, 8),
        )

        # --- Controls panel ---
        panel = tk.Frame(f, bg=C_BG_PANEL, padx=8, pady=6)
        panel.grid(row=4, column=0, columnspan=4, sticky="we", pady=(0, 6))
        panel.grid_columnconfigure(1, weight=1)

        # Speed
        tk.Label(panel, text="Speed:", anchor="w", font=("Segoe UI", 8),
                 bg=C_BG_PANEL, fg=C_TEXT).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.speed_var = tk.DoubleVar(value=settings.get("speed", 170.0))
        self.speed_slider, self.speed_val_label = make_slider(
            panel, "Speed", self.speed_var,
            from_=10, to=200, resolution=5, length=160,
        )
        self.speed_slider.grid(row=0, column=1, sticky="we", pady=(0, 2))
        self.speed_val_label.grid(row=0, column=2, sticky="e")

        # Timing toggle
        timing_toggle = tk.Frame(panel, bg=C_BG_PANEL)
        timing_toggle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))
        self._timing_toggle_btn = tk.Button(
            timing_toggle, text=self._timing_arrow(),
            command=self._toggle_timing, relief="flat", bd=0,
            font=("Segoe UI", 8), fg=C_MUTED, bg=C_BG_PANEL,
            activebackground=C_BG_PANEL, cursor="hand2",
        )
        self._timing_toggle_btn.pack(side="left")
        tk.Label(timing_toggle, text="Timing delays", fg=C_MUTED,
                 font=("Segoe UI", 8), bg=C_BG_PANEL).pack(side="left")

        # Collapsible timing frame
        self._timing_frame = tk.Frame(panel, bg=C_BG_PANEL)
        self._timing_frame.grid(row=2, column=0, columnspan=3, sticky="we")
        self._timing_frame.grid_columnconfigure(1, weight=1)

        tk.Label(self._timing_frame, text="Pre:", anchor="w",
                 font=("Segoe UI", 8), bg=C_BG_PANEL, fg=C_TEXT
                 ).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.pre_delay_var = tk.IntVar(value=settings.get("pre_delay", 500))
        self.pre_slider, self.pre_val_label = make_slider(
            self._timing_frame, "Pre", self.pre_delay_var,
            from_=100, to=2000, resolution=50, length=140,
        )
        self.pre_slider.grid(row=0, column=1, sticky="we")
        self.pre_val_label.grid(row=0, column=2, sticky="e")

        tk.Label(self._timing_frame, text="Post:", anchor="w",
                 font=("Segoe UI", 8), bg=C_BG_PANEL, fg=C_TEXT
                 ).grid(row=1, column=0, sticky="w", padx=(0, 4))
        self.post_delay_var = tk.IntVar(value=settings.get("post_delay", 500))
        self.post_slider, self.post_val_label = make_slider(
            self._timing_frame, "Post", self.post_delay_var,
            from_=100, to=2000, resolution=50, length=140,
        )
        self.post_slider.grid(row=1, column=1, sticky="we")
        self.post_val_label.grid(row=1, column=2, sticky="e")

        # --- Mode + Fallback row ---
        combo_row = tk.Frame(f, bg=C_BG)
        combo_row.grid(row=5, column=0, columnspan=4, sticky="we", pady=(0, 4))

        tk.Label(combo_row, text="Mode:", font=("Segoe UI", 8),
                 bg=C_BG, fg=C_TEXT).pack(side="left", padx=(0, 4))
        self.mode_combobox = tk.ttk.Combobox(
            combo_row, textvariable=self.mode_var,
            values=["Trap Words", "Random Words", "Short Words", "Long Words"],
            state="readonly", width=11,
        )
        self.mode_combobox.pack(side="left", padx=(0, 10))

        tk.Label(combo_row, text="Fallback:", font=("Segoe UI", 8),
                 bg=C_BG, fg=C_TEXT).pack(side="left", padx=(0, 4))
        self.fallback_combobox = tk.ttk.Combobox(
            combo_row, textvariable=self.fallback_var,
            values=["Short Words", "Random Words", "Long Words"],
            state="readonly", width=10,
        )
        self.fallback_combobox.pack(side="left")

        # --- Jitter row ---
        jitter_row = tk.Frame(f, bg=C_BG)
        jitter_row.grid(row=6, column=0, columnspan=4, sticky="we", pady=(0, 4))

        self.jitter_check = tk.Checkbutton(
            jitter_row, text="Jitter", variable=self.jitter_enabled,
            command=self._on_jitter_toggle, font=("Segoe UI", 8),
            bg=C_BG, fg=C_TEXT, activebackground=C_BG,
            selectcolor=C_ENTRY_BG,
        )
        self.jitter_check.pack(side="left")

        self.jitter_label = tk.Label(jitter_row, text="Intensity:",
                                     font=("Segoe UI", 8), bg=C_BG, fg=C_TEXT)
        self.jitter_label.pack(side="left", padx=(8, 2))

        self.jitter_slider, self.jitter_intensity_val = make_slider(
            jitter_row, "Intensity", self.jitter_intensity,
            from_=5, to=100, resolution=5, length=110, bg=C_BG,
        )
        self.jitter_slider.pack(side="left")
        self.jitter_intensity_val.pack(side="left", padx=(4, 0))

        # --- Separator ---
        make_separator(f, 7, column=0, columnspan=4, sticky="we", pady=(4, 6))

        # --- Bottom buttons ---
        make_secondary_button(
            f, "\u2699 Advanced", self.show_advanced,
            row=8, column=0, columnspan=1, sticky="we", padx=(0, 2), pady=(0, 2),
        )
        make_secondary_button(
            f, "Clear", self.on_clear_cache,
            row=8, column=1, columnspan=2, sticky="we", padx=(0, 2), pady=(0, 2),
        )
        make_secondary_button(
            f, "Used Words", self.show_used_words,
            row=8, column=3, columnspan=1, sticky="we", pady=(0, 2),
        )

        credit = tk.Label(f, text="Made by n6ufal", fg=C_MUTED,
                          font=("Segoe UI", 7), bg=C_BG, cursor="hand2")
        credit.grid(row=9, column=0, columnspan=4, sticky="e", pady=(2, 0))
        credit.bind("<Button-1>", lambda e: self.show_about())
        credit.bind("<Enter>", lambda e: credit.config(fg=C_TEXT))
        credit.bind("<Leave>", lambda e: credit.config(fg=C_MUTED))

        for col in range(4):
            f.grid_columnconfigure(col, weight=1)

    # ==================================================================
    # Collapsible timing
    # ==================================================================

    def _timing_arrow(self) -> str:
        return "\u25bc" if self.timing_expanded.get() else "\u25b6"

    def _toggle_timing(self) -> None:
        self.timing_expanded.set(not self.timing_expanded.get())
        self._apply_timing_state()

    def _apply_timing_state(self) -> None:
        if self.timing_expanded.get():
            self._timing_frame.grid()
        else:
            self._timing_frame.grid_remove()
        self._timing_toggle_btn.config(text=self._timing_arrow())

    # ==================================================================
    # Advanced window
    # ==================================================================

    def show_advanced(self) -> None:
        if self._advanced_window is not None and self._advanced_window.winfo_exists():
            self._advanced_window.lift()
            self._advanced_window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title("Advanced")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)
        self._advanced_window = win

        f = tk.Frame(win, padx=14, pady=12, bg=C_BG)
        f.pack(fill="both", expand=True)

        row = 0

        # --- Dictionary ---
        tk.Label(f, text="Dictionary", font=("Segoe UI", 8, "bold"),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        self.dict_label_var = tk.StringVar(value=self._dict_display_name())
        tk.Label(f, textvariable=self.dict_label_var, fg=C_MUTED,
                 font=("Segoe UI", 8), anchor="w", bg=C_BG
                 ).grid(row=row, column=0, sticky="w")
        make_secondary_button(
            f, "Load Dictionary", self.on_load_dict,
            row=row, column=1, sticky="e", padx=(12, 0),
        )
        row += 1
        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        # --- Timing ---
        tk.Label(f, text="Timing", font=("Segoe UI", 8, "bold"),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        tk.Label(f, text="Pre-type delay:", font=("Segoe UI", 8),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        adv_pre_val = tk.Label(f, text=f"{self.pre_delay_var.get()}ms",
                               font=("Segoe UI", 8), bg=C_BG, fg=C_MUTED)
        adv_pre_val.grid(row=row, column=1, sticky="e")
        adv_pre_slider, _ = make_slider(
            f, "Pre-type", self.pre_delay_var,
            from_=100, to=2000, resolution=50, length=200, bg=C_BG,
        )
        adv_pre_slider.grid(row=row, column=0, sticky="we", pady=(0, 6))
        adv_pre_slider.config(command=lambda v: (
            self.pre_val_label.config(text=f"{int(float(v))}ms"),
            adv_pre_val.config(text=f"{int(float(v))}ms"),
        ))
        row += 1

        tk.Label(f, text="Post-type delay:", font=("Segoe UI", 8),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        adv_post_val = tk.Label(f, text=f"{self.post_delay_var.get()}ms",
                                font=("Segoe UI", 8), bg=C_BG, fg=C_MUTED)
        adv_post_val.grid(row=row, column=1, sticky="e")
        adv_post_slider, _ = make_slider(
            f, "Post-type", self.post_delay_var,
            from_=100, to=2000, resolution=50, length=200, bg=C_BG,
        )
        adv_post_slider.grid(row=row, column=0, sticky="we", pady=(0, 4))
        adv_post_slider.config(command=lambda v: (
            self.post_val_label.config(text=f"{int(float(v))}ms"),
            adv_post_val.config(text=f"{int(float(v))}ms"),
        ))
        row += 1

        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        # --- Trap Endings ---
        tk.Label(f, text="Trap Endings", font=("Segoe UI", 8, "bold"),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        self.trap_status_var = tk.StringVar(
            value=f"{len(self.engine.trap_endings)} loaded")
        tk.Label(f, textvariable=self.trap_status_var, fg=C_MUTED,
                 font=("Segoe UI", 8), anchor="w", bg=C_BG
                 ).grid(row=row, column=0, sticky="w")
        row += 1

        btn_row_trap = tk.Frame(f, bg=C_BG)
        btn_row_trap.grid(row=row, column=0, columnspan=2, sticky="e", pady=(2, 0))
        make_secondary_button(btn_row_trap, "Reload Traps",
                              self.reload_trap_endings).pack(side="left", padx=(0, 4))
        make_secondary_button(btn_row_trap, "Edit",
                              self.edit_trap_endings).pack(side="left")
        row += 1

        make_separator(f, row, column=0, columnspan=2, sticky="we", pady=(8, 8))
        row += 1

        # --- Exceptions ---
        tk.Label(f, text="Exceptions", font=("Segoe UI", 8, "bold"),
                 anchor="w", bg=C_BG, fg=C_TEXT
                 ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        self.exceptions_status_var = tk.StringVar(
            value=f"{len(self.engine.word_exceptions)} loaded")
        tk.Label(f, textvariable=self.exceptions_status_var, fg=C_MUTED,
                 font=("Segoe UI", 8), anchor="w", bg=C_BG
                 ).grid(row=row, column=0, sticky="w")
        row += 1

        btn_row_exc = tk.Frame(f, bg=C_BG)
        btn_row_exc.grid(row=row, column=0, columnspan=2, sticky="e", pady=(2, 0))
        make_secondary_button(btn_row_exc, "Reload Exceptions",
                              self.reload_exceptions).pack(side="left", padx=(0, 4))
        make_secondary_button(btn_row_exc, "Edit",
                              self.edit_exceptions).pack(side="left")

        f.grid_columnconfigure(0, weight=1)
        self._center_window(win)

        def _on_adv_close():
            self._advanced_window = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_adv_close)

    # ==================================================================
    # Dictionary loading
    # ==================================================================

    def _dict_display_name(self) -> str:
        if self._dict_path:
            return f"Dict: {os.path.basename(self._dict_path)}"
        return "Dict: none"

    def on_load_dict(self) -> None:
        path = askopenfilename(
            title="Select dictionary file",
            filetypes=[
                ("All supported", "*.json *.txt"),
                ("JSON dictionary", "*.json"),
                ("Text word list", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._dict_path = path
        if hasattr(self, "dict_label_var"):
            self.dict_label_var.set(self._dict_display_name())
        threading.Thread(
            target=self._load_wordlist_thread, args=(path,), daemon=True,
        ).start()

    def _load_wordlist_thread(self, dict_path: str) -> None:
        try:
            wordlist, from_cache = load_wordlist_from_dict(dict_path)
            with self._wordlist_lock:
                self.engine.set_wordlist(wordlist)
            word_count = len(wordlist)
            self.root.after(0, lambda: self.status_var.set(f"{word_count:,} words"))
        except Exception:
            self.root.after(0, lambda: self.status_var.set("Failed to load dictionary"))

    # ==================================================================
    # Trap endings / exceptions
    # ==================================================================

    def reload_trap_endings(self) -> None:
        from config.trap_endings import load_trap_endings, TRAP_ENDINGS_FILE, DEFAULT_TRAP_ENDINGS
        try:
            with open(TRAP_ENDINGS_FILE, "r") as f:
                endings = [line.strip().lower() for line in f
                           if line.strip() and not line.startswith("#")]
            if endings:
                endings = list(dict.fromkeys(endings))
                self.engine.set_trap_endings(endings)
                if hasattr(self, "trap_status_var"):
                    self.trap_status_var.set(f"{len(endings)} loaded")
            else:
                if hasattr(self, "trap_status_var"):
                    self.trap_status_var.set("File is empty — using defaults")
        except FileNotFoundError:
            save_trap_endings(DEFAULT_TRAP_ENDINGS)
            self.engine.set_trap_endings(DEFAULT_TRAP_ENDINGS)
            if hasattr(self, "trap_status_var"):
                self.trap_status_var.set(
                    f"Not found — created {len(DEFAULT_TRAP_ENDINGS)} defaults")
        except Exception as ex:
            if hasattr(self, "trap_status_var"):
                self.trap_status_var.set(f"Reload failed: {ex}")

    def reload_exceptions(self) -> None:
        exceptions = load_exceptions()
        self.engine.set_exceptions(exceptions)
        if hasattr(self, "exceptions_status_var"):
            self.exceptions_status_var.set(f"{len(exceptions)} loaded")

    def edit_trap_endings(self):
        from config.trap_endings import TRAP_ENDINGS_FILE
        self._open_file_editor(
            title="Edit Trap Endings", file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=self.trap_status_var,
            default_content="# Trap endings - one per line, hardest first\n",
        )

    def edit_exceptions(self):
        from config.exceptions import EXCEPTIONS_FILE
        self._open_file_editor(
            title="Edit Exceptions", file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            status_var=self.exceptions_status_var,
            default_content="# Word exceptions - one per line\n",
        )

    # ==================================================================
    # In-app file editor
    # ==================================================================

    def _open_file_editor(self, title, file_path, reload_callback,
                          status_var, default_content):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(True, True)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)

        f = tk.Frame(win, padx=12, pady=12, bg=C_BG)
        f.pack(fill="both", expand=True)

        text_widget = ScrolledText(
            f, font=("Consolas", 10), width=60, height=20,
            bg=C_ENTRY_BG, fg=C_TEXT, insertbackground=C_TEXT,
            undo=True, maxundo=-1,
        )
        text_widget.pack(fill="both", expand=True, pady=(0, 8))

        try:
            with open(file_path, "r", encoding="utf-8") as f_in:
                content = f_in.read()
        except FileNotFoundError:
            content = default_content
        text_widget.insert("1.0", content)

        def save_and_close(event=None):
            self._save_editor_content(
                win, text_widget, file_path, reload_callback, status_var)

        def cancel(event=None):
            win.destroy()

        text_widget.bind("<Control-s>", save_and_close)
        text_widget.bind("<Control-S>", save_and_close)
        text_widget.bind("<Escape>", cancel)

        btn_frame = tk.Frame(f, bg=C_BG)
        btn_frame.pack(fill="x")
        make_secondary_button(btn_frame, "Cancel", cancel).pack(side="right", padx=(4, 0))

        save_btn = tk.Button(
            btn_frame, text="Save", command=save_and_close,
            font=("Segoe UI", 8), bg=C_PLAY_BG, fg=C_PLAY_FG,
            activebackground=C_PLAY_ACT, relief="flat", bd=0,
            padx=10, pady=3, cursor="hand2",
        )
        save_btn.pack(side="right")

        self._center_window(win)
        text_widget.focus_set()

    def _save_editor_content(self, win, text_widget, file_path,
                             reload_callback, status_var):
        content = text_widget.get("1.0", tk.END).strip()
        try:
            with open(file_path, "w", encoding="utf-8") as f_out:
                f_out.write(content)
                if content and not content.endswith("\n"):
                    f_out.write("\n")
            reload_callback()
            if "trap" in file_path:
                count = len(self.engine.trap_endings)
            else:
                count = len(self.engine.word_exceptions)
            status_var.set(f"{count} loaded")
            win.destroy()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Save Failed", f"Could not save file:\n{e}")

    # ==================================================================
    # Roblox
    # ==================================================================

    def _poll_roblox(self) -> None:
        running = is_roblox_running()
        self._update_roblox_indicator(running)
        self.root.after(3000, self._poll_roblox)

    def _update_roblox_indicator(self, running: bool) -> None:
        color = C_DOT_GREEN if running else C_DOT_RED
        text = "Roblox: on" if running else "Roblox: off"
        self.roblox_status_label.config(fg=color)
        self.roblox_status_var.set(text)

    # ==================================================================
    # Play round — the core game action
    # ==================================================================

    def on_play_round(self) -> None:
        with self._playing_lock:
            if self._is_playing:
                return

            prefix = self.prefix_var.get().strip()
            if not prefix:
                self._flash_error("#FFD700")
                return

            if not self.engine.wordlist:
                return

            completion = self.engine.find_completion(
                prefix, self.mode_var.get(), self.fallback_var.get())
            if completion is None:
                self._flash_error("#FF4444")
                return

            self._is_playing = True

        self.root.withdraw()
        self.prefix_var.set("")

        if is_roblox_running():
            focus_roblox_window()
            self._update_roblox_indicator(True)
        else:
            self._update_roblox_indicator(False)

        # Sync typer settings from UI
        self.typer.base_speed_ms = self.speed_var.get()
        self.typer.jitter_on = self.jitter_enabled.get()
        self.typer.jitter_sigma_ms = self.jitter_intensity.get()

        pre = max(0.1, self.pre_delay_var.get() / 1000.0)
        post = max(0.1, self.post_delay_var.get() / 1000.0)

        threading.Thread(
            target=self._type_and_return,
            args=(completion, pre, post),
            daemon=True,
        ).start()

    def on_ctrl_enter(self, event):
        self.on_play_round()
        return "break"

    def _type_and_return(self, completion: str, pre: float, post: float) -> None:
        try:
            success, message = self.typer.type_text(completion, pre_delay_s=pre, post_delay_s=post)
            if not success:
                print(f"[WARNING] Typing failed: {message}")
                self.root.after(0, lambda: self.status_var.set(f"Typing failed: {message}"))
        finally:
            with self._playing_lock:
                self._is_playing = False
            self.root.after(0, self.root.deiconify)
            if self._used_words_window_alive():
                self.root.after(0, self.update_used_words_list)

    # ==================================================================
    # Used words window
    # ==================================================================

    def _used_words_window_alive(self) -> bool:
        try:
            return (self.used_words_window is not None
                    and self.used_words_window.winfo_exists())
        except tk.TclError:
            return False

    def show_used_words(self) -> None:
        if not self._used_words_window_alive():
            self.used_words_window = tk.Toplevel(self.root)
            self.used_words_window.title("Used Words")
            self.used_words_window.resizable(True, True)
            self.used_words_window.attributes("-topmost", True)
            self.used_words_window.configure(bg=C_BG)

            outer = tk.Frame(self.used_words_window, bg=C_BG, padx=8, pady=8)
            outer.pack(fill="both", expand=True)

            list_frame = tk.Frame(outer, bg=C_BG_PANEL, padx=1, pady=1)
            list_frame.pack(fill="both", expand=True)

            scrollbar = tk.ttk.Scrollbar(list_frame)
            scrollbar.pack(side="right", fill="y")

            self.used_words_listbox = tk.Listbox(
                list_frame, yscrollcommand=scrollbar.set,
                font=("Consolas", 10), width=28, height=15,
                bg=C_ENTRY_BG, fg=C_TEXT,
                selectbackground=C_PLAY_BG, selectforeground=C_PLAY_FG,
                borderwidth=0, highlightthickness=0, relief="flat",
            )
            self.used_words_listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=self.used_words_listbox.yview)

            self.used_words_count = tk.Label(
                outer, text=f"{len(self.engine.used_words)} words used",
                anchor="w", font=("Segoe UI", 8), bg=C_BG, fg=C_MUTED,
            )
            self.used_words_count.pack(fill="x", pady=(6, 4))

            make_secondary_button(outer, "Close", self._close_used_words).pack()

            self._center_window(self.used_words_window)
            self.used_words_window.protocol("WM_DELETE_WINDOW", self._close_used_words)

        self.update_used_words_list()
        self.used_words_window.lift()
        self.used_words_window.focus_force()

    def _close_used_words(self) -> None:
        self.used_words_window.destroy()
        self.used_words_window = None

    def on_clear_cache(self) -> None:
        self.engine.clear_used_words()
        if self._used_words_window_alive():
            self.update_used_words_list()

    def update_used_words_list(self) -> None:
        if self._used_words_window_alive():
            self.used_words_listbox.delete(0, tk.END)
            for word in sorted(self.engine.used_words, key=str.lower):
                self.used_words_listbox.insert(tk.END, word)
            self.used_words_count.config(
                text=f"{len(self.engine.used_words)} words used")

    # ==================================================================
    # UI helpers
    # ==================================================================

    def _flash_error(self, color: str, duration_ms: int = 800) -> None:
        if self._flash_after_id is not None:
            self.root.after_cancel(self._flash_after_id)
            self._flash_after_id = None
        self.entry.config(highlightbackground=color, highlightthickness=2)
        winsound.MessageBeep(winsound.MB_ICONHAND)

        def _restore():
            focused = self.root.focus_get() == self.entry
            self.entry.config(
                highlightbackground=C_ENTRY_FOCUS if focused else C_ENTRY_BD,
                highlightthickness=2 if focused else 1,
            )
            self._flash_after_id = None

        self._flash_after_id = self.root.after(duration_ms, _restore)

    def _on_jitter_toggle(self) -> None:
        state = "normal" if self.jitter_enabled.get() else "disabled"
        enabled = self.jitter_enabled.get()
        self.jitter_slider.config(state=state)
        self.jitter_label.config(fg=C_TEXT if enabled else C_MUTED)
        self.jitter_intensity_val.config(fg=C_TEXT if enabled else C_MUTED)

    def _center_window(self, win: tk.Toplevel) -> None:
        """Center a Toplevel window on screen."""
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"+{x}+{y}")

    # ==================================================================
    # About
    # ==================================================================

    def show_about(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("About")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=C_BG)

        f = tk.Frame(win, bg=C_BG, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        title_row = tk.Frame(f, bg=C_BG)
        title_row.pack(anchor="w", fill="x")
        tk.Label(title_row, text="Letter Demon", font=("Segoe UI", 13, "bold"),
                 bg=C_BG, fg=C_TEXT).pack(side="left")
        tk.Label(title_row, text="v6 \u2022 April 2026", font=("Segoe UI", 7),
                 bg=C_BG, fg=C_MUTED).pack(side="left", padx=(6, 0))

        tk.Label(f, text="Last Letter word game assistant.",
                 font=("Segoe UI", 8), bg=C_BG, fg=C_MUTED
                 ).pack(anchor="w", pady=(2, 12))

        # Separator — use pack to match the rest of this frame's layout
        sep = tk.Frame(f, height=1, bg=C_SEP)
        sep.pack(fill="x", pady=(0, 12))

        tk.Label(f, text="Made by n6ufal", font=("Segoe UI", 8),
                 bg=C_BG, fg=C_TEXT).pack(anchor="w")
        tk.Label(f, text="Discord: b6xy", font=("Segoe UI", 8),
                 bg=C_BG, fg=C_TEXT).pack(anchor="w", pady=(2, 0))
        tk.Label(f, text="Email: boxcarr@proton.me", font=("Segoe UI", 8),
                 bg=C_BG, fg=C_TEXT).pack(anchor="w", pady=(2, 0))

        self._center_window(win)

    # ==================================================================
    # Quit
    # ==================================================================

    def on_quit(self) -> None:
        save_settings({
            "dict_path":        self._dict_path,
            "speed":            self.speed_var.get(),
            "mode":             self.mode_var.get(),
            "fallback":         self.fallback_var.get(),
            "pre_delay":        self.pre_delay_var.get(),
            "post_delay":       self.post_delay_var.get(),
            "jitter_enabled":   self.jitter_enabled.get(),
            "jitter_intensity": self.jitter_intensity.get(),
            "timing_expanded":  self.timing_expanded.get(),
            "win_x":            self.root.winfo_x(),
            "win_y":            self.root.winfo_y(),
        })
        import keyboard
        keyboard.unhook_all()
        self.root.destroy()
