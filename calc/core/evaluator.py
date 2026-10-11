"""AST evaluation.

The evaluator walks the tree produced by :mod:`calc.core.parser` and returns a
Python ``float``.  It never calls :func:`eval` -- the expression language is
fully described by the grammar, which is what makes the app safe to expose to
arbitrary user input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from . import functions as fn
from . import parser as ast
from .errors import (
    ArityError,
    DivisionByZeroError,
    DomainError,
    EvaluationError,
    OverflowResultError,
    UnknownSymbolError,
)

__all__ = ["Context", "evaluate", "Evaluator"]

#: Values larger than this are reported as an overflow instead of ``inf``.
MAX_MAGNITUDE = 1.7976931348623157e308


@dataclass
class Context:
    """Mutable evaluation state shared between calls."""

    angle_mode: str = fn.AngleMode.RAD
    variables: Dict[str, float] = field(default_factory=dict)

    def resolve(self, name: str) -> float:
        constant = fn.lookup_constant(name)
        if constant is not None:
            return constant
        if name in self.variables:
            return self.variables[name]
        lowered = name.lower()
        if lowered in self.variables:
            return self.variables[lowered]
        raise UnknownSymbolError(f"Unknown name '{name}'")

    def to_radians(self, value: float) -> float:
        return fn.AngleMode.to_radians(value, self.angle_mode)

    def from_radians(self, value: float) -> float:
        return fn.AngleMode.from_radians(value, self.angle_mode)


def _checked(value: float, pos: int = 0) -> float:
    """Normalise a computed value and reject results that are not usable."""
    if value is None:
        raise EvaluationError("Cannot compute", pos)
    if isinstance(value, bool):  # bools sneak in from comparisons
        value = float(value)
    value = float(value)
    if math.isnan(value):
        raise DomainError("Undefined result", pos)
    if math.isinf(value):
        raise OverflowResultError("Overflow", pos)
    return value


def _number_from_raw(raw: str, pos: int) -> float:
    try:
        if raw[:2].lower() == "0x":
            return float(int(raw, 16))
        if raw[:2].lower() == "0b":
            return float(int(raw, 2))
        if raw[:2].lower() == "0o":
            return float(int(raw, 8))
        return float(raw)
    except ValueError as exc:  # pragma: no cover - lexer guarantees validity
        raise EvaluationError(f"Cannot read number '{raw}' ({exc})", pos) from exc


class Evaluator:
    """Stateless walker; keeps a :class:`Context` for names and angle mode."""

    def __init__(self, context: Optional[Context] = None) -> None:
        self.context = context or Context()

    # -- entry point -------------------------------------------------------
    def evaluate(self, node: ast.Node) -> float:
        return _checked(self._visit(node), node.pos)

    # -- dispatch ----------------------------------------------------------
    def _visit(self, node: ast.Node) -> float:
        handler = _HANDLERS.get(type(node))
        if handler is None:  # pragma: no cover - defensive
            raise EvaluationError(f"Cannot evaluate {type(node).__name__}", getattr(node, "pos", 0))
        return handler(self, node)

    # -- node implementations ---------------------------------------------
    def _number(self, node: ast.NumberNode) -> float:
        return _number_from_raw(node.raw, node.pos)

    def _name(self, node: ast.NameNode) -> float:
        return self.context.resolve(node.name)

    def _unary(self, node: ast.UnaryNode) -> float:
        value = self._visit(node.operand)
        return -value if node.op == "-" else value

    def _postfix(self, node: ast.PostfixNode) -> float:
        value = self._visit(node.operand)
        if node.op == "%":
            return value / 100.0
        if node.op == "!":
            return fn.FUNCTIONS["fact"].impl(value)
        raise EvaluationError(f"Unknown postfix operator '{node.op}'", node.pos)

    def _binary(self, node: ast.BinaryNode) -> float:
        left = self._visit(node.left)
        right = self._visit(node.right)

        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise DivisionByZeroError("Division by zero", node.pos)
            return left / right
        if node.op == "^":
            return self._power(left, right, node.pos)
        raise EvaluationError(f"Unknown operator '{node.op}'", node.pos)

    def _power(self, left: float, right: float, pos: int) -> float:
        # Negative base with a fractional exponent is complex, not float.
        if left < 0 and not float(right).is_integer():
            raise DomainError("Negative base with a fractional exponent", pos)
        try:
            return math.pow(left, right)
        except OverflowError as exc:
            raise OverflowResultError("Overflow", pos) from exc
        except ValueError as exc:
            raise DomainError(str(exc), pos) from exc

    def _call(self, node: ast.CallNode) -> float:
        spec = fn.lookup_function(node.name)
        if not spec.accepts(len(node.args)):
            minimum, maximum = spec.arity
            expected = str(minimum) if maximum == minimum else f"{minimum}+"
            raise ArityError(
                f"{spec.name}() takes {expected} argument(s), got {len(node.args)}",
                node.pos,
            )

        values = [self._visit(arg) for arg in node.args]

        if spec.angular and values:
            values[0] = self.context.to_radians(values[0])

        try:
            result = spec.impl(*values)
        except ZeroDivisionError as exc:
            raise DivisionByZeroError("Division by zero", node.pos) from exc
        except ValueError as exc:
            raise DomainError(f"{spec.name}(): {exc}", node.pos) from exc
        except OverflowError as exc:
            raise OverflowResultError("Overflow", node.pos) from exc

        if spec.inverse_angular:
            result = self.context.from_radians(result)
        return result


_HANDLERS = {
    ast.NumberNode: Evaluator._number,
    ast.NameNode: Evaluator._name,
    ast.UnaryNode: Evaluator._unary,
    ast.PostfixNode: Evaluator._postfix,
    ast.BinaryNode: Evaluator._binary,
    ast.CallNode: Evaluator._call,
}


def evaluate(text: str, context: Optional[Context] = None) -> float:
    """Parse *and* evaluate ``text`` in one step.

    This is the function the CLI and the tests use; the GUI keeps a persistent
    :class:`Context` so that variables and the angle mode survive between keys.
    """
    tree = ast.parse(text)
    return Evaluator(context).evaluate(tree)
