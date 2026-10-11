"""Core, framework-free calculator engine.

Nothing in this package imports Qt, which is what lets the same engine run in a
Qt window on a desktop *and* in a Termux terminal on an Android phone.
"""

from .engine import CalculatorEngine, data_directory
from .errors import (
    ArityError,
    CalcError,
    DivisionByZeroError,
    DomainError,
    EvaluationError,
    LexError,
    OverflowResultError,
    ParseError,
    UnknownFunctionError,
    UnknownSymbolError,
)
from .evaluator import Context, Evaluator, evaluate
from .formatter import FormatSettings, format_number, pretty_expression
from .functions import AngleMode, CONSTANTS, FUNCTIONS, FunctionSpec
from .history import History, HistoryEntry
from .lexer import Token, TokenType, tokenize
from .memory import Memory
from .normalize import auto_close, strip_trailing_operators
from .parser import parse

__all__ = [
    "AngleMode",
    "ArityError",
    "CalcError",
    "CalculatorEngine",
    "CONSTANTS",
    "Context",
    "DivisionByZeroError",
    "DomainError",
    "EvaluationError",
    "FormatSettings",
    "FUNCTIONS",
    "FunctionSpec",
    "History",
    "HistoryEntry",
    "LexError",
    "Memory",
    "OverflowResultError",
    "ParseError",
    "Token",
    "TokenType",
    "UnknownFunctionError",
    "UnknownSymbolError",
    "data_directory",
    "evaluate",
    "Evaluator",
    "format_number",
    "parse",
    "pretty_expression",
    "tokenize",
    "auto_close",
    "strip_trailing_operators",
]
