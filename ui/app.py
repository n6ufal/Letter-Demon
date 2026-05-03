# app.py main window orchestration
"""Main application window — wires UI modules to engines."""

import os
import sys
import threading
if sys.platform == "win32":
    import winsound
else:
    winsound = None

import tkinter as tk
from tkinter.filedialog import askopenfilename

from core.dictionary import load_wordlist_from_dict
from core.word_engine import WordEngine
from config.settings import load_settings, save_settings
from config.trap_endings import load_trap_endings, save_trap_endings
from config.exceptions import load_exceptions, save_exceptions
from system.roblox import is_roblox_running, focus_roblox_window
from system.typer import Typer

from . import dialogs
from . import file_editors
from . import modes
from .main_layout import build_main_layout
from .theme import (
    C_BG,
    C_FEEDBACK_ERR_BG,
    C_FEEDBACK_ERR_FG,
    C_FEEDBACK_WARN_BG,
    C_FEEDBACK_WARN_FG,
    C_MUTED,
    C_TEXT,
)


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class LastLetterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Letter Demon")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        try:
            self.root.iconbitmap(resource_path("LastLetter.ico"))
        except Exception as e:
            print("Icon load error:", e)

        self.engine = WordEngine(
            wordlist=[],
            trap_endings=load_trap_endings(),
            exceptions=load_exceptions(),
        )
        self.typer = Typer()

        self._is_playing = False
        self._playing_lock = threading.Lock()
        self._dict_path: str | None = None
        self._feedback_after_id = None
        self._advanced_window = None
        self.used_words_window = None

        settings = load_settings()
        self._dict_path = settings.get("dict_path", None)

        self.prefix_var = tk.StringVar()
        saved_mode = settings.get("mode", "Trap Words")
        saved_fallback = settings.get("fallback", "Short Words")
        self.mode_var = tk.StringVar(value=modes.to_display_mode(saved_mode))
        self.fallback_var = tk.StringVar(value=modes.to_display_fallback(saved_fallback))
        self.jitter_enabled = tk.BooleanVar(value=settings.get("jitter_enabled", True))
        self.jitter_intensity = tk.IntVar(value=settings.get("jitter_intensity", 75))
        self.pre_delay_var = tk.IntVar(value=settings.get("pre_delay", 500))
        self.post_delay_var = tk.IntVar(value=settings.get("post_delay", 500))

        self.root.configure(bg=C_BG)
        self.main_frame = tk.Frame(self.root, padx=12, pady=10, bg=C_BG)
        self.main_frame.pack(fill="both", expand=True)

        build_main_layout(self, settings)

        if "win_x" in settings and "win_y" in settings:
            self.root.geometry(f"+{settings['win_x']}+{settings['win_y']}")

        self.root.after(50, self._on_jitter_toggle)
        self.root.bind("<FocusIn>", self._on_root_focus_in)
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

    def show_advanced(self) -> None:
        dialogs.show_advanced(self)

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
            self.engine.set_wordlist(wordlist)
            word_count = len(wordlist)
            self.root.after(0, lambda: self.status_var.set(f"{word_count:,} words"))
        except Exception:
            def _on_load_fail() -> None:
                self.notify("error", "Could not load dictionary.", duration_ms=6000)
                self.status_var.set("No dictionary loaded")

            self.root.after(0, _on_load_fail)

    def reload_trap_endings(self) -> None:
        from config.trap_endings import TRAP_ENDINGS_FILE, DEFAULT_TRAP_ENDINGS

        try:
            with open(TRAP_ENDINGS_FILE, "r") as f:
                endings = [
                    line.strip().lower()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
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
                    f"Not found — created {len(DEFAULT_TRAP_ENDINGS)} defaults"
                )
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

        file_editors.open_file_editor(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=self.trap_status_var,
            default_content="# Trap endings - one per line, hardest first\n",
        )

    def edit_exceptions(self):
        from config.exceptions import EXCEPTIONS_FILE

        file_editors.open_file_editor(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            status_var=self.exceptions_status_var,
            default_content="# Word exceptions - one per line\n",
        )

    def _poll_roblox(self) -> None:
        running = is_roblox_running()
        self._update_roblox_indicator(running)
        self.root.after(3000, self._poll_roblox)

    def _update_roblox_indicator(self, running: bool) -> None:
        from .theme import C_DOT_GREEN, C_DOT_RED

        color = C_DOT_GREEN if running else C_DOT_RED
        symbol = "●" if running else "○"
        text = f"{symbol} Roblox: {'on' if running else 'off'}"
        self.roblox_status_label.config(fg=color)
        self.roblox_status_var.set(text)

    def on_play_round(self) -> None:
        with self._playing_lock:
            if self._is_playing:
                return

            prefix = self.prefix_var.get().strip()
            if not prefix:
                self.notify(
                    "warn",
                    "Enter starting letters first.",
                    beep=True,
                )
                return

            if not self.engine.has_wordlist():
                self.notify(
                    "error",
                    "Load a dictionary first (Advanced → Load Dictionary).",
                    beep=True,
                )
                return

            completion = self.engine.find_completion(
                prefix,
                modes.to_internal_mode(self.mode_var.get()),
                modes.to_internal_fallback(self.fallback_var.get()),
            )
            if completion is None:
                self.notify(
                    "error",
                    "No matching word found.",
                    beep=True,
                )
                return

            self._is_playing = True

        self.root.withdraw()
        self.prefix_var.set("")

        if is_roblox_running():
            focus_roblox_window()
            self._update_roblox_indicator(True)
        else:
            self._update_roblox_indicator(False)

        self.typer.base_speed_ms = self.speed_var.get()
        self.typer.jitter_on = self.jitter_enabled.get()
        self.typer.jitter_pct = self.jitter_intensity.get()

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
            success, message = self.typer.type_text(
                completion, pre_delay_s=pre, post_delay_s=post
            )
            if not success:
                print(f"[WARNING] Typing failed: {message}")
                self.root.after(
                    0,
                    lambda m=message: self.notify(
                        "error",
                        f"Typing failed: {m}",
                        duration_ms=8000,
                    ),
                )
        finally:
            with self._playing_lock:
                self._is_playing = False
            self.root.after(0, self.root.deiconify)
            if dialogs.used_words_window_alive(self):
                self.root.after(0, lambda: dialogs.update_used_words_list(self))

    def show_used_words(self) -> None:
        dialogs.show_used_words(self)

    def on_clear_cache(self) -> None:
        self.engine.clear_used_words()
        if dialogs.used_words_window_alive(self):
            dialogs.update_used_words_list(self)

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

        if beep and winsound:
            winsound.MessageBeep(winsound.MB_ICONHAND)

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

    def _on_jitter_toggle(self) -> None:
        state = tk.NORMAL if self.jitter_enabled.get() else tk.DISABLED
        enabled = self.jitter_enabled.get()

        if hasattr(self, "humanizer_slider") and self.humanizer_slider.winfo_exists():
            self.humanizer_slider.config(state=state)
            self.humanizer_val_label.config(fg=C_TEXT if enabled else C_MUTED)

    def show_about(self) -> None:
        dialogs.show_about(self)

    def on_quit(self) -> None:
        if self._feedback_after_id is not None:
            self.root.after_cancel(self._feedback_after_id)
            self._feedback_after_id = None
        save_settings({
            "dict_path": self._dict_path,
            "speed": self.speed_var.get(),
            "mode": modes.to_internal_mode(self.mode_var.get()),
            "fallback": modes.to_internal_fallback(self.fallback_var.get()),
            "pre_delay": self.pre_delay_var.get(),
            "post_delay": self.post_delay_var.get(),
            "jitter_enabled": self.jitter_enabled.get(),
            "jitter_intensity": self.jitter_intensity.get(),
            "win_x": self.root.winfo_x(),
            "win_y": self.root.winfo_y(),
        })
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:
            pass
        self.root.destroy()
