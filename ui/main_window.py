"""Main application window — controller and top-level QMainWindow."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QThread
from PySide6.QtGui import QAction, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QStyle,
    QSystemTrayIcon,
)

from core.session import AppSession
from . import modes
from .dialogs import AboutDialog, AdvancedPanel, UsedWordsDialog
from .file_editors import EditorDialog
from .main_widget import MainWidget
from .theme import apply_theme
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
        self._used_words_dialog: UsedWordsDialog | None = None
        self._quitting = False
        self._fade_out_anim: QPropertyAnimation | None = None
        self._fade_in_anim: QPropertyAnimation | None = None

        self._dark_mode = bool(s.get("dark_mode", False))
        self._always_on_top = bool(s.get("always_on_top", True))
        if self._dark_mode:
            apply_theme(True)

        self._build_menu_bar()
        self._build_status_bar()
        self._setup_tray()
        self._wire_view_signals()
        self._wire_shortcuts()
        self._restore_window_position(s)

        self.view.set_auto_type_prefix(bool(s.get("auto_type_prefix", True)))
        self.view.set_shared_delays(s.get("pre_delay", 500), s.get("post_delay", 500))
        self._build_advanced_dock()

        compact = bool(s.get("compact_mode", False))
        if compact:
            self._compact_action.setChecked(True)
            self.view.set_compact_mode(True)

        self._startup_load_dict()
        self._start_roblox_polling()
        self._setup_global_hotkey()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_view_signals(self) -> None:
        self.view.play_requested.connect(self.on_play_round)
        self.view.dict_load_requested.connect(self.on_load_dict)
        self.view.dict_dropped.connect(self.on_load_dict_from_path)
        self.view.advanced_requested.connect(self.show_advanced)
        self.view.clear_used_requested.connect(self.on_clear_used_words)
        self.view.used_words_requested.connect(self.show_used_words)
        self.view.about_requested.connect(self.show_about)
        self.view.status_dict_changed.connect(self._set_status_dict)
        self.view.status_prefix_changed.connect(self._set_status_prefix)
        self.view.status_roblox_changed.connect(self._set_status_roblox)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        bar = self.menuBar()

        # -- File --
        file_menu = bar.addMenu("File")
        file_menu.addAction("Load Dictionary...", self.on_load_dict,
                            QKeySequence(Qt.CTRL | Qt.Key_O))

        self._recent_dicts_menu = QMenu("Recent Dictionaries")
        file_menu.addMenu(self._recent_dicts_menu)
        self._rebuild_recent_dicts_menu()

        file_menu.addSeparator()
        file_menu.addAction("Quit", self._quit_app, QKeySequence(Qt.CTRL | Qt.Key_Q))

        # -- View --
        view_menu = bar.addMenu("View")

        self._compact_action = QAction("Compact Mode", checkable=True)
        self._compact_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_M))
        self._compact_action.toggled.connect(self._on_toggle_compact)
        view_menu.addAction(self._compact_action)

        self._dark_action = QAction("Dark Mode", checkable=True)
        self._dark_action.setChecked(self._dark_mode)
        self._dark_action.toggled.connect(self.on_toggle_dark)
        view_menu.addAction(self._dark_action)

        self._always_on_top_action = QAction("Always on Top", checkable=True)
        self._always_on_top_action.setChecked(self._always_on_top)
        self._always_on_top_action.toggled.connect(self._on_toggle_always_on_top)
        view_menu.addAction(self._always_on_top_action)

        view_menu.addSeparator()

        self._advanced_action = QAction("Advanced", checkable=True)
        self._advanced_action.toggled.connect(self._on_toggle_advanced_dock)
        view_menu.addAction(self._advanced_action)

        # -- Help --
        help_menu = bar.addMenu("Help")
        help_menu.addAction("About", self.show_about)

    def _rebuild_recent_dicts_menu(self) -> None:
        self._recent_dicts_menu.clear()
        recent = self.session.settings.get("recent_dicts", [])
        if not recent:
            self._recent_dicts_menu.addAction("(empty)").setEnabled(False)
            return
        for path in recent:
            name = Path(path).name
            action = self._recent_dicts_menu.addAction(name)
            action.setData(path)
            action.triggered.connect(lambda checked=False, p=path: self._load_recent_dict(p))

    def _load_recent_dict(self, path: str) -> None:
        self.session.dict_path = path
        self.view.set_loading_state()
        self.view.update_dict_label(path)
        self._load_dict_in_background(path)

    def _add_recent_dict(self, path: str) -> None:
        recent: list = list(self.session.settings.get("recent_dicts", []))
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.session.settings.set("recent_dicts", recent[:5])
        self._rebuild_recent_dicts_menu()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        sb = self.statusBar()

        self._sb_dict_dot = QLabel("\u25cf")
        self._sb_dict_dot.setObjectName("dictDot")
        sb.addPermanentWidget(self._sb_dict_dot)

        self._sb_dict_label = QLabel("No dictionary")
        self._sb_dict_label.setObjectName("dictCountLabel")
        self._sb_dict_label.setToolTip("Dictionary word count")
        self._sb_dict_label.setCursor(Qt.WhatsThisCursor)
        sb.addPermanentWidget(self._sb_dict_label)

        sb.addPermanentWidget(QLabel("  |  "))

        self._sb_prefix_dot = QLabel("\u25cf")
        self._sb_prefix_dot.setObjectName("dictDot")
        sb.addPermanentWidget(self._sb_prefix_dot)

        self._sb_prefix_label = QLabel("")
        self._sb_prefix_label.setObjectName("dictCountLabel")
        self._sb_prefix_label.setToolTip(
            "Suffix \u2014 types only the ending / "
            "Full \u2014 types the complete word"
        )
        sb.addPermanentWidget(self._sb_prefix_label)

        sb.addPermanentWidget(QLabel("  |  "))

        self._sb_roblox_dot = QLabel("\u25cf")
        self._sb_roblox_dot.setObjectName("dictDot")
        sb.addPermanentWidget(self._sb_roblox_dot)

        self._sb_roblox_label = QLabel("")
        self._sb_roblox_label.setObjectName("dictCountLabel")
        self._sb_roblox_label.setToolTip("Roblox connection status")
        sb.addPermanentWidget(self._sb_roblox_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        sb.addPermanentWidget(self._progress_bar)

    def _set_status_dict(self, text: str, color: str) -> None:
        self._sb_dict_label.setText(text)
        dot_color = {"green": "#16a34a", "red": "#dc2626",
                     "blue": "#2563eb", "muted": "#71717a"}.get(color, "#71717a")
        self._sb_dict_dot.setStyleSheet(f"color: {dot_color};")

    def _set_status_prefix(self, text: str, color: str) -> None:
        self._sb_prefix_label.setText(text)
        dot_color = {"green": "#16a34a", "red": "#dc2626",
                     "blue": "#2563eb", "muted": "#71717a"}.get(color, "#71717a")
        self._sb_prefix_dot.setStyleSheet(f"color: {dot_color};")

    def _set_status_roblox(self, text: str, color: str) -> None:
        self._sb_roblox_label.setText(text)
        dot_color = {"green": "#16a34a", "red": "#dc2626",
                     "blue": "#2563eb", "muted": "#71717a"}.get(color, "#71717a")
        self._sb_roblox_dot.setStyleSheet(f"color: {dot_color};")

    # ------------------------------------------------------------------
    # View toggles
    # ------------------------------------------------------------------

    def _on_toggle_compact(self, enabled: bool) -> None:
        self.session.settings.set("compact_mode", enabled)
        self.view.set_compact_mode(enabled)

    def _on_escape(self) -> None:
        if self._advanced_dock.isVisible():
            self._advanced_action.setChecked(False)
        elif self._used_words_dialog is not None and self._used_words_dialog.isVisible():
            self._used_words_dialog.close()
        else:
            self.view.clear_prefix()

    def _on_toggle_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = enabled
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _wire_shortcuts(self) -> None:
        sc = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_Return), self)
        sc.activated.connect(self._on_ctrl_enter)

        sc = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_O), self)
        sc.activated.connect(self.on_load_dict)

        sc = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_Q), self)
        sc.activated.connect(self._quit_app)

        sc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        sc.activated.connect(self._on_escape)

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
        color = "green" if running else "red"
        self._set_status_roblox(self.session.window_title, color)

    # ------------------------------------------------------------------
    # Dictionary loading
    # ------------------------------------------------------------------

    def _startup_load_dict(self) -> None:
        dict_path = self.session.try_load_dict_at_startup()
        if dict_path:
            self.view.set_loading_state()
            self.view.update_dict_label(dict_path)
            self._add_recent_dict(dict_path)
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
        self._load_dict_from_path(path)

    def on_load_dict_from_path(self, path: str) -> None:
        self._load_dict_from_path(path)

    def _load_dict_from_path(self, path: str) -> None:
        self.session.dict_path = path
        self.view.set_loading_state()
        self.view.update_dict_label(path)
        self._add_recent_dict(path)
        self._load_dict_in_background(path)

    def _load_dict_in_background(self, path: str) -> None:
        self._progress_bar.setVisible(True)
        self._cleanup_thread(self._dict_thread)
        self._dict_thread = QThread()
        worker = DictWorker(self.session, path)
        worker.moveToThread(self._dict_thread)
        self._dict_thread.started.connect(worker.run)
        worker.finished.connect(self._on_dict_loaded)
        worker.error.connect(self._on_dict_error)
        worker.finished.connect(self._dict_thread.quit)
        worker.error.connect(self._dict_thread.quit)
        self._dict_thread.finished.connect(self._on_dict_load_finished)
        self._dict_thread.finished.connect(worker.deleteLater)
        self._dict_thread.finished.connect(lambda: setattr(self, '_dict_thread', None))
        self._dict_thread.start()

    def _on_dict_loaded(self, wordlist: list, from_cache: bool) -> None:
        count = len(wordlist)
        self._set_status_dict(f"{count:,} words", "green")
        self.view.update_play_button(True)
        self.view.set_ready_state()
        if hasattr(self, '_advanced_panel'):
            self._advanced_panel.refresh_dict_label()

    def _on_dict_error(self, msg: str) -> None:
        self._progress_bar.setVisible(False)
        self.view.show_feedback("error", f"Could not load dictionary: {msg}",
                                duration_ms=6000)
        self._set_status_dict("No dictionary", "muted")
        self.view.update_play_button(False)
        self.view.set_ready_state()

    def _on_dict_load_finished(self) -> None:
        self._progress_bar.setVisible(False)

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
            if self._fade_out_anim is not None and self._fade_out_anim.state() == QPropertyAnimation.Running:
                self._fade_out_anim.stop()
                self._fade_out_anim = None

            self._fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_out_anim.setDuration(100)
            self._fade_out_anim.setStartValue(1.0)
            self._fade_out_anim.setEndValue(0.0)
            self._fade_out_anim.finished.connect(self.hide)
            self._fade_out_anim.start()

            self.view.clear_prefix()

            from system.roblox import is_roblox_running, focus_roblox_window
            running = is_roblox_running(self.session.window_title)
            if running:
                focus_roblox_window(self.session.window_title)
            color = "green" if running else "red"
            self._set_status_roblox(self.session.window_title, color)

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

        if self._fade_in_anim is not None and self._fade_in_anim.state() == QPropertyAnimation.Running:
            self._fade_in_anim.stop()
            self._fade_in_anim = None

        self.show()
        self.raise_()
        self.activateWindow()

        self._fade_in_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in_anim.setDuration(100)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.start()

        self._show_tray_notification(success, message)
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
        if hasattr(self, '_advanced_panel'):
            self._advanced_panel._trap_status.setText(
                f"{len(self.session.engine.trap_endings)} loaded"
            )

    def reload_exceptions(self) -> None:
        self.session.reload_exceptions()
        if hasattr(self, '_advanced_panel'):
            self._advanced_panel._exc_status.setText(
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
            status_callback=lambda c: self._advanced_panel._trap_status.setText(
                f"{c} loaded"
            ) if hasattr(self, '_advanced_panel') else None,
        )

    def edit_exceptions(self) -> None:
        from config.exceptions import EXCEPTIONS_FILE
        EditorDialog(
            self,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self.reload_exceptions,
            default_content="# Word exceptions - one per line\n",
            status_callback=lambda c: self._advanced_panel._exc_status.setText(
                f"{c} loaded"
            ) if hasattr(self, '_advanced_panel') else None,
        )

    # ------------------------------------------------------------------
    # Advanced dock
    # ------------------------------------------------------------------

    def _build_advanced_dock(self) -> None:
        self._advanced_dock = QDockWidget("Advanced", self)
        self._advanced_panel = AdvancedPanel(self)
        self._advanced_dock.setWidget(self._advanced_panel)
        self._advanced_dock.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self._advanced_dock)
        self._advanced_dock.hide()
        self._advanced_dock.visibilityChanged.connect(
            self._advanced_action.setChecked
        )

    def _on_toggle_advanced_dock(self, visible: bool) -> None:
        self._advanced_dock.setVisible(visible)
        if visible:
            self._advanced_dock.raise_()

    def show_advanced(self) -> None:
        self._advanced_action.setChecked(True)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def on_toggle_dark(self, checked: bool) -> None:
        self._dark_mode = checked
        apply_theme(checked)

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
    # System tray
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self._tray_icon.setToolTip("Letter Demon")

        menu = QMenu()
        menu.addAction("Show/Hide", self._toggle_visibility)
        menu.addAction("Quick Type", self.on_play_round)
        menu.addSeparator()
        menu.addAction("Quit", self._quit_app)
        self._tray_icon.setContextMenu(menu)

        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

        self._quitting = False

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_app(self) -> None:
        self._quitting = True
        self.close()

    def _show_tray_notification(self, success: bool, message: str) -> None:
        title = "Typing complete" if success else "Typing failed"
        icon = QSystemTrayIcon.Information if success else QSystemTrayIcon.Warning
        self._tray_icon.showMessage(title, message, icon, 4000)

    # ------------------------------------------------------------------
    # Global hotkey
    # ------------------------------------------------------------------

    def _setup_global_hotkey(self) -> None:
        combo = str(self.session.settings.get("global_hotkey", "win+shift+d"))
        try:
            import keyboard
            keyboard.add_hotkey(combo, self._summon_from_hotkey)
        except Exception:
            logger.warning("Could not register global hotkey %s", combo)

    def _summon_from_hotkey(self) -> None:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._show_from_tray)

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.view.entry.setFocus()

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
        if not self._quitting and self._tray_icon.isVisible():
            event.ignore()
            self.hide()
            return

        self.view.dismiss_feedback()
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._tray_icon.hide()
        self.session.persist_settings({
            "wpm": self.view.speed_wpm,
            "mode": modes.to_internal_mode(self.view.mode),
            "fallback": modes.to_internal_fallback(self.view.fallback),
            "pre_delay": self.view.pre_delay_ms,
            "post_delay": self.view.post_delay_ms,
            "jitter_intensity": self.view.jitter_intensity,
            "auto_type_prefix": self.view.auto_type_prefix_enabled,
            "dark_mode": self._dark_mode,
            "compact_mode": self._compact_action.isChecked(),
            "always_on_top": self._always_on_top,
            "win_x": self.x(),
            "win_y": self.y(),
        })
        super().closeEvent(event)
