#!/usr/bin/env bash
#
# install.sh - install, upgrade or remove `how` for the current user.
# https://github.com/mtudls/how
#
#   curl -fsSL https://github.com/mtudls/how/releases/latest/download/install.sh | bash
#   curl -fsSL https://github.com/mtudls/how/releases/latest/download/install.sh | bash -s -- --dry-run
#   curl -fsSL https://github.com/mtudls/how/releases/latest/download/install.sh | bash -s -- --uninstall
#
# What it does, and nothing more:
#   1. downloads `how` and SHA256SUMS.txt for ONE pinned release tag from GitHub,
#   2. refuses to continue unless the sha256 of `how` matches SHA256SUMS.txt,
#   3. atomically places it at ${HOW_INSTALL_DIR:-$HOME/.local/bin}/how,
#   4. writes a small receipt to ${XDG_STATE_HOME:-$HOME/.local/state}/how/install-receipt
#      so --uninstall removes exactly that file and nothing else.
# It never uses sudo, never edits your shell rc files, and installs no cron
# job, hook or background updater. Upgrades happen only when you run it again
# (or `how update`, which asks first and then runs it).
#
# Everything lives inside main(), called on the last line, so a truncated
# `curl | bash` download cannot run half a script.

set -euo pipefail

HOW_DEFAULT_VERSION="v1.0.0"
HOW_REPO="mtudls/how"

main() {
  local mode="install" dry_run=0 force=0 purge=0 local_src=0

  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run|-n) dry_run=1 ;;
      --uninstall) mode="uninstall" ;;
      --purge) purge=1 ;;
      --force) force=1 ;;
      --local) local_src=1 ;;
      --version)
        [ $# -ge 2 ] || die "--version needs a tag, e.g. --version v1.0.0"
        HOW_VERSION="$2"
        shift
        ;;
      -h|--help) usage; return 0 ;;
      *) die "unknown option: $1 (see --help)" ;;
    esac
    shift
  done

  setup_colors

  local install_dir state_dir receipt
  install_dir="${HOW_INSTALL_DIR:-$HOME/.local/bin}"
  install_dir="${install_dir%/}"
  state_dir="${HOW_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/how}"
  receipt="$state_dir/install-receipt"

  if [ "$mode" = "uninstall" ]; then
    uninstall "$install_dir" "$state_dir" "$receipt" "$dry_run" "$purge"
  else
    [ "$purge" -eq 0 ] || die "--purge only makes sense with --uninstall"
    do_install "$install_dir" "$receipt" "$dry_run" "$force" "$local_src"
  fi
}

usage() {
  cat <<'EOF'
Usage: install.sh [--dry-run] [--force] [--version vX.Y.Z] [--local]
       install.sh --uninstall [--purge] [--dry-run]

Installs `how` for the current user, verified against the release's SHA256SUMS.txt.

  --dry-run, -n      show what would happen; downloads and verifies into a temp
                     dir but writes nothing outside it
  --version TAG      release tag to install (default: the tag this installer
                     shipped with; same as HOW_VERSION=TAG; "latest" asks GitHub)
  --force            replace an existing `how` that this installer did not put
                     there, or install even though /usr/bin/how exists
  --local            install ./how from the git checkout next to this script
                     (for development; no download, no checksum)
  --uninstall        remove the `how` this installer installed
  --purge            with --uninstall: also delete config (API key) and log/state

Environment:
  HOW_VERSION        release tag to install (same as --version)
  HOW_INSTALL_DIR    target directory (default: ~/.local/bin)
  HOW_CONFIG_DIR, HOW_STATE_DIR, XDG_CONFIG_HOME, XDG_STATE_HOME  (for --purge)
  NO_COLOR           disable colors
EOF
  printf '\nThis installer installs %s by default.\n' "$HOW_DEFAULT_VERSION"
}

# ---------------------------------------------------------------- output

