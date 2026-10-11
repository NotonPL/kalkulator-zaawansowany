"""Tokeniser for calculator expressions.

The lexer accepts the "friendly" input that a phone user actually types --
``÷``, ``×``, ``π``, ``²``, ``√`` -- and normalises it into a flat list of
tokens.  Implicit multiplication is *not* inserted here; the parser handles it,
because only the parser knows whether ``sin`` followed by ``(`` is a function
call or a product.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List

from .errors import LexError

__all__ = ["TokenType", "Token", "tokenize", "OPERATOR_ALIASES"]


class TokenType(Enum):
    NUMBER = auto()
    NAME = auto()      # identifier: function name, constant or variable
    OPERATOR = auto()  # + - * / ^
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    POSTFIX = auto()   # ! and the percent sign
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    start: int
    end: int

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.type.name}, {self.value!r}, {self.start})"


#: Aliases the user may type mapped onto canonical symbols.  Longer keys are
#: tried first so ``**`` wins over ``*``.
OPERATOR_ALIASES = {
    "**": "^",
    "×": "*",
    "·": "*",
    "∙": "*",
    "÷": "/",
    "−": "-",   # U+2212 minus sign
    "–": "-",   # en dash
    "—": "-",   # em dash
    "√": "sqrt",
    "²": "^2",
    "³": "^3",
}

_DIGITS = set("0123456789")
_RADIX_DIGITS = set("0123456789abcdefABCDEF_")
_NAME_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_NAME_CHARS = _NAME_START | _DIGITS
_SINGLE_CHAR_OPS = set("+-*/^")


def _is_name_start(ch: str) -> bool:
    """ASCII letters plus any non-ASCII letter (``π``, ``φ``, ``τ``...)."""
    return ch in _NAME_START or ch.isalpha()


def _match_alias(text: str, pos: int) -> str | None:
    for size in (2, 1):
        candidate = text[pos : pos + size]
        if candidate in OPERATOR_ALIASES:
            return candidate
    return None


def _read_number(text: str, pos: int) -> tuple[str, int]:
    """Read a decimal, scientific or radix (``0x``/``0b``/``0o``) literal."""
    start = pos
    length = len(text)

    if text[pos] == "0" and pos + 1 < length and text[pos + 1] in ("x", "b", "o"):
        pos += 2
        while pos < length and text[pos] in _RADIX_DIGITS:
            pos += 1
        return text[start:pos], pos

    while pos < length and text[pos] in _DIGITS:
        pos += 1
    if pos < length and text[pos] == ".":
        pos += 1
        while pos < length and text[pos] in _DIGITS:
            pos += 1

    # Scientific notation: 1.5e-10 / 3E+8
    if pos < length and text[pos] in ("e", "E"):
        lookahead = pos + 1
        if lookahead < length and text[lookahead] in ("+", "-"):
            lookahead += 1
        if lookahead < length and text[lookahead] in _DIGITS:
            pos = lookahead
            while pos < length and text[pos] in _DIGITS:
                pos += 1

    return text[start:pos], pos


def tokenize(text: str) -> List[Token]:
    """Convert ``text`` into a token list terminated by an ``EOF`` token.

    :raises LexError: if the input contains a character that cannot be read.
    """
    tokens: List[Token] = []
    pos = 0
    length = len(text)

    def push(tok_type: TokenType, value: str, start: int, end: int) -> None:
        tokens.append(Token(tok_type, value, start, end))

    while pos < length:
        ch = text[pos]

        if ch.isspace():
            pos += 1
            continue

        alias = _match_alias(text, pos)
        if alias is not None:
            replacement = OPERATOR_ALIASES[alias]
            end = pos + len(alias)
            if replacement == "sqrt":
                push(TokenType.NAME, replacement, pos, end)
            elif replacement.startswith("^"):
                push(TokenType.OPERATOR, "^", pos, end)
                push(TokenType.NUMBER, replacement[1:], end, end)
            else:
                push(TokenType.OPERATOR, replacement, pos, end)
            pos = end
            continue

        if ch in _DIGITS or (ch == "." and pos + 1 < length and text[pos + 1] in _DIGITS):
            start = pos
            raw, pos = _read_number(text, start)
            push(TokenType.NUMBER, raw.replace("_", ""), start, pos)
            continue

        if _is_name_start(ch):
            start = pos
            while pos < length and (text[pos] in _NAME_CHARS or text[pos].isalpha()):
                pos += 1
            push(TokenType.NAME, text[start:pos], start, pos)
            continue

        if ch == "(":
            push(TokenType.LPAREN, ch, pos, pos + 1)
            pos += 1
            continue

        if ch == ")":
            push(TokenType.RPAREN, ch, pos, pos + 1)
            pos += 1
            continue

        if ch in (",", ";"):
            push(TokenType.COMMA, ",", pos, pos + 1)
            pos += 1
            continue

        if ch in _SINGLE_CHAR_OPS:
            push(TokenType.OPERATOR, ch, pos, pos + 1)
            pos += 1
            continue

        if ch in ("%", "!"):
            push(TokenType.POSTFIX, ch, pos, pos + 1)
            pos += 1
            continue

        raise LexError(f"Unexpected character '{ch}'", pos)

    push(TokenType.EOF, "", length, length)
    return tokens


def iter_tokens(text: str) -> Iterator[Token]:  # pragma: no cover - convenience
    return iter(tokenize(text))
