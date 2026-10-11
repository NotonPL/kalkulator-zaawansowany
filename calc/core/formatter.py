"""Number and expression formatting.

The core engine speaks ``float``; everything a human reads goes through here.
Formatting is a pure function of ``(value, settings)`` so the CLI, the GUI and
the tests all render identically.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

__all__ = ["FormatSettings", "format_number", "pretty_expression"]


@dataclass
class FormatSettings:
    """User-tweakable output options."""

    thousands: bool = True
    group_separator: str = " "     # " ", ",", "." or "\u202f" (narrow nbsp)
    decimal_separator: str = "."   # "." or ","
    precision: int = 12            # significant digits
    scientific_threshold: float = 1e12   # |x| >= this -> scientific notation
    scientific_small: float = 1e-9       # 0 < |x| < this -> scientific notation
    trim_zeros: bool = True

    @property
    def swap_separators(self) -> bool:
        return self.decimal_separator == ","


def _split_mantissa_exponent(text: str) -> tuple[str, Optional[str]]:
    if "e" in text or "E" in text:
        mantissa, _, exponent = text.partition("e")
        if not exponent:
            mantissa, _, exponent = text.partition("E")
        return mantissa, exponent
    return text, None


def _group_digits(int_part: str, separator: str) -> str:
    sign = "-" if int_part.startswith("-") else ""
    digits = int_part.lstrip("-")
    groups = []
    while len(digits) > 3:
        groups.append(digits[-3:])
        digits = digits[:-3]
    groups.append(digits)
    return sign + separator.join(reversed(groups))


def format_number(value: float, settings: Optional[FormatSettings] = None) -> str:
    """Render ``value`` according to ``settings``.

    >>> format_number(1234567.891)
    '1 234 567.891'
    >>> format_number(-0.5)
    '-0.5'
    """
    settings = settings or FormatSettings()

    if value is None:
        return ""
    if math.isnan(value):
        return "undefined"
    if math.isinf(value):
        return "-\u221e" if value < 0 else "\u221e"

    magnitude = abs(value)
    use_scientific = (
        value != 0
        and (magnitude >= settings.scientific_threshold or magnitude < settings.scientific_small)
    )

    if use_scientific:
        text = f"{value:.{max(0, settings.precision - 1)}e}"
        mantissa, exponent = _split_mantissa_exponent(text)
    else:
        text = f"{value:.{settings.precision}g}"
        mantissa, exponent = text, None

    # --- mantissa ---------------------------------------------------------
    if "." in mantissa:
        int_part, _, frac_part = mantissa.partition(".")
        if settings.trim_zeros:
            frac_part = frac_part.rstrip("0")
    else:
        int_part, frac_part = mantissa, ""

    if settings.thousands and int_part.lstrip("-").isdigit():
        int_part = _group_digits(int_part, settings.group_separator)

    result = int_part if not frac_part else f"{int_part}{settings.decimal_separator}{frac_part}"
    if result in ("", "-", "-0"):
        result = "0"

    if exponent is not None:
        exp_value = int(exponent)
        if abs(exp_value) >= 1000 or settings.thousands:
            result = f"{result}\u00d710^{exp_value}"
        else:
            result = f"{result}e{exp_value:+d}".replace("e+0", "e").replace("e-0", "e")
    return result


def _read_number(text: str, settings: FormatSettings) -> Optional[float]:
    """Parse a string previously produced by :func:`format_number`."""
    cleaned = text.replace(settings.group_separator, "").replace("\u202f", "").replace(" ", "")
    cleaned = cleaned.replace(settings.decimal_separator, ".")
    cleaned = cleaned.replace("\u221e", "inf").replace("\u00d710^", "e")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_formatted(text: str, settings: Optional[FormatSettings] = None) -> Optional[float]:
    """Inverse of :func:`format_number`; returns ``None`` if not a number."""
    return _read_number(text, settings or FormatSettings())


_SPACED = set("+-*/^")
_UNARY_AFTER = ("", "(", ",", "+", "-", "*", "/", "^")


def pretty_expression(expression: str) -> str:
    """Insert readable spacing around operators.

    ``2*(3+4)`` becomes ``2 * (3 + 4)``.  A sign is treated as unary -- and so
    left attached to its operand -- when it follows the start of the input, an
    opening bracket, a comma or another operator, so ``-3 + 4`` does not turn
    into ``- 3 + 4`` and ``2^-3`` keeps its ``-3``.
    """
    pieces: list[str] = []
    previous = ""
    for char in expression:
        if char.isspace():
            continue
        if char in _SPACED:
            if char in "+-" and previous in _UNARY_AFTER:
                pieces.append(char)
            else:
                pieces.append(f" {char} ")
            previous = char
        else:
            pieces.append(char)
            previous = char
    return re.sub(r" {2,}", " ", "".join(pieces)).strip()
