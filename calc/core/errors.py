"""Exception hierarchy for the calculator engine.

Every error raised while turning a user's expression into a number derives
from :class:`CalcError`, which carries an optional ``position`` (index into the
original input string).  The GUI uses that position to highlight the offending
character in the expression line instead of showing a generic "error".
"""

from __future__ import annotations

from typing import Optional

__all__ = [
    "CalcError",
    "LexError",
    "ParseError",
    "EvaluationError",
    "UnknownSymbolError",
    "UnknownFunctionError",
    "ArityError",
    "DomainError",
    "DivisionByZeroError",
    "OverflowResultError",
]


class CalcError(Exception):
    """Base class for every error the engine can produce."""

    #: Default message shown by the GUI when no context is available.
    default_message = "Error"

    def __init__(self, message: Optional[str] = None, position: Optional[int] = None) -> None:
        self.message = message or self.default_message
        self.position = position
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.position is None:
            return self.message
        return f"{self.message} (at position {self.position})"


class LexError(CalcError):
    """Raised when the input contains a character the lexer cannot read."""

    default_message = "Invalid character"


class ParseError(CalcError):
    """Raised when the token stream does not form a valid expression."""

    default_message = "Invalid expression"


class EvaluationError(CalcError):
    """Raised when a syntactically valid expression cannot be computed."""

    default_message = "Cannot compute"


class UnknownSymbolError(EvaluationError):
    """Raised for an identifier that is neither a constant nor a variable."""

    default_message = "Unknown name"


class UnknownFunctionError(EvaluationError):
    """Raised when a called function is not registered."""

    default_message = "Unknown function"


class ArityError(EvaluationError):
    """Raised when a function is called with the wrong number of arguments."""

    default_message = "Wrong number of arguments"


class DomainError(EvaluationError):
    """Raised for values outside a function's mathematical domain."""

    default_message = "Domain error"


class DivisionByZeroError(EvaluationError):
    """Raised on division or modulo by zero."""

    default_message = "Division by zero"


class OverflowResultError(EvaluationError):
    """Raised when the magnitude of the result is not representable."""

    default_message = "Overflow"
