#!/usr/bin/env bash
#
# how installer - fast, minimalist installation script
# https://github.com/mdsyseng/how
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

# 3. Source detection: local repo or GitHub download
REPO_RAW_URL="https://raw.githubusercontent.com/mdsyseng/how/main/how"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/how" ]; then
  # Local copy if running inside cloned repository
  if [ "$SCRIPT_DIR/how" != "$TARGET" ]; then
    cp "$SCRIPT_DIR/how" "$TARGET.tmp"
  fi
else
  # Remote download via curl or wget
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$REPO_RAW_URL" -o "$TARGET.tmp" || abort "Failed to download how from GitHub ($REPO_RAW_URL)"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET.tmp" "$REPO_RAW_URL" || abort "Failed to download how from GitHub ($REPO_RAW_URL)"
  else
    abort "Neither curl nor wget found to download how."
  fi
fi

if [ -f "$TARGET.tmp" ]; then
  if [ ! -s "$TARGET.tmp" ]; then
    rm -f "$TARGET.tmp"
    abort "Installed binary file is empty."
  fi
  chmod +x "$TARGET.tmp"
  mv -f "$TARGET.tmp" "$TARGET"
else
  chmod +x "$TARGET"
fi

# 4. Verify installation
if ! "$TARGET" --help >/dev/null 2>&1; then
  abort "Installation verification failed ($TARGET --help failed)."
fi

success "Installed how to $TARGET"

# 5. Check PATH
case ":$PATH:" in
  *":$BIN_DIR:"*)
    ;;
  *)
    CURRENT_SHELL="$(basename "${SHELL:-bash}")"
    case "$CURRENT_SHELL" in
      zsh)  RC_FILE="~/.zshrc" ;;
      fish) RC_FILE="~/.config/fish/config.fish" ;;
      *)    RC_FILE="~/.bashrc" ;;
    esac

    echo
    warn "$BIN_DIR is not in your \$PATH"
    if [ "$CURRENT_SHELL" = "fish" ]; then
      info "Add it by running:"
      info "  fish_add_path $BIN_DIR"
    else
      info "Add it to $RC_FILE:"
      info "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
    info "Then reload your shell: exec \$SHELL"
    ;;
esac