setup_colors() {
  if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'; C_ERR=$'\033[0;31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
  else
    C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_OFF=""
  fi
}

say()  { printf '%s\n' "$*"; }
step() { printf '%s→%s %s\n' "${C_DIM:-}" "${C_OFF:-}" "$*"; }
ok()   { printf '%s✓%s %s\n' "${C_OK:-}" "${C_OFF:-}" "$*"; }
warn() { printf '%s!%s %s\n' "${C_WARN:-}" "${C_OFF:-}" "$*" >&2; }
die()  { printf '%s✗%s %s\n' "${C_ERR:-}" "${C_OFF:-}" "$*" >&2; exit 1; }

# ---------------------------------------------------------------- helpers

need() { command -v "$1" >/dev/null 2>&1; }

check_python() {
  need python3 || die "python3 is required (on Arch/Omarchy: sudo pacman -S python)."
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null ||
    die "Python >= 3.9 is required (found $(python3 -V 2>&1))."
}

# fetch URL FILE
fetch() {
  if need curl; then
    curl -fsSL --proto '=https' --tlsv1.2 --retry 2 -o "$2" "$1"
  elif need wget; then
    wget -q --https-only -O "$2" "$1"
  else
    die "need curl or wget to download how."
  fi
}

sha256_of() {
  sha256sum "$1" | awk '{print $1}'
}

resolve_version() {
  local v="${HOW_VERSION:-$HOW_DEFAULT_VERSION}" api tmp
  if [ "$v" = "latest" ]; then
    api="https://api.github.com/repos/$HOW_REPO/releases/latest"
    tmp="$(mktemp)"
    fetch "$api" "$tmp" || { rm -f "$tmp"; die "could not ask GitHub for the latest release ($api)."; }
    v="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag_name"])' "$tmp" 2>/dev/null || true)"
    rm -f "$tmp"
    [ -n "$v" ] || die "could not read the latest release tag from $api."
  fi
  case "$v" in v*) ;; *) v="v$v" ;; esac
  if ! printf '%s' "$v" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'; then
    die "invalid version '$v' (expected a tag like v1.0.0)."
  fi
  printf '%s' "$v"
}

# Is FILE a `how` script we may replace? (a Python file that defines __version__)
looks_like_how() {
  [ -f "$1" ] && grep -q '^__version__ *= *' "$1" 2>/dev/null &&
    head -n 1 "$1" | grep -q python
}

path_hint() {
  local dir="$1"
  case ":$PATH:" in
    *":$dir:"*) return 0 ;;
  esac
  say ""
  warn "$dir is not on your PATH yet. Add it (this installer does not edit your shell files):"
  case "$(basename "${SHELL:-bash}")" in
    fish) say "    fish_add_path $dir" ;;
    zsh)  say "    echo 'export PATH=\"$dir:\$PATH\"' >> ~/.zshrc && exec zsh" ;;
    *)    say "    echo 'export PATH=\"$dir:\$PATH\"' >> ~/.bashrc && exec bash" ;;
  esac
}

# ---------------------------------------------------------------- install

