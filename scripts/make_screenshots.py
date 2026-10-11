#!/usr/bin/env python3
"""Render README screenshots straight from the running application.

These are *not* hand-made mock-ups: the script builds a real ``MainWindow`` on
an offscreen Qt platform and grabs the widget, so the images in ``assets/``
always match the code.  Run it after any visual change::

    QT_QPA_PLATFORM=offscreen python scripts/make_screenshots.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PYTHON_CALCULATOR_HOME"] = str(ROOT / ".screenshot-home")

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from calc.gui.app import build_window  # noqa: E402
from calc.gui.settings import AppSettings  # noqa: E402

OUT = ROOT / "assets" / "screenshots"

#: filename, theme, keypad mode, expression typed into the buffer
SHOT = [
    ("01-midnight-standard.png", "Midnight", "standard", "7\u00d7(3+4)"),
    ("02-light-scientific.png", "Light", "scientific", "sin(30)+\u221a2"),
    ("03-dracula-scientific.png", "Dracula", "scientific", "log(1024,2)^2"),
    ("04-nord-standard.png", "Nord", "standard", "1234.5\u00d712%"),
    ("05-sakura-standard.png", "Sakura", "standard", "\u03c0\u00d72"),
    ("06-highcontrast-standard.png", "High Contrast", "standard", "2^10-1"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication([])

    for filename, theme, mode, expression in SHOT:
        settings = AppSettings(home=Path(os.environ["PYTHON_CALCULATOR_HOME"]))
        settings.appearance.theme = theme
        settings.appearance.keypad_mode = mode
        settings.behaviour.angle_mode = "deg"
        window = build_window(app, settings)
        window.resize(QSize(760, 620))
        window.insert_text(expression)
        window.evaluate()
        window.show()
        app.processEvents()

        target = OUT / filename
        window.grab().save(str(target), "PNG")
        print(f"wrote {target.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
