"""Secondary window classes: Advanced, About, Used Words (Qt)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import version_string
from .file_editors import EditorDialog


# ---------------------------------------------------------------------------
# About dialog
# ---------------------------------------------------------------------------


class AboutDialog(QDialog):
    """Stateless about window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setFixedSize(360, 220)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Letter Demon \U0001f608")
        title.setStyleSheet("font: 13pt 'Segoe UI'; font-weight: bold; color: #18181b;")
        layout.addWidget(title)

        ver = QLabel(version_string)
        ver.setStyleSheet("font: 8pt 'Segoe UI'; color: #71717a;")
        layout.addWidget(ver)

        tagline = QLabel(
            "The Demon knows every word your opponent doesn't."
        )
        tagline.setStyleSheet("font: 8pt 'Segoe UI'; color: #71717a; "
                              "padding: 2px 0 12px 0;")
        layout.addWidget(tagline)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #e4e4e7;")
        layout.addWidget(sep)

        credit = QLabel("Made by n6ufal with \U0001f49c")
        credit.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b; "
                             "padding: 8px 0 2px 0;")
        layout.addWidget(credit)

        email = QLabel('<a href="mailto:boxcarr@proton.me" '
                       'style="color: #18181b; text-decoration: none;">'
                       'Email: boxcarr@proton.me</a>')
        email.setOpenExternalLinks(True)
        email.setCursor(Qt.PointingHandCursor)
        email.setStyleSheet("font: 8pt 'Segoe UI';")
        layout.addWidget(email)

        gh = QLabel('<a href="https://github.com/n6ufal/Letter-Demon" '
                    'style="color: #18181b; text-decoration: none;">'
                    'GitHub: n6ufal/Letter-Demon</a>')
        gh.setOpenExternalLinks(True)
        gh.setCursor(Qt.PointingHandCursor)
        gh.setStyleSheet("font: 8pt 'Segoe UI';")
        layout.addWidget(gh)

        layout.addStretch()

    @staticmethod
    def show(parent) -> "AboutDialog":
        dlg = AboutDialog(parent)
        dlg.show()
        return dlg


# ---------------------------------------------------------------------------
# Advanced dialog
# ---------------------------------------------------------------------------


