"""Number formatting and expression prettifying."""

from __future__ import annotations

import math

import pytest

from calc.core.formatter import (
    FormatSettings,
    format_number,
    parse_formatted,
    pretty_expression,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0"),
        (1, "1"),
        (-1, "-1"),
        (0.5, "0.5"),
        (-0.5, "-0.5"),
        (1234, "1 234"),
        (1234567, "1 234 567"),
        (1234567.891, "1 234 567.891"),
        (-987654321, "-987 654 321"),
    ],
)
def test_default_formatting(value: float, expected: str):
    assert format_number(value) == expected


def test_thousands_can_be_disabled():
    settings = FormatSettings(thousands=False)
    assert format_number(1234567, settings) == "1234567"


def test_comma_decimal_separator():
    settings = FormatSettings(decimal_separator=",", group_separator=" ")
    assert format_number(1234.5, settings) == "1 234,5"


def test_group_separator_is_configurable():
    settings = FormatSettings(group_separator=",")
    assert format_number(1234567, settings) == "1,234,567"


def test_narrow_nbsp_group_separator():
    settings = FormatSettings(group_separator="\u202f")
    assert format_number(1234567, settings) == "1\u202f234\u202f567"


def test_precision_limits_significant_digits():
    settings = FormatSettings(thousands=False, precision=4)
    assert format_number(3.14159265, settings) == "3.142"


def test_large_numbers_switch_to_scientific():
    text = format_number(1.5e15)
    assert "\u00d710^" in text


def test_small_numbers_switch_to_scientific():
    text = format_number(1.5e-12)
    assert "\u00d710^" in text


def test_zero_never_uses_scientific_notation():
    assert format_number(0.0) == "0"


def test_infinity_and_nan():
    assert format_number(math.inf) == "\u221e"
    assert format_number(-math.inf) == "-\u221e"
    assert format_number(math.nan) == "undefined"


def test_negative_zero_renders_as_zero():
    assert format_number(-0.0) == "0"


def test_trailing_zeros_are_trimmed():
    assert format_number(2.50, FormatSettings(thousands=False)) == "2.5"
    assert format_number(7.0, FormatSettings(thousands=False)) == "7"


@pytest.mark.parametrize(
    "value",
    [0, 1, -42, 3.5, 1234567.891, -0.0001],
)
def test_round_trip(value: float):
    settings = FormatSettings()
    assert parse_formatted(format_number(value, settings), settings) == pytest.approx(value)


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("2*(3+4)", "2 * (3 + 4)"),
        ("1+2*3", "1 + 2 * 3"),
        ("-3+4", "-3 + 4"),
        ("2^-3", "2 ^ -3"),
        ("sqrt(9)", "sqrt(9)"),
        ("", ""),
    ],
)
def test_pretty_expression(expression: str, expected: str):
    assert pretty_expression(expression) == expected
