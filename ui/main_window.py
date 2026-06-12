"""Main application window — controller and top-level QMainWindow."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Top-level application window.

    Owns the session and main widget. Wires signals to slots.
    Phased migration from tkinter LetterDemonApp.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("\U0001f608")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setFixedSize(400, 300)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("Phase 1 skeleton — ready for MainWidget"))
