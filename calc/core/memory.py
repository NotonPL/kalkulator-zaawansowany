"""Memory registers.

Ten named slots (``M0`` .. ``M9``) with the classic calculator operations
(MC / MR / M+ / M- / MS).  Slots are persisted next to the history so a user's
stored values survive a restart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

__all__ = ["Memory"]

SLOTS = tuple(f"M{i}" for i in range(10))


class Memory:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else None
        self._slots: Dict[str, float] = {name: 0.0 for name in SLOTS}
        self._active = SLOTS[0]
        if self.path is not None and self.path.exists():
            self.load()

    # -- slots -------------------------------------------------------------
    @property
    def active(self) -> str:
        return self._active

    def select(self, name: str) -> None:
        if name not in self._slots:
            raise KeyError(f"Unknown memory slot '{name}'")
        self._active = name

    def slots(self) -> Dict[str, float]:
        return dict(self._slots)

    def is_empty(self) -> bool:
        return all(value == 0 for value in self._slots.values())

    # -- operations --------------------------------------------------------
    def recall(self, name: Optional[str] = None) -> float:
        return self._slots.get(name or self._active, 0.0)

    def store(self, value: float, name: Optional[str] = None) -> None:
        self._slots[name or self._active] = float(value)
        self.save()

    def add(self, value: float, name: Optional[str] = None) -> float:
        key = name or self._active
        self._slots[key] = self._slots.get(key, 0.0) + float(value)
        self.save()
        return self._slots[key]

    def subtract(self, value: float, name: Optional[str] = None) -> float:
        key = name or self._active
        self._slots[key] = self._slots.get(key, 0.0) - float(value)
        self.save()
        return self._slots[key]

    def clear(self, name: Optional[str] = None) -> None:
        key = name or self._active
        self._slots[key] = 0.0
        self.save()

    def clear_all(self) -> None:
        self._slots = {name: 0.0 for name in SLOTS}
        self.save()

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for name in SLOTS:
            if name in payload.get("slots", {}):
                try:
                    self._slots[name] = float(payload["slots"][name])
                except (TypeError, ValueError):
                    continue

    def save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"version": 1, "active": self._active, "slots": self._slots}, indent=2),
                encoding="utf-8",
            )
        except OSError:  # pragma: no cover - read-only filesystem
            pass
