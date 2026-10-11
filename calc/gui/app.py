"""Window construction, kept separate from the event loop so tests can build a
window without ever calling ``QApplication.exec()``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .settings import AppSettings

__all__ = ["build_window", "icon_path"]

ICON = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.svg"


def icon_path() -> Path:
    return ICON


def build_window(application: Optional[QApplication] = None, settings: Optional[AppSettings] = None) -> MainWindow:
    """Create the :class:`MainWindow` and apply the persisted settings."""
    if settings is None:
        settings = AppSettings.load()
    window = MainWindow(settings)
    if ICON.exists() and application is not None:
        application.setWindowIcon(QIcon(str(ICON)))
        window.setWindowIcon(QIcon(str(ICON)))
    return window
