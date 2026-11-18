#!/usr/bin/env bash
#
# how installer - fast, minimalist installation script
# https://github.com/mtudls/how
#

set -euo pipefail

# ANSI color codes (respect NO_COLOR)
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN="\033[0;32m"
  YELLOW="\033[0;33m"
  RED="\033[0;31m"
  RESET="\033[0m"
else
  GREEN=""
  YELLOW=""
  RED=""
  RESET=""
fi

info() {
  printf "  %s\n" "$*"
}

success() {
  printf "${GREEN}✓${RESET} %s\n" "$*"
}

warn() {
  printf "${YELLOW}!${RESET} %s\n" "$*"
}

error() {
  printf "${RED}✗${RESET} %s\n" "$*" >&2
}

abort() {
  error "$*"
  exit 1
}

# 1. Check Python 3 (3.8+)
if ! command -v python3 >/dev/null 2>&1; then
  abort "python3 is required but not installed."
fi

PYTHON_VERSION_OK=$(python3 -c "import sys; print('yes' if sys.version_info >= (3, 8) else 'no')" 2>/dev/null || echo "no")
if [ "$PYTHON_VERSION_OK" != "yes" ]; then
  CURRENT_PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
  abort "python3 version 3.8 or higher is required (found ${CURRENT_PY_VER})."
fi

# 2. Target bin directory
BIN_DIR="${HOW_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
TARGET="$BIN_DIR/how"

# 3. Source detection: local repo checkout (copy ./how) or download from a tagged GitHub release
HOW_VERSION="${HOW_VERSION:-v0.6.6}"
REPO_RAW_URL="https://raw.githubusercontent.com/mtudls/how/${HOW_VERSION}/how"
# When piped (`curl ... | bash`) there is no script file, so never treat the cwd as a checkout.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
fi
# `--python-only` / HOW_PYTHON_ONLY are accepted for backward compatibility and ignored:
# the installer always installs the plain Python script.
for arg in "$@"; do
  case "$arg" in
    --python-only) ;;
    *) warn "Ignoring unknown argument: $arg" ;;
  esac
done

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/how" ]; then
  if [ "$SCRIPT_DIR/how" != "$TARGET" ]; then
    cp "$SCRIPT_DIR/how" "$TARGET.tmp"
  fi
else
  # Remote download via curl or wget
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$REPO_RAW_URL" -o "$TARGET.tmp" || { rm -f "$TARGET.tmp"; abort "Failed to download how ${HOW_VERSION} from GitHub ($REPO_RAW_URL)"; }
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET.tmp" "$REPO_RAW_URL" || { rm -f "$TARGET.tmp"; abort "Failed to download how ${HOW_VERSION} from GitHub ($REPO_RAW_URL)"; }
  else
    abort "Neither curl nor wget found to download how."
  fi
fi

if [ -f "$TARGET.tmp" ]; then
  if [ ! -s "$TARGET.tmp" ]; then
    rm -f "$TARGET.tmp"
    abort "Installed file is empty."
  fi
  chmod +x "$TARGET.tmp"
  if [ -L "$TARGET" ]; then
    rm -f "$TARGET"
  fi
  mv -f "$TARGET.tmp" "$TARGET"
else
  chmod +x "$TARGET"
fi

# 4. Verify installation & clean up any legacy `om` symlink pointing to `how`
if ! "$TARGET" --help >/dev/null 2>&1; then
  abort "Installation verification failed ($TARGET --help failed)."
fi

if [ -L "$BIN_DIR/om" ] && [ "$(readlink "$BIN_DIR/om" 2>/dev/null)" = "$TARGET" ]; then
  rm -f "$BIN_DIR/om"
fi

success "Installed how to $TARGET"

# 5. Check PATH
case ":$PATH:" in
  *":$BIN_DIR:"*)
    ;;
  *)
    CURRENT_SHELL="$(basename "${SHELL:-bash}")"
    case "$CURRENT_SHELL" in
      zsh)  RC_FILE="$HOME/.zshrc" ;;
      fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
      *)    RC_FILE="$HOME/.bashrc" ;;
    esac

    echo
    warn "$BIN_DIR is not in your \$PATH"
    if [ "$CURRENT_SHELL" = "fish" ]; then
      info "Add it by running:"
      info "  fish_add_path $BIN_DIR"
    else
      info "Add it to $RC_FILE:"
      info "  export PATH=\"$BIN_DIR:\$PATH\""
    fi
    info "Then reload your shell: exec \$SHELL"
    ;;
esac
