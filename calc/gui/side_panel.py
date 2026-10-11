"""The side panel: history, memory registers and a function browser.

The three tabs are read-only views over objects the engine already owns
(:class:`~calc.core.history.History`, :class:`~calc.core.memory.Memory`,
:data:`~calc.core.functions.FUNCTIONS`).  The panel never stores calculation
state itself -- it only renders it and emits intents.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.formatter import FormatSettings, format_number
from ..core.functions import CONSTANTS, FUNCTIONS, FunctionSpec
from ..core.history import HistoryEntry
from ..core.memory import SLOTS

__all__ = ["SidePanel"]

_COMPACT = FormatSettings(thousands=False, precision=10)


def _compact(value: float) -> str:
    """Short, unambiguous rendering used inside list rows."""
    return format_number(value, _COMPACT)


class SidePanel(QFrame):
    """Tabs for history, memory and the function reference."""

    history_requested = Signal(str)          # text to insert
    history_clear_requested = Signal()
    memory_requested = Signal(str, str)      # (operation, slot)
    function_requested = Signal(str)         # signature to insert

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("SidePanel")
        self.setMinimumWidth(230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_history_tab()
        self._build_memory_tab()
        self._build_functions_tab()

    # -- history -----------------------------------------------------------
    def _build_history_tab(self) -> None:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search history\u2026")
        self.history_search.setClearButtonEnabled(True)
        self.history_search.textChanged.connect(self._apply_history_filter)
        vbox.addWidget(self.history_search)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_history_double_clicked)
        self.history_list.itemClicked.connect(self._on_history_double_clicked)
        vbox.addWidget(self.history_list, 1)

        self.history_empty = QLabel("No calculations yet")
        self.history_empty.setObjectName("HistoryEmpty")
        self.history_empty.setProperty("role", "muted")
        self.history_empty.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.history_empty)

        row = QHBoxLayout()
        self.history_clear_button = QPushButton("Clear")
        self.history_clear_button.setObjectName("HistoryClear")
        self.history_clear_button.setProperty("role", "clear")
        self.history_clear_button.clicked.connect(self.history_clear_requested.emit)
        row.addStretch(1)
        row.addWidget(self.history_clear_button)
        vbox.addLayout(row)

        self.tabs.addTab(page, "History")
        self._history_entries: List[HistoryEntry] = []

    def _apply_history_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for index in range(self.history_list.count()):
            item = self.history_list.item(index)
            entry: HistoryEntry = item.data(Qt.UserRole)
            visible = not needle or (
                needle in entry.expression.lower() or needle in entry.result.lower()
            )
            item.setHidden(not visible)

    def _on_history_double_clicked(self, item: QListWidgetItem) -> None:
        entry: HistoryEntry = item.data(Qt.UserRole)
        self.history_requested.emit(entry.expression)

    def set_history(self, entries: List[HistoryEntry], empty_text: str) -> None:
        """Rebuild the history list; ``entries`` is newest-first."""
        self._history_entries = list(entries)
        self.history_list.clear()
        for entry in self._history_entries:
            item = QListWidgetItem(f"{entry.expression}  =  {entry.result}")
            item.setData(Qt.UserRole, entry)
            item.setToolTip(f"{entry.formatted_time()}  \u00b7  {entry.angle_mode.upper()}")
            self.history_list.addItem(item)
        self.history_empty.setText(empty_text)
        self.history_empty.setVisible(not self._history_entries)
        self._apply_history_filter(self.history_search.text())

    def set_tab_titles(self, history: str, memory: str, functions: str) -> None:
        self.tabs.setTabText(0, history)
        self.tabs.setTabText(1, memory)
        self.tabs.setTabText(2, functions)

    # -- memory ------------------------------------------------------------
    def _build_memory_tab(self) -> None:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        self.memory_list = QListWidget()
        for slot in SLOTS:
            item = QListWidgetItem(f"{slot}  =  0")
            item.setData(Qt.UserRole, slot)
            self.memory_list.addItem(item)
        self.memory_list.itemSelectionChanged.connect(self._on_memory_selection)
        vbox.addWidget(self.memory_list, 1)

        self.memory_actions: Dict[str, QPushButton] = {}
        for column, (label, operation) in enumerate(
            (("MR", "recall"), ("MS", "store"), ("M+", "add"), ("M\u2212", "subtract"), ("MC", "clear"))
        ):
            button = QPushButton(label)
            button.setProperty("role", "memory")
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(lambda _c=False, op=operation: self._emit_memory(op))
            self.memory_actions[operation] = button

        row = QHBoxLayout()
        for operation in ("recall", "store", "add", "subtract", "clear"):
            row.addWidget(self.memory_actions[operation])
        vbox.addLayout(row)

        self.tabs.addTab(page, "Memory")
        self._selected_slot = SLOTS[0]

    def _selected(self) -> str:
        items = self.memory_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return self._selected_slot

    def _on_memory_selection(self) -> None:
        self._selected_slot = self._selected()

    def _emit_memory(self, operation: str) -> None:
        self.memory_requested.emit(operation, self._selected())

    def set_memory(self, slots: Dict[str, float], active: str) -> None:
        for index in range(self.memory_list.count()):
            item = self.memory_list.item(index)
            slot = item.data(Qt.UserRole)
            value = slots.get(slot, 0.0)
            item.setText(f"{slot}  =  {_compact(value)}")
            font = item.font()
            font.setBold(slot == active)
            item.setFont(font)
            if slot == active:
                self.memory_list.setCurrentItem(item)

    # -- functions ---------------------------------------------------------
    def _build_functions_tab(self) -> None:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        self.function_search = QLineEdit()
        self.function_search.setPlaceholderText("Filter functions\u2026")
        self.function_search.setClearButtonEnabled(True)
        self.function_search.textChanged.connect(self._apply_function_filter)
        vbox.addWidget(self.function_search)

        self.function_list = QListWidget()
        self.function_list.itemDoubleClicked.connect(self._on_function_double_clicked)
        vbox.addWidget(self.function_list, 1)

        self.tabs.addTab(page, "Functions")
        self._load_functions()

    def _load_functions(self) -> None:
        seen = set()
        specs: List[FunctionSpec] = []
        for spec in FUNCTIONS.values():
            if spec.name in seen:
                continue
            seen.add(spec.name)
            specs.append(spec)
        specs.sort(key=lambda spec: (spec.category, spec.name))

        current_category = None
        for spec in specs:
            if spec.category != current_category:
                current_category = spec.category
                header = QListWidgetItem(current_category.upper())
                header.setFlags(Qt.NoItemFlags)
                header.setData(Qt.UserRole, None)
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                self.function_list.addItem(header)

            item = QListWidgetItem(f"{spec.signature()}   \u2014   {spec.description}")
            item.setData(Qt.UserRole, spec)
            self.function_list.addItem(item)

        # Constants are useful to discover too.
        header = QListWidgetItem("CONSTANTS")
        header.setFlags(Qt.NoItemFlags)
        header.setData(Qt.UserRole, None)
        self.function_list.addItem(header)
        for name in sorted(CONSTANTS):
            item = QListWidgetItem(f"{name}   \u2014   {_compact(CONSTANTS[name])}")
            item.setData(Qt.UserRole, None)
            item.setData(Qt.UserRole + 1, name)
            self.function_list.addItem(item)

    def _apply_function_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for index in range(self.function_list.count()):
            item = self.function_list.item(index)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_function_double_clicked(self, item: QListWidgetItem) -> None:
        spec = item.data(Qt.UserRole)
        if isinstance(spec, FunctionSpec):
            self.function_requested.emit(f"{spec.name}(")
            return
        name = item.data(Qt.UserRole + 1)
        if name:
            self.function_requested.emit(str(name))
