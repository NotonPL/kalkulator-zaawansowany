#!/usr/bin/env bash
#
# install.sh -- one-command installer for python-calculator.
#
# Works two ways:
#   public repo :  curl -fsSL <raw-url>/scripts/install.sh | bash
#   private repo:  bash <(curl -fsSL -H "Authorization: Bearer $TOKEN" <raw-url>/scripts/install.sh)
#   from a clone:  bash scripts/install.sh
#
# Environment:
#   GITHUB_TOKEN   optional token used to clone a *private* repository.
#   CALC_REPO      override the repo URL (defaults to the origin of this repo).
#   CALC_PREFIX    install prefix (default: ~/.local).
#
set -euo pipefail

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
info()  { printf '\033[1;34m[pycalc]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[pycalc]\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31m[pycalc]\033[0m %s\n' "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

REPO_URL="${CALC_REPO:-https://github.com/NotonPL/kalkulator-zaawansowany.git}"
PREFIX="${CALC_PREFIX:-$HOME/.local}"
VENV_DIR="$PREFIX/share/python-calculator/venv"
APP_DIR="$PREFIX/share/python-calculator/src"
BIN_DIR="$PREFIX/bin"
LAUNCHER="$BIN_DIR/pycalc"

# ---------------------------------------------------------------------------
# 1. prerequisites
# ---------------------------------------------------------------------------
command_exists python3 || fail "python3 is required but was not found."
PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
info "Using Python $PYV"

# Termux / Android detection -- there we install the CLI-only flavour.
IS_TERMUX=0
if [ -n "${PREFIX:-}" ] && [ "${TERMUX_VERSION:-}" != "" ]; then IS_TERMUX=1; fi
if [ -d "/data/data/com.termux/files/usr" ]; then IS_TERMUX=1; fi
if [ "$(uname -o 2>/dev/null || true)" = "Android" ]; then IS_TERMUX=1; fi

HAS_DISPLAY=0
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then HAS_DISPLAY=1; fi

# ---------------------------------------------------------------------------
# 2. obtain the source (skip if we are already inside a checkout)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd || true)"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
    SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    info "Detected an existing checkout at $SRC_DIR -- reusing it."
else
    command_exists git || fail "git is required to download the app (or run this from a checkout)."
    SRC_DIR="$APP_DIR"
    CLONE_URL="$REPO_URL"
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        CLONE_URL="$(echo "$REPO_URL" | sed "s#https://#https://x-access-token:${GITHUB_TOKEN}@#")"
    fi
    info "Cloning $REPO_URL ..."
    rm -rf "$SRC_DIR"
    mkdir -p "$(dirname "$SRC_DIR")"
    git clone --depth 1 "$CLONE_URL" "$SRC_DIR" || fail "clone failed (private repo? set GITHUB_TOKEN)"
fi

# ---------------------------------------------------------------------------
# 3. isolated environment
# ---------------------------------------------------------------------------
info "Creating a virtual environment at $VENV_DIR ..."
mkdir -p "$PREFIX/share/python-calculator"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    python3 -m venv "$VENV_DIR" || fail "could not create a venv (is python3-venv installed?)"
fi
VENV_PY="$VENV_DIR/bin/python"

info "Installing python-calculator ..."
if [ "$IS_TERMUX" = "1" ] || [ "$HAS_DISPLAY" = "0" ]; then
    warn "No graphical session detected (or running on Termux) -- installing the CLI flavour."
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet "$SRC_DIR"
else
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet "$SRC_DIR[gui]"
fi

# ---------------------------------------------------------------------------
# 4. launcher on PATH
# ---------------------------------------------------------------------------
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_PY" -m calc "\$@"
EOF
chmod +x "$LAUNCHER"
info "Launcher written to $LAUNCHER"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        warn "$BIN_DIR is not on your PATH. Add this line to your shell profile:"
        warn "    export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac

# ---------------------------------------------------------------------------
# 5. done
# ---------------------------------------------------------------------------
info "Installation complete."
if [ "$IS_TERMUX" = "1" ] || [ "$HAS_DISPLAY" = "0" ]; then
    info "Start it with:  $LAUNCHER cli   (or simply: pycalc)"
else
    info "Start it with:  pycalc"
fi
