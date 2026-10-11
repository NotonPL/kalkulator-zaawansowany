"""Theme engine.

A theme is nothing more than a named palette plus a couple of defaults.  The
:func:`build_stylesheet` function turns a palette *and* the user's appearance
settings into one Qt stylesheet, so every visual choice in the settings dialog
(rounded corners, spacing, font, accent colour) is applied live without
restarting the app.

Adding a theme = appending a :class:`Theme` to :data:`BUILTIN_THEMES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List

__all__ = ["Palette", "Theme", "BUILTIN_THEMES", "theme_names", "get_theme", "build_stylesheet", "build_palette"]


@dataclass(frozen=True)
class Palette:
    """Every colour the UI can use.  All values are CSS colour strings."""

    background: str = "#111318"
    surface: str = "#1a1d24"
    surface_alt: str = "#232733"
    border: str = "#2e3340"
    text: str = "#f2f4f8"
    text_muted: str = "#8b93a7"

    display_bg: str = "#14171d"
    display_text: str = "#f2f4f8"
    display_muted: str = "#79819a"
    display_error: str = "#ff6b6b"

    digit: str = "#2a2f3d"
    digit_text: str = "#f2f4f8"
    operator: str = "#333a4d"
    operator_text: str = "#ffd479"
    function: str = "#232733"
    function_text: str = "#7fd1ff"
    clear: str = "#3a2b31"
    clear_text: str = "#ff8fa3"
    equals: str = "#3b82f6"
    equals_text: str = "#ffffff"
    memory: str = "#233033"
    memory_text: str = "#7fe3c0"

    hover_mix: str = "#ffffff"   # mixed into the base colour on hover
    ripple: str = "#ffffff"
    scrollbar: str = "#3a4152"


@dataclass(frozen=True)
class Theme:
    name: str
    palette: Palette
    is_dark: bool = True
    #: Default corner radius; the user can still override it in settings.
    radius: int = 14
    font_family: str = "Inter, Segoe UI, DejaVu Sans, sans-serif"
    mono_family: str = "JetBrains Mono, Consolas, DejaVu Sans Mono, monospace"
    tags: tuple = field(default_factory=tuple)

    def with_accent(self, accent: str) -> "Theme":
        """Return a copy whose accent (and equals key) uses ``accent``."""
        return replace(
            self,
            palette=replace(self.palette, equals=accent, memory=self.palette.memory),
        )


def _p(**overrides) -> Palette:
    return Palette(**overrides)


BUILTIN_THEMES: List[Theme] = [
    Theme(
        name="Midnight",
        tags=("dark", "default"),
        palette=_p(),
    ),
    Theme(
        name="Light",
        is_dark=False,
        radius=12,
        palette=_p(
            background="#eef1f6",
            surface="#ffffff",
            surface_alt="#f4f6fa",
            border="#d7dce6",
            text="#1d2230",
            text_muted="#6b7385",
            display_bg="#ffffff",
            display_text="#1d2230",
            display_muted="#8a92a6",
            display_error="#d63031",
            digit="#ffffff",
            digit_text="#1d2230",
            operator="#e8ecf5",
            operator_text="#b3610a",
            function="#f1f4fa",
            function_text="#0a6fb3",
            clear="#fdecef",
            clear_text="#c0392b",
            equals="#2f6fed",
            equals_text="#ffffff",
            memory="#e7f6f1",
            memory_text="#0d8a63",
            hover_mix="#000000",
            ripple="#2f6fed",
            scrollbar="#c3cad8",
        ),
    ),
    Theme(
        name="Nord",
        radius=16,
        palette=_p(
            background="#2e3440",
            surface="#3b4252",
            surface_alt="#434c5e",
            border="#4c566a",
            text="#eceff4",
            text_muted="#9aa5b8",
            display_bg="#2b303b",
            display_text="#eceff4",
            display_muted="#8f9bb0",
            display_error="#bf616a",
            digit="#434c5e",
            digit_text="#eceff4",
            operator="#4c566a",
            operator_text="#ebcb8b",
            function="#3b4252",
            function_text="#88c0d0",
            clear="#4a3a3f",
            clear_text="#bf616a",
            equals="#5e81ac",
            equals_text="#eceff4",
            memory="#37474f",
            memory_text="#a3be8c",
            ripple="#d8dee9",
            scrollbar="#4c566a",
        ),
    ),
    Theme(
        name="Dracula",
        radius=16,
        palette=_p(
            background="#282a36",
            surface="#343746",
            surface_alt="#3d4152",
            border="#44475a",
            text="#f8f8f2",
            text_muted="#9a9fbf",
            display_bg="#21222c",
            display_text="#f8f8f2",
            display_muted="#8b90ad",
            display_error="#ff5555",
            digit="#44475a",
            digit_text="#f8f8f2",
            operator="#525568",
            operator_text="#f1fa8c",
            function="#343746",
            function_text="#8be9fd",
            clear="#4a3346",
            clear_text="#ff79c6",
            equals="#bd93f9",
            equals_text="#282a36",
            memory="#2f4440",
            memory_text="#50fa7b",
            ripple="#f8f8f2",
            scrollbar="#6272a4",
        ),
    ),
    Theme(
        name="Solarized",
        radius=10,
        palette=_p(
            background="#002b36",
            surface="#073642",
            surface_alt="#0b4152",
            border="#114a5c",
            text="#eee8d5",
            text_muted="#7f9a9c",
            display_bg="#00212b",
            display_text="#eee8d5",
            display_muted="#6f8a8c",
            display_error="#dc322f",
            digit="#0b4152",
            digit_text="#eee8d5",
            operator="#11536a",
            operator_text="#b58900",
            function="#073642",
            function_text="#2aa198",
            clear="#4d2530",
            clear_text="#dc322f",
            equals="#268bd2",
            equals_text="#002b36",
            memory="#123f3a",
            memory_text="#859900",
            ripple="#eee8d5",
            scrollbar="#114a5c",
        ),
    ),
    Theme(
        name="Graphite",
        is_dark=False,
        radius=8,
        font_family="Roboto, Helvetica Neue, DejaVu Sans, sans-serif",
        palette=_p(
            background="#26282c",
            surface="#2f3237",
            surface_alt="#383c42",
            border="#454a52",
            text="#e8eaed",
            text_muted="#9aa0a6",
            display_bg="#202225",
            display_text="#e8eaed",
            display_muted="#80868b",
            display_error="#f28b82",
            digit="#3c4043",
            digit_text="#e8eaed",
            operator="#454a52",
            operator_text="#fdd663",
            function="#383c42",
            function_text="#8ab4f8",
            clear="#4a3b3d",
            clear_text="#f28b82",
            equals="#8ab4f8",
            equals_text="#202124",
            memory="#2f4440",
            memory_text="#81c995",
            ripple="#e8eaed",
            scrollbar="#5f6368",
        ),
    ),
    Theme(
        name="Sakura",
        is_dark=False,
        radius=18,
        palette=_p(
            background="#fdf2f6",
            surface="#ffffff",
            surface_alt="#fbe7ef",
            border="#f2d3e0",
            text="#4a2b3a",
            text_muted="#9d7c8c",
            display_bg="#fff8fb",
            display_text="#4a2b3a",
            display_muted="#b595a4",
            display_error="#d81b60",
            digit="#ffffff",
            digit_text="#4a2b3a",
            operator="#fbe0ea",
            operator_text="#c2185b",
            function="#fdf0f5",
            function_text="#ad1457",
            clear="#ffe3ec",
            clear_text="#d81b60",
            equals="#ec407a",
            equals_text="#ffffff",
            memory="#e8f5e9",
            memory_text="#2e7d32",
            hover_mix="#000000",
            ripple="#ec407a",
            scrollbar="#e8c3d3",
        ),
    ),
    Theme(
        name="High Contrast",
        radius=6,
        font_family="DejaVu Sans, sans-serif",
        palette=_p(
            background="#000000",
            surface="#000000",
            surface_alt="#101010",
            border="#ffffff",
            text="#ffffff",
            text_muted="#d0d0d0",
            display_bg="#000000",
            display_text="#ffffff",
            display_muted="#d0d0d0",
            display_error="#ffff00",
            digit="#000000",
            digit_text="#ffffff",
            operator="#000000",
            operator_text="#ffff00",
            function="#000000",
            function_text="#00ffff",
            clear="#000000",
            clear_text="#ff8080",
            equals="#ffff00",
            equals_text="#000000",
            memory="#000000",
            memory_text="#00ff80",
            hover_mix="#ffffff",
            ripple="#ffffff",
            scrollbar="#ffffff",
        ),
    ),
]

_INDEX: Dict[str, Theme] = {theme.name: theme for theme in BUILTIN_THEMES}
DEFAULT_THEME = "Midnight"


def theme_names() -> List[str]:
    return [theme.name for theme in BUILTIN_THEMES]


def get_theme(name: str) -> Theme:
    """Return the theme called ``name``, falling back to the default."""
    return _INDEX.get(name, _INDEX[DEFAULT_THEME])


# ---------------------------------------------------------------------------
# stylesheet generation
# ---------------------------------------------------------------------------
_QSS_TEMPLATE = """
/* ------------------------------------------------------------------ */
/* Generated by calc.gui.themes -- do not edit at runtime.             */
/* Theme: {theme_name}                                                 */
/* ------------------------------------------------------------------ */

