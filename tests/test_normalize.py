"""Input repair: auto-closing parentheses and stripping dangling operators."""

from __future__ import annotations

import pytest

from calc.core.normalize import auto_close, strip_trailing_operators


@pytest.mark.parametrize(
    "text, expected",
    [
        ("5+", "5"),
        ("5-", "5"),
        ("5*", "5"),
        ("5/", "5"),
        ("5^", "5"),
        ("5.", "5"),
        ("3*(", "3"),
        ("5 + ", "5"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_strip_trailing_operators(text: str, expected: str):
    assert strip_trailing_operators(text) == expected


def test_postfix_operators_are_kept():
    assert strip_trailing_operators("5!") == "5!"
    assert strip_trailing_operators("50%") == "50%"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("sin(30", "sin(30)"),
        ("2*(3+4", "2*(3+4)"),
        ("((1+2", "((1+2))"),
        ("sqrt(sqrt(4", "sqrt(sqrt(4))"),
        ("5+", "5"),
        ("(1+2)", "(1+2)"),
        ("", ""),
    ],
)
def test_auto_close(text: str, expected: str):
    assert auto_close(text) == expected


def test_extra_closing_parens_are_left_alone():
    # A surplus ")" is a genuine syntax error the user must be shown.
    assert auto_close("(1+2))") == "(1+2))"


def test_auto_close_then_evaluate():
    from calc.core.evaluator import evaluate

    assert evaluate(auto_close("sin(30")) == pytest.approx(
        evaluate("sin(30)")
    )
    assert evaluate(auto_close("2*(3+4")) == 14
    assert evaluate(auto_close("5+")) == 5