do_install() {
  local install_dir="$1" receipt="$2" dry_run="$3" force="$4" local_src="$5"
  local target="$install_dir/how" version tmp sums expected actual reported

  check_python
  if [ "$(id -u)" -eq 0 ]; then
    warn "running as root: this installs for root only ($install_dir). No sudo is needed for your own user."
  fi

  # Refuse to silently shadow a packaged /usr/bin/how.
  if [ -e /usr/bin/how ] && [ "$target" != "/usr/bin/how" ]; then
    if [ "$force" -eq 1 ]; then
      warn "/usr/bin/how exists (package). $target will take precedence if $install_dir comes first on PATH."
    else
      say "/usr/bin/how already exists, most likely from the how-omarchy package,"
      say "which upgrades with 'omarchy update'. A second copy in $install_dir would"
      say "shadow it and stop receiving those upgrades."
      die "not installing. Re-run with --force if you really want a per-user copy."
    fi
  fi

  # Never replace something we do not recognise.
  if [ -L "$target" ]; then
    local link
    link="$(readlink "$target" || true)"
    if [ "$force" -ne 1 ]; then
      case "$link" in
        */omarchy/plugins/*)
          die "$target is a symlink managed by the Omarchy plugin ($link). Update with 'omarchy plugin update', or use --force to replace it." ;;
        *)
          die "$target is a symlink to $link, which this installer did not create. Remove it or use --force." ;;
      esac
    fi
  elif [ -e "$target" ] && ! looks_like_how "$target" && [ "$force" -ne 1 ]; then
    die "$target exists and does not look like how. Not touching it (use --force to replace)."
  fi

  tmp="$(mktemp -d "${TMPDIR:-/tmp}/how-install.XXXXXX")"
  # shellcheck disable=SC2064  # expand $tmp now, on purpose
  trap "rm -rf '$tmp'" EXIT

  if [ "$local_src" -eq 1 ]; then
    local here=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
      here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi
    if [ -z "$here" ] || [ ! -f "$here/how" ]; then
      die "--local needs ./how next to install.sh (run it from a git checkout, not through a pipe)."
    fi
    version="local checkout ($here)"
    cp "$here/how" "$tmp/how"
    warn "--local: installing $here/how without checksum verification."
  else
    need sha256sum || die "sha256sum is not available, so the download cannot be verified. Install coreutils and retry; refusing to install unverified code."
    version="$(resolve_version)"
    local base="https://github.com/$HOW_REPO/releases/download/$version"
    step "Downloading how $version from $base/"
    fetch "$base/how" "$tmp/how" || die "download failed: $base/how"
    fetch "$base/SHA256SUMS.txt" "$tmp/SHA256SUMS.txt" || die "download failed: $base/SHA256SUMS.txt"

    sums="$tmp/SHA256SUMS.txt"
    expected="$(awk '$2 == "how" || $2 == "*how" {print $1; exit}' "$sums")"
    printf '%s' "$expected" | grep -Eq '^[0-9a-f]{64}$' || die "SHA256SUMS.txt has no valid entry for 'how'; refusing to install."
    actual="$(sha256_of "$tmp/how")"
    if [ "$actual" != "$expected" ]; then
      die "checksum mismatch for how $version (expected $expected, got $actual). Nothing was installed."
    fi
    ok "sha256 verified: $actual"
  fi

  [ -s "$tmp/how" ] || die "downloaded file is empty; nothing was installed."
  head -n 1 "$tmp/how" | grep -q python || die "downloaded file is not the how Python script; nothing was installed."
  chmod 755 "$tmp/how"
  reported="$(python3 "$tmp/how" --version 2>/dev/null | head -n 1 || true)"
  [ -n "$reported" ] || die "the downloaded how does not run ('how --version' failed); nothing was installed."

  local action="Install" done_word="Installed"
  if [ -e "$target" ] || [ -L "$target" ]; then
    action="Replace"; done_word="Replaced"
  fi

  if [ "$dry_run" -eq 1 ]; then
    say ""
    say "Dry run - nothing was changed. Would:"
    say "  $action $target   ($reported)"
    say "  write receipt  $receipt"
    path_hint "$install_dir"
    return 0
  fi

  mkdir -p "$install_dir"
  local staged="$install_dir/.how.install.$$"
  cp "$tmp/how" "$staged"
  chmod 755 "$staged"
  mv -f "$staged" "$target"        # atomic rename within the same directory

  mkdir -p "$(dirname "$receipt")"
  {
    printf 'path=%s\n' "$target"
    printf 'version=%s\n' "$version"
    printf 'sha256=%s\n' "$(sha256_of "$target")"
    printf 'installed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$receipt.tmp"
  mv -f "$receipt.tmp" "$receipt"

  ok "$done_word $target ($reported)"
  say "  receipt:   $receipt"
  say "  upgrade:   how update   (or re-run this installer)"
  say "  uninstall: curl -fsSL https://github.com/$HOW_REPO/releases/latest/download/install.sh | bash -s -- --uninstall"
  path_hint "$install_dir"
}

# ---------------------------------------------------------------- uninstall

# act CMD...: run it and say so, or with --dry-run only say what would run.
act() {
  if [ "${DRY_RUN:-0}" -eq 1 ]; then
    say "would run: $*"
  else
    "$@"
    ok "$*"
  fi
}

receipt_get() {
  [ -f "$1" ] || return 0
  awk -F= -v k="$2" '$1 == k {sub(/^[^=]*=/, ""); print; exit}' "$1"
}

uninstall() {
  local install_dir="$1" state_dir="$2" receipt="$3" dry_run="$4" purge="$5"
  local target recorded config_dir
  DRY_RUN="$dry_run"

  # The receipt names what was installed; an explicit HOW_INSTALL_DIR wins.
  if [ -n "${HOW_INSTALL_DIR:-}" ]; then
    target="$install_dir/how"
  else
    target="$(receipt_get "$receipt" path)"
    [ -n "$target" ] || target="$install_dir/how"
  fi

  if [ -L "$target" ]; then
    warn "$target is a symlink ($(readlink "$target")), not a script install - leaving it."
    warn "Plugin installs are removed with: omarchy plugin remove io.github.mdsyseng.how && rm $target"
  elif [ -f "$target" ]; then
    recorded="$(receipt_get "$receipt" sha256)"
    local ours=0
    if [ -n "$recorded" ] && [ "$(sha256_of "$target")" = "$recorded" ]; then
      ours=1
    elif looks_like_how "$target"; then
      ours=1
    fi
    if [ "$ours" -eq 1 ]; then
      act rm -f "$target"
    else
      warn "$target does not look like how; leaving it."
    fi
  else
    say "No script install found at $target."
  fi

  if [ -f "$receipt" ] && [ "$(receipt_get "$receipt" path)" = "$target" ]; then
    act rm -f "$receipt"
  fi

  if [ -e /usr/bin/how ]; then
    say "Note: /usr/bin/how is still there (package). Remove it with: sudo pacman -Rns how-omarchy"
  fi

  config_dir="${HOW_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/how}"
  if [ "$purge" -eq 1 ]; then
    [ ! -d "$config_dir" ] || act rm -rf "$config_dir"
    [ ! -d "$state_dir" ] || act rm -rf "$state_dir"
  else
    say "Kept your config and history (delete them with --purge):"
    say "  $config_dir"
    say "  $state_dir"
  fi
  [ "$dry_run" -eq 0 ] || say "Dry run - nothing was changed."
  return 0
}

main "$@"
