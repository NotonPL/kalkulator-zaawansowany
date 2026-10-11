"""Function and constant registry.

Every callable the expression language knows about lives here.  The GUI's
"function browser" reads :data:`FUNCTIONS` directly, so adding a function in
this file automatically makes it available in the UI, the docs and the CLI help.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Sequence, Tuple

from .errors import ArityError, DomainError

__all__ = ["FunctionSpec", "FUNCTIONS", "CONSTANTS", "AngleMode", "lookup_function", "lookup_constant"]


class AngleMode:
    DEG = "deg"
    RAD = "rad"
    GRAD = "grad"

    #: Order used when the user cycles the angle unit with Ctrl+M.
    ALL = (RAD, DEG, GRAD)

    @staticmethod
    def to_radians(value: float, mode: str) -> float:
        if mode == AngleMode.DEG:
            return math.radians(value)
        if mode == AngleMode.GRAD:
            return value * math.pi / 200.0
        return value

    @staticmethod
    def from_radians(value: float, mode: str) -> float:
        if mode == AngleMode.DEG:
            return math.degrees(value)
        if mode == AngleMode.GRAD:
            return value * 200.0 / math.pi
        return value


@dataclass(frozen=True)
class FunctionSpec:
    """Metadata + implementation for one callable."""

    name: str
    arity: Tuple[int, Optional[int]]  # (min, max); None == unlimited
    impl: Callable[..., float]
    description: str
    category: str = "general"
    angular: bool = False          # first argument is an angle -> convert
    inverse_angular: bool = False  # result is an angle  -> convert back
    aliases: Tuple[str, ...] = ()

    def accepts(self, count: int) -> bool:
        minimum, maximum = self.arity
        if count < minimum:
            return False
        return maximum is None or count <= maximum

    def signature(self) -> str:
        minimum, maximum = self.arity
        if minimum == maximum:
            inner = ", ".join("x" if minimum == 1 else f"x{i + 1}" for i in range(minimum))
        else:
            inner = ", ".join(["x"] + ["..."])
        return f"{self.name}({inner})"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _require_positive(value: float, name: str) -> None:
    if value < 0:
        raise DomainError(f"{name}() needs a non-negative argument")


def _factorial(value: float) -> float:
    if value < 0:
        raise DomainError("factorial() needs a non-negative argument")
    if value > 170:
        raise DomainError("factorial() argument too large")
    if float(value).is_integer():
        return float(math.factorial(int(value)))
    return math.gamma(value + 1)  # analytic continuation for x.5 etc.


def _log(value: float, base: Optional[float] = None) -> float:
    if value <= 0:
        raise DomainError("log() needs a positive argument")
    if base is None:
        return math.log10(value)
    if base <= 0 or base == 1:
        raise DomainError("log() base must be positive and different from 1")
    return math.log(value, base)


def _ln(value: float) -> float:
    if value <= 0:
        raise DomainError("ln() needs a positive argument")
    return math.log(value)


def _sqrt(value: float) -> float:
    _require_positive(value, "sqrt")
    return math.sqrt(value)


def _cbrt(value: float) -> float:
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def _root(value: float, degree: float) -> float:
    if degree == 0:
        raise DomainError("root() degree cannot be zero")
    if value < 0 and float(degree).is_integer() and int(degree) % 2 == 1:
        return -((-value) ** (1.0 / degree))
    if value < 0:
        raise DomainError("root() of a negative number needs an odd degree")
    return value ** (1.0 / degree)


def _mod(left: float, right: float) -> float:
    if right == 0:
        raise DomainError("mod() by zero")
    return math.fmod(left, right)


def _frac(value: float) -> float:
    return math.copysign(value - math.trunc(value), value)


def _trunc(value: float) -> float:
    return float(math.trunc(value))


def _round(value: float, digits: float = 0.0) -> float:
    return float(round(value, int(digits)))


def _gcd(*values: float) -> float:
    return float(math.gcd(*(int(v) for v in values)))


def _lcm(*values: float) -> float:
    return float(math.lcm(*(int(v) for v in values)))


def _hypot(*values: float) -> float:
    return math.hypot(*values)


def _mean(*values: float) -> float:
    if not values:
        raise ArityError("mean() needs at least one argument")
    return sum(values) / len(values)


def _comb(n: float, k: float) -> float:
    if n < 0 or k < 0 or k > n:
        raise DomainError("comb(n, k) needs 0 <= k <= n")
    return float(math.comb(int(n), int(k)))


def _perm(n: float, k: float) -> float:
    if n < 0 or k < 0 or k > n:
        raise DomainError("perm(n, k) needs 0 <= k <= n")
    return float(math.perm(int(n), int(k)))


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
def _spec(
    name: str,
    arity: Tuple[int, Optional[int]],
    impl: Callable[..., float],
    description: str,
    category: str = "general",
    **kwargs,
) -> FunctionSpec:
    return FunctionSpec(name=name, arity=arity, impl=impl, description=description,
                        category=category, **kwargs)


_FUNCTION_LIST: Sequence[FunctionSpec] = (
    # trigonometry -----------------------------------------------------------
    _spec("sin", (1, 1), math.sin, "Sine of an angle", "trigonometry", angular=True),
    _spec("cos", (1, 1), math.cos, "Cosine of an angle", "trigonometry", angular=True),
    _spec("tan", (1, 1), math.tan, "Tangent of an angle", "trigonometry", angular=True),
    _spec("asin", (1, 1), math.asin, "Arc sine, returns an angle", "trigonometry", inverse_angular=True),
    _spec("acos", (1, 1), math.acos, "Arc cosine, returns an angle", "trigonometry", inverse_angular=True),
    _spec("atan", (1, 1), math.atan, "Arc tangent, returns an angle", "trigonometry", inverse_angular=True),
    _spec("atan2", (2, 2), math.atan2, "Arc tangent of y/x, returns an angle", "trigonometry", inverse_angular=True),
    _spec("sinh", (1, 1), math.sinh, "Hyperbolic sine", "trigonometry"),
    _spec("cosh", (1, 1), math.cosh, "Hyperbolic cosine", "trigonometry"),
    _spec("tanh", (1, 1), math.tanh, "Hyperbolic tangent", "trigonometry"),
    _spec("degrees", (1, 1), math.degrees, "Radians to degrees", "trigonometry"),
    _spec("radians", (1, 1), math.radians, "Degrees to radians", "trigonometry"),
    # logarithms / exponentials ---------------------------------------------
    _spec("log", (1, 2), _log, "Base-10 logarithm, or log(x, base)", "logarithms"),
    _spec("ln", (1, 1), _ln, "Natural logarithm", "logarithms", aliases=("log_e",)),
    _spec("log2", (1, 1), math.log2, "Base-2 logarithm", "logarithms"),
    _spec("log10", (1, 1), math.log10, "Base-10 logarithm", "logarithms"),
    _spec("exp", (1, 1), math.exp, "e raised to the power of x", "logarithms"),
    # roots & powers ---------------------------------------------------------
    _spec("sqrt", (1, 1), _sqrt, "Square root", "powers", aliases=("√",)),
    _spec("cbrt", (1, 1), _cbrt, "Cube root", "powers"),
    _spec("root", (2, 2), _root, "nth root: root(x, n)", "powers"),
    _spec("pow", (2, 2), math.pow, "x raised to the power y", "powers"),
    _spec("hypot", (2, None), _hypot, "Euclidean norm of the arguments", "powers"),
    # rounding & sign --------------------------------------------------------
    _spec("abs", (1, 1), math.fabs, "Absolute value", "rounding", aliases=("fabs",)),
    _spec("sign", (1, 1), lambda x: float((x > 0) - (x < 0)), "Sign of x (-1, 0, 1)", "rounding"),
    _spec("floor", (1, 1), lambda x: float(math.floor(x)), "Round down", "rounding"),
    _spec("ceil", (1, 1), lambda x: float(math.ceil(x)), "Round up", "rounding"),
    _spec("round", (1, 2), _round, "Round to n digits", "rounding"),
    _spec("trunc", (1, 1), _trunc, "Drop the fractional part", "rounding"),
    _spec("frac", (1, 1), _frac, "Fractional part of x", "rounding"),
    # number theory ----------------------------------------------------------
    _spec("fact", (1, 1), _factorial, "Factorial (integers, or Gamma for x.5)", "number theory", aliases=("factorial",)),
    _spec("gcd", (2, None), _gcd, "Greatest common divisor", "number theory"),
    _spec("lcm", (2, None), _lcm, "Least common multiple", "number theory"),
    _spec("mod", (2, 2), _mod, "Remainder of x / y", "number theory"),
    _spec("comb", (2, 2), _comb, "Binomial coefficient C(n, k)", "number theory"),
    _spec("perm", (2, 2), _perm, "Number of k-permutations of n", "number theory"),
    # statistics -------------------------------------------------------------
    _spec("sum", (1, None), lambda *v: float(sum(v)), "Sum of all arguments", "statistics"),
    _spec("min", (1, None), lambda *v: float(min(v)), "Smallest argument", "statistics"),
    _spec("max", (1, None), lambda *v: float(max(v)), "Largest argument", "statistics"),
    _spec("mean", (1, None), _mean, "Arithmetic mean", "statistics", aliases=("avg",)),
)

FUNCTIONS: Dict[str, FunctionSpec] = {}
for _fn in _FUNCTION_LIST:
    FUNCTIONS[_fn.name] = _fn
    for _alias in _fn.aliases:
        FUNCTIONS[_alias] = _fn


CONSTANTS: Dict[str, float] = {
    "pi": math.pi,
    "π": math.pi,
    "tau": math.tau,
    "τ": math.tau,
    "e": math.e,
    "phi": (1 + 5 ** 0.5) / 2,
    "φ": (1 + 5 ** 0.5) / 2,
    "inf": math.inf,
    "c": 299_792_458.0,          # speed of light, m/s
    "g": 9.80665,                # standard gravity, m/s^2
    "avogadro": 6.022_140_76e23,
    "boltzmann": 1.380_649e-23,
}


def lookup_function(name: str) -> FunctionSpec:
    """Return the spec for ``name`` (case insensitive, aliases included)."""
    spec = FUNCTIONS.get(name) or FUNCTIONS.get(name.lower())
    if spec is None:
        from .errors import UnknownFunctionError

        raise UnknownFunctionError(f"Unknown function '{name}()'")
    return spec


def lookup_constant(name: str) -> Optional[float]:
    """Return the value of a built-in constant or ``None`` if unknown."""
    if name in CONSTANTS:
        return CONSTANTS[name]
    return CONSTANTS.get(name.lower())