* {{
    font-family: {font_family};
    outline: none;
}}

QWidget#CentralWidget {{
    background-color: {bg};
}}

/* ---------------- display ---------------- */
QFrame#DisplayFrame {{
    background-color: {display_bg};
    border: 1px solid {border};
    border-radius: {radius}px;
}}

QLabel#DisplayExpression {{
    color: {display_muted};
    font-size: {expr_size}px;
    font-family: {mono_family};
    background: transparent;
    padding: 2px 10px;
}}

QLabel#DisplayResult {{
    color: {display_text};
    font-size: {result_size}px;
    font-weight: 600;
    font-family: {mono_family};
    background: transparent;
    padding: 0px 10px;
}}

QLabel#DisplayResult[state="error"] {{
    color: {display_error};
}}

QLabel#DisplayHint {{
    color: {display_muted};
    font-size: {hint_size}px;
    font-family: {mono_family};
    background: transparent;
    padding: 0px 12px 6px 12px;
}}

QLabel#MemoryBadge {{
    color: {memory_text};
    background: {memory};
    border-radius: {badge_radius}px;
    padding: 2px 8px;
    font-size: {hint_size}px;
    font-weight: 700;
}}

QLabel#AngleBadge {{
    color: {operator_text};
    background: {operator};
    border-radius: {badge_radius}px;
    padding: 2px 8px;
    font-size: {hint_size}px;
    font-weight: 700;
}}

