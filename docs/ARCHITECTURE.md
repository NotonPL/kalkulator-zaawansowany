# Architecture

python-calculator is deliberately split into three layers with a strict dependency direction:

```
calc/core   (pure Python, no Qt)   <-  calc/gui   (PySide6)
             ^
             `--  calc/cli   (pure Python REPL)
```

The **core** owns every mathematical and persistence decision; the **gui** and **cli** are two
thin front ends over the same `CalculatorEngine`. That is why a calculation typed on a phone in
Termux behaves exactly like one typed in the Qt window.

## Layer map

```
calc/
├── core/
│   ├── lexer.py        text -> tokens (unicode aliases, implicit-multiplication *not* here)
│   ├── parser.py       tokens -> AST (recursive descent; implicit multiplication, arity-less calls)
│   ├── evaluator.py    AST -> float  (angle conversion, domain/overflow errors)
│   ├── functions.py    the single source of truth for functions & constants
│   ├── errors.py       CalcError hierarchy with character positions
│   ├── formatter.py    number rendering (grouping, precision, scientific, pretty-print)
│   ├── normalize.py    input repair (auto-close parens, strip dangling operators)
│   ├── history.py      persistent, bounded calculation history (JSON)
│   ├── memory.py       ten memory registers (JSON)
│   └── engine.py       CalculatorEngine facade + data-directory resolution
├── cli.py              terminal REPL + argparse one-shot mode
└── gui/
    ├── themes.py       Palette/Theme dataclasses -> stylesheet + QPalette
    ├── settings.py     Appearance/Behaviour dataclasses with safe JSON persistence
    ├── i18n.py         dict-based translator over i18n/*.json
    ├── widgets.py      RippleButton (hand-painted) + font-shrink helper
    ├── display.py      expression/result/hint with error state, shake & flash
    ├── keypad.py       data-driven keypad layouts
    ├── side_panel.py   history / memory / function browser tabs
    ├── settings_dialog.py  live-preview settings editor
    ├── main_window.py  window + input buffer + intent routing
    └── app.py          window construction & icon
```

## Design decisions

### The expression engine is a real compiler, never `eval()`

User text goes through *lexer → parser → evaluator*. This gives us three things for free:

1. **Safety** -- `tests/test_evaluator.py` asserts that `__import__('os')`, `open(...)`,
   `().__class__`, `eval('1')`, etc. all raise `CalcError` instead of executing.
2. **Precise errors** -- every token and AST node carries its offset in the source, so the GUI
   can point at the offending character and the CLI can print a caret marker.
3. **Friendly input** -- the lexer normalises `÷ × − √ ² π` and the parser accepts implicit
   multiplication (`2π`, `3(4+1)`) and parenthesis-less calls (`√16`, `sin30`).

### Implicit multiplication lives in the *parser*, not the lexer

A naive lexer that inserts `*` would turn `sin(30)` into `sin * (30)`. By deciding in the parser,
after knowing whether a `NAME` is followed by `(`, we keep function calls intact.

### Functions are data

`calc/core/functions.py` registers each callable as a `FunctionSpec` (name, arity, impl,
angularity, aliases, description). The GUI function browser, the CLI `fn` command and the docs
all read the same registry, so a function can never be "documented but not implemented".

### Styling is generated, not hand-edited

A `Theme` is a palette plus a few defaults. `build_stylesheet()` renders one Qt stylesheet from
the palette *and* the user's appearance settings (radius, spacing, sizes, accent), so the settings
dialog previews the exact code path that styles the app. `build_palette()` mirrors the theme into
a `QPalette` for the few native widgets QSS can't reach.

### Settings, history and memory are plain JSON

No database, no platform services -- the app must run on an Android filesystem with only the
standard library. Every loader is forgiving: unknown keys are ignored and out-of-range values are
clamped, so a corrupt or future-version file can never prevent startup.

## Data locations

`calc/core/engine.data_directory()` resolves (in order) an explicit override,
`$PYTHON_CALCULATOR_HOME`, `$XDG_DATA_HOME`, then the per-OS default. Tests always point it at a
temporary directory via the `PYTHON_CALCULATOR_HOME` environment variable.
