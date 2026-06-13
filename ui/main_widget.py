"""Main window widget — owns all widgets and Qt state."""

from PySide6.QtCore import Qt, QPropertyAnimation, QRegularExpression, QTimer, Signal
from PySide6.QtGui import QColor, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

from . import modes


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWidget(QWidget):
    """Owns all main-window widgets and Qt state.

    Emits signals for the controller to handle.
    """

    play_requested = Signal()
    dict_load_requested = Signal()
    advanced_requested = Signal()
    clear_used_requested = Signal()
    used_words_requested = Signal()
    about_requested = Signal()
    dict_dropped = Signal(str)                # path

    status_dict_changed = Signal(str, str)    # text, color name
    status_prefix_changed = Signal(str, str)  # text, color name
    status_roblox_changed = Signal(str, str)  # text, color name

    def __init__(self, settings: dict) -> None:
        super().__init__()
        self.setObjectName("mainWidget")
        self._feedback_timer: QTimer | None = None
        self._feedback_anim: QPropertyAnimation | None = None
        self._settings = settings
        self._build()
        self._add_drop_shadows()
        self._wire_tooltips()
        self._apply_defaults(settings)
        self._wire_signals()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self._build_header(layout)
        self._build_entry(layout)
        self._build_play_button(layout)
        self._build_settings_panel(layout)
        self._build_separator(layout)
        self._build_action_buttons(layout)
        self._build_bottom_row(layout)

    def _build_header(self, parent: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Starting letters:")
        label.setObjectName("headerLabel")
        row.addWidget(label)
        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("feedbackLabel")
        row.addWidget(self.feedback_label, 1)
        parent.addLayout(row)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        self.entry = QLineEdit()
        self.entry.setObjectName("prefixEntry")
        self.entry.setPlaceholderText("")
        self.entry.setMaxLength(18)
        validator = QRegularExpressionValidator(QRegularExpression("[A-Za-z]*"))
        self.entry.setValidator(validator)
        parent.addWidget(self.entry)

    def _build_play_button(self, parent: QVBoxLayout) -> None:
        self.play_btn = QPushButton("Click to load a dictionary")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setDefault(True)
        parent.addWidget(self.play_btn)

    def _build_settings_panel(self, parent: QVBoxLayout) -> None:
        self._settings_section = QWidget()
        self._settings_section.setObjectName("settingsSection")
        panel = QVBoxLayout(self._settings_section)
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setSpacing(4)

        # Card 1: Speed + Mode
        card1 = QFrame()
        card1.setObjectName("settingsCard")
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(8, 6, 8, 6)
        card1_layout.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)

        speed_row = QHBoxLayout()
        speed_row.setContentsMargins(0, 0, 0, 0)
        speed_label = QLabel("Speed:")
        speed_label.setObjectName("sliderLabel")
        speed_label.setFixedWidth(50)
        speed_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        speed_row.addWidget(speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setObjectName("speedSlider")
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setPageStep(5)
        self.speed_slider.setFixedWidth(140)
        speed_row.addWidget(self.speed_slider)

        self.speed_val_label = QLabel()
        self.speed_val_label.setObjectName("sliderValue")
        self.speed_val_label.setFixedWidth(70)
        self.speed_val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        speed_row.addWidget(self.speed_val_label)
        row1.addLayout(speed_row, 1)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(12, 0, 0, 0)
        mode_label = QLabel("Mode:")
        mode_label.setObjectName("comboLabel")
        mode_row.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("modeCombo")
        self.mode_combo.addItems(modes.MODE_DISPLAY)
        self.mode_combo.setFixedWidth(80)
        mode_row.addWidget(self.mode_combo)
        row1.addLayout(mode_row)
        card1_layout.addLayout(row1)
        panel.addWidget(card1)

        # Card 2: Humanizer + Fallback
        card2 = QFrame()
        card2.setObjectName("settingsCard")
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(8, 6, 8, 6)
        card2_layout.setSpacing(4)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)

        human_row = QHBoxLayout()
        human_row.setContentsMargins(0, 0, 0, 0)
        human_label = QLabel("Human:")
        human_label.setObjectName("sliderLabel")
        human_label.setFixedWidth(50)
        human_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        human_row.addWidget(human_label)

        self.humanizer_slider = QSlider(Qt.Horizontal)
        self.humanizer_slider.setObjectName("humanizerSlider")
        self.humanizer_slider.setRange(0, 100)
        self.humanizer_slider.setPageStep(5)
        self.humanizer_slider.setFixedWidth(140)
        human_row.addWidget(self.humanizer_slider)

        self.humanizer_val_label = QLabel()
        self.humanizer_val_label.setObjectName("sliderValue")
        self.humanizer_val_label.setFixedWidth(70)
        self.humanizer_val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        human_row.addWidget(self.humanizer_val_label)
        row2.addLayout(human_row, 1)

        fallback_row = QHBoxLayout()
        fallback_row.setContentsMargins(12, 0, 0, 0)
        fallback_label = QLabel("Fall:")
        fallback_label.setObjectName("comboLabel")
        fallback_row.addWidget(fallback_label)
        self.fallback_combo = QComboBox()
        self.fallback_combo.setObjectName("fallbackCombo")
        self.fallback_combo.addItems(modes.FALLBACK_DISPLAY)
        self.fallback_combo.setFixedWidth(80)
        fallback_row.addWidget(self.fallback_combo)
        row2.addLayout(fallback_row)
        card2_layout.addLayout(row2)
        panel.addWidget(card2)
        parent.addWidget(self._settings_section)

    def _build_separator(self, parent: QVBoxLayout) -> None:
        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.HLine)
        self._separator.setFrameShadow(QFrame.Sunken)
        self._separator.setObjectName("separator")
        parent.addWidget(self._separator)

    def _build_action_buttons(self, parent: QVBoxLayout) -> None:
        self._actions_section = QWidget()
        self._actions_section.setObjectName("actionsSection")
        row = QHBoxLayout(self._actions_section)
        row.setContentsMargins(0, 0, 0, 0)
        self.advanced_btn = QPushButton("Advanced")
        self.advanced_btn.setObjectName("actionBtn")
        self.advanced_btn.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.advanced_btn)
        self.clear_used_btn = QPushButton("Clear Used")
        self.clear_used_btn.setObjectName("actionBtn")
        self.clear_used_btn.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.clear_used_btn)
        parent.addWidget(self._actions_section)

    def _build_bottom_row(self, parent: QVBoxLayout) -> None:
        self._bottom_section = QWidget()
        self._bottom_section.setObjectName("bottomSection")
        row = QHBoxLayout(self._bottom_section)
        row.setContentsMargins(0, 0, 0, 0)

        self.used_words_label = _ClickableLabel("Used words")
        self.used_words_label.setObjectName("usedWordsLabel")
        self.used_words_label.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.used_words_label)

        row.addStretch()

        self._credit_label = _ClickableLabel("Made by n6ufal")
        self._credit_label.setObjectName("creditLabel")
        self._credit_label.setCursor(Qt.PointingHandCursor)
        row.addWidget(self._credit_label)

        parent.addWidget(self._bottom_section)

    # ------------------------------------------------------------------
    # Defaults & wiring
    # ------------------------------------------------------------------

    def _apply_defaults(self, settings: dict) -> None:
        self.speed_slider.setValue(settings.get("wpm", 70))
        self.mode_combo.setCurrentText(
            modes.to_display_mode(settings.get("mode", "Trap Words"))
        )
        self.fallback_combo.setCurrentText(
            modes.to_display_fallback(settings.get("fallback", "Short Words"))
        )
        self.humanizer_slider.setValue(settings.get("jitter_intensity", 75))
        self.slider_value_changed()
        self.speed_slider.valueChanged.connect(self.slider_value_changed)
        self.humanizer_slider.valueChanged.connect(self.slider_value_changed)

    def slider_value_changed(self) -> None:
        wpm = self.speed_slider.value()
        self.speed_val_label.setText(f"{wpm} WPM")
        human = self.humanizer_slider.value()
        self.humanizer_val_label.setText(f"{human}%")
        self.speed_val_label.setToolTip(
            f"{wpm} WPM (\u2248{12000 // max(wpm, 1)} ms/char)"
        )

    def _wire_signals(self) -> None:
        self.play_btn.clicked.connect(self.play_requested.emit)
        self.advanced_btn.clicked.connect(self.advanced_requested.emit)
        self.clear_used_btn.clicked.connect(self.clear_used_requested.emit)
        self.used_words_label.clicked.connect(self.used_words_requested.emit)
        self._credit_label.clicked.connect(self.about_requested.emit)

    # ------------------------------------------------------------------
    # Drop shadows
    # ------------------------------------------------------------------

    def _add_drop_shadows(self) -> None:
        entry_shadow = QGraphicsDropShadowEffect()
        entry_shadow.setBlurRadius(8)
        entry_shadow.setOffset(0, 1)
        entry_shadow.setColor(QColor(0, 0, 0, 32))
        self.entry.setGraphicsEffect(entry_shadow)

        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(8)
        btn_shadow.setOffset(0, 2)
        btn_shadow.setColor(QColor(0, 0, 0, 40))
        self.play_btn.setGraphicsEffect(btn_shadow)

    # ------------------------------------------------------------------
    # Drag-and-drop support
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith((".json", ".txt")):
                    event.acceptProposedAction()
                    self._show_drag_indicator(True)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._show_drag_indicator(False)

    def dropEvent(self, event) -> None:
        self._show_drag_indicator(False)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith((".json", ".txt")):
                self.dict_dropped.emit(path)
                break

    def _show_drag_indicator(self, visible: bool) -> None:
        if visible:
            self.setStyleSheet(
                "QWidget#mainWidget { border: 2px dashed #16a34a; }"
            )
        else:
            self.setStyleSheet("")

    # ------------------------------------------------------------------
    # Theme switching
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool) -> None:
        from .theme import apply_theme
        apply_theme(is_dark)

    # ------------------------------------------------------------------
    # Compact mode
    # ------------------------------------------------------------------

    def set_compact_mode(self, enabled: bool) -> None:
        self._settings_section.setVisible(not enabled)
        self._separator.setVisible(not enabled)
        self._actions_section.setVisible(not enabled)
        self._bottom_section.setVisible(not enabled)

    # ------------------------------------------------------------------
    # Tooltips
    # ------------------------------------------------------------------

    def _wire_tooltips(self) -> None:
        self.speed_slider.setToolTip(
            "Typing speed in WPM (70\u2013200 is typical)"
        )
        self.humanizer_slider.setToolTip(
            "Human-like timing variation (0 = robotic)"
        )
        self.mode_combo.setToolTip("Primary strategy for picking the word")
        self.fallback_combo.setToolTip(
            "Backup strategy when primary mode finds nothing"
        )
        self.advanced_btn.setToolTip(
            "Dictionary, timing, trap endings, exceptions"
        )
        self.clear_used_btn.setToolTip("Reset used words for a new game")
        self.used_words_label.setToolTip("Show words played this session")

    # ------------------------------------------------------------------
    # Controller-facing properties (read)
    # ------------------------------------------------------------------

    @property
    def prefix(self) -> str:
        return self.entry.text().strip()

    @property
    def mode(self) -> str:
        return self.mode_combo.currentText()

    @property
    def fallback(self) -> str:
        return self.fallback_combo.currentText()

    @property
    def speed_ms(self) -> float:
        wpm = self.speed_slider.value()
        return 12000.0 / wpm if wpm > 0 else 120.0

    @property
    def speed_wpm(self) -> int:
        return self.speed_slider.value()

    @property
    def jitter_intensity(self) -> int:
        return self.humanizer_slider.value()

    @property
    def pre_delay_ms(self) -> int:
        return self._pre_delay

    @property
    def post_delay_ms(self) -> int:
        return self._post_delay

    @property
    def auto_type_prefix_enabled(self) -> bool:
        return self._auto_type_prefix_enabled

    # ------------------------------------------------------------------
    # Update methods (called by controller)
    # ------------------------------------------------------------------

    def set_shared_delays(self, pre: int, post: int) -> None:
        self._pre_delay = pre
        self._post_delay = post

    def set_auto_type_prefix(self, enabled: bool) -> None:
        self._auto_type_prefix_enabled = enabled
        text = "Suffix" if enabled else "Full"
        color = "green" if enabled else "blue"
        self.status_prefix_changed.emit(text, color)

    def update_play_button(self, has_wordlist: bool) -> None:
        if not has_wordlist:
            self.play_btn.setText("Click to load a dictionary")
            self.play_btn.setObjectName("playBtnInactive")
            self._set_play_btn_state("inactive")
            self.play_btn.setToolTip(
                "No dictionary \u2014 click to load one"
            )
        else:
            self.play_btn.setText("Start (Ctrl+Enter)")
            self.play_btn.setObjectName("playBtnActive")
            self._set_play_btn_state("active")
            self.play_btn.setToolTip(
                "Type the word into Roblox (Ctrl+Enter)"
            )

    def _set_play_btn_state(self, state: str) -> None:
        if state == "active":
            self.play_btn.setProperty("playState", "active")
        else:
            self.play_btn.setProperty("playState", "inactive")
        self.play_btn.style().unpolish(self.play_btn)
        self.play_btn.style().polish(self.play_btn)

    def set_loading_state(self) -> None:
        self.play_btn.setText("Loading...")
        self.play_btn.setEnabled(False)

    def set_ready_state(self) -> None:
        self.play_btn.setEnabled(True)

    def clear_prefix(self) -> None:
        self.entry.clear()

    def show_feedback(
        self,
        level: str,
        message: str,
        *,
        duration_ms: int = 5000,
        beep: bool = False,
    ) -> None:
        if self._feedback_timer is not None and self._feedback_timer.isActive():
            self._feedback_timer.stop()
            self._feedback_timer = None

        if self._feedback_anim is not None and self._feedback_anim.state() == QPropertyAnimation.Running:
            self._feedback_anim.stop()
            self._feedback_anim = None

        css_class = "warn" if level == "warn" else "error"
        self.feedback_label.setText(message)
        self.feedback_label.setProperty("feedbackLevel", css_class)
        self.feedback_label.style().unpolish(self.feedback_label)
        self.feedback_label.style().polish(self.feedback_label)

        if beep:
            QApplication.beep()

        self._feedback_anim = QPropertyAnimation(self.feedback_label, b"windowOpacity")
        self._feedback_anim.setDuration(200)
        self._feedback_anim.setStartValue(0.0)
        self._feedback_anim.setEndValue(1.0)
        self._feedback_anim.start()

        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._clear_feedback)
        self._feedback_timer.start(duration_ms)

    def dismiss_feedback(self) -> None:
        if self._feedback_timer is not None:
            self._feedback_timer.stop()
            self._feedback_timer = None
        if self._feedback_anim is not None and self._feedback_anim.state() == QPropertyAnimation.Running:
            self._feedback_anim.stop()
            self._feedback_anim = None
        self._clear_feedback()

    def _clear_feedback(self) -> None:
        self.feedback_label.setText("")

    def update_dict_label(self, path: str | None) -> None:
        if path:
            from pathlib import Path
            self._dict_label = f"Dict: {Path(path).name}"
        else:
            self._dict_label = "Dict: none"

    @property
    def dict_label(self) -> str:
        return getattr(self, "_dict_label", "Dict: none")

    def set_trap_status(self, text: str) -> None:
        self._trap_status = text

    @property
    def trap_status(self) -> str:
        return getattr(self, "_trap_status", "")

    def set_exceptions_status(self, text: str) -> None:
        self._exceptions_status = text

    @property
    def exceptions_status(self) -> str:
        return getattr(self, "_exceptions_status", "")


