"""Main application window — wires UI modules to engines."""

import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)
if sys.platform == "win32":
    import winsound
    SOUND_ERROR = str(Path(__file__).parent / "error.wav")
else:
    winsound = None
    SOUND_ERROR = None

import tkinter as tk
from tkinter.filedialog import askopenfilename

from core.session import AppSession
from config.trap_endings import TRAP_ENDINGS_FILE
from config.exceptions import EXCEPTIONS_FILE
from system.roblox import is_roblox_running, focus_roblox_window

from . import dialogs
from . import file_editors
from . import modes
from .main_layout import build_main_layout
from .theme import (
    C_BG,
    C_BG_PANEL,
    C_DOT_GREEN,
    C_DOT_RED,
    C_FEEDBACK_ERR_BG,
    C_FEEDBACK_ERR_FG,
    C_FEEDBACK_WARN_BG,
    C_FEEDBACK_WARN_FG,
    C_MUTED,
    C_PLAY_ACT,
    C_PLAY_BG,
    C_PLAY_FG,
)


class LetterDemonApp:
    def __init__(self, root: tk.Tk, session: AppSession | None = None) -> None:
        self.session = session or AppSession()
        self.root = root
        self.root.title("😈")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self._used_words_window_open = False
        self._feedback_after_id = None
        self._poll_id = None
        self._advanced_window = None
        self.used_words_window = None

        s = self.session.settings

        self.prefix_var = tk.StringVar()
        self._validate_prefix_cmd = root.register(lambda v: v == "" or v.isalpha())
        self.mode_var = tk.StringVar(value=modes.to_display_mode(s.get("mode", "Trap Words")))
        self.fallback_var = tk.StringVar(value=modes.to_display_fallback(s.get("fallback", "Short Words")))
        self.jitter_intensity = tk.IntVar(value=s.get("jitter_intensity", 75))
        self.pre_delay_var = tk.IntVar(value=s.get("pre_delay", 500))
        self.post_delay_var = tk.IntVar(value=s.get("post_delay", 500))
        self.auto_type_prefix = tk.StringVar(value="On" if s.get("auto_type_prefix", True) else "Off")

        self.root.configure(bg=C_BG)
        self.main_frame = tk.Frame(self.root, padx=12, pady=10, bg=C_BG)
        self.main_frame.pack(fill="both", expand=True)

        build_main_layout(self, dict(s.as_dict()))
        self._update_auto_prefix_indicator()
        self.auto_type_prefix.trace_add("write", lambda *_: self._update_auto_prefix_indicator())

        win_x = s.get("win_x")
        win_y = s.get("win_y")
        if win_x is not None and win_y is not None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if -50 <= win_x < sw - 100 and -50 <= win_y < sh - 50:
                self.root.geometry(f"+{win_x}+{win_y}")

        self.root.bind("<FocusIn>", self._on_root_focus_in)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.entry.bind("<Control-Return>", self.on_ctrl_enter)

        self._poll_roblox()

        dict_path = self.session.try_load_dict_at_startup()
        if dict_path:
            if hasattr(self, "play_btn") and self.play_btn.winfo_exists():
                self.play_btn.config(text="Loading...", state=tk.DISABLED)
            threading.Thread(
                target=self._load_wordlist_thread,
                args=(dict_path,),
                daemon=True,
            ).start()
        else:
            self.status_var.set("")
            self._update_start_button()

    def _on_root_focus_in(self, event: tk.Event) -> None:
        self.root.after_idle(self._maybe_focus_prefix_entry)

    def _maybe_focus_prefix_entry(self) -> None:
        if not self.root.winfo_viewable():
            return
        try:
            w = self.root.focus_get()
        except tk.TclError:
            return
        if w is not None:
            try:
                top = w.winfo_toplevel()
            except tk.TclError:
                return
            if top is not self.root:
                return
        try:
            self.entry.focus_set()
        except tk.TclError:
            pass

    def _update_start_button(self) -> None:
        if not hasattr(self, "play_btn") or not self.play_btn.winfo_exists():
            return
        self.play_btn.unbind("<Enter>")
        self.play_btn.unbind("<Leave>")
        self.status_label.unbind("<Button-1>")
        self.status_label.unbind("<Enter>")
        self.status_label.unbind("<Leave>")
        if not self.session.has_wordlist():
            self.play_btn.config(
                text="Click to load a dictionary",
                command=self.on_load_dict,
                state=tk.NORMAL,
                fg=C_DOT_RED,
                bg=C_BG_PANEL,
                activeforeground="#c0392b",
                activebackground="#ddd",
            )
            self.status_var.set("")
            self.status_label.config(fg=C_MUTED, cursor="")
            if hasattr(self, "play_btn_tip"):
                self.play_btn_tip.text = "No dictionary — click to load one"
        else:
            self.play_btn.bind("<Enter>", lambda e: self.play_btn.config(bg=C_PLAY_ACT))
            self.play_btn.bind("<Leave>", lambda e: self.play_btn.config(bg=C_PLAY_BG))
            self.play_btn.config(
                text="Start (Ctrl+Enter)",
                command=self.on_play_round,
                state=tk.NORMAL,
                fg=C_PLAY_FG,
                bg=C_PLAY_BG,
                activebackground=C_PLAY_ACT,
                activeforeground=C_PLAY_FG,
            )
            if hasattr(self, "play_btn_tip"):
                self.play_btn_tip.text = "Type the word into Roblox (Ctrl+Enter)"

    def show_advanced(self) -> None:
        dialogs.show_advanced(self)

    def _dict_display_name(self) -> str:
        if self.session.dict_path:
            return f"Dict: {Path(self.session.dict_path).name}"
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
        self.session.dict_path = path
        if hasattr(self, "play_btn") and self.play_btn.winfo_exists():
            self.play_btn.config(text="Loading...", state=tk.DISABLED)
        if hasattr(self, "dict_label_var"):
            self.dict_label_var.set(self._dict_display_name())
        threading.Thread(
            target=self._load_wordlist_thread, args=(path,), daemon=True,
        ).start()

    def _load_wordlist_thread(self, dict_path: str) -> None:
        try:
            wordlist, from_cache = self.session.load_dictionary(dict_path)
            word_count = len(wordlist)
            self.root.after(0, lambda: self.status_var.set(f"{word_count:,} words"))
            self.root.after(0, self._update_start_button)
        except Exception:
            def _on_load_fail() -> None:
                self.notify("error", "Could not load dictionary.", duration_ms=6000)
                self.status_var.set("")
                self._update_start_button()

            self.root.after(0, _on_load_fail)

    def reload_trap_endings(self) -> None:
        self.session.reload_trap_endings()
        if hasattr(self, "trap_status_var"):
            self.trap_status_var.set(f"{len(self.session.engine.trap_endings)} loaded")

    def reload_exceptions(self) -> None:
        self.session.reload_exceptions()
        if hasattr(self, "exceptions_status_var"):
            self.exceptions_status_var.set(f"{len(self.session.engine.word_exceptions)} loaded")

    def edit_trap_endings(self):
        file_editors.open_file_editor(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=self.trap_status_var,
            default_content="# Trap endings - one per line, hardest first\n",
        )

    def edit_exceptions(self):
        file_editors.open_file_editor(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            status_var=self.exceptions_status_var,
            default_content="# Word exceptions - one per line\n",
        )

    def _poll_roblox(self) -> None:
        running = is_roblox_running(self.session.window_title)
        self._update_roblox_indicator(running)
        self._poll_id = self.root.after(15000, self._poll_roblox)

    def _update_auto_prefix_indicator(self) -> None:
        if not hasattr(self, "auto_prefix_label"):
            return
        self.auto_prefix_var.set("Suffix" if self.auto_type_prefix.get() == "On" else "Full")
        self.auto_prefix_label.config(fg=C_DOT_GREEN)

    def _update_roblox_indicator(self, running: bool) -> None:
        self.roblox_status_label.config(fg=C_DOT_GREEN if running else C_DOT_RED)
        self.roblox_status_var.set(self.session.window_title)

    def on_play_round(self) -> None:
        prefix = self.prefix_var.get().strip()
        if not prefix:
            self.notify("warn", "Enter starting letters first.", beep=True)
            return

        if not self.session.has_wordlist():
            self.notify(
                "error",
                "Load a dictionary first (Advanced → Load Dictionary).",
                beep=True,
            )
            return

        word_to_type = self.session.prepare_play_round(
            prefix,
            modes.to_internal_mode(self.mode_var.get()),
            modes.to_internal_fallback(self.fallback_var.get()),
            self.auto_type_prefix.get() == "On",
        )
        if word_to_type is None:
            self.notify("error", "No matching word found.", beep=True)
            return

        try:
            self.root.withdraw()
            self.prefix_var.set("")

            if is_roblox_running(self.session.window_title):
                focus_roblox_window(self.session.window_title)
                self._update_roblox_indicator(True)
            else:
                self._update_roblox_indicator(False)

            self.session.configure_typer(
                speed_ms=self.speed_var.get(),
                jitter_intensity=self.jitter_intensity.get(),
                pre_delay_s=self.pre_delay_var.get() / 1000.0,
                post_delay_s=self.post_delay_var.get() / 1000.0,
            )
        except Exception:
            self.session.finish_play_round()
            self.notify("error", "Failed to prepare for typing.", duration_ms=6000)
            logger.exception("Failed to prepare for typing")
            return

        try:
            threading.Thread(
                target=self._type_and_return,
                args=(word_to_type,),
                daemon=True,
            ).start()
        except Exception:
            self.session.finish_play_round()
            self.root.deiconify()
            self.notify("error", "Failed to start typing thread.", duration_ms=6000)
            logger.exception("Thread creation failed")

    def on_ctrl_enter(self, event):
        if not self.session.has_wordlist():
            self.on_load_dict()
        else:
            self.on_play_round()
        return "break"

    def _type_and_return(self, completion: str) -> None:
        try:
            success, message = self.session.typer.type_text(
                completion,
                pre_delay_s=self.session.pre_delay,
                post_delay_s=self.session.post_delay,
            )
            if not success:
                logger.warning("Typing failed: %s", message)
                self.root.after(
                    0,
                    lambda m=message: self._try_tcl(
                        self.notify, "error",
                        f"Typing failed: {m}",
                        duration_ms=8000,
                    ),
                )
        finally:
            self.session.finish_play_round()
            self.root.after(0, lambda: self._try_tcl(self.root.deiconify))
            if self._used_words_window_open:
                self.root.after(
                    0, lambda: self._try_tcl(dialogs.update_used_words_list, self)
                )

    def show_used_words(self) -> None:
        dialogs.show_used_words(self)

    def on_clear_used_words(self) -> None:
        self.session.clear_used_words()
        if dialogs.used_words_window_alive(self):
            dialogs.update_used_words_list(self)

    def _try_tcl(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except tk.TclError:
            pass

    def notify(
        self,
        level: str,
        message: str,
        *,
        duration_ms: int = 5000,
        beep: bool = False,
    ) -> None:
        """Non-modal message under the prefix field (no pop-up dialogs)."""
        if self._feedback_after_id is not None:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None

        if level == "warn":
            bg, fg = C_FEEDBACK_WARN_BG, C_FEEDBACK_WARN_FG
        else:
            bg, fg = C_FEEDBACK_ERR_BG, C_FEEDBACK_ERR_FG

        self.feedback_frame.config(bg=bg)
        self.feedback_label.config(text=message, bg=bg, fg=fg)
        self.feedback_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(0, 4))
        self.feedback_frame.update_idletasks()
        self.feedback_label.config(
            wraplength=max(200, self.feedback_frame.winfo_width() - 16)
        )

        if beep and winsound:
            try:
                winsound.PlaySound(
                    SOUND_ERROR,
                    winsound.SND_ASYNC | winsound.SND_NOSTOP | winsound.SND_FILENAME,
                )
            except Exception:
                winsound.Beep(800, 100)

        self._feedback_after_id = self.root.after(
            duration_ms, self._clear_feedback_strip
        )

    def _clear_feedback_strip(self) -> None:
        self._feedback_after_id = None
        try:
            self.feedback_label.config(text="", bg=C_BG, fg=C_BG)
            self.feedback_frame.config(bg=C_BG)
            self.feedback_frame.grid_remove()
        except tk.TclError:
            pass

    def show_about(self) -> None:
        dialogs.show_about(self)

    def on_quit(self) -> None:
        if self._feedback_after_id is not None:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
        self.session.persist_settings({
            "speed": self.speed_var.get(),
            "mode": modes.to_internal_mode(self.mode_var.get()),
            "fallback": modes.to_internal_fallback(self.fallback_var.get()),
            "pre_delay": self.pre_delay_var.get(),
            "post_delay": self.post_delay_var.get(),
            "jitter_intensity": self.jitter_intensity.get(),
            "auto_type_prefix": self.auto_type_prefix.get() == "On",
            "win_x": self.root.winfo_x(),
            "win_y": self.root.winfo_y(),
        })
        self.root.destroy()
