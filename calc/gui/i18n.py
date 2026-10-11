"""Tiny gettext-style translator.

Qt Linguist would be the "proper" tool, but it needs a build step and ``.qm``
binaries.  Two JSON files and a dict lookup keep the app installable with a
single ``pip install`` -- which matters when the install command is
``curl ... | bash`` on a phone.
"""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Dict, Optional

__all__ = ["Translator", "translator", "available_languages", "load_translations"]

I18N_DIR = Path(__file__).resolve().parents[2] / "i18n"
FALLBACK = "en"


def available_languages() -> tuple[str, ...]:
    """Language codes for which an ``i18n/<code>.json`` file exists."""
    if not I18N_DIR.is_dir():
        return (FALLBACK,)
    codes = sorted(path.stem for path in I18N_DIR.glob("*.json"))
    return tuple(codes) or (FALLBACK,)


def load_translations(code: str) -> Dict[str, str]:
    path = I18N_DIR / f"{code}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _system_language() -> str:
    for source in (os.environ.get("PYTHON_CALCULATOR_LANG"), locale.getdefaultlocale()[0],
                   os.environ.get("LANG")):
        if not source:
            continue
        code = source.split(".")[0].split("_")[0].lower()
        if code in available_languages():
            return code
    return FALLBACK


class Translator:
    """Looks a key up in the active language, then in English, then returns the key."""

    def __init__(self, language: str = "system") -> None:
        self._cache: Dict[str, Dict[str, str]] = {}
        self.language = FALLBACK
        self.set_language(language)

    # -- language ----------------------------------------------------------
    def set_language(self, language: str) -> None:
        resolved = _system_language() if language in ("", "system", None) else language.lower()
        if resolved not in available_languages():
            resolved = FALLBACK
        self.language = resolved

    def _table(self, code: str) -> Dict[str, str]:
        if code not in self._cache:
            self._cache[code] = load_translations(code)
        return self._cache[code]

    # -- lookup ------------------------------------------------------------
    def tr(self, key: str, **kwargs) -> str:
        text = self._table(self.language).get(key)
        if text is None:
            text = self._table(FALLBACK).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    __call__ = tr


#: Process-wide translator used by every widget.
translator = Translator()
tr = translator.tr


def current_language() -> Optional[str]:
    return translator.language
