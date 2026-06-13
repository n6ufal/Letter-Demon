"""QSS stylesheets — LIGHT_QSS and DARK_QSS for the entire application."""

def apply_theme(is_dark: bool = False) -> None:
    from PySide6.QtWidgets import QApplication
    qss = DARK_QSS if is_dark else LIGHT_QSS
    QApplication.instance().setStyleSheet(qss)


LIGHT_QSS = """
/* Main background */
QMainWindow, QWidget#mainWidget {
    background: #fafafa;
}

/* Settings cards */
QFrame#settingsCard {
    background: #f4f4f5;
    border-radius: 6px;
}

/* Header */
QLabel#headerLabel {
    font: 8pt "Segoe UI";
    font-weight: bold;
    color: #18181b;
}

/* Feedback label */
QLabel#feedbackLabel {
    font: 8pt "Segoe UI";
    padding: 1px 6px;
    border-radius: 3px;
}
QLabel#feedbackLabel[feedbackLevel="warn"] {
    background: #fef3c7;
    color: #92400e;
}
QLabel#feedbackLabel[feedbackLevel="error"] {
    background: #fee2e2;
    color: #991b1b;
}

/* Prefix entry */
QLineEdit#prefixEntry {
    font: 16pt "Segoe UI";
    padding: 6px 8px;
    border: 1px solid #d4d4d4;
    border-radius: 4px;
    background: #ffffff;
    color: #18181b;
    selection-background-color: #16a34a;
    selection-color: #ffffff;
}
QLineEdit#prefixEntry:focus {
    border: 2px solid #16a34a;
}

/* Play button */
QPushButton#playBtnActive {
    font: 10pt "Segoe UI";
    font-weight: bold;
    padding: 8px;
    border: none;
    border-radius: 4px;
    background: #16a34a;
    color: #ffffff;
}
QPushButton#playBtnActive:hover {
    background: #15803d;
}
QPushButton#playBtnActive:pressed {
    background: #166534;
}
QPushButton#playBtnInactive {
    font: 10pt "Segoe UI";
    font-weight: bold;
    padding: 8px;
    border: none;
    border-radius: 4px;
    background: #f4f4f5;
    color: #991b1b;
}
QPushButton#playBtnInactive:hover {
    background: #e4e4e7;
}
QPushButton#playBtnInactive:pressed {
    background: #d4d4d8;
}
QPushButton#playBtnActive:disabled,
QPushButton#playBtnInactive:disabled {
    background: #e4e4e7;
    color: #a1a1aa;
}

/* Slider labels */
QLabel#sliderLabel {
    font: 8pt "Segoe UI";
    color: #18181b;
}
QLabel#sliderValue {
    font: 8pt "Consolas";
    color: #18181b;
}
QLabel#comboLabel {
    font: 8pt "Segoe UI";
    color: #18181b;
}

/* Sliders */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #e4e4e7;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #18181b;
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #16a34a;
}
QSlider::sub-page:horizontal {
    background: #16a34a;
    border-radius: 3px;
}

/* Comboboxes */
QComboBox {
    font: 8pt "Segoe UI";
    padding: 2px 4px;
    border: 1px solid #d4d4d4;
    border-radius: 3px;
    background: #ffffff;
    color: #18181b;
}
QComboBox:focus {
    border: 1px solid #16a34a;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #71717a;
    margin-right: 4px;
}
QComboBox:hover {
    border: 1px solid #a1a1aa;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #18181b;
    selection-background-color: #e4e4e7;
    border: 1px solid #d4d4d4;
}

/* Separator */
QFrame#separator {
    color: #e4e4e7;
    max-height: 1px;
}

/* Action buttons */
QPushButton#actionBtn {
    font: 8pt "Segoe UI";
    padding: 4px 12px;
    border: none;
    border-radius: 3px;
    background: #e4e4e7;
    color: #18181b;
}
QPushButton#actionBtn:hover {
    background: #d4d4d8;
}
QPushButton#actionBtn:pressed {
    background: #a1a1aa;
}

/* Info bar dots */
QLabel#dictDot, QLabel#autoPrefixDot, QLabel#robloxDot {
    font: 8pt "Segoe UI";
}

/* Info bar labels */
QLabel#dictCountLabel, QLabel#autoPrefixLabel, QLabel#robloxStatusLabel {
    font: 8pt "Segoe UI";
    padding-left: 2px;
}

/* Bottom row */
QLabel#usedWordsLabel {
    font: 8pt "Segoe UI";
    color: #71717a;
}
QLabel#usedWordsLabel:hover {
    color: #18181b;
}
QLabel#creditLabel {
    font: 7pt "Segoe UI";
    color: #71717a;
}
QLabel#creditLabel:hover {
    color: #18181b;
}

/* Tooltips */
QToolTip {
    background: #1f2937;
    color: #f9fafb;
    border: none;
    padding: 4px 6px;
    font: 8pt "Segoe UI";
}

/* Status bar */
QStatusBar {
    font: 8pt "Segoe UI";
    color: #71717a;
    background: #fafafa;
    border-top: 1px solid #e4e4e7;
}

/* Menu bar */
QMenuBar {
    font: 8pt "Segoe UI";
    background: #fafafa;
    color: #18181b;
    border-bottom: 1px solid #e4e4e7;
}
QMenuBar::item:selected {
    background: #e4e4e7;
}
QMenu {
    font: 8pt "Segoe UI";
    background: #ffffff;
    color: #18181b;
    border: 1px solid #e4e4e7;
}
QMenu::item:selected {
    background: #e4e4e7;
}

/* Dock widget */
QDockWidget {
    font: 8pt "Segoe UI";
    color: #18181b;
    titlebar-close-icon: url(none);
}

/* Progress bar */
QProgressBar {
    border: none;
    border-radius: 2px;
    background: #e4e4e7;
    max-height: 4px;
}
QProgressBar::chunk {
    background: #16a34a;
    border-radius: 2px;
}
"""


