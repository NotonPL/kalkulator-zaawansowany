"""Persistent calculation history.

The history is a plain JSON file so it can be inspected, backed up or shared.
It is deliberately *not* a database: the app must run on a phone filesystem
where nothing is available beyond the standard library.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

__all__ = ["HistoryEntry", "History"]

DEFAULT_LIMIT = 200


@dataclass
class HistoryEntry:
    expression: str
    result: str
    timestamp: float = field(default_factory=time.time)
    angle_mode: str = "rad"

    def formatted_time(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return time.strftime(fmt, time.localtime(self.timestamp))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            expression=str(data.get("expression", "")),
            result=str(data.get("result", "")),
            timestamp=float(data.get("timestamp", time.time())),
            angle_mode=str(data.get("angle_mode", "rad")),
        )


class History:
    """An ordered, size-bounded list of past calculations."""

    def __init__(self, path: Optional[Path] = None, limit: int = DEFAULT_LIMIT) -> None:
        self.path = Path(path) if path else None
        self.limit = max(1, int(limit))
        self._entries: List[HistoryEntry] = []
        if self.path is not None and self.path.exists():
            self.load()

    # -- container protocol ------------------------------------------------
    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        # Newest first -- that is how the GUI panel shows it.
        return iter(reversed(self._entries))

    def __getitem__(self, index: int) -> HistoryEntry:
        return list(self)[index]

    @property
    def entries(self) -> List[HistoryEntry]:
        return list(self)

    # -- mutation ----------------------------------------------------------
    def add(self, expression: str, result: str, angle_mode: str = "rad") -> HistoryEntry:
        entry = HistoryEntry(expression=expression, result=result, angle_mode=angle_mode)
        self._entries.append(entry)
        if len(self._entries) > self.limit:
            self._entries = self._entries[-self.limit :]
        self.save()
        return entry

    def clear(self) -> None:
        self._entries.clear()
        self.save()

    def remove(self, entry: HistoryEntry) -> bool:
        try:
            self._entries.remove(entry)
        except ValueError:
            return False
        self.save()
        return True

    # -- search ------------------------------------------------------------
    def search(self, needle: str) -> List[HistoryEntry]:
        needle = needle.strip().lower()
        if not needle:
            return self.entries
        return [
            entry
            for entry in reversed(self._entries)
            if needle in entry.expression.lower() or needle in entry.result.lower()
        ]

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # A corrupt history file must never stop the app from starting.
            self._entries = []
            return
        raw_entries: Iterable[dict] = payload.get("entries", []) if isinstance(payload, dict) else payload
        self._entries = [HistoryEntry.from_dict(item) for item in raw_entries][-self.limit :]

    def save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "entries": [e.to_dict() for e in self._entries]}
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:  # pragma: no cover - read-only filesystem
            pass
