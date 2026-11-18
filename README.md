# how

Ask in plain words, get one terminal command with a safety badge, and run it with one keypress.
Nothing runs, and nothing leaves your machine, without you seeing it first.

```console
$ how to find largest files here
🟢 safe · reads only
  du -ah . | sort -rh | head -20
  Lists the 20 largest files and folders under the current directory.
[Enter] run · [c] copy · [e] explain · [q] quit
```

`how` is a single Python file with no dependencies beyond the standard library (Python 3.9+).
It is built for [Omarchy](https://omarchy.org) and Arch Linux, and works on any Linux with a terminal.

## Install

Pick one channel. The package is recommended: it upgrades with the rest of your system.

**1. AUR package `how-omarchy` (recommended)**

> Not on the AUR yet: the package will be published there after the 1.0.0 release.
> Until then, use the plugin or the install script.

<!-- install:package -->
```bash
yay -S how-omarchy                  # or, on Omarchy: omarchy pkg aur add how-omarchy
```

**2. Omarchy plugin**

<!-- install:plugin -->
```bash
omarchy plugin add https://github.com/mtudls/how.git --enable
```

**3. Install script** (installs to `~/.local/bin/how` from a tagged release, verified against the release's `SHA256SUMS`)

<!-- install:script -->
```bash
curl -fsSLO https://github.com/mtudls/how/releases/download/v1.0.0/install.sh
curl -fsSLO https://github.com/mtudls/how/releases/download/v1.0.0/SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS && bash install.sh
```

Then check the result with `how doctor`.

## First run

`how` needs an API key. Groq offers a free one at [console.groq.com/keys](https://console.groq.com/keys).

```bash
how key        # paste the key; input is hidden, the file is stored with mode 0600
how doctor     # confirms the key is present and the API is reachable
```

You can also set `GROQ_API_KEY` in your environment instead.

## Everyday use

```bash
how to find largest files here     # ask; a leading "to" is fine
how run                            # run the last suggested command (same confirmation rules)
how explain                        # short breakdown of the last command
how explain "tar -xzvf a.tgz"      # ...or of any command you paste
how good                           # rate the last answer
how bad "wrong flag for btrfs"     # rate it, with a note
```

After an answer you choose: **Enter** runs it (🟢 only), **c** copies it, **e** explains it, **q** quits.
When a clipboard tool is installed (`wl-copy`, `xclip` or `xsel`), the command is copied automatically.

Flags go before the question:

| Flag | Effect |
|---|---|
| `-y`, `--yes` | Run without asking, but only when the badge is 🟢 |
| `-n`, `--no-run` | Never prompt; print the command and copy it |
| `--json` | Print one JSON object on stdout; never prompts, never runs |
| `--debug` | Verbose diagnostics on stderr |

When stdout is not a terminal (for example `how to list ports | less`), `how` prints only the command on
stdout, puts the badge and note on stderr, and never prompts.

`how good` and `how bad` show you exactly what would be sent and ask for confirmation before sending anything.

## Safety model

Every command gets one of three badges:

| Badge | Meaning | To run it |
|---|---|---|
| 🟢 safe | Only reads: every part of the command is a known read-only tool | Press **Enter** |
| 🟡 modifies | Changes files, packages or settings, **or is not known to be read-only** | Press **y** (Enter does not run it) |
| 🔴 dangerous | Can destroy data or the system: `rm -rf`, `mkfs`, `dd of=/dev/…`, `curl … \| sh`, `git push --force`, `git reset --hard`, … | Type the word **run**; the reason is shown |

The badge is computed on your machine by fixed rules. The model never decides it.
Anything the rules do not recognise is 🟡. A command is 🟢 only if every segment of every pipeline,
`&&`, `;` and subshell is a known read-only command; redirecting output to a file is never 🟢.

The command shown is exactly the command executed, through your `$SHELL -c`, in your terminal.
If it exits non-zero, `how` tells you.

The badge is a seatbelt, not a guarantee. Read the command before you run it.
See [docs/DESIGN.md](docs/DESIGN.md) for how the classifier works and where it stops.

## Privacy and trust

- **What is sent:** your question, your OS name (for example "Arch Linux"), your shell name, and whether you run Omarchy.
  Nothing else: no file contents, no history, no environment.
- **Where:** one HTTPS request per question to `api.groq.com` (or the endpoint in `HOW_API_URL`).
  `how explain` makes one request, only when you ask for it.
- **Ratings:** `how good` and `how bad` send nothing until they have shown you exactly what will be sent, and where, and you answer `y`.
- **Never:** no telemetry, no background network calls, no update checks.
- **Your key** is stored locally with mode 0600, never logged, and never printed (at most its last 4 characters).

Check it yourself:

```bash
how privacy     # exactly what is sent, to which host, and every file how reads or writes
how log         # the last 20 entries of your local log (how log 50 for more)
how doctor      # version, install method, key, API reachability, clipboard tool, log path, update channel
```

## Updates

| Channel | How it updates |
|---|---|
| Package `how-omarchy` | With the rest of the system: `omarchy update` |
| Omarchy plugin | `omarchy plugin update io.github.mdsyseng.how` (`omarchy update` does not update plugins); `~/.local/bin/how` is a link into the plugin checkout |
| Install script | `how update` re-runs the installer for the latest release after you confirm |

`how update` always tells you which channel you are on and how updates arrive. `how` never checks for updates on its own.

## Uninstall

```bash
how uninstall   # prints the exact removal commands for your install method; it runs nothing
```

Your config and log stay until you delete them (see the paths below).

## Files and environment

| Path / variable | Purpose |
|---|---|
| `~/.config/how/config.json` | API key and model (mode 0600). Honours `$XDG_CONFIG_HOME` |
| `~/.local/state/how/how.log` | Local log, one JSON object per line (mode 0600). Rotates at 1 MiB to `how.log.1`. Honours `$XDG_STATE_HOME` |
| `~/.local/state/how/last.json` | The last answer, used by `how run`, `how explain`, `how good`/`bad` |
| `GROQ_API_KEY` | API key; used instead of the stored one |
| `HOW_MODEL` | Model name to request |
| `HOW_API_URL` | Any OpenAI-compatible chat completions endpoint |
| `HOW_CONFIG_DIR`, `HOW_STATE_DIR` | Override the config and state directories |
| `NO_COLOR` | Disable colour |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Answer shown (and, if run, the command finished) |
| `1` | Error: no key, rejected key, rate limit, network or timeout. The message says what to do |
| `2` | The model said it does not know |

## FAQ

**I have no API key.** Run `how key` and follow the link; Groq's key is free. Without a key, `how` stops with
a clear message. It never makes up an answer locally.

**Does it work offline?** No. Every answer comes from the API. There is no offline fallback.

**Can I use another provider?** Yes, any OpenAI-compatible endpoint:
`HOW_API_URL=https://api.example.com/v1/chat/completions HOW_MODEL=model-name how ...`.
Your question is then sent to that host instead; `how privacy` shows which.

**Why did a harmless command show 🟡?** The rules mark a command 🟢 only when they know every part of it is
read-only. An unfamiliar tool, a file redirect (`>`), or an unusual subcommand makes it 🟡. That is deliberate.
If you think a command should be 🟢, open an issue or a pull request with a test (see [CONTRIBUTING.md](CONTRIBUTING.md)).

**I saw 🟢 on a command that changes or destroys something.** That is a security bug. Please report it privately;
see [SECURITY.md](SECURITY.md).

## Contributing

```bash
python3 -m unittest discover -s tests
```

`how` stays one file, standard library only. See [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