/* ---------------- keypad ---------------- */
QPushButton {{
    background-color: {digit};
    color: {digit_text};
    border: 1px solid {border};
    border-radius: {radius}px;
    font-size: {key_font}px;
    font-weight: 500;
    min-height: {key_height}px;
    padding: 0px;
}}
QPushButton:hover {{
    background-color: {digit_hover};
}}
QPushButton:pressed {{
    background-color: {digit_pressed};
}}
QPushButton:disabled {{
    color: {text_muted};
    background-color: {surface};
}}

QPushButton[role="operator"] {{
    background-color: {operator};
    color: {operator_text};
    font-size: {op_font}px;
    font-weight: 700;
}}
QPushButton[role="operator"]:hover {{ background-color: {operator_hover}; }}
QPushButton[role="operator"]:pressed {{ background-color: {operator_pressed}; }}

QPushButton[role="function"] {{
    background-color: {function};
    color: {function_text};
    font-size: {fn_font}px;
}}
QPushButton[role="function"]:hover {{ background-color: {function_hover}; }}
QPushButton[role="function"]:pressed {{ background-color: {function_pressed}; }}

QPushButton[role="clear"] {{
    background-color: {clear};
    color: {clear_text};
}}
QPushButton[role="clear"]:hover {{ background-color: {clear_hover}; }}
QPushButton[role="clear"]:pressed {{ background-color: {clear_pressed}; }}

QPushButton[role="memory"] {{
    background-color: {memory};
    color: {memory_text};
    font-size: {fn_font}px;
}}
QPushButton[role="memory"]:hover {{ background-color: {memory_hover}; }}
QPushButton[role="memory"]:pressed {{ background-color: {memory_pressed}; }}

QPushButton[role="equals"] {{
    background-color: {equals};
    color: {equals_text};
    font-size: {op_font}px;
    font-weight: 800;
    border: none;
}}
QPushButton[role="equals"]:hover {{ background-color: {equals_hover}; }}
QPushButton[role="equals"]:pressed {{ background-color: {equals_pressed}; }}

QPushButton[role="tab"][checked="true"] {{
    background-color: {equals};
    color: {equals_text};
}}

/* ---------------- side panel ---------------- */
QFrame#SidePanel {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: {radius}px;
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {text_muted};
    padding: 6px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: {hint_size}px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {text};
    border-bottom: 2px solid {equals};
}}

QListWidget {{
    background: transparent;
    color: {text};
    border: none;
    font-size: {list_font}px;
    font-family: {mono_family};
}}
QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {border};
    border-radius: 0px;
}}
QListWidget::item:hover {{ background-color: {surface_alt}; }}
QListWidget::item:selected {{
    background-color: {equals};
    color: {equals_text};
}}

