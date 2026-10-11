"""Tokeniser tests."""

from __future__ import annotations

import pytest

from calc.core.errors import LexError
from calc.core.lexer import TokenType, tokenize


def types_of(text: str) -> list[str]:
    return [token.type.name for token in tokenize(text) if token.type is not TokenType.EOF]


def test_simple_expression_tokenizes():
    assert types_of("1+2") == ["NUMBER", "OPERATOR", "NUMBER"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("3 × 4", "*"),
        ("3 ÷ 4", "/"),
        ("5 − 2", "-"),
        ("2 ** 3", "^"),
        ("2²", "^"),
    ],
)
def test_unicode_operators_are_normalised(text: str, expected: str):
    operators = [t.value for t in tokenize(text) if t.type is TokenType.OPERATOR]
    assert expected in operators


def test_squared_alias_produces_exponent_token():
    tokens = tokenize("5²")
    assert tokens[1].value == "^"
    assert tokens[2].value == "2"
    assert tokens[2].type is TokenType.NUMBER


def test_sqrt_symbol_becomes_a_name():
    tokens = tokenize("√9")
    assert tokens[0].type is TokenType.NAME
    assert tokens[0].value == "sqrt"


def test_decimal_number():
    token = tokenize("3.1415")[0]
    assert token.type is TokenType.NUMBER
    assert token.value == "3.1415"


def test_scientific_notation():
    assert tokenize("1.5e-10")[0].value == "1.5e-10"
    assert tokenize("3E+8")[0].value == "3E+8"


def test_e_is_not_swallowed_as_exponent():
    # "2e" must stay two tokens: the number 2 and the constant e.
    tokens = tokenize("2e")
    assert tokens[0].value == "2"
    assert tokens[1].value == "e"
    assert tokens[1].type is TokenType.NAME


def test_radix_literals():
    assert tokenize("0xff")[0].value == "0xff"
    assert tokenize("0b1011")[0].value == "0b1011"
    assert tokenize("0o17")[0].value == "0o17"


def test_postfix_percent_and_factorial():
    assert types_of("50%") == ["NUMBER", "POSTFIX"]
    assert types_of("5!") == ["NUMBER", "POSTFIX"]


def test_names_may_be_unicode():
    tokens = tokenize("π")
    assert tokens[0].type is TokenType.NAME
    assert tokens[0].value == "π"


def test_positions_are_recorded():
    tokens = tokenize("12 + 34")
    assert tokens[0].start == 0 and tokens[0].end == 2
    assert tokens[2].start == 5 and tokens[2].end == 7


@pytest.mark.parametrize("text", ["1 $ 2", "1 & 2", "1 # 2", "@"])
def test_invalid_character_raises(text: str):
    with pytest.raises(LexError):
        tokenize(text)


def test_lex_error_reports_position():
    with pytest.raises(LexError) as excinfo:
        tokenize("12 + $3")
    assert excinfo.value.position == 5


def test_whitespace_is_ignored():
    assert types_of("  1   +   2  ") == ["NUMBER", "OPERATOR", "NUMBER"]


def test_comma_and_semicolon_are_argument_separators():
    assert types_of("max(1;2)") == ["NAME", "LPAREN", "NUMBER", "COMMA", "NUMBER", "RPAREN"]


def test_empty_input_yields_only_eof():
    assert types_of("") == []
    assert tokenize("")[-1].type is TokenType.EOF
