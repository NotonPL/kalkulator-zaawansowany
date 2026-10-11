"""GUI tests.

These run headless: pytest-qt creates an offscreen ``QApplication``, so the
whole Qt stack -- layouts, stylesheets, signals, dialogs -- is exercised in CI
without a display server.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from calc.core.engine import CalculatorEngine
from calc.gui.display import DisplayWidget
from calc.gui.i18n import available_languages, tr, translator
from calc.gui.keypad import LAYOUTS, STANDARD_LAYOUT, Key
from calc.gui.main_window import MainWindow
from calc.gui.settings import AppSettings
from calc.gui.settings_dialog import SettingsDialog
from calc.gui.side_panel import SidePanel
from calc.gui.themes import BUILTIN_THEMES, build_stylesheet, get_theme, theme_names
from calc.gui.widgets import RippleButton

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture
def window(qtbot, tmp_home: Path) -> MainWindow:
    settings = AppSettings(home=tmp_home)
    win = MainWindow(settings=settings, engine=CalculatorEngine(home=tmp_home))
    qtbot.addWidget(win)
    win.show()
    return win


def make_dialog(window: MainWindow, qtbot) -> SettingsDialog:
    """Build the dialog the same way MainWindow.open_settings() does.

    ``applied`` is only wired up by the owner, so a test that constructs the
    dialog by hand has to make that connection too.
    """
    dialog = SettingsDialog(window.settings, window)
    dialog.applied.connect(window._on_settings_applied)
    qtbot.addWidget(dialog)
    return dialog


def tap(window: MainWindow, label: str) -> None:
    button = window.keypad.button_for(label)
    assert button is not None, f"keypad has no '{label}' key"
    button.click()


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------
def test_window_builds(window: MainWindow):
    assert window.display.result_label.text() == "0"
    assert window.keypad.labels()


def test_window_title_is_translatable(window: MainWindow):
    assert window.windowTitle() == tr("app.name")


def test_every_builtin_theme_is_reachable(window: MainWindow):
    for name in theme_names():
        window.set_theme(name)
        assert window.settings.appearance.theme == name
        assert window.styleSheet()


def test_stylesheet_mentions_the_active_theme(window: MainWindow):
    window.set_theme("Nord")
    assert "Theme: Nord" in window.styleSheet()


def _occupancy(layout) -> list[list[str]]:
    """Expand a layout table into the grid it actually produces.

    ``colspan``/``rowspan`` mean a key occupies several cells, so summing the
    spans of one row is not enough -- the "=" key of the scientific keypad
    spans two rows and must still leave every cell filled exactly once.
    """
    grid: list[list[str]] = []
    for row_index, row_keys in enumerate(layout):
        while len(grid) <= row_index:
            grid.append([])
        column = 0
        for key in row_keys:
            while column < len(grid[row_index]) and grid[row_index][column]:
                column += 1
            for r in range(row_index, row_index + key.rowspan):
                while len(grid) <= r:
                    grid.append([])
                for c in range(column, column + key.colspan):
                    while len(grid[r]) <= c:
                        grid[r].append("")
                    assert grid[r][c] == "", f"cell ({r},{c}) is filled twice"
                    grid[r][c] = key.label
            column += key.colspan
    return grid


@pytest.mark.parametrize("mode", ["standard", "scientific"])
def test_layout_fills_a_rectangle_without_gaps_or_overlaps(mode: str):
    grid = _occupancy(LAYOUTS[mode])
    widths = {len(row) for row in grid}
    assert len(widths) == 1, f"rows have uneven widths: {[len(r) for r in grid]}"
    assert all(all(cell for cell in row) for row in grid), "layout has empty cells"


def test_standard_layout_has_five_columns():
    assert len(_occupancy(STANDARD_LAYOUT)[0]) == 5


def test_scientific_layout_has_seven_columns():
    assert len(_occupancy(LAYOUTS["scientific"])[0]) == 7


def test_equals_key_is_present_in_both_layouts():
    for mode, layout in LAYOUTS.items():
        labels = [key.label for row in layout for key in row]
        assert "=" in labels, mode


def test_no_duplicate_labels_within_a_layout():
    for mode, layout in LAYOUTS.items():
        labels = [key.label for row in layout for key in row]
        duplicates = {label for label in labels if labels.count(label) > 1}
        assert not duplicates, f"{mode} repeats: {duplicates}"


def test_every_key_is_either_an_insert_or_a_command():
    for layout in LAYOUTS.values():
        for row in layout:
            for key in row:
                assert key.insert is not None or key.command is not None


def test_keypad_can_switch_modes(window: MainWindow):
    window.set_mode("scientific")
    assert window.keypad.button_for("sin") is not None
    window.set_mode("standard")
    assert window.keypad.button_for("sin") is None


# ---------------------------------------------------------------------------
# calculation through the UI
# ---------------------------------------------------------------------------
def test_typing_on_the_keypad_computes(window: MainWindow):
    for label in ("7", "\u00d7", "(", "3", "+", "4", ")"):
        tap(window, label)
    assert window._buffer == "7*(3+4)"
    tap(window, "=")
    assert window.display.result_label.text() == "49"


def test_result_is_recorded_in_history(window: MainWindow):
    window.insert_text("6*7")
    tap(window, "=")
    assert list(window.engine.history)[0].expression == "6*7"
    assert window.side_panel.history_list.count() == 1


def test_live_preview_shows_while_typing(window: MainWindow):
    window.insert_text("2+2")
    assert "= 4" in window.display.hint_label.text()


def test_division_by_zero_shows_an_error_state(window: MainWindow):
    window.insert_text("1/0")
    tap(window, "=")
    assert window.display.result_label.property("state") == "error"
    assert window.display.result_label.text() == tr("error.divzero")


def test_unknown_name_shows_an_error(window: MainWindow):
    window.insert_text("foo")
    tap(window, "=")
    assert window.display.result_label.text() == tr("error.unknown")


def test_unclosed_parenthesis_is_repaired(window: MainWindow):
    window.insert_text("2*(3+4")
    tap(window, "=")
    assert window.display.result_label.text() == "14"


def test_dangling_operator_is_ignored(window: MainWindow):
    window.insert_text("5+")
    tap(window, "=")
    assert window.display.result_label.text() == "5"


def test_backspace_removes_one_character(window: MainWindow):
    window.insert_text("123")
    window.backspace()
    assert window._buffer == "12"


def test_clear_entry_empties_the_buffer(window: MainWindow):
    window.insert_text("123")
    window.clear_entry()
    assert window._buffer == ""
    assert window.display.result_label.text() == tr("display.placeholder")


def test_negate_toggles_the_sign_of_the_current_number(window: MainWindow):
    window.insert_text("12")
    window.negate()
    assert window._buffer == "-12"
    window.negate()
    assert window._buffer == "12"


def test_negate_on_an_empty_buffer_starts_a_minus(window: MainWindow):
    window.negate()
    assert window._buffer == "-"


def test_negate_after_an_operator_opens_a_group(window: MainWindow):
    window.insert_text("5*")
    window.negate()
    assert window._buffer == "5*-("


def test_keyboard_input_reaches_the_buffer(window: MainWindow, qtbot):
    qtbot.keyClick(window, Qt.Key_7)
    qtbot.keyClick(window, Qt.Key_Plus)
    qtbot.keyClick(window, Qt.Key_5)
    assert window._buffer == "7+5"


def test_enter_evaluates(window: MainWindow, qtbot):
    qtbot.keyClicks(window, "2*3")
    qtbot.keyPress(window, Qt.Key_Return)
    assert window.display.result_label.text() == "6"


def test_escape_clears(window: MainWindow, qtbot):
    qtbot.keyClicks(window, "2*3")
    qtbot.keyPress(window, Qt.Key_Escape)
    assert window._buffer == ""


# ---------------------------------------------------------------------------
# angle mode, memory, side panel
# ---------------------------------------------------------------------------
def test_angle_mode_badge_follows_the_setting(window: MainWindow):
    window.set_angle_mode("deg")
    assert window.display.angle_badge.text() == "DEG"
    assert window.angle_button.text() == "DEG"


def test_cycle_angle_wraps_around(window: MainWindow):
    seen = [window.engine.angle_mode]
    for _ in range(3):
        window.cycle_angle()
        seen.append(window.engine.angle_mode)
    assert seen == ["rad", "deg", "grad", "rad"]


def test_sine_uses_the_active_angle_mode(window: MainWindow):
    window.set_mode("scientific")
    window.set_angle_mode("deg")
    for label in ("sin", "3", "0"):
        tap(window, label)
    tap(window, "=")
    assert window.display.result_label.text() == "0.5"


def test_memory_store_and_recall(window: MainWindow):
    window.insert_text("6*7")
    tap(window, "=")
    window.memory_operation("store", "M0")
    assert window.engine.memory.recall("M0") == 42
    window.clear_all()
    window.memory_operation("recall", "M0")
    assert window._buffer.startswith("42")


def test_memory_badge_appears_when_non_zero(window: MainWindow):
    assert window.display.memory_badge.isVisibleTo(window) is False
    window.insert_text("9")
    window.memory_operation("store", "M0")
    assert window.display.memory_badge.text() == "M0"


def test_cycle_memory_slot(window: MainWindow):
    first = window.engine.memory.active
    window.cycle_memory_slot()
    assert window.engine.memory.active != first


def test_side_panel_lists_functions():
    panel = SidePanel()
    texts = [panel.function_list.item(i).text() for i in range(panel.function_list.count())]
    assert any(text.startswith("sin(") for text in texts)
    assert any("CONSTANTS" in text for text in texts)


def test_side_panel_history_signal_inserts_text(window: MainWindow, qtbot):
    window.insert_text("8*8")
    tap(window, "=")
    window.clear_all()
    item = window.side_panel.history_list.item(0)
    window.side_panel.history_requested.emit(item.data(Qt.UserRole).expression)
    assert window._buffer == "8*8"


def test_clearing_history_empties_the_panel(window: MainWindow):
    window.insert_text("1+1")
    tap(window, "=")
    assert window.side_panel.history_list.count() == 1
    window.clear_history()
    assert window.side_panel.history_list.count() == 0


def test_toggling_the_side_panel_persists(window: MainWindow):
    window.toggle_side_panel(False)
    assert window.side_panel.isVisible() is False
    assert window.settings.appearance.show_side_panel is False


# ---------------------------------------------------------------------------
# theming & settings dialog
# ---------------------------------------------------------------------------
def test_build_stylesheet_for_every_theme():
    settings = AppSettings()
    for theme in BUILTIN_THEMES:
        sheet = build_stylesheet(theme, settings.appearance)
        assert "QPushButton" in sheet
        assert f"Theme: {theme.name}" in sheet


def test_accent_colour_overrides_the_theme(window: MainWindow):
    window.settings.appearance.accent_color = "#ff0000"
    window.apply_settings()
    assert "#ff0000" in window.styleSheet()


def test_corner_radius_reaches_the_stylesheet(window: MainWindow):
    window.settings.appearance.corner_radius = 27
    window.apply_settings()
    assert "border-radius: 27px" in window.styleSheet()


def test_key_height_is_applied_to_the_buttons(window: MainWindow):
    window.settings.appearance.key_height = 90
    window.apply_settings()
    assert window.keypad.buttons()[0].minimumHeight() == 90


def test_side_panel_visibility_follows_the_setting(window: MainWindow):
    window.settings.appearance.show_side_panel = False
    window.apply_settings()
    assert window.side_panel.isVisible() is False


def test_settings_dialog_opens_and_applies(window: MainWindow, qtbot):
    dialog = make_dialog(window, qtbot)
    dialog.radius_slider.setValue(19)
    dialog.theme_combo.setCurrentText("Dracula")
    dialog._on_apply()
    assert window.settings.appearance.corner_radius == 19
    assert window.settings.appearance.theme == "Dracula"


def test_settings_dialog_reset_restores_defaults(window: MainWindow, qtbot):
    from calc.gui.settings import Appearance

    dialog = make_dialog(window, qtbot)
    dialog.radius_slider.setValue(31)
    dialog._on_reset()
    assert dialog.draft.appearance == Appearance()
    assert dialog.radius_slider.value() == Appearance().corner_radius


def test_settings_dialog_preview_follows_the_controls(window: MainWindow, qtbot):
    dialog = make_dialog(window, qtbot)
    dialog.theme_combo.setCurrentText("Light")
    assert "Theme: Light" in dialog.preview_frame.styleSheet()


def test_settings_dialog_switches_keypad_mode(window: MainWindow, qtbot):
    dialog = make_dialog(window, qtbot)
    dialog.mode_combo.setCurrentIndex(1)
    dialog._on_apply()
    assert window.settings.appearance.keypad_mode == "scientific"
    assert window.keypad.button_for("sin") is not None


def test_settings_dialog_apply_persists_to_disk(window: MainWindow, qtbot):
    dialog = make_dialog(window, qtbot)
    dialog.theme_combo.setCurrentText("Nord")
    dialog._on_apply()
    assert AppSettings.load(window.settings.home).appearance.theme == "Nord"


def test_open_settings_creates_a_dialog(window: MainWindow, qtbot, monkeypatch):
    created = {}

    class FakeDialog:
        def __init__(self, settings, parent=None):
            created["settings"] = settings

        applied = type("S", (), {"connect": staticmethod(lambda *_a, **_k: None)})()

        def exec(self):
            created["executed"] = True

    monkeypatch.setattr("calc.gui.main_window.SettingsDialog", FakeDialog)
    window.open_settings()
    assert created.get("executed") is True


# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
def test_two_languages_ship():
    assert set(available_languages()) >= {"en", "pl"}


def test_translator_falls_back_to_english_for_a_missing_key():
    translator.set_language("pl")
    assert translator.tr("definitely.not.a.key") == "definitely.not.a.key"


def test_polish_translation_is_complete():
    from calc.gui.i18n import load_translations

    english = load_translations("en")
    polish = load_translations("pl")
    missing = set(english) - set(polish)
    assert not missing, f"pl.json is missing: {sorted(missing)}"


def test_switching_the_language_retranslates(window: MainWindow):
    window.set_language("pl")
    assert window.windowTitle() == "Kalkulator Python"
    window.set_language("en")
    assert window.windowTitle() == "Python Calculator"


# ---------------------------------------------------------------------------
# widgets
# ---------------------------------------------------------------------------
def test_ripple_button_can_be_constructed(qtbot):
    button = RippleButton("x")
    qtbot.addWidget(button)
    button.set_clip_radius(8)
    button.set_ripple_color("#ffffff")
    assert button.text() == "x"


def test_display_shrinks_a_long_result(qtbot):
    display = DisplayWidget()
    qtbot.addWidget(display)
    display.resize(200, 120)
    display.set_result("1" * 60)
    assert display.result_label.font().pointSize() < display._base_result_size


def test_display_elides_a_long_expression(qtbot):
    display = DisplayWidget()
    qtbot.addWidget(display)
    display.resize(220, 120)
    display.set_expression("9" * 200)
    assert display.expression_label.text().startswith("\u2026")


def test_clipboard_copy(window: MainWindow):
    window.insert_text("6*7")
    tap(window, "=")
    window.copy_result()
    assert QApplication.clipboard().text() == "42"


def test_about_and_shortcuts_dialogs_do_not_crash(window: MainWindow, monkeypatch):
    shown = []
    monkeypatch.setattr("calc.gui.main_window.QMessageBox.about",
                        staticmethod(lambda *a, **k: shown.append("about")))
    monkeypatch.setattr("calc.gui.main_window.QMessageBox.information",
                        staticmethod(lambda *a, **k: shown.append("info")))
    window.show_about()
    window.show_shortcuts()
    assert shown == ["about", "info"]


def test_run_command_rejects_an_unknown_command(window: MainWindow):
    with pytest.raises(ValueError):
        window.run_command("self_destruct")


def test_key_dataclass_defaults():
    key = Key(label="x")
    assert key.insert is None and key.command is None and key.role == "digit"