class AdvancedDialog(QDialog):
    """Singleton advanced settings window — timing, dictionary, traps."""

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self._main = main_window
        self._session = main_window.session
        self._view = main_window.view
        self.setWindowTitle("Advanced")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._build_dict_tab(), "Dictionary")
        tabs.addTab(self._build_timing_tab(), "Timing")
        tabs.addTab(self._build_typing_tab(), "Typing")
        tabs.addTab(self._build_traps_tab(), "Trap Endings")
        layout.addWidget(tabs)

        self.setFixedSize(420, 320)

    def _build_dict_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        self._dict_label = QLabel(self._view.dict_label)
        self._dict_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #71717a;")
        layout.addWidget(self._dict_label)

        load_btn = QPushButton("Load Dictionary")
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.clicked.connect(self._main.on_load_dict)
        load_btn.setToolTip("Open a .json or .txt word list file")
        layout.addWidget(load_btn)

        layout.addStretch()
        return tab

    def _build_timing_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        pre_label = QLabel("Pre-type delay:")
        pre_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(pre_label)

        pre_row = QHBoxLayout()
        self._pre_spin = QSpinBox()
        self._pre_spin.setRange(100, 2000)
        self._pre_spin.setSingleStep(50)
        self._pre_spin.setSuffix(" ms")
        self._pre_spin.setValue(self._view.pre_delay_ms)
        self._pre_spin.valueChanged.connect(self._on_pre_changed)
        self._pre_spin.setToolTip("Pause before typing the first character")
        pre_row.addWidget(self._pre_spin)
        pre_row.addStretch()
        layout.addLayout(pre_row)

        post_label = QLabel("Post-type delay:")
        post_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b; "
                                 "padding-top: 6px;")
        layout.addWidget(post_label)

        post_row = QHBoxLayout()
        self._post_spin = QSpinBox()
        self._post_spin.setRange(100, 2000)
        self._post_spin.setSingleStep(50)
        self._post_spin.setSuffix(" ms")
        self._post_spin.setValue(self._view.post_delay_ms)
        self._post_spin.valueChanged.connect(self._on_post_changed)
        self._post_spin.setToolTip("Pause after pressing Enter")
        post_row.addWidget(self._post_spin)
        post_row.addStretch()
        layout.addLayout(post_row)

        layout.addStretch()
        return tab

    def _on_pre_changed(self, val: int) -> None:
        self._view.set_shared_delays(val, self._view.post_delay_ms)

    def _on_post_changed(self, val: int) -> None:
        self._view.set_shared_delays(self._view.pre_delay_ms, val)

    def _build_typing_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        auto_row = QHBoxLayout()
        auto_label = QLabel("Auto Type Prefix:")
        auto_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        auto_row.addWidget(auto_label)

        self._auto_type_combo = QComboBox()
        self._auto_type_combo.addItems(["On", "Off"])
        self._auto_type_combo.setCurrentText(
            "On" if self._view.auto_type_prefix_enabled else "Off"
        )
        self._auto_type_combo.currentTextChanged.connect(self._on_auto_type_changed)
        self._auto_type_combo.setToolTip(
            "On: types only the ending / Off: types the full word"
        )
        auto_row.addWidget(self._auto_type_combo)
        auto_row.addStretch()
        layout.addLayout(auto_row)

        layout.addStretch()
        return tab

    def _on_auto_type_changed(self, text: str) -> None:
        self._view.set_auto_type_prefix(text == "On")

    def _build_traps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        # Trap endings section
        trap_header = QLabel("Trap endings")
        trap_header.setStyleSheet("font: 8pt 'Segoe UI'; font-weight: bold; "
                                  "color: #18181b;")
        layout.addWidget(trap_header)

        self._trap_status = QLabel(
            f"{len(self._session.engine.trap_endings)} loaded"
        )
        self._trap_status.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(self._trap_status)

        trap_btn_row = QHBoxLayout()
        trap_reload = QPushButton("Reload")
        trap_reload.setCursor(Qt.PointingHandCursor)
        trap_reload.clicked.connect(self._reload_traps)
        trap_reload.setToolTip("Reload trap endings from the file")
        trap_btn_row.addWidget(trap_reload)

        trap_edit = QPushButton("Edit")
        trap_edit.setCursor(Qt.PointingHandCursor)
        trap_edit.clicked.connect(self._edit_traps)
        trap_edit.setToolTip("Edit the trap endings list")
        trap_btn_row.addWidget(trap_edit)
        trap_btn_row.addStretch()
        layout.addLayout(trap_btn_row)

        # Exceptions section
        exc_header = QLabel("Exceptions")
        exc_header.setStyleSheet("font: 8pt 'Segoe UI'; font-weight: bold; "
                                 "color: #18181b; padding-top: 12px;")
        layout.addWidget(exc_header)

        self._exc_status = QLabel(
            f"{len(self._session.engine.word_exceptions)} loaded"
        )
        self._exc_status.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(self._exc_status)

        exc_btn_row = QHBoxLayout()
        exc_reload = QPushButton("Reload")
        exc_reload.setCursor(Qt.PointingHandCursor)
        exc_reload.clicked.connect(self._reload_exceptions)
        exc_reload.setToolTip("Reload exceptions from the file")
        exc_btn_row.addWidget(exc_reload)

        exc_edit = QPushButton("Edit")
        exc_edit.setCursor(Qt.PointingHandCursor)
        exc_edit.clicked.connect(self._edit_exceptions)
        exc_edit.setToolTip("Edit the word exceptions list")
        exc_btn_row.addWidget(exc_edit)
        exc_btn_row.addStretch()
        layout.addLayout(exc_btn_row)

        layout.addStretch()
        return tab

    def _reload_traps(self) -> None:
        self._session.reload_trap_endings()
        self._trap_status.setText(
            f"{len(self._session.engine.trap_endings)} loaded"
        )

    def _reload_exceptions(self) -> None:
        self._session.reload_exceptions()
        self._exc_status.setText(
            f"{len(self._session.engine.word_exceptions)} loaded"
        )

    def _edit_traps(self) -> None:
        from config.trap_endings import TRAP_ENDINGS_FILE
        EditorDialog(
            self._main,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self._session.reload_trap_endings,
            default_content="# Trap endings - one per line, hardest first\n",
            status_callback=lambda c: self._trap_status.setText(f"{c} loaded"),
        )

    def _edit_exceptions(self) -> None:
        from config.exceptions import EXCEPTIONS_FILE
        EditorDialog(
            self._main,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self._session.reload_exceptions,
            default_content="# Word exceptions - one per line\n",
            status_callback=lambda c: self._exc_status.setText(f"{c} loaded"),
        )

    def refresh_dict_label(self) -> None:
        self._dict_label.setText(self._view.dict_label)


