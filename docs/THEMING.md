# Theming guide

Every pixel of python-calculator is derived from a small, typed palette. This document shows how
to read, tweak and create themes.

## What a theme is

```python
from calc.gui.themes import Palette, Theme

my_theme = Theme(
    name="Ocean",
    is_dark=True,
    radius=16,
    palette=Palette(
        background="#0b1620",
        surface="#10202e",
        digit="#173042",
        digit_text="#e6f1ff",
        operator="#1d3a52",
        operator_text="#7dd3fc",
        equals="#0ea5e9",
        equals_text="#04121c",
        # ... every field has a sensible default; override only what you need
    ),
)
```

Append it to `BUILTIN_THEMES` in `calc/gui/themes.py` and it immediately appears in the theme
picker, the toolbar and the `View → Theme` menu. No stylesheet editing required.

## Palette roles

| Field | Used for |
| ----- | -------- |
| `background` / `surface` / `surface_alt` | window, panels, inputs |
| `text` / `text_muted` | labels, menus, status bar |
| `display_*` | the expression/result area and its error state |
| `digit*` / `operator*` / `function*` | the three key families |
| `clear*` | `C` / `⌫` |
| `equals*` | the accent: `=` key, selections, sliders, focus rings |
| `memory*` | memory keys and the `M` badge |
| `hover_mix` | colour blended into keys on hover/press (white on dark, black on light) |
| `ripple` | the touch ripple colour |

## User appearance settings

On top of the palette, every user preference is multiplied into the generated stylesheet:

- `corner_radius` — button / panel roundness (`0`..`32`)
- `spacing` — gap between keys
- `key_height`, `key_font_size`, `result_font_size`
- `ui_scale` — global scale factor
- `accent_color` — overrides the theme's `equals` accent
- `font_family` — overrides the theme font

Both the application and the *live preview* in the settings dialog consume the same
`build_stylesheet(theme, appearance)` output, so what you preview is exactly what you get.

## Light vs dark

Set `is_dark=False` for light themes. The only behavioural difference is the hover blend strength
and the default `hover_mix` (black), which keeps light keys from glowing.

## Accessibility

The bundled **High Contrast** theme demonstrates the extremes: pure black background, white text,
yellow operators and `=`, and no rounded corners. Use it as the reference when you need a theme
that stays readable at low vision.

## Regenerating screenshots

After adding a theme, update the README gallery:

```bash
QT_QPA_PLATFORM=offscreen python scripts/make_screenshots.py
```
