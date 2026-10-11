"""Application settings with safe JSON persistence.

Settings are split into :class:`Appearance` (how it looks) and
:class:`Behaviour` (how it calculates).  Both are plain dataclasses so they can
be diffed, serialised and unit-tested without touching Qt.

Loading is deliberately forgiving: a file written by an older version, or
corrupted by a killed process, must never prevent the app from starting --
unknown keys are ignored and out-of-range values are clamped.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.engine import data_directory
from ..core.formatter import FormatSettings

__all__ = ["Appearance", "Behaviour", "AppSettings"]

FILENAME = "settings.json"

LANGUAGES = ("en", "pl")


def _clamp(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    if number != number:  # NaN
        return float(default)
    return max(minimum, min(maximum, number))


@dataclass
class Appearance:
    """Everything the settings dialog exposes under "Look & feel"."""

    theme: str = "Midnight"
    accent_color: str = ""          # empty == use the theme's own accent
    font_family: str = ""           # empty == use the theme's font
    corner_radius: int = 14
    spacing: int = 6
    key_height: int = 56
    key_font_size: int = 18
    result_font_size: int = 40
    ui_scale: float = 1.0
    animations: bool = True
    ripples: bool = True
    show_side_panel: bool = True
    keypad_mode: str = "standard"   # "standard" | "scientific"

    def sanitised(self) -> "Appearance":
        return Appearance(
            theme=str(self.theme or "Midnight"),
            accent_color=_validate_colour(self.accent_color, ""),
            font_family=str(self.font_family or ""),
            corner_radius=int(_clamp(self.corner_radius, 0, 32, 14)),
            spacing=int(_clamp(self.spacing, 0, 20, 6)),
            key_height=int(_clamp(self.key_height, 28, 120, 56)),
            key_font_size=int(_clamp(self.key_font_size, 9, 32, 18)),
            result_font_size=int(_clamp(self.result_font_size, 18, 96, 40)),
            ui_scale=float(_clamp(self.ui_scale, 0.6, 1.8, 1.0)),
            animations=bool(self.animations),
            ripples=bool(self.ripples),
            show_side_panel=bool(self.show_side_panel),
            keypad_mode=self.keypad_mode if self.keypad_mode in ("standard", "scientific") else "standard",
        )


@dataclass
class Behaviour:
    """Calculation and formatting preferences."""

    angle_mode: str = "rad"          # rad | deg | grad
    language: str = "system"         # system | en | pl
    thousands: bool = True
    group_separator: str = " "
    decimal_separator: str = "."
    precision: int = 12
    history_limit: int = 200
    copy_result_on_equals: bool = False
    keep_expression_after_equals: bool = True
    show_bases: bool = True          # show hex/oct/bin under the result

    def sanitised(self) -> "Behaviour":
        group = self.group_separator if self.group_separator in (" ", ",", ".", "\u202f") else " "
        decimal = self.decimal_separator if self.decimal_separator in (".", ",") else "."
        # A comma decimal separator needs a different grouping character.
        if decimal == "," and group == ",":
            group = " "
        return Behaviour(
            angle_mode=self.angle_mode if self.angle_mode in ("rad", "deg", "grad") else "rad",
            language=self.language if self.language in ("system", "en", "pl") else "system",
            thousands=bool(self.thousands),
            group_separator=group,
            decimal_separator=decimal,
            precision=int(_clamp(self.precision, 1, 16, 12)),
            history_limit=int(_clamp(self.history_limit, 10, 5000, 200)),
            copy_result_on_equals=bool(self.copy_result_on_equals),
            keep_expression_after_equals=bool(self.keep_expression_after_equals),
            show_bases=bool(self.show_bases),
        )

    def to_format_settings(self) -> FormatSettings:
        return FormatSettings(
            thousands=self.thousands,
            group_separator=self.group_separator,
            decimal_separator=self.decimal_separator,
            precision=self.precision,
        )


def _validate_colour(value: Any, default: str) -> str:
    if not isinstance(value, str) or not value:
        return default
    text = value.strip()
    if text.startswith("#") and len(text) in (4, 7):
        try:
            int(text.lstrip("#"), 16)
        except ValueError:
            return default
        return text
    return default


@dataclass
class AppSettings:
    """Top-level settings object; owns its own persistence."""

    appearance: Appearance = None  # type: ignore[assignment]
    behaviour: Behaviour = None    # type: ignore[assignment]
    home: Optional[Path] = None

    def __post_init__(self) -> None:
        self.appearance = self.appearance or Appearance()
        self.behaviour = self.behaviour or Behaviour()
        self.home = Path(self.home) if self.home else data_directory()

    # -- paths -------------------------------------------------------------
    @property
    def path(self) -> Path:
        return self.home / FILENAME

    # -- persistence -------------------------------------------------------
    @classmethod
    def load(cls, home: Optional[Path] = None) -> "AppSettings":
        settings = cls(home=home)
        if not settings.path.exists():
            return settings
        try:
            payload = json.loads(settings.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return settings
        if not isinstance(payload, dict):
            return settings
        settings.appearance = _from_dict(Appearance, payload.get("appearance", {})).sanitised()
        settings.behaviour = _from_dict(Behaviour, payload.get("behaviour", {})).sanitised()
        return settings

    def save(self) -> Path:
        self.appearance = self.appearance.sanitised()
        self.behaviour = self.behaviour.sanitised()
        self.home.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "appearance": asdict(self.appearance),
            "behaviour": asdict(self.behaviour),
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.path

    def reset(self) -> None:
        self.appearance = Appearance()
        self.behaviour = Behaviour()

    def to_dict(self) -> Dict[str, Any]:
        return {"appearance": asdict(self.appearance), "behaviour": asdict(self.behaviour)}


def _from_dict(cls, data: Any):
    """Build a dataclass from ``data``, ignoring keys the class does not know."""
    instance = cls()
    if not isinstance(data, dict):
        return instance
    known = {f.name: f.type for f in fields(cls) if f.init}
    for key, value in data.items():
        if key in known:
            setattr(instance, key, value)
    return instance


def default_settings(home: Optional[Path] = None) -> AppSettings:
    """Fresh settings; mostly useful in tests."""
    return AppSettings(home=home or Path.cwd())
