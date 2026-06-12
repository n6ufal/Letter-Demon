"""QSS stylesheet — single source of truth for all UI styling."""

QSS = """
/* Main background */
QMainWindow, QWidget#mainWidget {
    background: #fafafa;
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
"""

__all__ = ["QSS"]
