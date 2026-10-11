"""Custom-painted widgets: the ripple key and the display.

Both are plain :mod:`PySide6.QtWidgets` classes with hand-written
``paintEvent`` implementations -- no image assets, no third-party widget
library.  Everything is drawn from the active theme's colours so a theme switch
re-colours them instantly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QRadialGradient,
)
from PySide6.QtWidgets import QPushButton, QWidget

__all__ = ["RippleButton", "set_ripple_enabled", "ripple_enabled"]

RIPPLE_DURATION_MS = 520
_RIPPLES_ENABLED = True


def set_ripple_enabled(enabled: bool) -> None:
    """Global switch driven by the "Ripple effect" setting."""
    global _RIPPLES_ENABLED
    _RIPPLES_ENABLED = bool(enabled)


def ripple_enabled() -> bool:
    return _RIPPLES_ENABLED


@dataclass
class _Ripple:
    center: QPointF
    progress: float = 0.0
    animation: QPropertyAnimation | None = field(default=None, repr=False)


class RippleButton(QPushButton):
    """:class:`QPushButton` that paints an expanding ripple from the press point.

    The button's own styling (colour, border radius) still comes entirely from
    the stylesheet; this class only draws an overlay on top, so the settings
    dialog stays the single source of truth for the look.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WA_Hover, True)
        self._ripples: List[_Ripple] = []
        self._ripple_color = QColor(255, 255, 255)
        self._clip_radius = 12.0

    # -- configuration -----------------------------------------------------
    def set_ripple_color(self, colour: QColor | str) -> None:
        self._ripple_color = QColor(colour)

    def set_clip_radius(self, radius: float) -> None:
        self._clip_radius = max(0.0, float(radius))

    # -- interaction -------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if ripple_enabled() and event.button() == Qt.LeftButton:
            self._spawn_ripple(QPointF(event.position()))
        super().mousePressEvent(event)

    def _spawn_ripple(self, center: QPointF) -> None:
        ripple = _Ripple(center=center)
        animation = QVariantAnimation(self)
        animation.setDuration(RIPPLE_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)

        def on_value(value) -> None:
            ripple.progress = min(1.0, max(0.0, float(value)))
            self.update()

        animation.valueChanged.connect(on_value)
        animation.finished.connect(lambda r=ripple: self._remove_ripple(r))
        ripple.animation = animation
        self._ripples.append(ripple)
        animation.start()

        # Safety net: if the animation object is dropped, do not leak the ripple.
        QTimer.singleShot(RIPPLE_DURATION_MS + 250, lambda r=ripple: self._remove_ripple(r))
        self.update()

    def _remove_ripple(self, ripple: _Ripple) -> None:
        if ripple in self._ripples:
            self._ripples.remove(ripple)
            self.update()

    # -- painting ----------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().paintEvent(event)
        if not self._ripples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1),
                            self._clip_radius, self._clip_radius)
        painter.setClipPath(path)

        max_radius = math.hypot(self.width(), self.height())
        for ripple in self._ripples:
            progress = max(0.0, min(1.0, ripple.progress))
            radius = max(1.0, max_radius * progress)
            alpha = int(90 * (1.0 - progress))
            if alpha <= 0:
                continue
            colour = QColor(self._ripple_color)
            colour.setAlpha(alpha)
            gradient = QRadialGradient(ripple.center, radius)
            gradient.setColorAt(0.0, colour)
            fade = QColor(colour)
            fade.setAlpha(0)
            gradient.setColorAt(1.0, fade)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(ripple.center, radius, radius)
        painter.end()


def shrink_font(label_text: str, font: QFont, available_width: int, min_size: int = 12) -> QFont:
    """Return ``font`` with a point size small enough to fit ``available_width``."""
    result = QFont(font)
    metrics = QFontMetrics(result)
    while result.pointSize() > min_size and metrics.horizontalAdvance(label_text) > available_width:
        result.setPointSize(result.pointSize() - 1)
        metrics = QFontMetrics(result)
    return result


def press_point(widget: QWidget, position: QPoint) -> QPointF:  # pragma: no cover - helper
    return QPointF(position)