QLineEdit {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius_small}px;
    padding: 6px 10px;
    selection-background-color: {equals};
    selection-color: {equals_text};
    font-size: {list_font}px;
}}
QLineEdit:focus {{ border: 1px solid {equals}; }}

QLabel {{ color: {text}; background: transparent; font-size: {list_font}px; }}
QLabel[role="muted"] {{ color: {text_muted}; }}
QLabel[role="heading"] {{ font-size: {heading_size}px; font-weight: 700; }}

/* ---------------- toolbar ---------------- */
QToolBar {{
    background: transparent;
    border: none;
    spacing: {spacing}px;
    padding: 2px;
}}
QToolButton {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius_small}px;
    padding: 5px 10px;
    font-size: {list_font}px;
    font-weight: 600;
}}
QToolButton:hover {{ background-color: {surface}; }}
QToolButton:checked {{ background-color: {equals}; color: {equals_text}; }}
QToolButton::menu-indicator {{ image: none; }}

QComboBox {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius_small}px;
    padding: 5px 10px;
    font-size: {list_font}px;
}}
QComboBox:hover {{ background-color: {surface}; }}
QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    selection-background-color: {equals};
    selection-color: {equals_text};
}}

/* ---------------- inputs ---------------- */
QSpinBox, QDoubleSpinBox {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius_small}px;
    padding: 4px 8px;
    font-size: {list_font}px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{ width: 16px; }}

QSlider::groove:horizontal {{
    height: 4px;
    background: {border};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {equals};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{ background: {equals}; border-radius: 2px; }}

QCheckBox {{ color: {text}; font-size: {list_font}px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {border};
    border-radius: 5px;
    background: {surface_alt};
}}
QCheckBox::indicator:checked {{ background: {equals}; border-color: {equals}; }}

QGroupBox {{
    border: 1px solid {border};
    border-radius: {radius_small}px;
    margin-top: 14px;
    padding-top: 10px;
    font-size: {list_font}px;
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {text_muted};
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {scrollbar}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {scrollbar}; border-radius: 5px; min-width: 24px; }}

QStatusBar {{ background: {surface}; color: {text_muted}; font-size: {hint_size}px; }}
QStatusBar::item {{ border: none; }}

QMenuBar {{ background: {surface}; color: {text}; font-size: {list_font}px; }}
QMenuBar::item:selected {{ background: {surface_alt}; }}
QMenu {{ background: {surface}; color: {text}; border: 1px solid {border}; font-size: {list_font}px; }}
QMenu::item:selected {{ background: {equals}; color: {equals_text}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}

QToolTip {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    padding: 6px;
    font-size: {hint_size}px;
}}

QDialog {{ background-color: {bg}; }}
QScrollArea {{ border: none; background: transparent; }}

QPushButton#DialogPrimary {{
    background-color: {equals};
    color: {equals_text};
    font-weight: 700;
    border: none;
    padding: 8px 20px;
}}
QPushButton#DialogPrimary:hover {{ background-color: {equals_hover}; }}
QPushButton#DialogSecondary {{
    background-color: {surface_alt};
    color: {text};
    padding: 8px 20px;
}}
"""


def _mix(base: str, mixer: str, amount: float) -> str:
    """Blend two ``#rrggbb`` colours; ``amount`` is the share of ``mixer``."""
    def parse(colour: str) -> tuple[int, int, int]:
        colour = colour.lstrip("#")
        if len(colour) == 3:
            colour = "".join(ch * 2 for ch in colour)
        return int(colour[0:2], 16), int(colour[2:4], 16), int(colour[4:6], 16)

    def clamp(value: float) -> int:
        return max(0, min(255, int(round(value))))

    r1, g1, b1 = parse(base)
    r2, g2, b2 = parse(mixer)
    return "#{:02x}{:02x}{:02x}".format(
        clamp(r1 + (r2 - r1) * amount),
        clamp(g1 + (g2 - g1) * amount),
        clamp(b1 + (b2 - b1) * amount),
    )


