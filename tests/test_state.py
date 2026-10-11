"""History, memory and settings persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from calc.core.engine import CalculatorEngine
from calc.core.history import History, HistoryEntry
from calc.core.memory import SLOTS, Memory
from calc.gui.settings import AppSettings, Appearance, Behaviour


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------
def test_history_records_calculations(engine: CalculatorEngine):
    engine.evaluate("1+1")
    engine.evaluate("2+2")
    entries = list(engine.history)
    assert [entry.expression for entry in entries] == ["2+2", "1+1"]  # newest first


def test_history_persists_across_instances(tmp_home: Path):
    first = CalculatorEngine(home=tmp_home)
    first.evaluate("6*7")

    second = CalculatorEngine(home=tmp_home)
    assert len(second.history) == 1
    assert list(second.history)[0].result == "42"


def test_history_is_bounded(tmp_home: Path):
    history = History(tmp_home / "history.json", limit=5)
    for index in range(12):
        history.add(f"{index}+1", str(index + 1))
    assert len(history) == 5
    assert list(history)[0].expression == "11+1"


def test_history_clear(engine: CalculatorEngine):
    engine.evaluate("1+1")
    engine.clear_history()
    assert len(engine.history) == 0


def test_history_search(engine: CalculatorEngine):
    engine.evaluate("sin(30)")
    engine.evaluate("2+2")
    assert len(engine.history.search("sin")) == 1
    assert len(engine.history.search("2+2")) == 1
    assert len(engine.history.search("nomatch")) == 0


def test_history_remove(tmp_home: Path):
    history = History(tmp_home / "history.json")
    entry = history.add("1+1", "2")
    assert history.remove(entry) is True
    assert len(history) == 0
    assert history.remove(entry) is False


def test_corrupt_history_file_does_not_crash(tmp_home: Path):
    path = tmp_home / "history.json"
    path.write_text("{not json at all", encoding="utf-8")
    history = History(path)
    assert len(history) == 0


def test_history_entry_round_trip():
    entry = HistoryEntry(expression="1+1", result="2", angle_mode="deg")
    assert HistoryEntry.from_dict(entry.to_dict()).expression == "1+1"


def test_history_stores_the_angle_mode(engine: CalculatorEngine):
    engine.set_angle_mode("grad")
    engine.evaluate("1+1")
    assert list(engine.history)[0].angle_mode == "grad"


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------
def test_memory_store_and_recall(tmp_home: Path):
    memory = Memory(tmp_home / "memory.json")
    memory.store(42, "M3")
    assert memory.recall("M3") == 42
    assert memory.recall("M0") == 0


def test_memory_add_and_subtract(tmp_home: Path):
    memory = Memory(tmp_home / "memory.json")
    memory.store(10)
    assert memory.add(5) == 15
    assert memory.subtract(3) == 12


def test_memory_clear_and_clear_all(tmp_home: Path):
    memory = Memory(tmp_home / "memory.json")
    memory.store(1, "M1")
    memory.store(2, "M2")
    memory.clear("M1")
    assert memory.recall("M1") == 0
    memory.clear_all()
    assert memory.is_empty()


def test_memory_active_slot(tmp_home: Path):
    memory = Memory(tmp_home / "memory.json")
    memory.select("M5")
    assert memory.active == "M5"
    memory.store(9)
    assert memory.recall("M5") == 9


def test_memory_select_unknown_slot_raises(tmp_home: Path):
    memory = Memory(tmp_home / "memory.json")
    with pytest.raises(KeyError):
        memory.select("M99")


def test_memory_persists(tmp_home: Path):
    Memory(tmp_home / "memory.json").store(7, "M2")
    assert Memory(tmp_home / "memory.json").recall("M2") == 7


def test_memory_has_ten_slots(tmp_home: Path):
    assert len(SLOTS) == 10
    assert len(Memory(tmp_home / "memory.json").slots()) == 10


def test_engine_memory_operations(engine: CalculatorEngine):
    engine.evaluate("6*7")
    engine.memory.store(engine.last_result, "M0")
    assert engine.memory.recall("M0") == 42


# ---------------------------------------------------------------------------
# variables & ans
# ---------------------------------------------------------------------------
def test_ans_is_not_listed_as_a_user_variable(engine: CalculatorEngine):
    engine.evaluate("3+4")
    assert "ans" in engine.variables()
    engine.define("x", 1)
    assert engine.variables()["x"] == 1


def test_data_directory_is_isolated(tmp_home: Path):
    engine = CalculatorEngine(home=tmp_home)
    engine.evaluate("1+1")
    assert (tmp_home / "history.json").exists()


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------
def test_settings_round_trip(tmp_home: Path):
    settings = AppSettings(home=tmp_home)
    settings.appearance.theme = "Nord"
    settings.appearance.corner_radius = 21
    settings.behaviour.angle_mode = "deg"
    settings.behaviour.decimal_separator = ","
    settings.save()

    loaded = AppSettings.load(tmp_home)
    assert loaded.appearance.theme == "Nord"
    assert loaded.appearance.corner_radius == 21
    assert loaded.behaviour.angle_mode == "deg"
    assert loaded.behaviour.decimal_separator == ","


def test_comma_decimal_forces_a_different_group_separator(tmp_home: Path):
    settings = AppSettings(home=tmp_home)
    settings.behaviour.decimal_separator = ","
    settings.behaviour.group_separator = ","
    settings.save()
    loaded = AppSettings.load(tmp_home)
    assert loaded.behaviour.group_separator != ","


def test_unknown_keys_are_ignored(tmp_home: Path):
    path = tmp_home / "settings.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "appearance": {"theme": "Light", "from_the_future": True},
                "behaviour": {"angle_mode": "deg"},
            }
        ),
        encoding="utf-8",
    )
    loaded = AppSettings.load(tmp_home)
    assert loaded.appearance.theme == "Light"
    assert loaded.behaviour.angle_mode == "deg"


def test_corrupt_settings_fall_back_to_defaults(tmp_home: Path):
    (tmp_home / "settings.json").write_text("]]] not json", encoding="utf-8")
    loaded = AppSettings.load(tmp_home)
    assert loaded.appearance == Appearance()
    assert loaded.behaviour == Behaviour()


def test_out_of_range_values_are_clamped(tmp_home: Path):
    (tmp_home / "settings.json").write_text(
        json.dumps(
            {
                "appearance": {"corner_radius": 9999, "ui_scale": -5, "keypad_mode": "nonsense"},
                "behaviour": {"precision": 0, "angle_mode": "banana"},
            }
        ),
        encoding="utf-8",
    )
    loaded = AppSettings.load(tmp_home)
    assert loaded.appearance.corner_radius == 32
    assert loaded.appearance.ui_scale == 0.6
    assert loaded.appearance.keypad_mode == "standard"
    assert loaded.behaviour.precision == 1
    assert loaded.behaviour.angle_mode == "rad"


def test_settings_reset(tmp_home: Path):
    settings = AppSettings(home=tmp_home)
    settings.appearance.theme = "Dracula"
    settings.reset()
    assert settings.appearance.theme == Appearance().theme


def test_to_format_settings(tmp_home: Path):
    settings = AppSettings(home=tmp_home)
    settings.behaviour.thousands = False
    settings.behaviour.precision = 6
    format_settings = settings.behaviour.to_format_settings()
    assert format_settings.thousands is False
    assert format_settings.precision == 6


def test_settings_file_is_valid_json(tmp_home: Path):
    settings = AppSettings(home=tmp_home)
    path = settings.save()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert "appearance" in payload and "behaviour" in payload
