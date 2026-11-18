# Contributing

Thanks for helping. Keep changes small and focused; one idea per pull request.

## Rules

- **One file.** `how` is a single Python file. Do not split it into modules.
- **Standard library only.** No third-party imports, Python 3.9+.
- **Trust first.** No new network calls, background work or data sent without the user seeing it.
  If you change what is sent or which files are touched, update `how privacy` and the README in the same change.
- **The model never decides the badge.** Safety stays a local, pure function.

## Test and lint

```bash
python3 -m unittest discover -s tests
ruff check how tests/
shellcheck install.sh
```

Tests must not touch your real config or the network: point `HOW_CONFIG_DIR` and `HOW_STATE_DIR` at a
temporary directory and stub the API.

## Adding a classifier rule

1. Write the test first. Add the command and its expected level to the classifier tests in `tests/`,
   including at least one look-alike that must keep a different level
   (for example `git status` 🟢 next to `git stash drop` 🟡).
2. Make the smallest change in `classify()` or its allowlists in `how`.
   - A read-only allowlist entry must be read-only for **every** flag the tool accepts, or list the
     read-only subcommands explicitly.
   - When in doubt, leave it 🟡. Never widen 🟢 to fix a 🟡 that is merely inconvenient.
3. Run the full test suite.

A harmful command shown as 🟢 is a security bug: report it privately as described in [SECURITY.md](SECURITY.md)
rather than in a public issue or pull request.

## Changelog

Add a line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md) for anything a user would notice.
