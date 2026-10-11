"""The keypad.

Layouts are pure data (:data:`STANDARD_LAYOUT`, :data:`SCIENTIFIC_LAYOUT`), so
adding a key or a whole new mode never touches widget code.  The keypad emits a
single ``key_activated`` signal carrying the :class:`Key` that was pressed; the
main window decides what that means.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QWidget

from .widgets import RippleButton

__all__ = ["Key", "Keypad", "STANDARD_LAYOUT", "SCIENTIFIC_LAYOUT", "LAYOUTS"]


@dataclass(frozen=True)
class Key:
    """One button.  Either it inserts text or it triggers a command."""

    label: str
    insert: Optional[str] = None
    command: Optional[str] = None
    role: str = "digit"       # digit | operator | function | clear | equals | memory
    colspan: int = 1
    rowspan: int = 1
    tooltip: str = ""


def _digit(label: str) -> Key:
    return Key(label=label, insert=label, role="digit")


def _op(label: str, insert: str, tooltip: str = "") -> Key:
    return Key(label=label, insert=insert, role="operator", tooltip=tooltip)


def _fn(label: str, insert: Optional[str] = None, command: Optional[str] = None,
        tooltip: str = "") -> Key:
    return Key(label=label, insert=insert, command=command, role="function", tooltip=tooltip)


def _mem(label: str, command: str, tooltip: str = "") -> Key:
    return Key(label=label, command=command, role="memory", tooltip=tooltip)


# ---------------------------------------------------------------------------
# layouts
# ---------------------------------------------------------------------------
STANDARD_LAYOUT: List[List[Key]] = [
    [
        _mem("MC", "memory_clear", "Memory clear"),
        _mem("MR", "memory_recall", "Memory recall"),
        _mem("M+", "memory_add", "Memory add"),
        _mem("M\u2212", "memory_subtract", "Memory subtract"),
        _mem("MS", "memory_store", "Memory store"),
    ],
    [
        Key("C", command="clear_all", role="clear", tooltip="Clear everything (Esc)"),
        Key("\u232b", command="backspace", role="clear", tooltip="Delete one character (Backspace)"),
        Key("(", insert="(", role="function", tooltip="Open parenthesis"),
        Key(")", insert=")", role="function", tooltip="Close parenthesis"),
        _op("\u00f7", "/", "Divide"),
    ],
    [_digit("7"), _digit("8"), _digit("9"), _op("\u00d7", "*", "Multiply"),
     _fn("\u221a", insert="sqrt(", tooltip="Square root")],
    [_digit("4"), _digit("5"), _digit("6"), _op("\u2212", "-", "Subtract"),
     _fn("x\u00b2", insert="^2", tooltip="Square")],
    [_digit("1"), _digit("2"), _digit("3"), _op("+", "+", "Add"),
     _fn("1/x", insert="^(-1)", tooltip="Reciprocal")],
    [
        Key("\u00b1", command="negate", role="function", tooltip="Change sign"),
        _digit("0"),
        Key(".", insert=".", role="digit", tooltip="Decimal separator"),
        Key("%", insert="%", role="function", tooltip="Percent"),
        Key("=", command="equals", role="equals", tooltip="Evaluate (Enter)"),
    ],
]

SCIENTIFIC_LAYOUT: List[List[Key]] = [
    [
        Key("DEG", command="angle", role="function", tooltip="Cycle angle unit"),
        _mem("MC", "memory_clear", "Memory clear"),
        _mem("MR", "memory_recall", "Memory recall"),
        _mem("M+", "memory_add", "Memory add"),
        _mem("MS", "memory_store", "Memory store"),
        Key("C", command="clear_all", role="clear", tooltip="Clear everything"),
        Key("\u232b", command="backspace", role="clear", tooltip="Backspace"),
    ],
    [
        _fn("sin", insert="sin(", tooltip="Sine"),
        _fn("cos", insert="cos(", tooltip="Cosine"),
        _fn("tan", insert="tan(", tooltip="Tangent"),
        _fn("ln", insert="ln(", tooltip="Natural logarithm"),
        _fn("log", insert="log(", tooltip="Base-10 logarithm"),
        Key("(", insert="(", role="function", tooltip="Open parenthesis"),
        _op("\u00f7", "/", "Divide"),
    ],
    [
        _fn("asin", insert="asin(", tooltip="Arc sine"),
        _fn("acos", insert="acos(", tooltip="Arc cosine"),
        _fn("atan", insert="atan(", tooltip="Arc tangent"),
        _fn("\u03c0", insert="pi", tooltip="Pi"),
        _fn("e", insert="e", tooltip="Euler's number"),
        Key(")", insert=")", role="function", tooltip="Close parenthesis"),
        _op("\u00d7", "*", "Multiply"),
    ],
    [
        _digit("7"), _digit("8"), _digit("9"),
        _fn("\u221a", insert="sqrt(", tooltip="Square root"),
        _fn("x\u00b2", insert="^2", tooltip="Square"),
        _fn("mod", insert="mod(", tooltip="Modulo"),
        _op("\u2212", "-", "Subtract"),
    ],
    [
        _digit("4"), _digit("5"), _digit("6"),
        _fn("x\u02b8", insert="^", tooltip="Power"),
        _fn("x!", insert="!", tooltip="Factorial"),
        _fn("abs", insert="abs(", tooltip="Absolute value"),
        _op("+", "+", "Add"),
    ],
    [
        _digit("1"), _digit("2"), _digit("3"),
        _fn("1/x", insert="^(-1)", tooltip="Reciprocal"),
        Key("%", insert="%", role="function", tooltip="Percent"),
        _fn("ans", insert="ans", tooltip="Previous answer"),
        Key("=", command="equals", role="equals", rowspan=2, tooltip="Evaluate (Enter)"),
    ],
    [
        Key("0", insert="0", role="digit", colspan=2),
        Key(".", insert=".", role="digit", tooltip="Decimal separator"),
        Key("\u00b1", command="negate", role="function", tooltip="Change sign"),
        _fn("10\u02e3", insert="10^", tooltip="Power of ten"),
        _fn("exp", insert="exp(", tooltip="e to the power x"),
    ],
]

LAYOUTS = {"standard": STANDARD_LAYOUT, "scientific": SCIENTIFIC_LAYOUT}


class Keypad(QWidget):
    """A grid of :class:`RippleButton` widgets built from a layout table."""

    key_activated = Signal(object)

    def __init__(self, mode: str = "standard", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._mode = mode
        self._buttons: List[RippleButton] = []
        # The QGridLayout is the widget's own layout: it is the only layout in
        # the chain, so its margins *are* the keypad's outer margins.  Nesting a
        # second layout here would add a second, uncontrollable gap.
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self.set_mode(mode)

    # -- construction ------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        """(Re)build the grid for ``mode`` ("standard" or "scientific")."""
        if mode == self._mode and self._buttons:
            return  # nothing to do; rebuilding would only create zombie buttons
        self._mode = mode
        layout = LAYOUTS.get(mode, STANDARD_LAYOUT)
        self._clear_grid()

        for row, row_keys in enumerate(layout):
            column = 0
            for key in row_keys:
                button = RippleButton(key.label)
                button.setProperty("role", key.role)
                button.setFocusPolicy(Qt.NoFocus)
                button.setCursor(Qt.PointingHandCursor)
                if key.tooltip:
                    button.setToolTip(key.tooltip)
                button.clicked.connect(lambda _checked=False, k=key: self.key_activated.emit(k))
                self._grid.addWidget(button, row, column, key.rowspan, key.colspan)
                self._buttons.append(button)
                column += key.colspan

        self._apply_uniform_columns(layout)

    def _clear_grid(self) -> None:
        for button in self._buttons:
            self._grid.removeWidget(button)
            # Detach *and* hide immediately: deleteLater() alone would leave the
            # old buttons painted on top of the fresh layout until the event
            # loop gets around to destroying them.
            button.hide()
            button.setParent(None)
            button.deleteLater()
        self._buttons.clear()

    def _apply_uniform_columns(self, layout: List[List[Key]]) -> None:
        columns = max(sum(key.colspan for key in row) for row in layout)
        for index in range(columns):
            self._grid.setColumnStretch(index, 1)

    # -- theming hooks -----------------------------------------------------
    def buttons(self) -> List[RippleButton]:
        return list(self._buttons)

    def set_key_height(self, height: int) -> None:
        for button in self._buttons:
            button.setMinimumHeight(int(height))

    def set_ripple_color(self, colour) -> None:
        for button in self._buttons:
            button.set_ripple_color(colour)

    def set_clip_radius(self, radius: float) -> None:
        for button in self._buttons:
            button.set_clip_radius(radius)

    def set_spacing(self, spacing: int) -> None:
        self._grid.setSpacing(int(spacing))

    # -- queries used by tests ---------------------------------------------
    def button_for(self, label: str) -> Optional[RippleButton]:
        for button in self._buttons:
            if button.text() == label:
                return button
        return None

    def labels(self) -> List[str]:
        return [button.text() for button in self._buttons]
