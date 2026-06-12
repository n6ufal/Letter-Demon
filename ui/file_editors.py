"""Modal text editors for trap endings and exceptions files (Qt)."""

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QShortcut,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


C_SEARCH_BG = QColor("#fef08a")
C_SEARCH_FG = QColor("#1a1a1a")


class EditorDialog(QWidget):
    """Modal text editor window for trap endings / exceptions files."""

    def __init__(
        self,
        main_window,
        *,
        title: str,
        file_path: str,
        reload_callback,
        default_content: str,
        status_callback=None,
    ) -> None:
        super().__init__(main_window, Qt.Window)
        self._main = main_window
        self._file_path = file_path
        self._reload_callback = reload_callback
        self._status_callback = status_callback
        self._default_content = default_content
        self._search_term = ""
        self._match_positions: list[int] = []
        self._match_index = 0

        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(640, 480)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setUndoRedoEnabled(True)
        self._text_edit.setTabStopDistance(20)
        layout.addWidget(self._text_edit)

        # Load content
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = self._default_content
        self._text_edit.setPlainText(content)

        # Search bar
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)

        find_label = QLabel("Find:")
        find_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #18181b;")
        search_row.addWidget(find_label)

        self._search_entry = QLineEdit()
        self._search_entry.setPlaceholderText("")
        self._search_entry.textChanged.connect(self._on_search)
        self._search_entry.setStyleSheet(
            "font: 8pt 'Segoe UI'; padding: 2px 4px; "
            "border: 1px solid #d4d4d4; border-radius: 2px;"
        )
        search_row.addWidget(self._search_entry, 1)

        self._match_label = QLabel("")
        self._match_label.setStyleSheet("font: 8pt 'Segoe UI'; color: #71717a;")
        self._match_label.setFixedWidth(70)
        search_row.addWidget(self._match_label)

        self._prev_btn = QPushButton("\u25c0")
        self._prev_btn.setFixedWidth(24)
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(self._go_prev)
        search_row.addWidget(self._prev_btn)

        self._next_btn = QPushButton("\u25b6")
        self._next_btn.setFixedWidth(24)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._go_next)
        search_row.addWidget(self._next_btn)

        layout.addLayout(search_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(
            "font: 8pt 'Segoe UI'; font-weight: bold; padding: 3px 10px; "
            "border: none; border-radius: 3px; "
            "background: #16a34a; color: #ffffff;"
        )
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

        # Shortcuts
        save_sc = QShortcut(QKeySequence("Ctrl+S"), self)
        save_sc.activated.connect(self._save_and_close)
        esc_sc = QShortcut(QKeySequence("Escape"), self)
        esc_sc.activated.connect(self.close)

        self._text_edit.setFocus()
        self.show()

    # -- Search --

    def _on_search(self, text: str) -> None:
        self._search_term = text
        self._reset_highlight()
        if not text:
            self._match_label.setText("")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            self._match_positions = []
            return

        self._match_positions = []
        fmt = QTextCharFormat()
        fmt.setBackground(C_SEARCH_BG)
        fmt.setForeground(C_SEARCH_FG)

        pos = 0
        doc = self._text_edit.document()
        while True:
            c = doc.find(text, pos, QTextDocument.FindCaseInsensitively)
            if c.isNull():
                break
            c.mergeCharFormat(fmt)
            self._match_positions.append(c.position())
            pos = c.position()

        if self._match_positions:
            self._match_index = 0
            self._highlight_current()
            self._match_label.setText(
                f"{self._match_index + 1}/{len(self._match_positions)}"
            )
            self._prev_btn.setEnabled(True)
            self._next_btn.setEnabled(True)
        else:
            self._match_label.setText("0 matches")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)

    def _go_prev(self) -> None:
        if not self._match_positions:
            return
        self._match_index = (self._match_index - 1) % len(self._match_positions)
        self._highlight_current()

    def _go_next(self) -> None:
        if not self._match_positions:
            return
        self._match_index = (self._match_index + 1) % len(self._match_positions)
        self._highlight_current()

    def _highlight_current(self) -> None:
        if not self._match_positions:
            return
        pos = self._match_positions[self._match_index]
        cursor = QTextCursor(self._text_edit.document())
        cursor.setPosition(pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.Left,
            QTextCursor.MoveMode.KeepAnchor,
            len(self._search_term),
        )
        self._text_edit.setTextCursor(cursor)
        self._text_edit.centerCursor()
        self._match_label.setText(
            f"{self._match_index + 1}/{len(self._match_positions)}"
        )

    def _reset_highlight(self) -> None:
        doc = self._text_edit.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        cursor.mergeCharFormat(fmt)

    # -- Save --

    def _save_and_close(self) -> None:
        content = self._text_edit.toPlainText().strip()
        try:
            fp = Path(self._file_path)
            if fp.exists():
                shutil.copy2(fp, fp.with_suffix(".bak"))
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
                if content and not content.endswith("\n"):
                    f.write("\n")
            self._reload_callback()
            if self._status_callback:
                basename = fp.name.lower()
                if basename == "trap_endings.txt":
                    count = len(self._main.session.engine.trap_endings)
                elif basename == "exceptions.txt":
                    count = len(self._main.session.engine.word_exceptions)
                else:
                    count = 0
                self._status_callback(count)
            self.close()
        except Exception as e:
            self._main.view.show_feedback(
                "error", f"Could not save file: {e}", duration_ms=8000
            )
