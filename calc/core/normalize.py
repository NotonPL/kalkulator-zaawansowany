"""Input normalisation.

People press ``=`` mid-formula all the time.  Rather than rejecting
``sin(30`` or ``5 +``, the app repairs the obvious cases first -- this is what
every hardware calculator does, and doing it in the core (instead of the
widget) keeps it testable and shared with the CLI.
"""

from __future__ import annotations

__all__ = ["auto_close", "strip_trailing_operators"]

#: Characters that cannot legally end an expression.
_DANGLING = set("+-*/^(.,\u00d7\u00f7\u2212")


def strip_trailing_operators(expression: str) -> str:
    """Remove operators and separators left hanging at the end.

    ``"5+"`` becomes ``"5"``; ``"3*("`` becomes ``"3"``.  Postfix operators
    (``!``, ``%``) are kept because they are meaningful.
    """
    text = expression.rstrip()
    while text and text[-1] in _DANGLING:
        text = text[:-1].rstrip()
    return text


def auto_close(expression: str) -> str:
    """Repair a partially typed expression so it can be evaluated.

    Two steps, in this order:

    1. drop a dangling trailing operator (``2 +`` -> ``2``),
    2. append the missing closing parentheses (``sin(30`` -> ``sin(30)``).

    Extra closing parentheses are left alone -- they are a real syntax error
    the user should see.
    """
    text = strip_trailing_operators(expression)
    if not text:
        return text

    depth = 0
    for character in text:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
    if depth > 0:
        text += ")" * depth
    return text
