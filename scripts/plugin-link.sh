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
  local src target current

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
      log "ok: $target already links to $src"
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
    log "skip: $target exists and is not a symlink (script install?); leaving it. Remove it, then re-enable the plugin, to let the plugin manage how"
    return 0
  fi

  mkdir -p "$bin_dir"
  ln -sfn "$src" "$target.plugin-tmp"
  mv -fT "$target.plugin-tmp" "$target"
  log "linked: $target -> $src"
}

log() {
  local line
  line="$(date -u +%Y-%m-%dT%H:%M:%SZ) how-plugin $*"
  printf '%s\n' "$line"
  { mkdir -p "$(dirname "$log_file")" && printf '%s\n' "$line" >>"$log_file"; } 2>/dev/null || true
}

log_file=/dev/null
main "$@"
