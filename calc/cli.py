"""Headless terminal interface.

This is what runs on a phone: Termux gives you Python but no window system, so
the same engine is driven through a REPL.  It supports the full expression
language, variables, history recall and all the commands the GUI exposes.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .core.engine import CalculatorEngine
from .core.errors import CalcError
from .core.formatter import FormatSettings
from .core.functions import CONSTANTS, FUNCTIONS, AngleMode

__all__ = ["main", "REPL"]


BANNER = """\
python-calculator {version} -- terminal mode
Type an expression and press Enter.  "?" lists every command, "quit" exits.
"""

HELP = """\
Commands
  <expression>        evaluate, e.g.  2*(3+4)^2
  ans                 previous result is always available as "ans"
  let x = 5           define a variable
  vars                list defined variables
  mode deg|rad|grad   set the angle unit (now: {angle})
  hist [n]            show the last n calculations (default 10)
  mem                 show memory slots
  mem store|add|sub|clear [slot]
  fn                  list every function
  const               list every constant
  fmt [n]             set significant digits (now: {precision})
  help                this text
  quit | exit         leave
"""


def _terminal_width() -> int:
    try:
        return max(40, shutil.get_terminal_size((80, 24)).columns)
    except Exception:  # pragma: no cover - very defensive
        return 80


def _print_error(error: CalcError, out=None) -> None:
    marker = ""
    if error.position is not None:
        marker = "\n" + " " * error.position + "^"
    print(f"  ! {error.message}{marker}", file=out or sys.stdout)


class REPL:
    """Read-eval-print loop over a :class:`CalculatorEngine`."""

    def __init__(self, engine: Optional[CalculatorEngine] = None, out=None) -> None:
        self.engine = engine or CalculatorEngine()
        self.out = out or sys.stdout
        self.precision = self.engine.format_settings.precision

    # -- helpers -----------------------------------------------------------
    def write(self, text: str = "") -> None:
        print(text, file=self.out)

    def prompt(self) -> str:
        mode = self.engine.angle_mode.upper()
        return f"[{mode}] > "

    # -- entry point -------------------------------------------------------
    def run(self) -> int:
        self.write(BANNER.format(version=__version__))
        while True:
            try:
                line = input(self.prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                self.write()
                return 0
            if not line:
                continue
            if line in ("quit", "exit", "q"):
                return 0
            self.execute(line)

    # -- dispatch ----------------------------------------------------------
    def execute(self, line: str) -> None:
        parts = line.split()
        head = parts[0].lower()

        if line == "?":
            self.write(HELP.format(angle=self.engine.angle_mode, precision=self.precision))
            return

        if head == "help":
            self.write(HELP.format(angle=self.engine.angle_mode, precision=self.precision))
            return

        if head == "let":
            self._let(line)
            return

        if head == "vars":
            variables = {k: v for k, v in self.engine.variables().items() if k != "ans"}
            self.write("  (none)" if not variables else "")
            for name, value in sorted(variables.items()):
                self.write(f"  {name} = {self.engine.format(value)}")
            return

        if head == "mode":
            self._mode(parts)
            return

        if head == "hist":
            self._history(parts)
            return

        if head == "mem":
            self._memory(parts)
            return

        if head == "fn":
            self._functions()
            return

        if head == "const":
            for name in sorted(CONSTANTS):
                self.write(f"  {name} = {CONSTANTS[name]:.10g}")
            return

        if head == "fmt":
            self._format(parts)
            return

        self._evaluate(line)

    # -- individual commands ------------------------------------------------
    def _evaluate(self, line: str) -> None:
        try:
            value = self.engine.evaluate(line)
        except CalcError as error:
            _print_error(error, self.out)
            return
        self.write(f"  = {self.engine.format(value)}")

    def _let(self, line: str) -> None:
        body = line[3:].strip()
        if "=" not in body:
            self.write("  usage: let x = 5")
            return
        name, _, expression = body.partition("=")
        name = name.strip()
        if not name.isidentifier():
            self.write("  variable names must be alphanumeric")
            return
        try:
            value = self.engine.evaluate(expression.strip(), remember=False)
        except CalcError as error:
            _print_error(error, self.out)
            return
        self.engine.define(name, value)
        self.write(f"  {name} = {self.engine.format(value)}")

    def _mode(self, parts: List[str]) -> None:
        if len(parts) < 2:
            self.write(f"  angle unit is {self.engine.angle_mode}")
            return
        requested = parts[1].lower()[:4]
        mapping = {"deg": AngleMode.DEG, "rad": AngleMode.RAD, "grad": AngleMode.GRAD}
        if requested not in mapping:
            self.write("  usage: mode deg|rad|grad")
            return
        self.engine.set_angle_mode(mapping[requested])
        self.write(f"  angle unit = {self.engine.angle_mode}")

    def _history(self, parts: List[str]) -> None:
        count = 10
        if len(parts) > 1 and parts[1].isdigit():
            count = int(parts[1])
        entries = list(self.engine.history)[:count]
        if not entries:
            self.write("  (history is empty)")
            return
        for entry in reversed(entries):
            self.write(f"  {entry.formatted_time('%H:%M:%S')}  {entry.expression} = {entry.result}")

    def _memory(self, parts: List[str]) -> None:
        memory = self.engine.memory
        if len(parts) < 2:
            for slot, value in memory.slots().items():
                marker = "*" if slot == memory.active else " "
                self.write(f" {marker} {slot} = {self.engine.format(value)}")
            return
        operation = parts[1].lower()
        slot = parts[2].upper() if len(parts) > 2 else memory.active
        if operation not in ("store", "add", "sub", "clear"):
            self.write("  usage: mem store|add|sub|clear [slot]")
            return
        if operation == "clear":
            memory.clear(slot)
            self.write(f"  {slot} cleared")
            return
        if self.engine.last_result is None:
            self.write("  nothing to store yet")
            return
        value = self.engine.last_result
        if operation == "store":
            memory.store(value, slot)
        elif operation == "add":
            memory.add(value, slot)
        else:
            memory.subtract(value, slot)
        self.write(f"  {slot} = {self.engine.format(memory.recall(slot))}")

    def _functions(self) -> None:
        seen = set()
        rows = []
        for spec in FUNCTIONS.values():
            if spec.name in seen:
                continue
            seen.add(spec.name)
            rows.append(f"{spec.signature():<18} {spec.description}")
        width = _terminal_width()
        for row in sorted(rows):
            self.write("  " + row[: width - 2])

    def _format(self, parts: List[str]) -> None:
        if len(parts) < 2:
            self.write(f"  significant digits = {self.precision}")
            return
        if not parts[1].isdigit():
            self.write("  usage: fmt <1-16>")
            return
        self.precision = max(1, min(16, int(parts[1])))
        self.engine.format_settings = FormatSettings(
            thousands=self.engine.format_settings.thousands,
            group_separator=self.engine.format_settings.group_separator,
            decimal_separator=self.engine.format_settings.decimal_separator,
            precision=self.precision,
        )
        self.write(f"  significant digits = {self.precision}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pycalc",
        description="python-calculator in terminal mode",
        add_help=False,
    )
    parser.add_argument("expression", nargs="*", help="evaluate this and exit")
    parser.add_argument("--mode", choices=("deg", "rad", "grad"), default="rad")
    parser.add_argument("--precision", type=int, default=12)
    parser.add_argument("--home", type=Path, default=None, help="data directory")
    parser.add_argument("-h", "--help", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.help:
        build_parser().print_help()
        return 0

    engine = CalculatorEngine(home=args.home)
    engine.set_angle_mode(args.mode)
    engine.format_settings.precision = max(1, min(16, args.precision))

    if args.expression:
        repl = REPL(engine)
        repl.execute(" ".join(args.expression))
        return 0

    return REPL(engine).run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
