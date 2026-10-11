"""Facade that ties the engine, history, memory and formatting together.

Both the Qt GUI and the headless CLI drive exactly this object, which is why a
calculation behaves identically whether it is typed on a keyboard or on a
touchscreen.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from . import functions as fn
from .errors import CalcError
from .evaluator import Context, Evaluator
from .formatter import FormatSettings, format_number, pretty_expression
from .history import History, HistoryEntry
from .memory import Memory
from .parser import parse

__all__ = ["CalculatorEngine", "CalcError"]

APP_NAME = "python-calculator"


def data_directory(override: Optional[Path] = None) -> Path:
    """Where history, memory and settings live.

    Resolution order: explicit override, ``$PYTHON_CALCULATOR_HOME``, then the
    XDG/AppData/macOS convention.  Never raises -- falls back to ``~/.calc``.
    """
    import os

    if override is not None:
        path = Path(override)
    elif os.environ.get("PYTHON_CALCULATOR_HOME"):
        path = Path(os.environ["PYTHON_CALCULATOR_HOME"]).expanduser()
    elif os.environ.get("XDG_DATA_HOME"):
        path = Path(os.environ["XDG_DATA_HOME"]).expanduser() / APP_NAME
    elif os.name == "nt":
        base = os.environ.get("APPDATA", Path.home())
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / ".local" / "share" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


class CalculatorEngine:
    """Stateful calculator: one instance per window (or CLI session)."""

    def __init__(
        self,
        home: Optional[Path] = None,
        history_limit: int = 200,
        settings: Optional[FormatSettings] = None,
    ) -> None:
        self.home = data_directory(home)
        self.context = Context()
        self.history = History(self.home / "history.json", limit=history_limit)
        self.memory = Memory(self.home / "memory.json")
        self.format_settings = settings or FormatSettings()
        self.evaluator = Evaluator(self.context)
        self.last_expression: str = ""
        self.last_result: Optional[float] = None
        self.error: Optional[CalcError] = None

    # -- angle mode --------------------------------------------------------
    @property
    def angle_mode(self) -> str:
        return self.context.angle_mode

    def set_angle_mode(self, mode: str) -> None:
        if mode not in fn.AngleMode.ALL:
            raise ValueError(f"Unknown angle mode '{mode}'")
        self.context.angle_mode = mode

    def cycle_angle_mode(self) -> str:
        modes = list(fn.AngleMode.ALL)
        current = modes.index(self.angle_mode) if self.angle_mode in modes else 0
        self.set_angle_mode(modes[(current + 1) % len(modes)])
        return self.angle_mode

    # -- variables ---------------------------------------------------------
    def define(self, name: str, value: float) -> None:
        self.context.variables[name] = float(value)

    def variables(self) -> dict:
        return dict(self.context.variables)

    # -- evaluation --------------------------------------------------------
    def evaluate(self, expression: str, *, remember: bool = True) -> float:
        """Evaluate ``expression``, updating history, ``ans`` and last result.

        :raises CalcError: with a ``position`` pointing at the offending token.
        """
        tree = parse(expression)
        value = self.evaluator.evaluate(tree)

        self.last_expression = expression
        self.last_result = value
        self.error = None
        self.context.variables["ans"] = value
        if remember:
            self.history.add(
                expression=expression,
                result=self.format(value),
                angle_mode=self.angle_mode,
            )
        return value

    def evaluate_formatted(self, expression: str) -> str:
        """Evaluate and return the value rendered with the current settings."""
        return self.format(self.evaluate(expression))

    def format(self, value: float) -> str:
        return format_number(value, self.format_settings)

    def pretty(self, expression: str) -> str:
        return pretty_expression(expression)

    def try_evaluate(self, expression: str) -> tuple[Optional[float], Optional[CalcError]]:
        """Non-raising variant used for the live preview line."""
        if not expression.strip():
            return None, None
        try:
            return self.evaluate(expression, remember=False), None
        except CalcError as exc:
            return None, exc

    # -- history -----------------------------------------------------------
    def history_entries(self) -> List[HistoryEntry]:
        return self.history.entries

    def clear_history(self) -> None:
        self.history.clear()

    def recall_history(self, entry: HistoryEntry, *, use_result: bool = True) -> str:
        """Text to drop into the input when a history row is tapped."""
        if use_result:
            try:
                return str(float(entry.result.replace(" ", "").replace(",", ".")))
            except ValueError:
                return entry.result
        return entry.expression
