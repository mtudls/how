# Changelog

All notable changes to `how` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-18

A distilled rewrite. `how` is again one small Python file: ask in plain words, get one command with a
safety badge, run it with one keypress. See [docs/DESIGN.md](docs/DESIGN.md) for what was cut and why.

### Added

- Interactive answer prompt: `[Enter] run · [c] copy · [e] explain · [q] quit`.
- Confirmation by badge: Enter runs 🟢, 🟡 needs `y`, 🔴 needs the word `run` and shows the reason.
- `how key` to store the API key (hidden input, file mode 0600).
- `how log [N]` and `how log --path` for the local JSON-lines log in `$XDG_STATE_HOME/how/how.log`
  (rotates at 1 MiB).
- `how privacy`: exactly what is sent, to which host, and every file `how` reads or writes.
- `how doctor`: version, install method, key, API reachability, clipboard tool, log path, update channel.
- `how update`: shows the install channel and how updates arrive; for script installs, re-runs the
  installer after confirmation.
- `how uninstall`: prints (does not run) the removal commands for the current install method.
- Flags `-y/--yes` (auto-run only 🟢), `-n/--no-run`, `--json` (versioned schema, never prompts or runs),
  `--debug`.
- `HOW_API_URL` for any OpenAI-compatible endpoint; `HOW_STATE_DIR` for the state directory.
- AUR package `how-omarchy` (PKGBUILD in this repository; published to the AUR after this release).
- Install script verified against the release's `SHA256SUMS`.
- `SECURITY.md` and `CONTRIBUTING.md`.

### Changed

- Safety levels are `safe`, `modifies` and `dangerous` (was `destructive`). The badge is computed only by
  local rules; unknown commands are 🟡.
- `how good` / `how bad [note]` show exactly what will be sent and ask before sending.
- `how explain [command]` makes one API call and returns a short breakdown with the badge
  (previously an offline rule-based breakdown).
- Each question sends only the question, OS pretty name, shell name and an Omarchy marker, to one host.
- State moved to `$XDG_STATE_HOME/how/` (`how.log`, `last.json`). Config stays in
  `$XDG_CONFIG_HOME/how/config.json` (default `~/.config/how/config.json`).
- Requires Python 3.9 or newer.
- README rewritten; `docs/DESIGN.md` and `docs/PLUGIN.md` replace the old design notes.

### Removed

- Offline reflex engine (`how reflex`, `--offline`, `--reflex`) and all offline answers.
- Python-to-Rust transpiler, native binary and `how build`.
- Context discovery and local documentation lookup (`how context`, `careful`/`yolo`/`dry-run`, `--no-context`).
- SQLite answer cache and repeat-question memory (`how cache`, `--no-cache`).
- Model selection and benchmarking (`how model`, `how model check`), deep-thinking tier (`-t/--think`, `--fast`)
  and triage (`how triage`).
- Explicit state machine engine (`how fsm`, `--trace`).
- Subcommands `how where`, `how fix`, `how status`, `how history`, `how bash-history`, `how verbosity`,
  `how feedback`, `how auth`, `how shell-init`, `how test`, `how !`; verbosity flags `-0` and `--low`.
- Scheduled AI review and self-patching workflows and their documentation (`docs/ASI.md`,
  `docs/ideas.md`, `docs/requirements.md`).

### Migration from 0.6.x

- **Install.** Pick one channel and remove any others; see the README. If you used the Rust build, delete
  the old binary at `~/.local/bin/how` and reinstall.
- **Key and config.** The config file is still `~/.config/how/config.json`. If `how doctor` reports no key,
  run `how key` once.
- **Leftover files you can delete:** `~/.config/how/commands.log`, `~/.config/how/last_answer.json`,
  and the cache directory `~/.cache/how/`.
- **Shell init.** If you added `eval "$(how shell-init bash)"` to your shell rc file, remove that line.
- **Removed commands:**

  | 0.6.x | 1.0.0 |
  |---|---|
  | `how auth login` | `how key` |
  | `how status` | `how doctor` |
  | `how history` | `how log` |
  | `how !` | `how run` |
  | `how feedback "…"` | `how bad "…"` |
  | `how -0 …` | `how -n …` (or pipe the output) |
  | `how fix`, `how where`, `how reflex`, `how context`, `how cache`, `how model`, `how triage`, `how test`, `how build` | removed |

- **Updates.** Run `how update` to see which channel you are on and how it updates. Package installs
  update with `omarchy update`; plugin installs with `omarchy plugin update io.github.mdsyseng.how`.
- **Package name.** The package is `how-omarchy` (`how` and `how-cli` are other projects on the AUR).
  It is published to the AUR after the 1.0.0 release.

## [0.6.6] - 2026-11-18

### Changed

- Repository moved from `mdsyseng/how` to `mtudls/how`; URLs in the script, packaging and docs updated.
- `install.sh`, `PKGBUILD` and the release workflow ship the plain Python script from a tagged release.
  The Rust launcher is no longer installed, packaged or released.
- Unknown commands are classified as "modifies" unless every segment is a known read-only command.
  `curl`/`wget` piped to a shell, `eval` and `dd of=/dev/*` are classified as destructive;
  `dd` to a regular file is "modifies".
- `--json` errors return `ok: false` with an `error` object (`code`, `message`, `hint`).

### Removed

- Implicit offline fallback. Without an API key, or on a provider error, `how` prints a clear error and
  exits 1 instead of answering from the offline engine. `how reflex`, `--offline` and `--reflex` still
  work when asked for explicitly.

[1.0.0]: https://github.com/mtudls/how/compare/v0.6.6...v1.0.0
[0.6.6]: https://github.com/mtudls/how/compare/v0.6.5...v0.6.6
