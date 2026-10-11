"""Qt front end.

Importing this package pulls in PySide6, so nothing outside it should import it
at module scope -- :mod:`calc` imports it lazily inside :func:`calc.run_gui`.
"""

from __future__ import annotations

from typing import List

from .. import NoDisplayError

__all__ = ["run_gui", "NoDisplayError", "MainWindow"]


def _display_available() -> bool:
    """Best-effort check for a usable graphical session."""
    import os
    import sys

    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return True
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def run_gui(argv: List[str]) -> int:
    """Create the application, show the main window and run the event loop.

    :raises NoDisplayError: when Qt cannot attach to a display, so the caller
        can fall back to the terminal interface.
    """
    if not _display_available():
        raise NoDisplayError("no DISPLAY or WAYLAND_DISPLAY in the environment")

    from PySide6.QtWidgets import QApplication

    from .app import build_window

    application = QApplication.instance() or QApplication(list(argv))
    application.setApplicationName("python-calculator")
    application.setOrganizationName("python-calculator")

    window = build_window(application)
    window.show()
    return application.exec()


def __getattr__(name: str):  # pragma: no cover - convenience re-export
    if name == "MainWindow":
        from .main_window import MainWindow

        return MainWindow
    raise AttributeError(name)