def build_stylesheet(theme: Theme, appearance) -> str:
    """Render the application stylesheet.

    :param theme: the selected :class:`Theme`.
    :param appearance: a :class:`calc.gui.settings.Appearance` instance.
    """
    palette = theme.palette
    if appearance.accent_color:
        palette = replace(palette, equals=appearance.accent_color)

    hover = 0.10 if theme.is_dark else 0.06
    press = 0.18 if theme.is_dark else 0.12
    mixer = palette.hover_mix

    def variants(colour: str) -> tuple[str, str]:
        return _mix(colour, mixer, hover), _mix(colour, mixer, press)

    digit_hover, digit_pressed = variants(palette.digit)
    operator_hover, operator_pressed = variants(palette.operator)
    function_hover, function_pressed = variants(palette.function)
    clear_hover, clear_pressed = variants(palette.clear)
    memory_hover, memory_pressed = variants(palette.memory)
    equals_hover, equals_pressed = variants(palette.equals)

    scale = max(0.6, float(appearance.ui_scale))
    values = {
        "theme_name": theme.name,
        "bg": palette.background,
        "border": palette.border,
        "surface": palette.surface,
        "surface_alt": palette.surface_alt,
        "text": palette.text,
        "text_muted": palette.text_muted,
        "display_bg": palette.display_bg,
        "display_text": palette.display_text,
        "display_muted": palette.display_muted,
        "display_error": palette.display_error,
        "font_family": appearance.font_family or theme.font_family,
        "mono_family": theme.mono_family,
        "radius": int(appearance.corner_radius),
        "radius_small": max(2, int(appearance.corner_radius) - 4),
        "badge_radius": max(2, int(appearance.corner_radius) - 8),
        "spacing": int(appearance.spacing),
        "key_height": int(appearance.key_height * scale),
        "key_font": int(appearance.key_font_size * scale),
        "op_font": int((appearance.key_font_size + 4) * scale),
        "fn_font": int(max(8, appearance.key_font_size - 3) * scale),
        "expr_size": int(13 * scale),
        "result_size": int(appearance.result_font_size * scale),
        "hint_size": int(11 * scale),
        "list_font": int(12 * scale),
        "heading_size": int(14 * scale),
        "digit": palette.digit,
        "digit_text": palette.digit_text,
        "digit_hover": digit_hover,
        "digit_pressed": digit_pressed,
        "operator": palette.operator,
        "operator_text": palette.operator_text,
        "operator_hover": operator_hover,
        "operator_pressed": operator_pressed,
        "function": palette.function,
        "function_text": palette.function_text,
        "function_hover": function_hover,
        "function_pressed": function_pressed,
        "clear": palette.clear,
        "clear_text": palette.clear_text,
        "clear_hover": clear_hover,
        "clear_pressed": clear_pressed,
        "memory": palette.memory,
        "memory_text": palette.memory_text,
        "memory_hover": memory_hover,
        "memory_pressed": memory_pressed,
        "equals": palette.equals,
        "equals_text": palette.equals_text,
        "equals_hover": equals_hover,
        "equals_pressed": equals_pressed,
        "scrollbar": palette.scrollbar,
    }
    return _QSS_TEMPLATE.format(**values)


def build_palette(theme: Theme):
    """Return a :class:`QPalette` matching the theme.

    The stylesheet styles almost everything, but a handful of native elements
    (menu bar tear-offs, some platform widgets) fall back to the application
    palette.  Setting both keeps light and dark themes fully consistent.
    """
    from PySide6.QtGui import QColor, QPalette

    palette = QPalette()
    p = theme.palette

    def c(value: str) -> QColor:
        return QColor(value)

    palette.setColor(QPalette.Window, c(p.background))
    palette.setColor(QPalette.WindowText, c(p.text))
    palette.setColor(QPalette.Base, c(p.display_bg))
    palette.setColor(QPalette.AlternateBase, c(p.surface_alt))
    palette.setColor(QPalette.Text, c(p.text))
    palette.setColor(QPalette.PlaceholderText, c(p.text_muted))
    palette.setColor(QPalette.Button, c(p.digit))
    palette.setColor(QPalette.ButtonText, c(p.digit_text))
    palette.setColor(QPalette.Highlight, c(p.equals))
    palette.setColor(QPalette.HighlightedText, c(p.equals_text))
    palette.setColor(QPalette.Link, c(p.equals))
    palette.setColor(QPalette.LinkVisited, c(p.function_text))
    palette.setColor(QPalette.ToolTipBase, c(p.surface_alt))
    palette.setColor(QPalette.ToolTipText, c(p.text))
    palette.setColor(QPalette.BrightText, c(p.equals_text))
    disabled = QPalette.ColorGroup.Disabled
    palette.setColor(disabled, QPalette.Text, c(p.text_muted))
    palette.setColor(disabled, QPalette.ButtonText, c(p.text_muted))
    palette.setColor(disabled, QPalette.WindowText, c(p.text_muted))
    return palette
