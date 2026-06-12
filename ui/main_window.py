"""Main application window — controller and top-level QMainWindow."""

import logging

from PySide6.QtCore import Qt, QTimer, QThread
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow

from core.session import AppSession
from . import modes
from .dialogs import AboutDialog, AdvancedDialog, UsedWordsDialog
from .file_editors import EditorDialog
from .main_widget import MainWidget
from .workers import DictWorker, TypeWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level application window.

    Owns the session and main widget. Wires all signals to slots
    and manages threading for dictionary loading and typing.
    """

    _POLL_INTERVAL_MS = 15000

    def __init__(self, session: AppSession | None = None) -> None:
        super().__init__()
        self.session = session or AppSession()
        self.setWindowTitle("\U0001f608")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        s = self.session.settings
        self.view = MainWidget(dict(s.as_dict()))
        self.setCentralWidget(self.view)

        self._dict_thread: QThread | None = None
        self._typing_thread: QThread | None = None
        self._poll_timer: QTimer | None = None
        self._advanced_dialog: AdvancedDialog | None = None
        self._used_words_dialog: UsedWordsDialog | None = None

        self._wire_view_signals()
        self._wire_shortcuts()
        self._restore_window_position(s)

        self.view.set_auto_type_prefix(bool(s.get("auto_type_prefix", True)))
        self.view.set_shared_delays(s.get("pre_delay", 500), s.get("post_delay", 500))

        self._startup_load_dict()
        self._start_roblox_polling()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_view_signals(self) -> None:
        self.view.play_requested.connect(self.on_play_round)
        self.view.dict_load_requested.connect(self.on_load_dict)
        self.view.advanced_requested.connect(self.show_advanced)
        self.view.clear_used_requested.connect(self.on_clear_used_words)
        self.view.used_words_requested.connect(self.show_used_words)
        self.view.about_requested.connect(self.show_about)

    def _wire_shortcuts(self) -> None:
        sc = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_Return), self)
        sc.activated.connect(self._on_ctrl_enter)

    # ------------------------------------------------------------------
    # Window position
    # ------------------------------------------------------------------

    def _restore_window_position(self, settings) -> None:
        win_x = settings.get("win_x")
        win_y = settings.get("win_y")
        if win_x is not None and win_y is not None:
            screen = self.screen()
            if screen:
                geo = screen.availableGeometry()
                sw, sh = geo.width(), geo.height()
                if -50 <= win_x < sw - 100 and -50 <= win_y < sh - 50:
                    self.move(win_x, win_y)
        self.adjustSize()
        self.setFixedSize(self.size())

    # ------------------------------------------------------------------
    # Roblox polling
    # ------------------------------------------------------------------

    def _start_roblox_polling(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_roblox_once)
        self._poll_roblox_once()
        self._poll_timer.start(self._POLL_INTERVAL_MS)

    def _poll_roblox_once(self) -> None:
        from system.roblox import is_roblox_running

        running = is_roblox_running(self.session.window_title)
        self.view.set_roblox_indicator(running)
        self.view.set_roblox_title(self.session.window_title)

    # ------------------------------------------------------------------
    # Dictionary loading
    # ------------------------------------------------------------------

    def _startup_load_dict(self) -> None:
        dict_path = self.session.try_load_dict_at_startup()
        if dict_path:
            self.view.set_loading_state()
            self.view.update_dict_label(dict_path)
            self._load_dict_in_background(dict_path)
        else:
            self.view.update_play_button(False)

    def on_load_dict(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select dictionary file",
            "",
            "All supported (*.json *.txt);;"
            "JSON dictionary (*.json);;"
            "Text word list (*.txt);;"
            "All files (*.*)",
        )
        if not path:
            return
        self.session.dict_path = path
        self.view.set_loading_state()
        self.view.update_dict_label(path)
        self._load_dict_in_background(path)

    def _load_dict_in_background(self, path: str) -> None:
        self._cleanup_thread(self._dict_thread)
        self._dict_thread = QThread()
        worker = DictWorker(self.session, path)
        worker.moveToThread(self._dict_thread)
        self._dict_thread.started.connect(worker.run)
        worker.finished.connect(self._on_dict_loaded)
        worker.error.connect(self._on_dict_error)
        worker.finished.connect(self._dict_thread.quit)
        worker.error.connect(self._dict_thread.quit)
        self._dict_thread.finished.connect(worker.deleteLater)
        self._dict_thread.finished.connect(self._dict_thread.deleteLater)
        self._dict_thread.finished.connect(lambda: setattr(self, '_dict_thread', None))
        self._dict_thread.start()

    def _on_dict_loaded(self, wordlist: list, from_cache: bool) -> None:
        count = len(wordlist)
        self.view.update_dict_word_count(count)
        self.view.update_play_button(True)
        self.view.set_ready_state()
        if self._advanced_dialog is not None:
            self._advanced_dialog.refresh_dict_label()

    def _on_dict_error(self, msg: str) -> None:
        self.view.show_feedback("error", f"Could not load dictionary: {msg}",
                                duration_ms=6000)
        self.view.update_dict_word_count(None)
        self.view.update_play_button(False)
        self.view.set_ready_state()

    # ------------------------------------------------------------------
    # Play round
    # ------------------------------------------------------------------

    def on_play_round(self) -> None:
        if not self.session.has_wordlist():
            self.on_load_dict()
            return

        prefix = self.view.prefix
        if not prefix:
            self.view.show_feedback("warn", "Enter starting letters first.",
                                    duration_ms=3000, beep=True)
            return

        word_to_type = self.session.prepare_play_round(
            prefix,
            modes.to_internal_mode(self.view.mode),
            modes.to_internal_fallback(self.view.fallback),
            self.view.auto_type_prefix_enabled,
        )
        if word_to_type is None:
            self.view.show_feedback("error", "No matching word found.",
                                    duration_ms=3000, beep=True)
            return

        if not self._prepare_for_typing(word_to_type):
            return

    def _on_ctrl_enter(self) -> None:
        if not self.session.has_wordlist():
            self.on_load_dict()
        else:
            self.on_play_round()

    def _prepare_for_typing(self, completion: str) -> bool:
        try:
            self.hide()
            self.view.clear_prefix()

            from system.roblox import is_roblox_running, focus_roblox_window
            running = is_roblox_running(self.session.window_title)
            if running:
                focus_roblox_window(self.session.window_title)
            self.view.set_roblox_indicator(running)

            self.session.configure_typer(
                speed_ms=self.view.speed_ms,
                jitter_intensity=self.view.jitter_intensity,
                pre_delay_s=self.view.pre_delay_ms / 1000.0,
                post_delay_s=self.view.post_delay_ms / 1000.0,
            )

            self._start_typing(completion)
            return True
        except Exception:
            self.session.finish_play_round()
            self.view.show_feedback("error", "Failed to prepare for typing.",
                                    duration_ms=6000)
            logger.exception("Failed to prepare for typing")
            return False

    def _start_typing(self, completion: str) -> None:
        self._cleanup_thread(self._typing_thread)
        self._typing_thread = QThread()
        worker = TypeWorker(
            self.session, completion,
            self.session.pre_delay, self.session.post_delay,
        )
        worker.moveToThread(self._typing_thread)
        self._typing_thread.started.connect(worker.run)
        worker.finished.connect(self._on_typing_finished)
        worker.finished.connect(self._typing_thread.quit)
        self._typing_thread.finished.connect(worker.deleteLater)
        self._typing_thread.finished.connect(self._typing_thread.deleteLater)
        self._typing_thread.finished.connect(
            lambda: setattr(self, '_typing_thread', None)
        )
        self._typing_thread.start()

    def _on_typing_finished(self, success: bool, message: str) -> None:
        self.session.finish_play_round()
        self.show()
        self.raise_()
        self.activateWindow()
        if self._used_words_dialog is not None:
            self._used_words_dialog.update_list()
        if not success:
            logger.warning("Typing failed: %s", message)
            self.view.show_feedback("error", f"Typing failed: {message}",
                                    duration_ms=8000)

    # ------------------------------------------------------------------
    # Trap endings / exceptions
    # ------------------------------------------------------------------

    def reload_trap_endings(self) -> None:
        self.session.reload_trap_endings()
        if self._advanced_dialog is not None:
            self._advanced_dialog._trap_status.setText(
                f"{len(self.session.engine.trap_endings)} loaded"
            )

    def reload_exceptions(self) -> None:
        self.session.reload_exceptions()
        if self._advanced_dialog is not None:
            self._advanced_dialog._exc_status.setText(
                f"{len(self.session.engine.word_exceptions)} loaded"
            )

    def edit_trap_endings(self) -> None:
        from config.trap_endings import TRAP_ENDINGS_FILE
        EditorDialog(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            default_content="# Trap endings - one per line, hardest first\n",
            status_callback=lambda c: self._advanced_dialog._trap_status.setText(
                f"{c} loaded"
            ) if self._advanced_dialog else None,
        )

    def edit_exceptions(self) -> None:
        from config.exceptions import EXCEPTIONS_FILE
        EditorDialog(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            default_content="# Word exceptions - one per line\n",
            status_callback=lambda c: self._advanced_dialog._exc_status.setText(
                f"{c} loaded"
            ) if self._advanced_dialog else None,
        )

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def show_advanced(self) -> None:
        if self._advanced_dialog is None:
            self._advanced_dialog = AdvancedDialog(self)
        self._advanced_dialog.show()
        self._advanced_dialog.raise_()
        self._advanced_dialog.activateWindow()

    def show_used_words(self) -> None:
        if self._used_words_dialog is None:
            self._used_words_dialog = UsedWordsDialog(self)
        self._used_words_dialog.show()
        self._used_words_dialog.update_list()
        self._used_words_dialog.raise_()
        self._used_words_dialog.activateWindow()

    def show_about(self) -> None:
        AboutDialog(self).show()

    def on_clear_used_words(self) -> None:
        self.session.clear_used_words()
        if self._used_words_dialog is not None:
            self._used_words_dialog.update_list()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cleanup_thread(thread: QThread | None) -> None:
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(3000)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self.view.dismiss_feedback()
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self.session.persist_settings({
            "wpm": self.view.speed_wpm,
            "mode": modes.to_internal_mode(self.view.mode),
            "fallback": modes.to_internal_fallback(self.view.fallback),
            "pre_delay": self.view.pre_delay_ms,
            "post_delay": self.view.post_delay_ms,
            "jitter_intensity": self.view.jitter_intensity,
            "auto_type_prefix": self.view.auto_type_prefix_enabled,
            "win_x": self.x(),
            "win_y": self.y(),
        })
        super().closeEvent(event)
