"""Abstract syntax tree and recursive-descent parser.

Grammar (in order of increasing binding strength)::

    expression   := additive
    additive     := multiplicative (('+' | '-') multiplicative)*
    multiplicative := unary (('*' | '/') unary | <implicit> unary)*
    unary        := ('+' | '-') unary | power
    power        := postfix ('^' unary)?            # right associative
    postfix      := primary (('%' | '!'))*
    primary      := NUMBER | NAME | NAME '(' args ')' | '(' expression ')'

Implicit multiplication is recognised in ``multiplicative``: whenever an
operand can start right after a complete one (``2π``, ``(1)(2)``, ``3sin(x)``)
a multiplication is implied.  Doing it here rather than in the lexer is what
makes ``sin(30)`` a call instead of ``sin * 30``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union

from .errors import ParseError
from .functions import FUNCTIONS
from .lexer import Token, TokenType, tokenize

__all__ = [
    "Node",
    "NumberNode",
    "NameNode",
    "UnaryNode",
    "BinaryNode",
    "PostfixNode",
    "CallNode",
    "parse",
]


@dataclass(frozen=True)
class Node:
    """Base class for every AST node; ``pos`` is an index into the input."""

    pos: int = 0


@dataclass(frozen=True)
class NumberNode(Node):
    raw: str = "0"


@dataclass(frozen=True)
class NameNode(Node):
    name: str = ""


@dataclass(frozen=True)
class UnaryNode(Node):
    op: str = "+"
    operand: Node | None = None


@dataclass(frozen=True)
class BinaryNode(Node):
    op: str = "+"
    left: Node | None = None
    right: Node | None = None


@dataclass(frozen=True)
class PostfixNode(Node):
    op: str = "%"
    operand: Node | None = None


@dataclass(frozen=True)
class CallNode(Node):
    name: str = ""
    args: tuple = field(default_factory=tuple)


_OPERAND_START = (TokenType.NUMBER, TokenType.LPAREN, TokenType.NAME)


class _Parser:
    def __init__(self, tokens: List[Token], function_names: set[str] | None = None) -> None:
        self._tokens = tokens
        self._index = 0
        # Names that may be called without parentheses: "√16", "sin30".
        self._function_names = set(FUNCTIONS) if function_names is None else set(function_names)

    # -- token helpers -----------------------------------------------------
    @property
    def current(self) -> Token:
        return self._tokens[self._index]

    def peek(self, offset: int = 0) -> Token:
        index = min(self._index + offset, len(self._tokens) - 1)
        return self._tokens[index]

    def advance(self) -> Token:
        token = self._tokens[self._index]
        if token.type is not TokenType.EOF:
            self._index += 1
        return token

    def check(self, tok_type: TokenType, value: str | None = None) -> bool:
        token = self.current
        if token.type is not tok_type:
            return False
        return value is None or token.value == value

    def expect(self, tok_type: TokenType, value: str | None = None) -> Token:
        if not self.check(tok_type, value):
            wanted = value or tok_type.name.lower()
            got = self.current.value or "end of input"
            raise ParseError(f"Expected '{wanted}' but found '{got}'", self.current.start)
        return self.advance()

    # -- grammar -----------------------------------------------------------
    def parse_all(self) -> Node:
        """Parse a *complete* input: expression followed by end of input."""
        node = self.parse_expression()
        if self.current.type is not TokenType.EOF:
            raise ParseError(f"Unexpected '{self.current.value}'", self.current.start)
        return node

    def parse_expression(self) -> Node:
        """Parse one expression.

        Deliberately does *not* require EOF: this is also used for the inside
        of parentheses and for every argument of a call, where the expression
        legitimately ends at ``)`` or ``,``.
        """
        return self.parse_additive()

    def parse_additive(self) -> Node:
        node = self.parse_multiplicative()
        while self.check(TokenType.OPERATOR) and self.current.value in ("+", "-"):
            op = self.advance().value
            right = self.parse_multiplicative()
            node = BinaryNode(pos=node.pos, op=op, left=node, right=right)
        return node

    def parse_multiplicative(self) -> Node:
        node = self.parse_unary()
        while True:
            if self.check(TokenType.OPERATOR) and self.current.value in ("*", "/"):
                op = self.advance().value
                right = self.parse_unary()
                node = BinaryNode(pos=node.pos, op=op, left=node, right=right)
            elif self.current.type in _OPERAND_START:
                # Implicit multiplication: 2pi, (1)(2), 3sin(x)
                right = self.parse_unary()
                node = BinaryNode(pos=node.pos, op="*", left=node, right=right)
            else:
                return node

    def parse_unary(self) -> Node:
        if self.check(TokenType.OPERATOR) and self.current.value in ("+", "-"):
            op_token = self.advance()
            operand = self.parse_unary()
            return UnaryNode(pos=op_token.start, op=op_token.value, operand=operand)
        return self.parse_power()

    def parse_power(self) -> Node:
        base = self.parse_postfix()
        if self.check(TokenType.OPERATOR, "^"):
            self.advance()
            # Right associative and allows a unary exponent: 2^-3
            exponent = self.parse_unary()
            return BinaryNode(pos=base.pos, op="^", left=base, right=exponent)
        return base

    def parse_postfix(self) -> Node:
        node = self.parse_primary()
        while self.current.type is TokenType.POSTFIX:
            op_token = self.advance()
            node = PostfixNode(pos=node.pos, op=op_token.value, operand=node)
        return node

    def parse_primary(self) -> Node:
        token = self.current

        if token.type is TokenType.NUMBER:
            self.advance()
            return NumberNode(pos=token.start, raw=token.value)

        if token.type is TokenType.LPAREN:
            self.advance()
            inner = self.parse_expression()
            self.expect(TokenType.RPAREN, ")")
            return inner

        if token.type is TokenType.NAME:
            self.advance()
            if self.current.type is TokenType.LPAREN:
                self.advance()
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, ")")
                return CallNode(pos=token.start, name=token.value, args=tuple(args))
            if self._is_argument_less_call(token.value):
                # "√16" / "sin30" -- the argument binds tightly, so √16+4 == (√16)+4
                argument = self.parse_postfix()
                return CallNode(pos=token.start, name=token.value, args=(argument,))
            return NameNode(pos=token.start, name=token.value)

        raise ParseError(
            f"Expected a number or name but found '{token.value or 'end of input'}'",
            token.start,
        )

    def parse_arguments(self) -> List[Node]:
        if self.current.type is TokenType.RPAREN:
            return []
        args = [self.parse_expression()]
        while self.current.type is TokenType.COMMA:
            self.advance()
            args.append(self.parse_expression())
        return args

    def _is_argument_less_call(self, name: str) -> bool:
        """True for ``√16`` / ``sin30`` -- a known function directly followed
        by an operand, so it can be called without parentheses."""
        if self.current.type not in _OPERAND_START:
            return False
        return name in self._function_names or name.lower() in self._function_names


AnyNode = Union[NumberNode, NameNode, UnaryNode, BinaryNode, PostfixNode, CallNode]


def parse(text: str, function_names: set[str] | None = None) -> Node:
    """Parse ``text`` into an AST.

    :param function_names: names allowed to be called without parentheses.
        Defaults to every function in :data:`calc.core.functions.FUNCTIONS`.
    :raises LexError: on an unreadable character.
    :raises ParseError: on malformed syntax.
    """
    tokens = tokenize(text)
    if tokens[0].type is TokenType.EOF:
        raise ParseError("Empty expression", 0)
    return _Parser(tokens, function_names).parse_all()
