"""Parser tests: structure, precedence, associativity and error positions."""

from __future__ import annotations

import pytest

from calc.core.errors import ParseError
from calc.core.parser import (
    BinaryNode,
    CallNode,
    NameNode,
    NumberNode,
    PostfixNode,
    UnaryNode,
    parse,
)


def test_number():
    assert isinstance(parse("42"), NumberNode)


def test_addition_is_binary():
    node = parse("1+2")
    assert isinstance(node, BinaryNode) and node.op == "+"


def test_multiplication_binds_tighter_than_addition():
    node = parse("1+2*3")
    assert isinstance(node, BinaryNode) and node.op == "+"
    assert isinstance(node.right, BinaryNode) and node.right.op == "*"


def test_left_associativity_of_subtraction():
    node = parse("10-3-2")
    # ((10-3)-2), not (10-(3-2))
    assert isinstance(node.left, BinaryNode) and node.left.op == "-"
    assert isinstance(node.right, NumberNode) and node.right.raw == "2"


def test_exponent_is_right_associative():
    node = parse("2^3^2")
    assert node.op == "^"
    assert isinstance(node.right, BinaryNode) and node.right.op == "^"


def test_unary_minus_applies_to_the_whole_power():
    node = parse("-2^2")
    assert isinstance(node, UnaryNode) and node.op == "-"
    assert isinstance(node.operand, BinaryNode) and node.operand.op == "^"


def test_negative_exponent_is_allowed():
    node = parse("2^-3")
    assert isinstance(node.right, UnaryNode) and node.right.op == "-"


def test_parentheses_override_precedence():
    node = parse("(1+2)*3")
    assert node.op == "*"
    assert isinstance(node.left, BinaryNode) and node.left.op == "+"


def test_function_call():
    node = parse("sin(30)")
    assert isinstance(node, CallNode) and node.name == "sin"
    assert len(node.args) == 1


def test_multi_argument_call():
    node = parse("max(1,2,3)")
    assert isinstance(node, CallNode)
    assert len(node.args) == 3


def test_zero_argument_call():
    node = parse("now()")
    assert isinstance(node, CallNode) and node.args == ()


def test_bare_name_is_a_name_node():
    node = parse("pi")
    assert isinstance(node, NameNode) and node.name == "pi"


def test_postfix_operators():
    assert isinstance(parse("50%"), PostfixNode)
    assert isinstance(parse("5!"), PostfixNode)


def test_implicit_multiplication_with_parentheses():
    node = parse("2(3+4)")
    assert isinstance(node, BinaryNode) and node.op == "*"
    assert isinstance(node.left, NumberNode) and node.left.raw == "2"


def test_implicit_multiplication_with_a_name():
    node = parse("2pi")
    assert isinstance(node, BinaryNode) and node.op == "*"
    assert isinstance(node.right, NameNode) and node.right.name == "pi"


def test_implicit_multiplication_does_not_break_calls():
    # sin(30) must stay a call, never "sin * (30)".
    assert isinstance(parse("sin(30)"), CallNode)


def test_implicit_multiplication_after_a_call():
    node = parse("2sin(30)")
    assert isinstance(node, BinaryNode) and node.op == "*"
    assert isinstance(node.right, CallNode)


def test_chained_implicit_multiplication():
    node = parse("2(3)(4)")
    assert isinstance(node, BinaryNode) and node.op == "*"
    assert isinstance(node.left, BinaryNode) and node.left.op == "*"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "1+",
        "*2",
        "(1+2",
        "1+2)",
        "sin(",
        "1,,2",
        "max(1,)",
    ],
)
def test_invalid_syntax_raises(text: str):
    with pytest.raises(ParseError):
        parse(text)


def test_error_carries_a_position():
    with pytest.raises(ParseError) as excinfo:
        parse("1 + )")
    assert excinfo.value.position == 4


def test_position_points_at_the_unexpected_token():
    with pytest.raises(ParseError) as excinfo:
        parse("12 + + ")
    assert excinfo.value.position == 7
