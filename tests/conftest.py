"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the package importable when the tests are run straight from the repo.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calc.core.engine import CalculatorEngine  # noqa: E402
from calc.core.formatter import FormatSettings  # noqa: E402


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """An isolated data directory so tests never touch the user's real data."""
    home = tmp_path / "calc-home"
    home.mkdir()
    return home


@pytest.fixture
def engine(tmp_home: Path) -> CalculatorEngine:
    eng = CalculatorEngine(home=tmp_home)
    eng.set_angle_mode("deg")
    return eng


@pytest.fixture
def plain_settings() -> FormatSettings:
    return FormatSettings(thousands=False, decimal_separator=".")


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    """Keep every test away from the real home directory."""
    monkeypatch.setenv("PYTHON_CALCULATOR_HOME", str(tmp_path / "env-home"))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    if os.name == "nt":  # pragma: no cover
        monkeypatch.delenv("APPDATA", raising=False)
