"""The display area: expression line, big result, error state and hints.

The display owns three visual behaviours that make the app feel responsive:

* the result font shrinks automatically so a long number never gets clipped,
* the expression line is elided from the *left*, because the interesting end of
  a formula is the one you just typed,
* an invalid expression turns the result red and shakes the panel.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QVariantAnimation
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

__all__ = ["DisplayWidget"]

SHAKE_MS = 320
FLASH_MS = 260


class DisplayWidget(QFrame):
    """Expression + result + hint, with badges for angle unit and memory."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DisplayFrame")
        self._base_result_size = 40
        self._shake_origin: QPoint | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(2)

        badges = QHBoxLayout()
        badges.setSpacing(6)
        self.angle_badge = QLabel("RAD")
        self.angle_badge.setObjectName("AngleBadge")
        self.angle_badge.setAlignment(Qt.AlignCenter)
        self.memory_badge = QLabel("M")
        self.memory_badge.setObjectName("MemoryBadge")
        self.memory_badge.setAlignment(Qt.AlignCenter)
        self.memory_badge.setVisible(False)
        badges.addWidget(self.angle_badge)
        badges.addWidget(self.memory_badge)
        badges.addStretch(1)
        root.addLayout(badges)

        self.expression_label = QLabel("")
        self.expression_label.setObjectName("DisplayExpression")
        self.expression_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.expression_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.expression_label)

        self.result_label = QLabel("0")
        self.result_label.setObjectName("DisplayResult")
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.result_label, 1)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("DisplayHint")
        self.hint_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        root.addWidget(self.hint_label)

        self._flash_animation: QVariantAnimation | None = None
        self._shake_animation: QVariantAnimation | None = None

    # -- content -----------------------------------------------------------
    def set_expression(self, text: str) -> None:
        self.expression_label.setText(self._elide_left(text))

    def set_result(self, text: str, *, error: bool = False) -> None:
        self.result_label.setProperty("state", "error" if error else "normal")
        # A dynamic property change needs a style re-polish to take effect.
        style = self.result_label.style()
        style.unpolish(self.result_label)
        style.polish(self.result_label)
        self.result_label.setText(text)
        self._fit_result_font()

    def set_hint(self, text: str) -> None:
        self.hint_label.setText(text)
        self.hint_label.setVisible(bool(text))

    def set_angle_badge(self, mode: str) -> None:
        self.angle_badge.setText(mode.upper())

    def set_memory_badge(self, slot: str, value: float) -> None:
        if value == 0:
            self.memory_badge.setVisible(False)
        else:
            self.memory_badge.setText(slot)
            self.memory_badge.setVisible(True)

    def set_result_font_size(self, size: int) -> None:
        self._base_result_size = max(10, int(size))
        self._fit_result_font()

    # -- layout ------------------------------------------------------------
    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._fit_result_font()
        self.set_expression(self.expression_label.text())

    def _fit_result_font(self) -> None:
        """Shrink the result font until the text fits the label's width."""
        text = self.result_label.text()
        if not text:
            return
        available = max(40, self.result_label.width() - 24)
        font = QFont(self.result_label.font())
        font.setPointSize(self._base_result_size)
        metrics = QFontMetrics(font)
        while font.pointSize() > 12 and metrics.horizontalAdvance(text) > available:
            font.setPointSize(font.pointSize() - 1)
            metrics = QFontMetrics(font)
        if self.result_label.font().pointSize() != font.pointSize():
            self.result_label.setFont(font)

    def _elide_left(self, text: str) -> str:
        """Keep the tail of ``text`` if it does not fit."""
        if not text:
            return ""
        available = max(40, self.width() - 120)
        metrics = QFontMetrics(self.expression_label.font())
        if metrics.horizontalAdvance(text) <= available:
            return text
        while text and metrics.horizontalAdvance("\u2026" + text) > available:
            text = text[1:]
        return "\u2026" + text

    # -- feedback ----------------------------------------------------------
    def shake(self) -> None:
        """Short horizontal shake, used when evaluation fails."""
        if self._shake_origin is None:
            self._shake_origin = self.pos()
        origin = self._shake_origin

        if self._shake_animation is not None:
            self._shake_animation.stop()

        animation = QVariantAnimation(self)
        animation.setDuration(SHAKE_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        def on_value(value: float) -> None:
            # Damped oscillation: 9px, 6px, 3px, 0px
            decay = 1.0 - value
            offset = int(round(9 * decay * _oscillate(value)))
            self.move(origin + QPoint(offset, 0))

        animation.valueChanged.connect(on_value)
        animation.finished.connect(self._end_shake)
        self._shake_animation = animation
        animation.start()

    def _end_shake(self) -> None:
        if self._shake_origin is not None:
            self.move(self._shake_origin)
            self._shake_origin = None
        self._shake_animation = None

    def flash(self) -> None:
        """Brief highlight of the result, used after a successful "=".

        Implemented through the label's own font weight rather than a colour
        animation, so it stays readable in every theme, including the
        high-contrast one.
        """
        if self._flash_animation is not None:
            self._flash_animation.stop()

        base_size = self.result_label.font().pointSize()
        animation = QVariantAnimation(self)
        animation.setDuration(FLASH_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)

        def on_value(value: float) -> None:
            bump = 1.0 - abs(value - 0.4) / 0.6
            font = QFont(self.result_label.font())
            font.setPointSize(max(10, base_size + int(round(3 * max(0.0, bump)))))
            self.result_label.setFont(font)

        animation.valueChanged.connect(on_value)
        animation.finished.connect(lambda: self._fit_result_font())
        self._flash_animation = animation
        animation.start()

    def clear_flash(self) -> None:
        if self._flash_animation is not None:
            self._flash_animation.stop()
            self._flash_animation = None


def _oscillate(t: float) -> float:
    """A few alternating swings that settle at zero."""
    import math

    return math.cos(t * math.pi * 3.0)
