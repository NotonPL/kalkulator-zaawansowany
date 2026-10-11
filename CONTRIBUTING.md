# Contributing to python-calculator

Thanks for taking the time to contribute! 🎉

## Ground rules

- Be kind. See the [code of conduct](CODE_OF_CONDUCT.md).
- Keep the **core engine Qt-free** (`calc/core/` must never import PySide6) so the
  CLI keeps working on phones and servers.
- New functions belong in `calc/core/functions.py` — the UI, docs and CLI pick them
  up automatically.
- Every new behaviour needs a test in `tests/`.

## Getting started

```bash
git clone https://github.com/NotonPL/kalkulator-zaawansowany.git
cd python-calculator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[gui,dev]"
pytest
```

The GUI tests run headless (offscreen Qt), so they work in CI and on a plain server.

## Pull requests

1. Fork and create a branch from `main` (`feature/...` / `fix/...`).
2. Write or update tests; make `pytest` green.
3. If you touched the UI, regenerate the screenshots:
   `QT_QPA_PLATFORM=offscreen python scripts/make_screenshots.py`.
4. If you added a translatable string, add it to **both** `i18n/en.json` and `i18n/pl.json`
   (a CI test enforces completeness).
5. Keep commits small and describe *why*, not just *what*.

## Adding a theme

See [`docs/THEMING.md`](docs/THEMING.md). A theme is one `Theme` dataclass appended to
`BUILTIN_THEMES` in `calc/gui/themes.py`.

## Reporting bugs

Use the *Bug report* issue template and include the version (`pycalc --version`), the
platform (desktop / Termux) and the exact expression that misbehaves.
