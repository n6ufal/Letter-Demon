"""Main application window — controller and top-level QMainWindow."""

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow

from core.session import AppSession
from . import modes
from .main_widget import MainWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level application window.

    Owns the session and main widget. Wires signals to slots.
    Phased migration from tkinter LetterDemonApp.
    """

    def __init__(self, session: AppSession | None = None) -> None:
        super().__init__()
        self.session = session or AppSession()
        self.setWindowTitle("\U0001f608")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        s = self.session.settings
        self.view = MainWidget(dict(s.as_dict()))
        self.setCentralWidget(self.view)

        self._poll_id = None
        self._is_playing = False

        self._wire_view_signals()
        self._restore_window_position(s)
        self._start_roblox_polling()

    # -- Signal wiring --

    def _wire_view_signals(self) -> None:
        self.view.play_requested.connect(self.on_play_round)
        self.view.dict_load_requested.connect(self.on_load_dict)
        self.view.advanced_requested.connect(self.show_advanced)
        self.view.clear_used_requested.connect(self.on_clear_used_words)
        self.view.used_words_requested.connect(self.show_used_words)
        self.view.about_requested.connect(self.show_about)

    # -- Window position persistence --

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

    # -- Roblox polling --

    def _start_roblox_polling(self) -> None:
        from system.roblox import is_roblox_running

        def poll() -> None:
            running = is_roblox_running(self.session.window_title)
            self.view.set_roblox_indicator(running)
            self.view.set_roblox_title(self.session.window_title)
            self._poll_id = QTimer.singleShot(15000, poll)

        poll()

    # -- Dictionary loading (stub) --

    def on_load_dict(self) -> None:
        logger.info("Load dictionary requested — will implement in Phase 4")

    def on_play_round(self) -> None:
        logger.info("Play round requested — will implement in Phase 4")

    def show_advanced(self) -> None:
        logger.info("Advanced dialog requested — will implement in Phase 6")

    def show_used_words(self) -> None:
        logger.info("Used words dialog requested — will implement in Phase 6")

    def show_about(self) -> None:
        logger.info("About dialog requested — will implement in Phase 6")

    def on_clear_used_words(self) -> None:
        self.session.clear_used_words()
        logger.info("Used words cleared")

    # -- Cleanup --

    def closeEvent(self, event) -> None:
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
