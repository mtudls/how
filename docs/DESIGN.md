# Design

`how` 1.0.0 is a distilled rewrite. This page records what it is, what was cut and why, the principles it
keeps, and how the safety badge works, including what it cannot do.

## The concept

Ask in plain words, get **one** terminal command with a safety badge, copied to your clipboard. Asking never
holds the terminal: you are back at your own prompt, and `how run` runs the command after one keypress.
Nothing runs, and nothing leaves the machine, without the user seeing it.

Three things are optimised, in this order of tie-breaking:

1. **Trust and awareness.** The user always sees what will run and what will be sent.
2. **Seconds saved per question.** One question, one command, already on your clipboard.
3. **Joy of use.** A short answer, a clear badge, no ceremony.

## From 0.6.6 to 1.0.0

By 0.6.6 `how` had grown to a single 6,400-line script with a long list of subsystems. Each had a reason
when it was added. Together they made the tool hard to read, hard to test and hard to trust: a user could
not easily say what it read, what it sent, or why it answered the way it did.

1.0.0 follows the author's own 295-line direction (the `how-small` branch) and keeps only what serves the
concept. Target: one Python file, standard library only, Python 3.9+, a few hundred readable lines.

| Cut | Why |
|---|---|
| Offline "reflex" engine (System-1 rules answering without the API) | Silent local answers of uneven quality. A wrong command with a confident face costs more than a clear "no key" error. |
| Python-to-Rust transpiler and native binary | Startup time was never the bottleneck; the API round trip is. It doubled the code that had to be correct. |
| Context discovery (`careful` / `yolo` / `dry-run`), local RAG from `man`/`tldr`/`--help` | Reading the machine is the opposite of "nothing leaves without you seeing it". The question plus OS and shell is enough for one command. |
| SQLite answer cache, repeat-question memory | Stale answers and a second place where questions were stored. A plain log does the useful part. |
| Model benchmarking, deep-thinking tier, triage routing, multi-provider menus | Choice the user should not have to make. One default model; `HOW_MODEL` and `HOW_API_URL` for those who want another. |
| `where`, `fix`, `status`, `history`, `cache`, `context`, `verbosity`, `shell-init`, `build`, `test`, `auth`, `model` subcommands | Each one widened the surface. What remains: ask, `run`, `explain`, `good`/`bad`, and trust tools (`key`, `log`, `privacy`, `doctor`, `update`, `uninstall`). |
| Scheduled AI self-review and self-patching CI | Not part of the product. Tests and lint stay. |

Kept from earlier versions because they still hold:

- **Honesty.** When the model is not sure, `how` says "I don't know" and exits 2 instead of inventing flags.
- **No hidden shells.** `how` never runs anything on its own. It runs the shown command only after the
  confirmation its badge requires, in the user's own `$SHELL`, attached to the user's terminal.
- **Omarchy-aware prompt.** The model is told the machine is Omarchy (Arch + Hyprland) when it is, so it
  prefers `omarchy`, `pacman`/`yay`, `systemctl`, `hyprctl` and `wl-copy` where they fit.
- **The `# omarchy:` header** at the top of the script, so Omarchy can list `how` with its other tools.

## Trust principles

1. **What you see is what runs.** The displayed command is the executed command, byte for byte.
2. **The model proposes; local rules judge.** The badge is computed by a pure function on the machine.
   The model's output never influences the level.
3. **Unknown means careful.** Anything the rules do not recognise is 🟡 and needs an explicit `y`.
4. **One request, one host, stated up front.** Each question sends the question text, OS pretty name,
   shell name and an Omarchy marker (plus the API key and model name) to one host (`api.groq.com` unless
   `HOW_API_URL` says otherwise). `how explain` sends the command instead; `how doctor` checks the same host.
   No telemetry, no background calls, no update pings.
5. **Sharing is the user's act.** `how good` / `how bad` log the rating locally. To share it, `how` shows the
   exact text and, after `y`, opens a pre-filled GitHub issue in the browser; the user submits it.
6. **`how privacy` must be literally true.** It describes what the code does; a change to either changes both.
7. **The key is the user's.** Stored with mode 0600, never logged, never printed beyond its last 4 characters.
8. **Everything is inspectable.** A local JSON-lines log (`how log`), a health check (`how doctor`),
   and removal commands printed, not run (`how uninstall`).
9. **Fail loudly.** No key, a rejected key, a rate limit or a network error gives a clear message and
   exit 1. There is no silent fallback.

## The safety classifier

`classify(command) -> (level, reason)` is a pure function: no network, no model, no file access. It is
distilled from the 0.6.6 `classify_command_safety` and its read-only allowlists, with the level
`destructive` renamed to `dangerous`.

| Level | Rule |
|---|---|
| 🟢 safe | Every segment (split on pipes, `&&`, `\|\|`, `;` and subshells) is a known read-only command, with no output written to a file (other than `/dev/null`) |
| 🟡 modifies | Everything else that is not dangerous, including every command the rules do not know |
| 🔴 dangerous | Matches a known destructive pattern |

Dangerous patterns include: recursive forced removal (`rm -rf` and variants), `mkfs`, `wipefs`, `fdisk`,
`parted`, `shred`, `dd of=/dev/…`, writing to a raw disk (`> /dev/sdX`), downloads piped or substituted
into a shell (`curl … | sh`, `… | sudo bash`, `bash <(curl …)`, `sh -c "$(curl …)"`), `eval`, fork bombs,
`chmod -R 777 /`, `git push --force` and `git reset --hard`.

Some tools are read-only only with certain subcommands or flags (for example `git status` versus
`git stash drop`, or `find . -name x` versus `find . -delete`, which is 🔴). The allowlist names those
forms explicitly. A command that cannot be parsed (for example, unbalanced quotes) is 🟡, never 🟢.

Confirmation follows the level: Enter runs 🟢, `y` runs 🟡 (Enter does not), and 🔴 requires typing
`run` after the reason is shown. `-y/--yes` auto-runs only 🟢.

### Limits, stated plainly

A rule-based badge is a seatbelt, not a guarantee.

- **It reads text, not intent.** It does not execute, sandbox or trace the command. A read-only tool
  given a hostile argument, an alias or a function in the user's shell, or a script the command calls,
  can do things the text does not show.
- **Allowlists age.** A tool that was read-only can gain a writing flag in a new release. The allowlist
  must be kept conservative and tested.
- **Shell syntax is large.** Quoting, expansion, here-documents and nested substitutions can hide
  structure from a lexer. When parsing is uncertain the classifier must fall back to 🟡 or 🔴, never 🟢.
- **The default is the safety net.** Because unknown commands are 🟡, a gap in the rules usually costs
  an extra keypress, not a silent run. The failure that matters is a harmful command shown as 🟢;
  that is treated as a security bug (see [SECURITY.md](../SECURITY.md)).
- **🔴 is not exhaustive.** A destructive command that matches no pattern is still 🟡 and still needs `y`,
  but it will not carry the stronger warning.

The badge helps the user read the command. It does not replace reading it.

## Testing

The classifier is a pure function, tested with a table of commands and expected levels: dangerous
patterns, allowlisted read-only forms, and known bypass attempts. CLI tests point `HOW_CONFIG_DIR` and
`HOW_STATE_DIR` at temporary directories so they never touch the user's files, and must not reach the network.