# ---------------------------------------------------------------------------
# Advanced Panel (dockable — no window chrome)
# ---------------------------------------------------------------------------


class AdvancedPanel(QWidget):
    """Plain widget with Advanced settings tabs — used inside QDockWidget."""

    def __init__(self, main_window) -> None:
        super().__init__()
        self._main = main_window
        self._session = main_window.session
        self._view = main_window.view

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._build_dict_tab(), "Dictionary")
        tabs.addTab(self._build_timing_tab(), "Timing")
        tabs.addTab(self._build_typing_tab(), "Typing")
        tabs.addTab(self._build_traps_tab(), "Trap Endings")
        layout.addWidget(tabs)

    def _build_dict_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        self._dict_label = QLabel(self._view.dict_label)
        self._dict_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #71717a;")
        layout.addWidget(self._dict_label)

        load_btn = QPushButton("Load Dictionary")
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.clicked.connect(self._main.on_load_dict)
        load_btn.setToolTip("Open a .json or .txt word list file")
        layout.addWidget(load_btn)

        layout.addStretch()
        return tab

    def _build_timing_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        pre_label = QLabel("Pre-type delay:")
        pre_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(pre_label)

        pre_row = QHBoxLayout()
        self._pre_spin = QSpinBox()
        self._pre_spin.setRange(100, 2000)
        self._pre_spin.setSingleStep(50)
        self._pre_spin.setSuffix(" ms")
        self._pre_spin.setValue(self._view.pre_delay_ms)
        self._pre_spin.valueChanged.connect(self._on_pre_changed)
        self._pre_spin.setToolTip("Pause before typing the first character")
        pre_row.addWidget(self._pre_spin)
        pre_row.addStretch()
        layout.addLayout(pre_row)

        post_label = QLabel("Post-type delay:")
        post_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b; "
                                 "padding-top: 6px;")
        layout.addWidget(post_label)

        post_row = QHBoxLayout()
        self._post_spin = QSpinBox()
        self._post_spin.setRange(100, 2000)
        self._post_spin.setSingleStep(50)
        self._post_spin.setSuffix(" ms")
        self._post_spin.setValue(self._view.post_delay_ms)
        self._post_spin.valueChanged.connect(self._on_post_changed)
        self._post_spin.setToolTip("Pause after pressing Enter")
        post_row.addWidget(self._post_spin)
        post_row.addStretch()
        layout.addLayout(post_row)

        layout.addStretch()
        return tab

    def _on_pre_changed(self, val: int) -> None:
        self._view.set_shared_delays(val, self._view.post_delay_ms)

    def _on_post_changed(self, val: int) -> None:
        self._view.set_shared_delays(self._view.pre_delay_ms, val)

    def _build_typing_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        auto_row = QHBoxLayout()
        auto_label = QLabel("Auto Type Prefix:")
        auto_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        auto_row.addWidget(auto_label)

        self._auto_type_combo = QComboBox()
        self._auto_type_combo.addItems(["On", "Off"])
        self._auto_type_combo.setCurrentText(
            "On" if self._view.auto_type_prefix_enabled else "Off"
        )
        self._auto_type_combo.currentTextChanged.connect(self._on_auto_type_changed)
        self._auto_type_combo.setToolTip(
            "On: types only the ending / Off: types the full word"
        )
        auto_row.addWidget(self._auto_type_combo)
        auto_row.addStretch()
        layout.addLayout(auto_row)

        layout.addStretch()
        return tab

    def _on_auto_type_changed(self, text: str) -> None:
        self._view.set_auto_type_prefix(text == "On")

    def _build_traps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)

        trap_header = QLabel("Trap endings")
        trap_header.setStyleSheet("font: 8pt 'Segoe UI'; font-weight: bold; "
                                  "color: #18181b;")
        layout.addWidget(trap_header)

        self._trap_status = QLabel(
            f"{len(self._session.engine.trap_endings)} loaded"
        )
        self._trap_status.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(self._trap_status)

        trap_btn_row = QHBoxLayout()
        trap_reload = QPushButton("Reload")
        trap_reload.setCursor(Qt.PointingHandCursor)
        trap_reload.clicked.connect(self._reload_traps)
        trap_reload.setToolTip("Reload trap endings from the file")
        trap_btn_row.addWidget(trap_reload)

        trap_edit = QPushButton("Edit")
        trap_edit.setCursor(Qt.PointingHandCursor)
        trap_edit.clicked.connect(self._edit_traps)
        trap_edit.setToolTip("Edit the trap endings list")
        trap_btn_row.addWidget(trap_edit)
        trap_btn_row.addStretch()
        layout.addLayout(trap_btn_row)

        exc_header = QLabel("Exceptions")
        exc_header.setStyleSheet("font: 8pt 'Segoe UI'; font-weight: bold; "
                                 "color: #18181b; padding-top: 12px;")
        layout.addWidget(exc_header)

        self._exc_status = QLabel(
            f"{len(self._session.engine.word_exceptions)} loaded"
        )
        self._exc_status.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        layout.addWidget(self._exc_status)

        exc_btn_row = QHBoxLayout()
        exc_reload = QPushButton("Reload")
        exc_reload.setCursor(Qt.PointingHandCursor)
        exc_reload.clicked.connect(self._reload_exceptions)
        exc_reload.setToolTip("Reload exceptions from the file")
        exc_btn_row.addWidget(exc_reload)

        exc_edit = QPushButton("Edit")
        exc_edit.setCursor(Qt.PointingHandCursor)
        exc_edit.clicked.connect(self._edit_exceptions)
        exc_edit.setToolTip("Edit the word exceptions list")
        exc_btn_row.addWidget(exc_edit)
        exc_btn_row.addStretch()
        layout.addLayout(exc_btn_row)

        layout.addStretch()
        return tab

    def _reload_traps(self) -> None:
        self._session.reload_trap_endings()
        self._trap_status.setText(
            f"{len(self._session.engine.trap_endings)} loaded"
        )

    def _reload_exceptions(self) -> None:
        self._session.reload_exceptions()
        self._exc_status.setText(
            f"{len(self._session.engine.word_exceptions)} loaded"
        )

    def _edit_traps(self) -> None:
        from config.trap_endings import TRAP_ENDINGS_FILE
        EditorDialog(
            self._main,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self._session.reload_trap_endings,
            default_content="# Trap endings - one per line, hardest first\n",
            status_callback=lambda c: self._trap_status.setText(f"{c} loaded"),
        )

    def _edit_exceptions(self) -> None:
        from config.exceptions import EXCEPTIONS_FILE
        EditorDialog(
            self._main,
            title="Edit Exceptions",
            file_path=EXCEPTIONS_FILE,
            reload_callback=self._session.reload_exceptions,
            default_content="# Word exceptions - one per line\n",
            status_callback=lambda c: self._exc_status.setText(f"{c} loaded"),
        )

    def refresh_dict_label(self) -> None:
        self._dict_label.setText(self._view.dict_label)


# ---------------------------------------------------------------------------
# Used Words dialog
# ---------------------------------------------------------------------------


class UsedWordsDialog(QDialog):
    """Persistent window showing previously used words."""

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self._main = main_window
        self._session = main_window.session
        self.setWindowTitle("Used Words")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(280, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._listbox = QListWidget()
        self._listbox.setFont(QFont("Consolas", 10))
        self._listbox.setAlternatingRowColors(True)
        layout.addWidget(self._listbox)

        self._count_label = QLabel("0 words used")
        self._count_label.setStyleSheet(
            "font: 8pt 'Segoe UI'; color: #71717a;"
        )
        layout.addWidget(self._count_label)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.update_list()

    def update_list(self) -> None:
        words, count = self._session.used_words_for_display()
        self._listbox.clear()
        for word in words:
            self._listbox.addItem(word)
        self._count_label.setText(f"{count} words used")
