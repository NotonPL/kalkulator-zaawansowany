# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-11

### Added

- Safe expression engine: lexer + recursive-descent parser + AST evaluator (no `eval()`), with
  implicit multiplication, unicode operators, radix literals and parenthesis-less calls.
- Standard and Scientific keypads with ripple animation and live themable keys.
- 8 built-in themes (Midnight, Light, Nord, Dracula, Solarized, Graphite, Sakura, High Contrast)
  plus custom accent, font, radius, spacing, sizes and scale -- all live-previewed and persisted.
- Searchable persistent history and ten memory registers.
- Angle units (rad/deg/grad), number formatting options and a hex/oct/bin hint.
- Terminal (CLI) mode that runs without Qt, suited to Termux/Android.
- English and Polish localisation.
- One-command installer (`scripts/install.sh`) and uninstaller.
- 305 unit and GUI tests, all runnable headless; CI workflow.

[1.0.0]: https://github.com/NotonPL/kalkulator-zaawansowany/releases/tag/v1.0.0
