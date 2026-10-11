"""python-calculator -- a themeable scientific calculator in Python + Qt.

The package is split so the heavy Qt import only happens when you actually want
a window::

    from calc.core import CalculatorEngine     # no Qt, works anywhere
    from calc.gui import run_gui               # imports PySide6 lazily
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "python-calculator contributors"
__license__ = "MIT"

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "NoDisplayError",
    "run",
    "run_cli",
    "run_gui",
]


class NoDisplayError(RuntimeError):
    """Raised when a graphical session cannot be created.

    ``calc.gui`` imports this from here (rather than defining its own copy) so
    that :func:`run` can catch it without importing Qt at module scope.
    """


def run(argv: list[str] | None = None) -> int:
    """Entry point used by the ``pycalc`` console script.

    Tries the graphical app first and falls back to the terminal REPL when no
    display is available -- which is exactly what happens on a phone running
    Termux.
    """
    import sys

    args = list(sys.argv[1:] if argv is None else argv)

    if "--version" in args or "-V" in args:
        print(f"python-calculator {__version__}")
        return 0

    if "--help" in args or "-h" in args:
        print(_usage())
        return 0

    if args and args[0] in ("cli", "--cli"):
        return run_cli(args[1:])

    try:
        return run_gui(args)
    except (NoDisplayError, ImportError) as exc:
        print(f"No graphical session available ({exc}).")
        print("Starting the terminal interface instead.")
        print("Install the GUI extras with:  pip install 'python-calculator[gui]'\n")
        return run_cli(args)


def run_gui(argv: list[str] | None = None) -> int:
    """Start the Qt application.  Imports PySide6 only when called."""
    from .gui import run_gui as _run_gui

    return _run_gui(argv or [])


def run_cli(argv: list[str] | None = None) -> int:
    """Start the terminal REPL.  Never imports Qt."""
    from .cli import main

    return main(argv or [])


def _usage() -> str:
    return (
        "python-calculator -- a themeable scientific calculator\n"
        "\n"
        "Usage:\n"
        "  pycalc                 start the graphical app (falls back to the terminal)\n"
        "  pycalc cli             start the terminal interface directly\n"
        "  pycalc --version       print the version\n"
        "  pycalc --help          show this help\n"
    )
