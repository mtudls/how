#!/usr/bin/env bash
#
# plugin-link.sh - run by Service.qml when the `how` Omarchy plugin is enabled.
#
#   bash scripts/plugin-link.sh <plugin-dir>
#
# Makes ~/.local/bin/how a symlink to <plugin-dir>/how, so `omarchy plugin
# update` (a fast-forward of the plugin checkout) also updates the `how` CLI.
#
# Rules: no network, no sudo, idempotent, every decision is logged (stdout, which
# the shell's console shows, and ${XDG_STATE_HOME:-~/.local/state}/how/plugin.log).
# It never replaces a regular file or a symlink it does not recognise, and it
# steps aside when a packaged /usr/bin/how exists.

set -euo pipefail

main() {
  local plugin_dir="${1:-}"
  local bin_dir="${HOW_PLUGIN_BIN_DIR:-$HOME/.local/bin}"
  local state_dir="${HOW_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/how}"
  local src target current changed=""

  log_file="$state_dir/plugin.log"

  [ -n "$plugin_dir" ] || { log "error: no plugin dir given; nothing done"; return 1; }
  plugin_dir="${plugin_dir%/}"
  src="$plugin_dir/how"
  target="$bin_dir/how"

  if [ ! -f "$src" ]; then
    log "error: $src not found; nothing done"
    return 1
  fi
  [ -x "$src" ] || chmod u+x "$src" 2>/dev/null || true

  if [ -e /usr/bin/how ]; then
    log "skip: /usr/bin/how exists (package install, upgraded by omarchy update); not linking $target"
    return 0
  fi

  if [ -L "$target" ]; then
    current="$(readlink "$target" || true)"
    if [ "$current" = "$src" ]; then
      # Print only (no log file line): this runs at every shell start.
      printf '%s\n' "how-plugin ok: $target already links to $src"
      return 0
    fi
    case "$current" in
      */omarchy/plugins/*/how)
        # A link we made earlier for another checkout of this plugin: repoint it.
        log "relink: $target was -> $current" ;;
      *)
        if [ -e "$target" ]; then
          log "skip: $target is a symlink to $current, not ours; leaving it"
          return 0
        fi
        log "relink: $target was a dangling symlink -> $current" ;;
    esac
  elif [ -e "$target" ]; then
    if [ -f "$target" ] && is_legacy_copy "$target" "$state_dir/install-receipt"; then
      # Plugin versions before 1.0.0 copied `how` here instead of linking it, so
      # it never updated. Keep that copy next to it and switch to the link.
      mv -f "$target" "$target.pre-plugin-link"
      log "migrate: moved the old copied $target to $target.pre-plugin-link"
      changed="replaced an old copy (kept as $target.pre-plugin-link)"
    else
      log "skip: $target exists and is not a symlink (script install?); leaving it. To let the plugin manage how: install.sh --uninstall, then disable and re-enable the plugin"
      return 0
    fi
  fi

  mkdir -p "$bin_dir"
  ln -sfn "$src" "$target.plugin-tmp"
  mv -fT "$target.plugin-tmp" "$target"
  log "linked: $target -> $src"
  notify "how is now linked from the Omarchy plugin${changed:+ ($changed)}: $target"
}

# A regular file that is a `how` script (defines __version__) and was NOT put
# there by install.sh (whose receipt names it) is a copy made by the old plugin.
is_legacy_copy() {
  local file="$1" receipt="$2"
  grep -q '^__version__ *= *' "$file" 2>/dev/null || return 1
  head -n 1 "$file" | grep -q python || return 1
  if [ -f "$receipt" ] && grep -qxF "path=$file" "$receipt"; then
    return 1
  fi
  return 0
}

# Best-effort desktop notification, only when something changed.
notify() {
  command -v notify-send >/dev/null 2>&1 || return 0
  notify-send -a how "how" "$*" >/dev/null 2>&1 || true
}

log() {
  local line
  line="$(date -u +%Y-%m-%dT%H:%M:%SZ) how-plugin $*"
  printf '%s\n' "$line"
  { mkdir -p "$(dirname "$log_file")" && printf '%s\n' "$line" >>"$log_file"; } 2>/dev/null || true
}

log_file=/dev/null
main "$@"
