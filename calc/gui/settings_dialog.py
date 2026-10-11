"""The settings dialog, with a live preview of every appearance change.

The preview is a real, miniature instance of the same :class:`Keypad` and
:class:`DisplayWidget` the main window uses, styled by the same
:func:`~calc.gui.themes.build_stylesheet`.  That means what you see in the
dialog is literally the code path that styles the app -- not a mock-up that
could drift out of sync.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .display import DisplayWidget
from .keypad import Keypad
from .settings import AppSettings
from .themes import build_stylesheet, get_theme, theme_names

__all__ = ["SettingsDialog"]

ACCENT_PRESETS = [
    ("", "Theme default"),
    ("#3b82f6", "Blue"),
    ("#8b5cf6", "Violet"),
    ("#ec4899", "Pink"),
    ("#ef4444", "Red"),
    ("#f59e0b", "Amber"),
    ("#10b981", "Emerald"),
    ("#14b8a6", "Teal"),
    ("#06b6d4", "Cyan"),
]

GROUP_SEPARATORS = [(" ", "Space"), (",", "Comma"), (".", "Dot"), ("\u202f", "Narrow space")]


def _slider(minimum: int, maximum: int, value: int, tick: int = 1) -> QSlider:
    slider = QSlider(Qt.Horizontal)
    slider.setRange(minimum, maximum)
    slider.setValue(value)
    slider.setSingleStep(tick)
    slider.setPageStep(max(1, tick * 4))
    return slider


def _value_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "muted")
    label.setMinimumWidth(34)
    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return label


class SettingsDialog(QDialog):
    """Edits a *copy* of the settings; the caller decides whether to keep them."""

    applied = Signal(object)   # emitted with the draft AppSettings on Apply/OK

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(880, 640)
        self.settings = settings
        self.draft = AppSettings(
            appearance=settings.appearance.sanitised(),
            behaviour=settings.behaviour.sanitised(),
            home=settings.home,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_appearance_tab(), "Look & feel")
        self.tabs.addTab(self._build_behaviour_tab(), "Behaviour")

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
            | QDialogButtonBox.RestoreDefaults
        )
        self.reset_button = buttons.button(QDialogButtonBox.RestoreDefaults)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self.apply_button.clicked.connect(self._on_apply)
        self.reset_button.clicked.connect(self._on_reset)
        root.addWidget(buttons)

        self._connect_live_preview()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # appearance tab
    # ------------------------------------------------------------------
    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        controls = QWidget()
        form = QFormLayout(controls)
        form.setContentsMargins(0, 0, 8, 0)
        form.setSpacing(10)
        appearance = self.draft.appearance

        # theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(appearance.theme)
        form.addRow("Theme", self.theme_combo)

        # accent colour
        self.accent_combo = QComboBox()
        for value, label in ACCENT_PRESETS:
            self.accent_combo.addItem(_swatch(value) + label, value)
        self.accent_combo.addItem("\u25cf Custom\u2026", "__custom__")
        index = self.accent_combo.findData(appearance.accent_color)
        self.accent_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("Accent colour", self.accent_combo)

        # font
        self.font_combo = QComboBox()
        self.font_combo.addItem("System default", "")
        for family in sorted(QFontDatabase.families()):
            self.font_combo.addItem(family, family)
        font_index = self.font_combo.findData(appearance.font_family)
        self.font_combo.setCurrentIndex(font_index if font_index >= 0 else 0)
        form.addRow("Font", self.font_combo)

        # keypad mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Standard", "standard")
        self.mode_combo.addItem("Scientific", "scientific")
        self.mode_combo.setCurrentIndex(0 if appearance.keypad_mode == "standard" else 1)
        form.addRow("Keypad", self.mode_combo)

        # sliders
        self.radius_slider = _slider(0, 32, appearance.corner_radius)
        self.radius_value = _value_label(f"{appearance.corner_radius} px")
        form.addRow("Corner radius", _slider_row(self.radius_slider, self.radius_value))

        self.spacing_slider = _slider(0, 20, appearance.spacing)
        self.spacing_value = _value_label(f"{appearance.spacing} px")
        form.addRow("Button spacing", _slider_row(self.spacing_slider, self.spacing_value))

        self.height_slider = _slider(28, 120, appearance.key_height, 2)
        self.height_value = _value_label(f"{appearance.key_height} px")
        form.addRow("Key height", _slider_row(self.height_slider, self.height_value))

        self.key_font_slider = _slider(9, 32, appearance.key_font_size)
        self.key_font_value = _value_label(f"{appearance.key_font_size} pt")
        form.addRow("Key font size", _slider_row(self.key_font_slider, self.key_font_value))

        self.result_font_slider = _slider(18, 96, appearance.result_font_size)
        self.result_font_value = _value_label(f"{appearance.result_font_size} pt")
        form.addRow("Result font size", _slider_row(self.result_font_slider, self.result_font_value))

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.6, 1.8)
        self.scale_spin.setSingleStep(0.05)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setValue(appearance.ui_scale)
        self.scale_spin.setSuffix("\u00d7")
        form.addRow("Interface scale", self.scale_spin)

        # switches
        switches = QGroupBox("Effects")
        switch_layout = QVBoxLayout(switches)
        self.animations_check = QCheckBox("Animations")
        self.animations_check.setChecked(appearance.animations)
        self.ripples_check = QCheckBox("Ripple effect on keys")
        self.ripples_check.setChecked(appearance.ripples)
        self.side_panel_check = QCheckBox("Show side panel")
        self.side_panel_check.setChecked(appearance.show_side_panel)
        switch_layout.addWidget(self.animations_check)
        switch_layout.addWidget(self.ripples_check)
        switch_layout.addWidget(self.side_panel_check)
        form.addRow(switches)

        scroll.setWidget(controls)
        layout.addWidget(scroll, 3)

        # live preview
        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("CentralWidget")
        inner = QVBoxLayout(self.preview_frame)
        inner.setContentsMargins(10, 10, 10, 10)
        inner.setSpacing(8)
        self.preview_display = DisplayWidget()
        self.preview_display.set_expression("12 \u00d7 (3 + 4)")
        self.preview_display.set_result("84")
        self.preview_display.set_angle_badge("rad")
        self.preview_display.set_memory_badge("M0", 0.0)
        self.preview_keypad = Keypad("standard")
        inner.addWidget(self.preview_display)
        inner.addWidget(self.preview_keypad, 1)
        preview_layout.addWidget(self.preview_frame)
        layout.addWidget(preview_box, 2)

        return page

    # ------------------------------------------------------------------
    # behaviour tab
    # ------------------------------------------------------------------
    def _build_behaviour_tab(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        controls = QWidget()
        form = QFormLayout(controls)
        form.setSpacing(10)
        behaviour = self.draft.behaviour

        self.angle_combo = QComboBox()
        self.angle_combo.addItem("Radians", "rad")
        self.angle_combo.addItem("Degrees", "deg")
        self.angle_combo.addItem("Gradians", "grad")
        self.angle_combo.setCurrentIndex(max(0, self.angle_combo.findData(behaviour.angle_mode)))
        form.addRow("Angle unit", self.angle_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItem("System", "system")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Polski", "pl")
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(behaviour.language)))
        form.addRow("Language", self.language_combo)

        self.thousands_check = QCheckBox("Group thousands")
        self.thousands_check.setChecked(behaviour.thousands)
        form.addRow(self.thousands_check)

        self.group_combo = QComboBox()
        for value, label in GROUP_SEPARATORS:
            self.group_combo.addItem(label, value)
        self.group_combo.setCurrentIndex(max(0, self.group_combo.findData(behaviour.group_separator)))
        form.addRow("Grouping character", self.group_combo)

        self.decimal_combo = QComboBox()
        self.decimal_combo.addItem("Dot  (1.5)", ".")
        self.decimal_combo.addItem("Comma  (1,5)", ",")
        self.decimal_combo.setCurrentIndex(max(0, self.decimal_combo.findData(behaviour.decimal_separator)))
        form.addRow("Decimal separator", self.decimal_combo)

        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(1, 16)
        self.precision_spin.setValue(behaviour.precision)
        form.addRow("Significant digits", self.precision_spin)

        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 5000)
        self.history_spin.setSingleStep(50)
        self.history_spin.setValue(behaviour.history_limit)
        form.addRow("History entries kept", self.history_spin)

        switches = QGroupBox("Convenience")
        switch_layout = QVBoxLayout(switches)
        self.copy_check = QCheckBox("Copy result to clipboard on =")
        self.copy_check.setChecked(behaviour.copy_result_on_equals)
        self.keep_check = QCheckBox("Keep the expression after =")
        self.keep_check.setChecked(behaviour.keep_expression_after_equals)
        self.bases_check = QCheckBox("Show hex / oct / bin hint")
        self.bases_check.setChecked(behaviour.show_bases)
        switch_layout.addWidget(self.copy_check)
        switch_layout.addWidget(self.keep_check)
        switch_layout.addWidget(self.bases_check)
        form.addRow(switches)

        scroll.setWidget(controls)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return page

    # ------------------------------------------------------------------
    # wiring
    # ------------------------------------------------------------------
    def _connect_live_preview(self) -> None:
        self.theme_combo.currentTextChanged.connect(self._collect_and_preview)
        self.accent_combo.currentIndexChanged.connect(self._on_accent_changed)
        self.font_combo.currentIndexChanged.connect(self._collect_and_preview)
        self.mode_combo.currentIndexChanged.connect(self._collect_and_preview)
        for slider, label in (
            (self.radius_slider, self.radius_value),
            (self.spacing_slider, self.spacing_value),
            (self.height_slider, self.height_value),
            (self.key_font_slider, self.key_font_value),
            (self.result_font_slider, self.result_font_value),
        ):
            slider.valueChanged.connect(lambda _v, lab=label, sl=slider: self._update_slider_label(sl, lab))
            slider.valueChanged.connect(self._collect_and_preview)
        self.scale_spin.valueChanged.connect(self._collect_and_preview)
        for checkbox in (self.animations_check, self.ripples_check, self.side_panel_check):
            checkbox.toggled.connect(self._collect_and_preview)

    def _update_slider_label(self, slider: QSlider, label: QLabel) -> None:
        suffix = " pt" if slider is self.key_font_slider or slider is self.result_font_slider else " px"
        label.setText(f"{slider.value()}{suffix}")

    def _on_accent_changed(self, index: int) -> None:
        value = self.accent_combo.itemData(index)
        if value == "__custom__":
            current = self.draft.appearance.accent_color or "#3b82f6"
            colour = QColorDialog.getColor(QColor(current), self, "Accent colour")
            if colour.isValid():
                hex_value = colour.name()
                self.accent_combo.insertItem(self.accent_combo.count() - 1, _swatch(hex_value) + "Custom", hex_value)
                self.accent_combo.setCurrentIndex(self.accent_combo.count() - 2)
            else:
                self.accent_combo.setCurrentIndex(0)
        self._collect_and_preview()

    def _collect(self) -> AppSettings:
        """Read every control into :attr:`draft`."""
        appearance = self.draft.appearance
        appearance.theme = self.theme_combo.currentText()
        accent_value = self.accent_combo.currentData()
        appearance.accent_color = "" if accent_value in (None, "__custom__") else str(accent_value)
        appearance.font_family = self.font_combo.currentData() or ""
        appearance.keypad_mode = self.mode_combo.currentData() or "standard"
        appearance.corner_radius = self.radius_slider.value()
        appearance.spacing = self.spacing_slider.value()
        appearance.key_height = self.height_slider.value()
        appearance.key_font_size = self.key_font_slider.value()
        appearance.result_font_size = self.result_font_slider.value()
        appearance.ui_scale = round(float(self.scale_spin.value()), 2)
        appearance.animations = self.animations_check.isChecked()
        appearance.ripples = self.ripples_check.isChecked()
        appearance.show_side_panel = self.side_panel_check.isChecked()

        behaviour = self.draft.behaviour
        behaviour.angle_mode = self.angle_combo.currentData() or "rad"
        behaviour.language = self.language_combo.currentData() or "system"
        behaviour.thousands = self.thousands_check.isChecked()
        behaviour.group_separator = self.group_combo.currentData() or " "
        behaviour.decimal_separator = self.decimal_combo.currentData() or "."
        behaviour.precision = self.precision_spin.value()
        behaviour.history_limit = self.history_spin.value()
        behaviour.copy_result_on_equals = self.copy_check.isChecked()
        behaviour.keep_expression_after_equals = self.keep_check.isChecked()
        behaviour.show_bases = self.bases_check.isChecked()

        self.draft.appearance = appearance.sanitised()
        self.draft.behaviour = behaviour.sanitised()
        return self.draft

    def _refresh_preview(self) -> None:
        appearance = self.draft.appearance
        theme = get_theme(appearance.theme)
        self.preview_frame.setStyleSheet(build_stylesheet(theme, appearance))
        self.preview_keypad.set_mode(appearance.keypad_mode)
        self.preview_keypad.set_spacing(appearance.spacing)
        self.preview_keypad.set_key_height(int(appearance.key_height * appearance.ui_scale))
        self.preview_keypad.set_clip_radius(appearance.corner_radius)
        self.preview_keypad.set_ripple_color(theme.palette.ripple)
        self.preview_display.set_result_font_size(int(appearance.result_font_size * appearance.ui_scale))
        self.preview_display.set_result("84")

    def _collect_and_preview(self, *_args) -> None:
        self._collect()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # buttons
    # ------------------------------------------------------------------
    def _on_apply(self) -> None:
        self.applied.emit(self._collect())

    def _on_accept(self) -> None:
        self.applied.emit(self._collect())
        self.accept()

    def _on_reset(self) -> None:
        from .settings import Appearance, Behaviour

        self.draft.appearance = Appearance()
        self.draft.behaviour = Behaviour()
        self._load_draft_into_controls()
        self._refresh_preview()

    def _load_draft_into_controls(self) -> None:
        appearance, behaviour = self.draft.appearance, self.draft.behaviour
        self.theme_combo.setCurrentText(appearance.theme)
        index = self.accent_combo.findData(appearance.accent_color)
        self.accent_combo.setCurrentIndex(index if index >= 0 else 0)
        font_index = self.font_combo.findData(appearance.font_family)
        self.font_combo.setCurrentIndex(font_index if font_index >= 0 else 0)
        self.mode_combo.setCurrentIndex(0 if appearance.keypad_mode == "standard" else 1)
        self.radius_slider.setValue(appearance.corner_radius)
        self.spacing_slider.setValue(appearance.spacing)
        self.height_slider.setValue(appearance.key_height)
        self.key_font_slider.setValue(appearance.key_font_size)
        self.result_font_slider.setValue(appearance.result_font_size)
        self.scale_spin.setValue(appearance.ui_scale)
        self.animations_check.setChecked(appearance.animations)
        self.ripples_check.setChecked(appearance.ripples)
        self.side_panel_check.setChecked(appearance.show_side_panel)

        self.angle_combo.setCurrentIndex(max(0, self.angle_combo.findData(behaviour.angle_mode)))
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(behaviour.language)))
        self.thousands_check.setChecked(behaviour.thousands)
        self.group_combo.setCurrentIndex(max(0, self.group_combo.findData(behaviour.group_separator)))
        self.decimal_combo.setCurrentIndex(max(0, self.decimal_combo.findData(behaviour.decimal_separator)))
        self.precision_spin.setValue(behaviour.precision)
        self.history_spin.setValue(behaviour.history_limit)
        self.copy_check.setChecked(behaviour.copy_result_on_equals)
        self.keep_check.setChecked(behaviour.keep_expression_after_equals)
        self.bases_check.setChecked(behaviour.show_bases)

        for slider, label in (
            (self.radius_slider, self.radius_value),
            (self.spacing_slider, self.spacing_value),
            (self.height_slider, self.height_value),
            (self.key_font_slider, self.key_font_value),
            (self.result_font_slider, self.result_font_value),
        ):
            self._update_slider_label(slider, label)


def _slider_row(slider: QSlider, value_label: QLabel) -> QWidget:
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(slider, 1)
    layout.addWidget(value_label)
    return holder


def _swatch(colour: str) -> str:
    """A text swatch so the combo shows the colour without an icon asset."""
    return "\u25cf " if colour else "\u25cb "
