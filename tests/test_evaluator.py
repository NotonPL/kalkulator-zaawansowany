"""End-to-end evaluation tests -- the mathematical contract of the app."""

from __future__ import annotations

import math

import pytest

from calc.core.engine import CalculatorEngine
from calc.core.errors import (
    ArityError,
    CalcError,
    DivisionByZeroError,
    DomainError,
    LexError,
    OverflowResultError,
    ParseError,
    UnknownFunctionError,
    UnknownSymbolError,
)
from calc.core.evaluator import Context, evaluate


# ---------------------------------------------------------------------------
# arithmetic
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "expression, expected",
    [
        ("1+1", 2),
        ("2-5", -3),
        ("6*7", 42),
        ("7/2", 3.5),
        ("2^10", 1024),
        ("2^-2", 0.25),
        ("50%", 0.5),
        ("5!", 120),
        ("0.1+0.2", pytest.approx(0.3)),
        ("-5+3", -2),
        ("--5", 5),
        ("-(-5)", 5),
        ("2^3^2", 512),            # right associative
        ("-2^2", -4),              # unary binds looser than ^
        ("(1+2)*3", 9),
        ("1+2*3", 7),
        ("100/10/2", 5),           # left associative
        ("2(3+4)", 14),            # implicit multiplication
        ("2pi", 2 * math.pi),
        ("(2)(3)", 6),
        ("3×4", 12),
        ("12÷4", 3),
        ("5²", 25),
        ("√16", 4),
        ("0xff", 255),
        ("0b1010", 10),
        ("0o17", 15),
        ("1.5e3", 1500),
    ],
)
def test_arithmetic(expression: str, expected):
    assert evaluate(expression) == pytest.approx(expected)


def test_percent_applies_to_the_preceding_operand_only():
    assert evaluate("200*10%") == pytest.approx(20.0)


def test_percent_followed_by_a_number_is_an_implicit_product():
    # "10 % 4" reads as (10/100) * 4 -- % is always the postfix percent.
    assert evaluate("10 % 4") == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# functions & constants
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "expression, expected",
    [
        ("sqrt(144)", 12),
        ("cbrt(-27)", -3),
        ("root(81,4)", 3),
        ("abs(-7)", 7),
        ("sign(-3)", -1),
        ("floor(2.7)", 2),
        ("ceil(2.1)", 3),
        ("round(2.567,1)", 2.6),
        ("trunc(-2.9)", -2),
        ("frac(3.25)", pytest.approx(0.25)),
        ("log(1000)", 3),
        ("log(8,2)", 3),
        ("ln(e)", 1),
        ("log2(512)", 9),
        ("exp(0)", 1),
        ("pow(2,8)", 256),
        ("hypot(3,4)", 5),
        ("min(4,2,9)", 2),
        ("max(4,2,9)", 9),
        ("sum(1,2,3,4)", 10),
        ("mean(2,4,6)", 4),
        ("gcd(12,18)", 6),
        ("lcm(4,6)", 12),
        ("mod(7,3)", 1),
        ("comb(5,2)", 10),
        ("perm(5,2)", 20),
        ("fact(6)", 720),
        ("fact(0)", 1),
        ("pi", math.pi),
        ("π", math.pi),
        ("e", math.e),
        ("tau", math.tau),
        ("phi", (1 + 5 ** 0.5) / 2),
    ],
)
def test_functions_and_constants(expression: str, expected):
    assert evaluate(expression) == pytest.approx(expected)


def test_trig_respects_the_angle_mode():
    ctx = Context(angle_mode="deg")
    assert evaluate("sin(30)", ctx) == pytest.approx(0.5)
    assert evaluate("cos(60)", ctx) == pytest.approx(0.5)

    ctx_rad = Context(angle_mode="rad")
    assert evaluate("sin(pi/6)", ctx_rad) == pytest.approx(0.5)

    ctx_grad = Context(angle_mode="grad")
    assert evaluate("sin(100)", ctx_grad) == pytest.approx(1.0)


def test_inverse_trig_returns_angles_in_the_active_mode():
    ctx = Context(angle_mode="deg")
    assert evaluate("asin(0.5)", ctx) == pytest.approx(30)
    assert evaluate("atan(1)", ctx) == pytest.approx(45)


def test_function_aliases_work():
    assert evaluate("factorial(5)") == 120
    assert evaluate("avg(2,4)") == 3


def test_functions_are_case_insensitive():
    assert evaluate("SQRT(9)") == 3


def test_nested_calls():
    assert evaluate("sqrt(abs(-16))") == 4
    assert evaluate("max(sqrt(9), 2^1, 1)") == 3


# ---------------------------------------------------------------------------
# variables
# ---------------------------------------------------------------------------
def test_user_variables(engine: CalculatorEngine):
    engine.define("x", 5)
    assert engine.evaluate("x*2") == 10


def test_ans_holds_the_previous_result(engine: CalculatorEngine):
    engine.evaluate("6*7")
    assert engine.evaluate("ans+1") == 43


def test_unknown_name_reports_the_identifier():
    with pytest.raises(UnknownSymbolError) as excinfo:
        evaluate("foo+1")
    assert "foo" in str(excinfo.value.message)


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------
def test_division_by_zero():
    with pytest.raises(DivisionByZeroError):
        evaluate("1/0")


def test_zero_modulo_raises():
    with pytest.raises(DomainError):
        evaluate("mod(5,0)")


def test_sqrt_of_negative_raises():
    with pytest.raises(DomainError):
        evaluate("sqrt(-1)")


def test_negative_base_fractional_exponent_is_a_domain_error():
    with pytest.raises(DomainError):
        evaluate("(-8)^0.5")


def test_log_of_zero_raises():
    with pytest.raises(DomainError):
        evaluate("ln(0)")


def test_factorial_of_negative_raises():
    with pytest.raises(DomainError):
        evaluate("(-1)!")


def test_wrong_arity_raises():
    with pytest.raises(ArityError):
        evaluate("sqrt(1,2)")


def test_unknown_function_raises():
    with pytest.raises(UnknownFunctionError):
        evaluate("foobar(1)")


def test_overflow_raises():
    with pytest.raises(OverflowResultError):
        evaluate("10^400")


@pytest.mark.parametrize(
    "expression, error",
    [
        ("1 $ 1", LexError),
        ("1 +", ParseError),
        ("nope", UnknownSymbolError),
        ("1/0", DivisionByZeroError),
    ],
)
def test_all_errors_derive_from_calc_error(expression: str, error):
    with pytest.raises(CalcError) as excinfo:
        evaluate(expression)
    assert isinstance(excinfo.value, error)


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "open('/etc/passwd')",
        "().__class__",
        "eval('1')",
        "exec('x=1')",
    ],
)
def test_python_injection_is_not_possible(expression: str):
    """The engine is a real parser, never eval() -- these must all fail."""
    with pytest.raises(CalcError):
        evaluate(expression)