DARK_QSS = """
/* Main background */
QMainWindow, QWidget#mainWidget {
    background: #1e1e2e;
}

/* Settings cards */
QFrame#settingsCard {
    background: #2a2a3e;
    border-radius: 6px;
}

/* Header */
QLabel#headerLabel {
    font: 8pt "Segoe UI";
    font-weight: bold;
    color: #e4e4e7;
}

/* Feedback label */
QLabel#feedbackLabel {
    font: 8pt "Segoe UI";
    padding: 1px 6px;
    border-radius: 3px;
}
QLabel#feedbackLabel[feedbackLevel="warn"] {
    background: #422006;
    color: #fcd34d;
}
QLabel#feedbackLabel[feedbackLevel="error"] {
    background: #450a0a;
    color: #fca5a5;
}

/* Prefix entry */
QLineEdit#prefixEntry {
    font: 16pt "Segoe UI";
    padding: 6px 8px;
    border: 1px solid #4a4a5e;
    border-radius: 4px;
    background: #3a3a4e;
    color: #e4e4e7;
    selection-background-color: #16a34a;
    selection-color: #ffffff;
}
QLineEdit#prefixEntry:focus {
    border: 2px solid #16a34a;
}

/* Play button */
QPushButton#playBtnActive {
    font: 10pt "Segoe UI";
    font-weight: bold;
    padding: 8px;
    border: none;
    border-radius: 4px;
    background: #16a34a;
    color: #ffffff;
}
QPushButton#playBtnActive:hover {
    background: #22c55e;
}
QPushButton#playBtnActive:pressed {
    background: #15803d;
}
QPushButton#playBtnInactive {
    font: 10pt "Segoe UI";
    font-weight: bold;
    padding: 8px;
    border: none;
    border-radius: 4px;
    background: #2a2a3e;
    color: #fca5a5;
}
QPushButton#playBtnInactive:hover {
    background: #3a3a4e;
}
QPushButton#playBtnInactive:pressed {
    background: #4a4a5e;
}
QPushButton#playBtnActive:disabled,
QPushButton#playBtnInactive:disabled {
    background: #3a3a4e;
    color: #6b7280;
}

/* Slider labels */
QLabel#sliderLabel {
    font: 8pt "Segoe UI";
    color: #e4e4e7;
}
QLabel#sliderValue {
    font: 8pt "Consolas";
    color: #9ca3af;
}
QLabel#comboLabel {
    font: 8pt "Segoe UI";
    color: #e4e4e7;
}

/* Sliders */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #4a4a5e;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #e4e4e7;
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #16a34a;
}
QSlider::sub-page:horizontal {
    background: #16a34a;
    border-radius: 3px;
}

/* Comboboxes */
QComboBox {
    font: 8pt "Segoe UI";
    padding: 2px 4px;
    border: 1px solid #4a4a5e;
    border-radius: 3px;
    background: #3a3a4e;
    color: #e4e4e7;
}
QComboBox:focus {
    border: 1px solid #16a34a;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9ca3af;
    margin-right: 4px;
}
QComboBox:hover {
    border: 1px solid #6b7280;
}
QComboBox QAbstractItemView {
    background: #2a2a3e;
    color: #e4e4e7;
    selection-background-color: #3a3a4e;
    border: 1px solid #4a4a5e;
}

/* Separator */
QFrame#separator {
    color: #4a4a5e;
    max-height: 1px;
}

/* Action buttons */
QPushButton#actionBtn {
    font: 8pt "Segoe UI";
    padding: 4px 12px;
    border: none;
    border-radius: 3px;
    background: #3a3a4e;
    color: #e4e4e7;
}
QPushButton#actionBtn:hover {
    background: #4a4a5e;
}
QPushButton#actionBtn:pressed {
    background: #5a5a6e;
}

/* Info bar dots */
QLabel#dictDot, QLabel#autoPrefixDot, QLabel#robloxDot {
    font: 8pt "Segoe UI";
}

/* Info bar labels */
QLabel#dictCountLabel, QLabel#autoPrefixLabel, QLabel#robloxStatusLabel {
    font: 8pt "Segoe UI";
    padding-left: 2px;
    color: #9ca3af;
}

/* Bottom row */
QLabel#usedWordsLabel {
    font: 8pt "Segoe UI";
    color: #9ca3af;
}
QLabel#usedWordsLabel:hover {
    color: #e4e4e7;
}
QLabel#creditLabel {
    font: 7pt "Segoe UI";
    color: #9ca3af;
}
QLabel#creditLabel:hover {
    color: #e4e4e7;
}

/* Tooltips */
QToolTip {
    background: #1f2937;
    color: #f9fafb;
    border: none;
    padding: 4px 6px;
    font: 8pt "Segoe UI";
}

/* Status bar */
QStatusBar {
    font: 8pt "Segoe UI";
    color: #9ca3af;
    background: #1e1e2e;
    border-top: 1px solid #4a4a5e;
}

/* Menu bar */
QMenuBar {
    font: 8pt "Segoe UI";
    background: #1e1e2e;
    color: #e4e4e7;
    border-bottom: 1px solid #4a4a5e;
}
QMenuBar::item:selected {
    background: #3a3a4e;
}
QMenu {
    font: 8pt "Segoe UI";
    background: #2a2a3e;
    color: #e4e4e7;
    border: 1px solid #4a4a5e;
}
QMenu::item:selected {
    background: #3a3a4e;
}

/* Dock widget */
QDockWidget {
    font: 8pt "Segoe UI";
    color: #e4e4e7;
    titlebar-close-icon: url(none);
}

/* Progress bar */
QProgressBar {
    border: none;
    border-radius: 2px;
    background: #4a4a5e;
    max-height: 4px;
}
QProgressBar::chunk {
    background: #16a34a;
    border-radius: 2px;
}
"""


__all__ = ["LIGHT_QSS", "DARK_QSS", "apply_theme"]
