"""Terminal interface tests -- these run with no display at all."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from calc.cli import REPL, build_parser, main
from calc.core.engine import CalculatorEngine


@pytest.fixture
def repl(tmp_home: Path):
    engine = CalculatorEngine(home=tmp_home)
    engine.set_angle_mode("deg")
    buffer = io.StringIO()
    return REPL(engine, out=buffer), buffer


def output(buffer: io.StringIO) -> str:
    return buffer.getvalue()


def test_evaluate_simple_expression(repl):
    loop, buffer = repl
    loop.execute("2+2")
    assert "= 4" in output(buffer)


def test_evaluate_reports_engine_errors(repl):
    loop, buffer = repl
    loop.execute("1/0")
    assert "Division by zero" in output(buffer)


def test_ans_is_available(repl):
    loop, buffer = repl
    loop.execute("6*7")
    loop.execute("ans+1")
    assert "= 43" in output(buffer)


def test_let_defines_a_variable(repl):
    loop, buffer = repl
    loop.execute("let x = 5")
    loop.execute("x*3")
    assert "= 15" in output(buffer)


def test_let_requires_an_equals_sign(repl):
    loop, buffer = repl
    loop.execute("let x")
    assert "usage" in output(buffer)


def test_let_rejects_bad_names(repl):
    loop, buffer = repl
    loop.execute("let 1x = 5")
    assert "alphanumeric" in output(buffer)


def test_vars_lists_variables(repl):
    loop, buffer = repl
    loop.execute("let y = 2")
    loop.execute("vars")
    assert "y = 2" in output(buffer)


def test_mode_switch(repl):
    loop, buffer = repl
    loop.execute("mode rad")
    assert "angle unit = rad" in output(buffer)
    loop.execute("mode banana")
    assert "usage" in output(buffer)


def test_history_command(repl):
    loop, buffer = repl
    loop.execute("1+1")
    loop.execute("2+2")
    buffer.truncate(0)
    buffer.seek(0)
    loop.execute("hist")
    text = output(buffer)
    assert "1+1 = 2" in text and "2+2 = 4" in text


def test_history_empty(repl):
    loop, buffer = repl
    loop.execute("hist")
    assert "empty" in output(buffer)


def test_memory_commands(repl):
    loop, buffer = repl
    loop.execute("6*7")
    loop.execute("mem store M1")
    buffer.truncate(0)
    buffer.seek(0)
    loop.execute("mem")
    assert "M1 = 42" in output(buffer)


def test_memory_without_a_result(repl):
    loop, buffer = repl
    loop.execute("mem store")
    assert "nothing to store" in output(buffer)


def test_memory_bad_operation(repl):
    loop, buffer = repl
    loop.execute("mem explode")
    assert "usage" in output(buffer)


def test_fn_lists_functions(repl):
    loop, buffer = repl
    loop.execute("fn")
    text = output(buffer)
    assert "sin(x)" in text and "sqrt(x)" in text


def test_const_lists_constants(repl):
    loop, buffer = repl
    loop.execute("const")
    assert "pi = " in output(buffer)


def test_fmt_changes_precision(repl):
    loop, buffer = repl
    loop.execute("fmt 4")
    loop.execute("1/3")
    assert "= 0.3333" in output(buffer)


def test_fmt_rejects_garbage(repl):
    loop, buffer = repl
    loop.execute("fmt abc")
    assert "usage" in output(buffer)


def test_help(repl):
    loop, buffer = repl
    loop.execute("help")
    assert "Commands" in output(buffer)


def test_question_mark_is_help(repl):
    loop, buffer = repl
    loop.execute("?")
    assert "Commands" in output(buffer)


# ---------------------------------------------------------------------------
# argument parsing / main()
# ---------------------------------------------------------------------------
def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.expression == []
    assert args.mode == "rad"
    assert args.precision == 12


def test_parser_accepts_an_expression():
    args = build_parser().parse_args(["2", "+", "2"])
    assert args.expression == ["2", "+", "2"]


def test_main_evaluates_and_exits(tmp_home: Path, capsys):
    code = main(["--home", str(tmp_home), "6*7"])
    assert code == 0
    assert "= 42" in capsys.readouterr().out


def test_main_honours_the_mode_flag(tmp_home: Path, capsys):
    main(["--home", str(tmp_home), "--mode", "deg", "sin(30)"])
    assert "= 0.5" in capsys.readouterr().out


def test_main_help_exits_zero(capsys):
    assert main(["--help"]) == 0
    assert "pycalc" in capsys.readouterr().out


def test_run_version(capsys):
    from calc import run

    assert run(["--version"]) == 0
    assert "python-calculator" in capsys.readouterr().out


def test_run_help(capsys):
    from calc import run

    assert run(["--help"]) == 0
    assert "Usage:" in capsys.readouterr().out


def test_run_cli_subcommand(tmp_home: Path, capsys, monkeypatch):
    from calc import run

    monkeypatch.setenv("PYTHON_CALCULATOR_HOME", str(tmp_home))
    assert run(["cli", "9*9"]) == 0
    assert "= 81" in capsys.readouterr().out
