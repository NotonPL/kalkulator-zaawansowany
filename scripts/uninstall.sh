#!/usr/bin/env bash
# Remove everything scripts/install.sh created. User data (history, settings)
# is left untouched on purpose.
set -euo pipefail

PREFIX="${CALC_PREFIX:-$HOME/.local}"
info() { printf '\033[1;34m[pycalc]\033[0m %s\n' "$*"; }

rm -rf "$PREFIX/share/python-calculator"
rm -f  "$PREFIX/bin/pycalc"
info "Removed $PREFIX/share/python-calculator and $PREFIX/bin/pycalc"
info "Your data (history, memory, settings) is still in ~/.local/share/python-calculator"
