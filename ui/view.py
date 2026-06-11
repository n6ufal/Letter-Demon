"""Main window view — owns all widgets and tkinter state."""

import sys
import tkinter as tk
from pathlib import Path

from . import modes
from .theme import (
    C_BG,
    C_BG_PANEL,
    C_DOT_GREEN,
    C_DOT_RED,
    C_ENTRY_BD,
    C_ENTRY_BG,
    C_ENTRY_FOCUS,
    C_FEEDBACK_ERR_BG,
    C_FEEDBACK_ERR_FG,
    C_FEEDBACK_WARN_BG,
    C_FEEDBACK_WARN_FG,
    C_MUTED,
    C_PLAY_ACT,
    C_PLAY_BG,
    C_PLAY_FG,
    C_TEXT,
    FONT_BTN,
    FONT_MAIN,
    FONT_MAIN_BOLD,
    FONT_SMALL,
    FONT_TITLE,
)
from .widgets import (
    make_secondary_button,
    make_separator,
    make_slider,
    setup_ttk_styles,
    add_tooltip,
)

if sys.platform == "win32":
    import winsound

    _SOUND_ERROR = str(Path(__file__).parent / "error.wav")
else:
    winsound = None
    _SOUND_ERROR = None


class MainView:
    """Owns all main-window widgets and tkinter variables.

    Controller (LetterDemonApp) constructs one, then reads/writes state
    through properties and update methods.  Widget bindings call back
    into the controller.
    """

    def __init__(
        self, root: tk.Tk, controller, window_title: str, settings: dict
    ) -> None:
        self.root = root
        self._controller = controller
        self._window_title = window_title
        self._feedback_after_id = None

        self._build(settings)
        self._wire_tooltips()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self, settings: dict) -> None:
        setup_ttk_styles()
        self.root.configure(bg=C_BG)

        self.main_frame = tk.Frame(self.root, padx=12, pady=10, bg=C_BG)
        self.main_frame.pack(fill="both", expand=True)

        self._build_header()
        self._build_entry()
        self._build_feedback()
        self._build_info_bar()
        self._build_play_button()
        self._build_sliders(settings)
        self._build_combos(settings)
        self._build_separator()
        self._build_action_buttons()
        self._build_credit()
        self._build_shared_vars(settings)

        for col in range(4):
            self.main_frame.grid_columnconfigure(col, weight=1)

    def _build_header(self) -> None:
        header = tk.Frame(self.main_frame, bg=C_BG)
        header.grid(row=0, column=0, columnspan=4, sticky="we", pady=(0, 2))
        tk.Label(
            header,
            text="Starting letters:",
            anchor="w",
            font=FONT_MAIN_BOLD,
            bg=C_BG,
            fg=C_TEXT,
        ).pack(side="left")

    def _build_entry(self) -> None:
        validate = self.root.register(lambda v: v == "" or v.isalpha())
        self._prefix_var = tk.StringVar()
        self.entry = tk.Entry(
            self.main_frame,
            textvariable=self._prefix_var,
            font=FONT_TITLE,
            width=18,
            bg=C_ENTRY_BG,
            fg=C_TEXT,
            insertbackground=C_TEXT,
            selectbackground=C_ENTRY_FOCUS,
            selectforeground=C_PLAY_FG,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=C_ENTRY_BD,
            highlightcolor=C_ENTRY_FOCUS,
            validate="key",
            validatecommand=(validate, "%P"),
        )
        self.entry.grid(
            row=1, column=0, columnspan=4, sticky="we", ipady=6, ipadx=8, pady=(0, 6)
        )
        self.entry.bind(
            "<FocusIn>",
            lambda e: self.entry.config(
                highlightbackground=C_ENTRY_FOCUS, highlightthickness=2
            ),
        )
        self.entry.bind(
            "<FocusOut>",
            lambda e: self.entry.config(
                highlightbackground=C_ENTRY_BD, highlightthickness=1
            ),
        )

    def _build_feedback(self) -> None:
        self.feedback_frame = tk.Frame(self.main_frame, bg=C_BG)
        self.feedback_label = tk.Label(
            self.feedback_frame,
            text="",
            anchor="w",
            justify="left",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_BG,
            padx=8,
            pady=5,
        )
        self.feedback_label.pack(fill="x")
        self.feedback_frame.grid(
            row=2, column=0, columnspan=4, sticky="we", pady=(0, 4)
        )
        self.feedback_frame.grid_remove()

    def _build_info_bar(self) -> None:
        bar = tk.Frame(self.main_frame, bg=C_BG)
        bar.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 4))
        for col in range(3):
            bar.grid_columnconfigure(col, weight=1)

        self._status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            bar,
            textvariable=self._status_var,
            fg=C_TEXT,
            anchor="w",
            font=FONT_MAIN,
            bg=C_BG,
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self._auto_prefix_var = tk.StringVar(value="")
        self.auto_prefix_label = tk.Label(
            bar,
            textvariable=self._auto_prefix_var,
            fg=C_DOT_GREEN,
            font=FONT_MAIN,
            bg=C_BG,
        )
        self.auto_prefix_label.grid(row=0, column=1)

        self._roblox_status_var = tk.StringVar(value="Roblox")
        self.roblox_status_label = tk.Label(
            bar,
            textvariable=self._roblox_status_var,
            fg=C_DOT_RED,
            anchor="e",
            font=FONT_MAIN,
            bg=C_BG,
        )
        self.roblox_status_label.grid(row=0, column=2, sticky="e")

    def _build_play_button(self) -> None:
        self.play_btn = tk.Button(
            self.main_frame,
            text="Click to load a dictionary",
            command=self._controller.on_load_dict,
            font=FONT_BTN,
            pady=6,
            bg=C_BG_PANEL,
            fg=C_DOT_RED,
            activebackground="#ddd",
            activeforeground="#c0392b",
            relief="flat",
            bd=0,
            cursor="hand2",
        )
        self.play_btn.grid(row=4, column=0, columnspan=4, sticky="we", pady=(4, 8))

    def _build_sliders(self, settings: dict) -> None:
        panel = tk.Frame(self.main_frame, bg=C_BG)
        panel.grid(row=5, column=0, columnspan=4, sticky="we", pady=(0, 6))
        panel.grid_columnconfigure(0, weight=1)

        speed_frame = tk.Frame(panel, bg=C_BG)
        speed_frame.grid(row=0, column=0, sticky="we")
        speed_frame.columnconfigure(1, weight=1)
        tk.Label(
            speed_frame,
            text="Speed:",
            anchor="e",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_TEXT,
            width=12,
        ).grid(row=0, column=0, sticky="e", padx=(0, 8))
        self._speed_var = tk.DoubleVar(value=settings.get("speed", 170.0))
        self.speed_slider, self.speed_val_label = make_slider(
            speed_frame,
            "Speed",
            self._speed_var,
            from_=10,
            to=250,
            resolution=5,
            length=160,
            suffix="",
        )
        self.speed_slider.grid(row=0, column=1, sticky="ew", pady=(0, 2))
        self.speed_val_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

        humanizer_frame = tk.Frame(panel, bg=C_BG)
        humanizer_frame.grid(row=1, column=0, sticky="we", pady=(4, 0))
        humanizer_frame.columnconfigure(1, weight=1)
        tk.Label(
            humanizer_frame,
            text="Humanizer:",
            anchor="e",
            font=FONT_MAIN,
            bg=C_BG,
            fg=C_TEXT,
            width=12,
        ).grid(row=0, column=0, sticky="e", padx=(0, 8))
        self._jitter_var = tk.IntVar(value=settings.get("jitter_intensity", 75))
        self.humanizer_slider, self.humanizer_val_label = make_slider(
            humanizer_frame,
            "Humanizer",
            self._jitter_var,
            from_=0,
            to=100,
            resolution=5,
            length=160,
            suffix="%",
        )
        self.humanizer_slider.grid(row=0, column=1, sticky="ew", pady=(0, 2))
        self.humanizer_val_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

    def _build_combos(self, settings: dict) -> None:
        combo_row = tk.Frame(self.main_frame, bg=C_BG)
        combo_row.grid(row=6, column=0, columnspan=4, sticky="we", pady=(0, 4))

        self._mode_var = tk.StringVar(
            value=modes.to_display_mode(settings.get("mode", "Trap Words"))
        )
        tk.Label(combo_row, text="Mode:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT).pack(
            side="left", padx=(0, 8)
        )
        self.mode_combobox = tk.ttk.Combobox(
            combo_row,
            textvariable=self._mode_var,
            values=modes.MODE_DISPLAY,
            state="readonly",
            width=8,
        )
        self.mode_combobox.pack(side="left", padx=(0, 12))

        self._fallback_var = tk.StringVar(
            value=modes.to_display_fallback(settings.get("fallback", "Short Words"))
        )
        tk.Label(
            combo_row, text="Fallback:", font=FONT_MAIN, bg=C_BG, fg=C_TEXT
        ).pack(side="left", padx=(0, 8))
        self.fallback_combobox = tk.ttk.Combobox(
            combo_row,
            textvariable=self._fallback_var,
            values=modes.FALLBACK_DISPLAY,
            state="readonly",
            width=8,
        )
        self.fallback_combobox.pack(side="left")

    def _build_separator(self) -> None:
        make_separator(
            self.main_frame, 7, column=0, columnspan=4, sticky="we", pady=(4, 6)
        )

    def _build_action_buttons(self) -> None:
        btn_row = tk.Frame(self.main_frame, bg=C_BG)
        btn_row.grid(row=8, column=0, columnspan=4, sticky="we", pady=(0, 2))
        for col in range(3):
            btn_row.grid_columnconfigure(col, weight=1)

        self.advanced_btn = make_secondary_button(
            btn_row,
            "Advanced",
            self._controller.show_advanced,
            row=0,
            column=0,
            sticky="we",
            padx=2,
            pady=(0, 2),
        )
        self.clear_used_btn = make_secondary_button(
            btn_row,
            "Clear Used",
            self._controller.on_clear_used_words,
            row=0,
            column=1,
            sticky="we",
            padx=2,
            pady=(0, 2),
        )
        self.used_words_btn = make_secondary_button(
            btn_row,
            "Used Words",
            self._controller.show_used_words,
            row=0,
            column=2,
            sticky="we",
            padx=2,
            pady=(0, 2),
        )

    def _build_credit(self) -> None:
        credit = tk.Label(
            self.main_frame,
            text="Made by n6ufal",
            fg=C_MUTED,
            font=FONT_SMALL,
            bg=C_BG,
            cursor="hand2",
        )
        credit.grid(row=9, column=0, columnspan=4, sticky="e", pady=(2, 0))
        credit.bind("<Button-1>", lambda e: self._controller.show_about())
        credit.bind("<Enter>", lambda e: credit.config(fg=C_TEXT))
        credit.bind("<Leave>", lambda e: credit.config(fg=C_MUTED))

    def _build_shared_vars(self, settings: dict) -> None:
        self._pre_delay_var = tk.IntVar(value=settings.get("pre_delay", 500))
        self._post_delay_var = tk.IntVar(value=settings.get("post_delay", 500))
        self._auto_type_prefix_var = tk.StringVar(
            value="On" if settings.get("auto_type_prefix", True) else "Off"
        )
        self._trap_status_var = tk.StringVar()
        self._exceptions_status_var = tk.StringVar()
        self._dict_label_var = tk.StringVar()
        self._auto_type_prefix_var.trace_add(
            "write", lambda *_: self._update_auto_prefix_indicator()
        )

    def _wire_tooltips(self) -> None:
        add_tooltip(
            self.auto_prefix_label,
            "Suffix: types only the ending / Full: types the complete word",
        )
        add_tooltip(
            self.roblox_status_label,
            f"Green: {self._window_title} running / "
            f"Red: {self._window_title} not found",
        )
        self._play_btn_tip = add_tooltip(
            self.play_btn, "No dictionary — click to load one", delay_ms=200
        )
        add_tooltip(
            self.speed_slider,
            "Average keystroke delay in ms (actual delays vary around this)",
        )
        add_tooltip(
            self.humanizer_slider, "Human-like timing variation (0 = robotic)"
        )
        add_tooltip(self.mode_combobox, "Primary strategy for picking the word")
        add_tooltip(
            self.fallback_combobox, "Backup strategy when primary mode finds nothing"
        )
        add_tooltip(self.advanced_btn, "Dictionary, timing, trap endings, exceptions")
        add_tooltip(self.clear_used_btn, "Reset used words for a new game")
        add_tooltip(self.used_words_btn, "Show words played this session")

    # ------------------------------------------------------------------
    # Controller-facing properties (read)
    # ------------------------------------------------------------------

    @property
    def prefix(self) -> str:
        return self._prefix_var.get().strip()

    @property
    def mode(self) -> str:
        return self._mode_var.get()

    @property
    def fallback(self) -> str:
        return self._fallback_var.get()

    @property
    def speed_ms(self) -> float:
        return self._speed_var.get()

    @property
    def jitter_intensity(self) -> int:
        return self._jitter_var.get()

    @property
    def pre_delay_ms(self) -> int:
        return self._pre_delay_var.get()

    @property
    def post_delay_ms(self) -> int:
        return self._post_delay_var.get()

    @property
    def auto_type_prefix_enabled(self) -> bool:
        return self._auto_type_prefix_var.get() == "On"

    # Shared tkinter vars for dialogs (IntVar / StringVar objects)
    @property
    def pre_delay_var(self) -> tk.IntVar:
        return self._pre_delay_var

    @property
    def post_delay_var(self) -> tk.IntVar:
        return self._post_delay_var

    @property
    def auto_type_prefix_var(self) -> tk.StringVar:
        return self._auto_type_prefix_var

    @property
    def trap_status_var(self) -> tk.StringVar:
        return self._trap_status_var

    @property
    def exceptions_status_var(self) -> tk.StringVar:
        return self._exceptions_status_var

    @property
    def dict_label_var(self) -> tk.StringVar:
        return self._dict_label_var

    # ------------------------------------------------------------------
    # Update methods (called by controller)
    # ------------------------------------------------------------------

    def update_play_button(self, has_wordlist: bool) -> None:
        self.play_btn.unbind("<Enter>")
        self.play_btn.unbind("<Leave>")
        if not has_wordlist:
            self.play_btn.config(
                text="Click to load a dictionary",
                command=self._controller.on_load_dict,
                state=tk.NORMAL,
                fg=C_DOT_RED,
                bg=C_BG_PANEL,
                activeforeground="#c0392b",
                activebackground="#ddd",
            )
            self._status_var.set("")
            self.status_label.config(fg=C_MUTED, cursor="")
            self._play_btn_tip.text = "No dictionary — click to load one"
        else:
            self.play_btn.bind(
                "<Enter>", lambda e: self.play_btn.config(bg=C_PLAY_ACT)
            )
            self.play_btn.bind(
                "<Leave>", lambda e: self.play_btn.config(bg=C_PLAY_BG)
            )
            self.play_btn.config(
                text="Start (Ctrl+Enter)",
                command=self._controller.on_play_round,
                state=tk.NORMAL,
                fg=C_PLAY_FG,
                bg=C_PLAY_BG,
                activebackground=C_PLAY_ACT,
                activeforeground=C_PLAY_FG,
            )
            self._play_btn_tip.text = "Type the word into Roblox (Ctrl+Enter)"

    def set_loading_state(self) -> None:
        self.play_btn.config(text="Loading...", state=tk.DISABLED)

    def set_status(self, text: str) -> None:
        self._status_var.set(text)

    def clear_prefix(self) -> None:
        self._prefix_var.set("")

    def show_feedback(
        self,
        level: str,
        message: str,
        *,
        duration_ms: int = 5000,
        beep: bool = False,
    ) -> None:
        if self._feedback_after_id is not None:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None

        if level == "warn":
            bg, fg = C_FEEDBACK_WARN_BG, C_FEEDBACK_WARN_FG
        else:
            bg, fg = C_FEEDBACK_ERR_BG, C_FEEDBACK_ERR_FG

        self.feedback_frame.config(bg=bg)
        self.feedback_label.config(text=message, bg=bg, fg=fg)
        self.feedback_frame.grid(
            row=2, column=0, columnspan=4, sticky="we", pady=(0, 4)
        )
        self.feedback_frame.update_idletasks()
        self.feedback_label.config(
            wraplength=max(200, self.feedback_frame.winfo_width() - 16)
        )

        if beep and winsound:
            try:
                winsound.PlaySound(
                    _SOUND_ERROR,
                    winsound.SND_ASYNC | winsound.SND_NOSTOP | winsound.SND_FILENAME,
                )
            except Exception:
                winsound.Beep(800, 100)

        self._feedback_after_id = self.root.after(
            duration_ms, self._clear_feedback
        )

    def dismiss_feedback(self) -> None:
        if self._feedback_after_id is not None:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None
        self._clear_feedback()

    def _clear_feedback(self) -> None:
        self._feedback_after_id = None
        try:
            self.feedback_label.config(text="", bg=C_BG, fg=C_BG)
            self.feedback_frame.config(bg=C_BG)
            self.feedback_frame.grid_remove()
        except tk.TclError:
            pass

    def set_roblox_indicator(self, running: bool) -> None:
        self.roblox_status_label.config(
            fg=C_DOT_GREEN if running else C_DOT_RED
        )
        self._roblox_status_var.set(self._window_title)

    def _update_auto_prefix_indicator(self) -> None:
        text = "Suffix" if self._auto_type_prefix_var.get() == "On" else "Full"
        self._auto_prefix_var.set(text)
        self.auto_prefix_label.config(fg=C_DOT_GREEN)

    def update_dict_label(self, path: str | None) -> None:
        if path:
            self._dict_label_var.set(f"Dict: {Path(path).name}")
        else:
            self._dict_label_var.set("Dict: none")

    def set_trap_status(self, text: str) -> None:
        self._trap_status_var.set(text)

    def set_exceptions_status(self, text: str) -> None:
        self._exceptions_status_var.set(text)
