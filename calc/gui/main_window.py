"""The main window.

Responsibilities are kept deliberately thin: the window owns the input buffer
and routes intents (key presses, menu actions, panel signals) to the
:class:`~calc.core.engine.CalculatorEngine`.  All mathematics lives in the core
package, all styling in :mod:`calc.gui.themes`.
"""

from __future__ import annotations

import sys
import webbrowser
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core.engine import CalculatorEngine
from ..core.normalize import auto_close
from ..core.errors import (
    CalcError,
    DivisionByZeroError,
    DomainError,
    EvaluationError,
    LexError,
    OverflowResultError,
    ParseError,
    UnknownFunctionError,
    UnknownSymbolError,
)
from .display import DisplayWidget
from .i18n import available_languages, tr, translator
from .keypad import Keypad, Key
from .settings import AppSettings
from .settings_dialog import SettingsDialog
from .side_panel import SidePanel
from .themes import build_palette, build_stylesheet, get_theme, theme_names
from .widgets import set_ripple_enabled

__all__ = ["MainWindow"]

REPO_URL = "https://github.com/NotonPL/kalkulator-zaawansowany"
_DIGITS = "0123456789"


class MainWindow(QMainWindow):
    """Top level window: display + keypad + side panel + menus."""

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        engine: Optional[CalculatorEngine] = None,
    ) -> None:
        super().__init__()
        self.settings = settings or AppSettings.load()
        self.engine = engine or CalculatorEngine(home=self.settings.home)
        self.engine.set_angle_mode(self.settings.behaviour.angle_mode)
        self.engine.history.limit = self.settings.behaviour.history_limit
        self.engine.format_settings = self.settings.behaviour.to_format_settings()

        translator.set_language(self.settings.behaviour.language)
        set_ripple_enabled(self.settings.appearance.ripples and self.settings.appearance.animations)

        self._buffer = ""
        self._just_evaluated = False
        self._esc_armed = False

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._wire_signals()
        self.apply_settings()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(10)

        self.display = DisplayWidget()
        root.addWidget(self.display)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)

        self.keypad = Keypad(self.settings.appearance.keypad_mode)
        self.splitter.addWidget(self.keypad)

        self.side_panel = SidePanel()
        self.splitter.addWidget(self.side_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        root.addWidget(self.splitter, 1)

        self.resize(900, 660)
        self.setMinimumSize(420, 420)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu(tr("menu.file"))
        self.settings_action = QAction(tr("menu.settings"), self)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        self.quit_action = QAction(tr("menu.quit"), self)
        self.quit_action.setShortcut(QKeySequence.Quit)
        file_menu.addAction(self.quit_action)

        edit_menu = bar.addMenu(tr("menu.edit"))
        self.copy_action = QAction(tr("menu.copy"), self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_expression_action = QAction(tr("menu.copy.expression"), self)
        self.copy_expression_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.paste_action = QAction(tr("menu.paste"), self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.backspace_action = QAction(tr("menu.backspace"), self)
        self.backspace_action.setShortcut(QKeySequence.Backspace)
        self.clear_action = QAction(tr("menu.clear"), self)
        self.clear_action.setShortcut(QKeySequence("Ctrl+Backspace"))
        self.clear_all_action = QAction(tr("menu.clear.all"), self)
        self.clear_all_action.setShortcut(QKeySequence("Esc"))
        for action in (self.copy_action, self.copy_expression_action, self.paste_action):
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        for action in (self.backspace_action, self.clear_action, self.clear_all_action):
            edit_menu.addAction(action)

        view_menu = bar.addMenu(tr("menu.view"))
        self.theme_menu = view_menu.addMenu(tr("menu.theme"))
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        for name in theme_names():
            action = QAction(name, self, checkable=True)
            action.setData(name)
            action.setChecked(name == self.settings.appearance.theme)
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)

        self.mode_menu = view_menu.addMenu(tr("menu.scientific"))
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        for label, value in (("Standard", "standard"), ("Scientific", "scientific")):
            action = QAction(label, self, checkable=True)
            action.setData(value)
            action.setChecked(value == self.settings.appearance.keypad_mode)
            self.mode_group.addAction(action)
            self.mode_menu.addAction(action)

        self.angle_menu = view_menu.addMenu(tr("menu.angle"))
        self.angle_group = QActionGroup(self)
        self.angle_group.setExclusive(True)
        for label, value in (("Radians", "rad"), ("Degrees", "deg"), ("Gradians", "grad")):
            action = QAction(label, self, checkable=True)
            action.setData(value)
            action.setChecked(value == self.settings.behaviour.angle_mode)
            self.angle_group.addAction(action)
            self.angle_menu.addAction(action)

        self.language_menu = view_menu.addMenu(tr("menu.language"))
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        labels = {"en": "English", "pl": "Polski"}
        system_action = QAction(tr("settings.language.system"), self, checkable=True)
        system_action.setData("system")
        system_action.setChecked(self.settings.behaviour.language == "system")
        self.language_group.addAction(system_action)
        self.language_menu.addAction(system_action)
        for code in available_languages():
            action = QAction(labels.get(code, code.upper()), self, checkable=True)
            action.setData(code)
            action.setChecked(code == self.settings.behaviour.language)
            self.language_group.addAction(action)
            self.language_menu.addAction(action)

        view_menu.addSeparator()
        self.history_action = QAction(tr("menu.history"), self, checkable=True)
        self.history_action.setShortcut(QKeySequence("Ctrl+H"))
        self.history_action.setChecked(self.settings.appearance.show_side_panel)
        view_menu.addAction(self.history_action)

        help_menu = bar.addMenu(tr("menu.help"))
        self.shortcuts_action = QAction(tr("menu.shortcuts"), self)
        self.shortcuts_action.setShortcut(QKeySequence("F1"))
        self.functions_action = QAction(tr("menu.functions"), self)
        self.about_action = QAction(tr("menu.about"), self)
        for action in (self.shortcuts_action, self.functions_action):
            help_menu.addAction(action)
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("mode.standard"), "standard")
        self.mode_combo.addItem(tr("mode.scientific"), "scientific")
        self.mode_combo.setCurrentIndex(0 if self.settings.appearance.keypad_mode == "standard" else 1)
        toolbar.addWidget(self.mode_combo)

        self.angle_button = QToolButton()
        self.angle_button.setText(self.settings.behaviour.angle_mode.upper())
        self.angle_button.setToolTip(tr("menu.angle") + "  (Ctrl+M)")
        toolbar.addWidget(self.angle_button)

        self.memory_button = QToolButton()
        self.memory_button.setText("M0")
        self.memory_button.setToolTip(tr("status.memory", slot="M0"))
        toolbar.addWidget(self.memory_button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(self.settings.appearance.theme)
        toolbar.addWidget(QLabel("  " + tr("menu.theme") + ": "))
        toolbar.addWidget(self.theme_combo)

        self.settings_button = QToolButton()
        self.settings_button.setText("\u2699")
        self.settings_button.setToolTip(tr("menu.settings") + "  (Ctrl+,)")
        toolbar.addWidget(self.settings_button)

    def _build_statusbar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self.mode_status = QLabel()
        self.angle_status = QLabel()
        self.memory_status = QLabel()
        status.addWidget(self.mode_status)
        status.addWidget(self.angle_status)
        status.addWidget(self.memory_status)
        self.message_status = QLabel(tr("status.ready"))
        status.addPermanentWidget(self.message_status)

    def _wire_signals(self) -> None:
        self.keypad.key_activated.connect(self.on_key)
        self.side_panel.history_requested.connect(self.insert_text)
        self.side_panel.history_clear_requested.connect(self.clear_history)
        self.side_panel.memory_requested.connect(self.on_memory)
        self.side_panel.function_requested.connect(self.insert_text)

        self.settings_action.triggered.connect(self.open_settings)
        self.quit_action.triggered.connect(self.close)
        self.copy_action.triggered.connect(self.copy_result)
        self.copy_expression_action.triggered.connect(self.copy_expression)
        self.paste_action.triggered.connect(self.paste)
        self.backspace_action.triggered.connect(self.backspace)
        self.clear_action.triggered.connect(self.clear_entry)
        self.clear_all_action.triggered.connect(self.clear_all)
        self.history_action.toggled.connect(self.toggle_side_panel)
        self.about_action.triggered.connect(self.show_about)
        self.shortcuts_action.triggered.connect(self.show_shortcuts)
        self.functions_action.triggered.connect(self.show_functions)
        self.settings_button.clicked.connect(self.open_settings)
        self.angle_button.clicked.connect(self.cycle_angle)
        self.memory_button.clicked.connect(self.cycle_memory_slot)
        self.theme_combo.currentTextChanged.connect(self.set_theme)
        self.mode_combo.currentIndexChanged.connect(self.set_mode_from_combo)
        self.theme_group.triggered.connect(lambda action: self.set_theme(action.data()))
        self.mode_group.triggered.connect(lambda action: self.set_mode(action.data()))
        self.angle_group.triggered.connect(lambda action: self.set_angle_mode(action.data()))
        self.language_group.triggered.connect(lambda action: self.set_language(action.data()))

    # ------------------------------------------------------------------
    # input buffer
    # ------------------------------------------------------------------
    def _show_buffer(self) -> None:
        decimal = self.settings.behaviour.decimal_separator
        shown = self._buffer.replace(".", decimal) if decimal == "," else self._buffer
        self.display.set_expression(shown)
        if self._buffer.strip():
            self._live_preview()
        else:
            self.display.set_result(tr("display.placeholder"))
            self.display.set_hint("")

    def _live_preview(self) -> None:
        """Evaluate the half-typed expression and show it as a dim hint."""
        value, error = self.engine.try_evaluate(auto_close(self._buffer))
        if error is None and value is not None:
            self.display.set_hint("= " + self.engine.format(value))
        else:
            self.display.set_hint("")

    def insert_text(self, text: str) -> None:
        if self._just_evaluated and text and text[0] in _DIGITS + ".(":
            self._buffer = ""
        elif self._just_evaluated:
            # Continuing with an operator keeps the previous answer.
            self._just_evaluated = False
        self._just_evaluated = False
        self._buffer += text
        self._show_buffer()

    def backspace(self) -> None:
        self._buffer = self._buffer[:-1]
        self._just_evaluated = False
        self._show_buffer()

    def clear_entry(self) -> None:
        self._buffer = ""
        self._just_evaluated = False
        self.display.set_result(tr("display.placeholder"))
        self.display.set_hint("")
        self.display.set_expression("")

    def clear_all(self) -> None:
        self.clear_entry()
        self.engine.last_result = None
        self.engine.last_expression = ""

    def paste(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip() if clipboard else ""
        if text:
            self.insert_text(text)

    def copy_result(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None and self.display.result_label.text():
            clipboard.setText(self.display.result_label.text())
            self.flash_message(tr("status.copied"))

    def copy_expression(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._buffer)
            self.flash_message(tr("status.copied"))

    def flash_message(self, text: str, ms: int = 3000) -> None:
        self.statusBar().showMessage(text, ms)

    # ------------------------------------------------------------------
    # keypad handling
    # ------------------------------------------------------------------
    def on_key(self, key: Key) -> None:
        if key.insert is not None:
            self.insert_text(key.insert)
        elif key.command:
            self.run_command(key.command)

    def run_command(self, command: str) -> None:
        handler = {
            "equals": self.evaluate,
            "backspace": self.backspace,
            "clear": self.clear_entry,
            "clear_all": self.clear_all,
            "negate": self.negate,
            "angle": self.cycle_angle,
            "memory_recall": lambda: self.memory_operation("recall"),
            "memory_store": lambda: self.memory_operation("store"),
            "memory_add": lambda: self.memory_operation("add"),
            "memory_subtract": lambda: self.memory_operation("subtract"),
            "memory_clear": lambda: self.memory_operation("clear"),
        }.get(command)
        if handler is None:
            raise ValueError(f"Unknown command '{command}'")
        handler()

    def negate(self) -> None:
        """Toggle the sign of the number currently being typed."""
        if not self._buffer:
            self._buffer = "-"
            self._show_buffer()
            return
        index = len(self._buffer)
        while index > 0 and (self._buffer[index - 1] in _DIGITS + "."):
            index -= 1
        if index == len(self._buffer):
            # No trailing number: start a negated group instead.
            self._buffer += "-("
            self._show_buffer()
            return
        if index > 0 and self._buffer[index - 1] == "-":
            self._buffer = self._buffer[: index - 1] + self._buffer[index:]
        else:
            self._buffer = self._buffer[:index] + "-" + self._buffer[index:]
        self._show_buffer()

    def evaluate(self) -> None:
        expression = auto_close(self._buffer.strip())
        if not expression:
            if self.engine.last_result is not None:
                self.display.set_result(self.engine.format(self.engine.last_result))
            return
        try:
            value = self.engine.evaluate(expression)
        except CalcError as exc:
            self._show_error(exc)
            return

        text = self.engine.format(value)
        self.display.set_expression(self.engine.pretty(expression))
        self.display.set_result(text)
        self.display.set_hint(self._bases_hint(value))
        if self.settings.appearance.animations:
            self.display.flash()

        behaviour = self.settings.behaviour
        if behaviour.copy_result_on_equals:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(text)
        self._buffer = repr(float(value)) if behaviour.keep_expression_after_equals else ""
        self._just_evaluated = True
        self._refresh_panels()

    def _show_error(self, error: CalcError) -> None:
        message = _error_message(error)
        self.display.set_result(message, error=True)
        self.display.set_hint(
            f"\u2191 position {error.position + 1}" if error.position is not None else ""
        )
        if self.settings.appearance.animations:
            self.display.shake()
        self.flash_message(message)

    def _bases_hint(self, value: float) -> str:
        if not self.settings.behaviour.show_bases:
            return ""
        if abs(value) >= 2 ** 63 or float(value).is_integer() is False:
            return ""
        integer = int(value)
        return tr(
            "display.hint.bases",
            hex=format(integer & 0xFFFFFFFFFFFFFFFF, "x").upper(),
            oct=format(integer & 0xFFFFFFFF, "o"),
            bin=format(integer & 0xFF, "b"),
        )

    # ------------------------------------------------------------------
    # memory
    # ------------------------------------------------------------------
    def memory_operation(self, operation: str, slot: Optional[str] = None) -> None:
        memory = self.engine.memory
        slot = slot or memory.active
        if operation == "recall":
            self.insert_text(repr(memory.recall(slot)))
        elif operation == "store":
            value = self._current_value()
            if value is not None:
                memory.store(value, slot)
        elif operation == "add":
            value = self._current_value()
            if value is not None:
                memory.add(value, slot)
        elif operation == "subtract":
            value = self._current_value()
            if value is not None:
                memory.subtract(value, slot)
        elif operation == "clear":
            memory.clear(slot)
        else:
            raise ValueError(f"Unknown memory operation '{operation}'")
        self._refresh_memory()

    def on_memory(self, operation: str, slot: str) -> None:
        self.engine.memory.select(slot)
        self.memory_operation(operation, slot)

    def cycle_memory_slot(self) -> None:
        from ..core.memory import SLOTS

        current = self.engine.memory.active
        index = SLOTS.index(current) if current in SLOTS else 0
        self.engine.memory.select(SLOTS[(index + 1) % len(SLOTS)])
        self._refresh_memory()

    def _current_value(self) -> Optional[float]:
        if self._buffer.strip():
            value, _error = self.engine.try_evaluate(self._buffer)
            if value is not None:
                return value
        return self.engine.last_result

    def _refresh_memory(self) -> None:
        memory = self.engine.memory
        value = memory.recall()
        self.display.set_memory_badge(memory.active, value)
        self.memory_button.setText(memory.active)
        self.memory_button.setToolTip(tr("status.memory", slot=f"{memory.active} = {self.engine.format(value)}"))
        self.memory_status.setText(tr("status.memory", slot=memory.active))
        self.side_panel.set_memory(memory.slots(), memory.active)

    def clear_history(self) -> None:
        self.engine.clear_history()
        self._refresh_panels()

    def _refresh_panels(self) -> None:
        self.side_panel.set_history(
            list(self.engine.history),
            tr("panel.history.empty"),
        )
        self.side_panel.set_tab_titles(
            tr("panel.history"), tr("panel.memory"), tr("panel.functions")
        )
        self._refresh_memory()

    # ------------------------------------------------------------------
    # appearance & preferences
    # ------------------------------------------------------------------
    def apply_settings(self) -> None:
        appearance, behaviour = self.settings.appearance, self.settings.behaviour

        translator.set_language(behaviour.language)
        self.engine.set_angle_mode(behaviour.angle_mode)
        self.engine.format_settings = behaviour.to_format_settings()
        self.engine.history.limit = behaviour.history_limit
        set_ripple_enabled(appearance.ripples and appearance.animations)

        theme = get_theme(appearance.theme)
        self.setStyleSheet(build_stylesheet(theme, appearance))
        application = QApplication.instance()
        if application is not None:
            application.setPalette(build_palette(theme))

        self.keypad.set_mode(appearance.keypad_mode)
        self.keypad.set_spacing(appearance.spacing)
        self.keypad.set_key_height(int(appearance.key_height * appearance.ui_scale))
        self.keypad.set_clip_radius(appearance.corner_radius)
        self.keypad.set_ripple_color(theme.palette.ripple)

        base_font = QFont(self.font())
        if appearance.font_family:
            base_font.setFamily(appearance.font_family)
        base_font.setPointSizeF(base_font.pointSizeF() * appearance.ui_scale)
        self.setFont(base_font)

        self.display.set_result_font_size(int(appearance.result_font_size * appearance.ui_scale))
        self.side_panel.setVisible(appearance.show_side_panel)
        self.history_action.setChecked(appearance.show_side_panel)
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(appearance.theme)
        self.theme_combo.blockSignals(False)
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(0 if appearance.keypad_mode == "standard" else 1)
        self.mode_combo.blockSignals(False)

        self.setWindowTitle(tr("app.name"))
        self._sync_menu_checks()
        self._refresh_status()
        self._refresh_panels()
        self._show_buffer()

    def _sync_menu_checks(self) -> None:
        for action in self.theme_group.actions():
            action.setChecked(action.data() == self.settings.appearance.theme)
        for action in self.mode_group.actions():
            action.setChecked(action.data() == self.settings.appearance.keypad_mode)
        for action in self.angle_group.actions():
            action.setChecked(action.data() == self.settings.behaviour.angle_mode)
        for action in self.language_group.actions():
            action.setChecked(action.data() == self.settings.behaviour.language)

    def _refresh_status(self) -> None:
        mode = tr("mode.scientific") if self.settings.appearance.keypad_mode == "scientific" else tr("mode.standard")
        self.mode_status.setText(tr("status.mode", mode=mode))
        self.angle_status.setText(tr("status.angle", angle=self.engine.angle_mode.upper()))
        self.angle_button.setText(self.engine.angle_mode.upper())
        self.display.set_angle_badge(self.engine.angle_mode)
        self.memory_status.setText(tr("status.memory", slot=self.engine.memory.active))

    def set_theme(self, name: str) -> None:
        self.settings.appearance.theme = name
        self.settings.save()
        self.apply_settings()

    def set_mode(self, mode: str) -> None:
        self.settings.appearance.keypad_mode = mode
        self.settings.save()
        self.apply_settings()

    def set_mode_from_combo(self, index: int) -> None:
        mode = self.mode_combo.itemData(index)
        if mode:
            self.set_mode(mode)

    def set_angle_mode(self, mode: str) -> None:
        self.settings.behaviour.angle_mode = mode
        self.settings.save()
        self.apply_settings()
        if self._buffer.strip():
            self._live_preview()

    def cycle_angle(self) -> None:
        mode = self.engine.cycle_angle_mode()
        self.set_angle_mode(mode)

    def set_language(self, code: str) -> None:
        self.settings.behaviour.language = code
        self.settings.save()
        self.apply_settings()
        self.flash_message(tr("status.language"))

    def toggle_side_panel(self, visible: bool) -> None:
        self.settings.appearance.show_side_panel = visible
        self.side_panel.setVisible(visible)
        self.settings.save()

    def show_functions(self) -> None:
        self.side_panel.setVisible(True)
        self.history_action.setChecked(True)
        self.side_panel.tabs.setCurrentIndex(2)

    # ------------------------------------------------------------------
    # dialogs
    # ------------------------------------------------------------------
    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        dialog.applied.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self, draft: AppSettings) -> None:
        self.settings.appearance = draft.appearance.sanitised()
        self.settings.behaviour = draft.behaviour.sanitised()
        path = self.settings.save()
        self.apply_settings()
        self.flash_message(tr("settings.saved", path=str(path)))

    def show_about(self) -> None:
        from PySide6.QtCore import qVersion

        QMessageBox.about(
            self,
            tr("about.title"),
            tr(
                "about.body",
                version=__version__,
                tagline=tr("app.tagline"),
                qt=qVersion(),
                python=sys.version.split()[0],
            ),
        )

    def show_shortcuts(self) -> None:
        rows = [
            tr("shortcut.digits"),
            tr("shortcut.enter"),
            tr("shortcut.backspace"),
            tr("shortcut.esc"),
            tr("shortcut.ctrlc"),
            tr("shortcut.ctrlv"),
            tr("shortcut.ctrlh"),
            tr("shortcut.ctrlm"),
            tr("shortcut.ctrlcomma"),
            tr("shortcut.f1"),
        ]
        QMessageBox.information(self, tr("shortcut.title"), "\n".join("\u2022 " + row for row in rows))

    # ------------------------------------------------------------------
    # keyboard
    # ------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        text = event.text()
        key = event.key()
        modifiers = event.modifiers()

        if modifiers & Qt.ControlModifier and key == Qt.Key_M:
            self.cycle_angle()
            return
        if text and text[0] in _DIGITS + ".()^%!+-*/":
            self.insert_text(text)
            return
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Equal):
            self.evaluate()
            return
        if key == Qt.Key_Backspace:
            self.backspace()
            return
        if key == Qt.Key_Escape:
            if self._buffer and not self._esc_armed:
                self.clear_entry()
                self._esc_armed = True
            else:
                self.clear_all()
                self._esc_armed = False
            return
        if key == Qt.Key_Delete:
            self.clear_all()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.key() != Qt.Key_Escape:
            self._esc_armed = False
        super().keyReleaseEvent(event)


def _error_message(error: CalcError) -> str:
    """Map an engine exception onto a translated, user-facing string."""
    if isinstance(error, DivisionByZeroError):
        return tr("error.divzero")
    if isinstance(error, (DomainError, OverflowResultError)):
        return tr("error.overflow") if isinstance(error, OverflowResultError) else tr("error.domain")
    if isinstance(error, (UnknownSymbolError, UnknownFunctionError)):
        return tr("error.unknown")
    if isinstance(error, LexError):
        return tr("error.lex")
    if isinstance(error, ParseError):
        return tr("error.parse")
    if isinstance(error, EvaluationError):
        return tr("error.generic")
    return tr("error.generic")
