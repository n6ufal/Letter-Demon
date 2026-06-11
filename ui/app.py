"""Application controller — mediates between session and view."""

import logging
import threading

import tkinter as tk
from tkinter.filedialog import askopenfilename

from core.session import AppSession
from config.trap_endings import TRAP_ENDINGS_FILE
from config.exceptions import EXCEPTIONS_FILE
from system.roblox import is_roblox_running, focus_roblox_window

from . import dialogs
from . import file_editors
from . import modes
from .view import MainView

logger = logging.getLogger(__name__)


class LetterDemonApp:
    """Controller — owns session and view, wires them together."""

    def __init__(self, root: tk.Tk, session: AppSession | None = None) -> None:
        self.session = session or AppSession()
        self.root = root
        self.root.title("😈")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self._poll_id = None
        self._advanced_dialog: dialogs.AdvancedDialog | None = None
        self._used_words_dialog: dialogs.UsedWordsDialog | None = None

        s = self.session.settings
        self.view = MainView(root, self, self.session.window_title, dict(s.as_dict()))

        win_x = s.get("win_x")
        win_y = s.get("win_y")
        if win_x is not None and win_y is not None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if -50 <= win_x < sw - 100 and -50 <= win_y < sh - 50:
                self.root.geometry(f"+{win_x}+{win_y}")

        self.root.bind("<FocusIn>", self._on_root_focus_in)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.view.entry.bind("<Control-Return>", self.on_ctrl_enter)

        self._poll_roblox()

        dict_path = self.session.try_load_dict_at_startup()
        if dict_path:
            self.view.set_loading_state()
            self._run_thread(self._load_wordlist_thread, (dict_path,))
        else:
            self.view.update_play_button(False)

    # -- Focus helpers --

    @staticmethod
    def _run_thread(target, args=()) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

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
            self.view.entry.focus_set()
        except tk.TclError:
            pass

    # -- Dictionary --

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
        self.view.set_loading_state()
        self.view.update_dict_label(self.session.dict_path)
        self._run_thread(self._load_wordlist_thread, (path,))

    def _load_wordlist_thread(self, dict_path: str) -> None:
        try:
            wordlist, from_cache = self.session.load_dictionary(dict_path)
            word_count = len(wordlist)
            self.root.after(0, lambda: self.view.set_status(f"{word_count:,} words"))
            self.root.after(0, lambda: self.view.update_play_button(True))
        except Exception:
            def _on_fail() -> None:
                self.view.show_feedback("error", "Could not load dictionary.",
                                        duration_ms=6000)
                self.view.set_status("")
                self.view.update_play_button(False)

            self.root.after(0, _on_fail)

    # -- Trap endings / exceptions --

    def reload_trap_endings(self) -> None:
        self.session.reload_trap_endings()
        self.view.set_trap_status(
            f"{len(self.session.engine.trap_endings)} loaded"
        )

    def reload_exceptions(self) -> None:
        self.session.reload_exceptions()
        self.view.set_exceptions_status(
            f"{len(self.session.engine.word_exceptions)} loaded"
        )

    def edit_trap_endings(self) -> None:
        file_editors.EditorDialog(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=self.view.trap_status_var,
            default_content="# Trap endings - one per line, hardest first\n",
        )

    def edit_exceptions(self) -> None:
        file_editors.EditorDialog(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            status_var=self.view.exceptions_status_var,
            default_content="# Word exceptions - one per line\n",
        )

    # -- Roblox polling --

    def _poll_roblox(self) -> None:
        running = is_roblox_running(self.session.window_title)
        self.view.set_roblox_indicator(running)
        self._poll_id = self.root.after(15000, self._poll_roblox)

    # -- Play round --

    def _prepare_for_typing(self) -> bool:
        """Hide window, focus Roblox, configure typer. Returns False on error."""
        try:
            self.root.withdraw()
            self.view.clear_prefix()
            if is_roblox_running(self.session.window_title):
                focus_roblox_window(self.session.window_title)
                self.view.set_roblox_indicator(True)
            else:
                self.view.set_roblox_indicator(False)
            self.session.configure_typer(
                speed_ms=self.view.speed_ms,
                jitter_intensity=self.view.jitter_intensity,
                pre_delay_s=self.view.pre_delay_ms / 1000.0,
                post_delay_s=self.view.post_delay_ms / 1000.0,
            )
            return True
        except Exception:
            self.session.finish_play_round()
            self.view.show_feedback("error", "Failed to prepare for typing.",
                                    duration_ms=6000)
            logger.exception("Failed to prepare for typing")
            return False

    def on_play_round(self) -> None:
        prefix = self.view.prefix
        if not prefix:
            self.view.show_feedback("warn", "Enter starting letters first.", beep=True)
            return

        if not self.session.has_wordlist():
            self.view.show_feedback(
                "error",
                "Load a dictionary first (Advanced \u2192 Load Dictionary).",
                beep=True,
            )
            return

        word_to_type = self.session.prepare_play_round(
            prefix,
            modes.to_internal_mode(self.view.mode),
            modes.to_internal_fallback(self.view.fallback),
            self.view.auto_type_prefix_enabled,
        )
        if word_to_type is None:
            self.view.show_feedback("error", "No matching word found.", beep=True)
            return

        if not self._prepare_for_typing():
            return

        self._run_thread(self._type_and_return, (word_to_type,))

    def on_ctrl_enter(self, event: tk.Event) -> str:
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
                    lambda m=message: self.view.show_feedback(
                        "error", f"Typing failed: {m}", duration_ms=8000
                    ),
                )
        finally:
            self.session.finish_play_round()
            self.root.after(0, lambda: self._try_tcl(self.root.deiconify))
            self.root.after(
                0, lambda: self._used_words_dialog
                and self._used_words_dialog.update_list()
            )

    def show_advanced(self) -> None:
        if self._advanced_dialog is None:
            self._advanced_dialog = dialogs.AdvancedDialog(
                self.root, self, self.view
            )
        self._advanced_dialog.show()

    def show_used_words(self) -> None:
        if self._used_words_dialog is None:
            self._used_words_dialog = dialogs.UsedWordsDialog(
                self.root, self
            )
        self._used_words_dialog.show()

    def show_about(self) -> None:
        dialogs.AboutDialog.show(self.root)

    def on_clear_used_words(self) -> None:
        self.session.clear_used_words()
        if self._used_words_dialog is not None:
            self._used_words_dialog.update_list()

    # -- Utilities --

    @staticmethod
    def _try_tcl(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except tk.TclError:
            pass

    # -- Cleanup --

    def on_quit(self) -> None:
        self.view.dismiss_feedback()
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
        self._poll_id = None
        self.session.persist_settings({
            "speed": self.view.speed_ms,
            "mode": modes.to_internal_mode(self.view.mode),
            "fallback": modes.to_internal_fallback(self.view.fallback),
            "pre_delay": self.view.pre_delay_ms,
            "post_delay": self.view.post_delay_ms,
            "jitter_intensity": self.view.jitter_intensity,
            "auto_type_prefix": self.view.auto_type_prefix_enabled,
            "win_x": self.root.winfo_x(),
            "win_y": self.root.winfo_y(),
        })
        self.root.destroy()
