# how

Ask in plain words, get one terminal command with a safety badge, copied to your clipboard.
You are straight back at your own prompt: paste it, edit it, or type `how run`.
Nothing runs, and nothing leaves your machine, without you seeing it first.

```console
$ how to find largest files here
🟢 safe · reads only
  du -ah . | sort -rh | head -20
  Lists the 20 largest files and folders under the current directory. · copied
$ █
```

`how` is a single Python file with no dependencies beyond the standard library (Python 3.9+).
It is built for [Omarchy](https://omarchy.org) and Arch Linux, and works on any Linux with a terminal.

## Install

Pick one channel. The package is recommended: it upgrades with the rest of your system.

**1. AUR package `how-omarchy` (recommended)**

> Not on the AUR yet: the package will be published there after the first release.
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

Enabling the plugin makes `~/.local/bin/how` a link into the plugin checkout. It steps aside if the package is installed.

**3. Install script**

<!-- install:script -->
```bash
curl -fsSL https://github.com/mtudls/how/releases/latest/download/install.sh | bash
```

The installer downloads `how` from one pinned release tag, refuses to install it unless its SHA-256 matches the
release's checksum file, and puts it in `~/.local/bin/how`. It never uses sudo, never edits your shell files and
installs no background updater. Add `-s -- --dry-run` to see what it would do, or download `install.sh` and read it
before running `bash install.sh`.

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
how run                            # run the last suggested command, after a keypress
how explain                        # short breakdown of the last command
how explain "tar -xzvf a.tgz"      # ...or of any command you paste
how good                           # rate the last answer
how bad "wrong flag for btrfs"     # rate it, with a note
```

Asking never runs anything and never holds your terminal: `how` prints the answer, copies the command
(with `wl-copy`, `xclip` or `xsel`) and exits. Paste it at your prompt, or type `how run`.
`how run` shows the command again and waits: **Enter** runs it (🟢 only), **c** copies it, **e** explains it, **q** quits.

Flags go before the question:

| Flag | Effect |
|---|---|
| `-y`, `--yes` | Run straight away, but only when the badge is 🟢 |
| `-n`, `--no-run` | Print only the command on stdout (badge and note go to stderr) and copy it |
| `--json` | Print one JSON object on stdout; never prompts, never runs |
| `--debug` | Verbose diagnostics on stderr |

When stdout is not a terminal (for example `how to list ports | less`), `how` prints only the command on
stdout, puts the badge and note on stderr, and never prompts.

`how good` and `how bad` record your rating locally. Sharing it is a separate step you confirm (see Privacy).

## Safety model

Every command gets one of three badges:

| Badge | Meaning | To run it with `how run` |
|---|---|---|
| 🟢 safe | Only reads: every part of the command is a known read-only tool | Press **Enter** |
| 🟡 modifies | Changes files, packages or settings, **or is not known to be read-only** | Press **y** (Enter does not run it) |
| 🔴 dangerous | Can destroy data or the system: `rm -rf`, `mkfs`, `dd of=/dev/…`, `curl … \| sh`, `git push --force`, `git reset --hard`, … | Type the word **run** and press Enter; the reason is shown, and Enter alone quits |

The badge is computed on your machine by fixed rules. The model never decides it.
Anything the rules do not recognise is 🟡. A command is 🟢 only if every segment of every pipeline,
`&&`, `;` and subshell is a known read-only command; writing output to a file (other than `/dev/null`) is never 🟢.

The command shown is exactly the command executed, through your `$SHELL -c`, in your terminal.
If it exits non-zero, `how` tells you and exits with the same code.

The badge is a seatbelt, not a guarantee. Read the command before you run it.
See [docs/DESIGN.md](docs/DESIGN.md) for how the classifier works and where it stops.

## Privacy and trust

- **What is sent:** your question, your OS name (for example "Arch Linux"), your shell name, and whether you run Omarchy.
  Nothing else: no file contents, no history, no environment.
- **Where:** one HTTPS request per question to `api.groq.com` (or the endpoint in `HOW_API_URL`), carrying your
  API key and the model name. `how explain` sends the command instead of a question. `how doctor` contacts the
  same host to check that it answers.
- **Ratings:** `how good` and `how bad` are noted in your local log. To share one, `how` shows the exact text,
  and only after you answer `y` opens a pre-filled GitHub issue in your browser, which you submit yourself.
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

For example: `yay -Rns how-omarchy` for the package, `omarchy plugin remove io.github.mdsyseng.how` for the
plugin, or `install.sh --uninstall` (add `--purge` to delete your key and log) for the script.
Your config and log stay until you delete them; `how uninstall` prints that command too.

## Files and environment

| Path / variable | Purpose |
|---|---|
| `~/.config/how/config.json` | API key and model (mode 0600). Honours `$XDG_CONFIG_HOME` |
| `~/.local/state/how/how.log` | Local log, one JSON object per line (mode 0600). Rotates at 1 MiB to `how.log.1`. Honours `$XDG_STATE_HOME` |
| `~/.local/state/how/last.json` | The last answer, used by `how run`, `how explain`, `how good`/`bad` |
| `~/.local/state/how/install-receipt` | Written by the install script, so `install.sh --uninstall` removes only what it installed |
| `~/.local/state/how/plugin.log` | Written by the Omarchy plugin when it links `~/.local/bin/how` |
| `/etc/os-release` | Read for your OS name |
| `GROQ_API_KEY` | API key; used instead of the stored one |
| `HOW_MODEL` | Model name to request |
| `HOW_API_URL` | Any OpenAI-compatible chat completions endpoint |
| `HOW_CONFIG_DIR`, `HOW_STATE_DIR` | Override the config and state directories |
| `HOW_VERSION`, `HOW_INSTALL_DIR` | Install script only: release tag and target directory |
| `NO_COLOR` | Disable colour |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Answer shown, and the command (if you ran it) succeeded |
| `1` | Error: no key, rejected key, rate limit, network or timeout. The message says what to do. `how doctor` also exits 1 when a check fails |
| `2` | The model said it does not know, or the command line was not understood |
| `130` | Interrupted with Ctrl-C |
| other | You ran the command and it failed: `how` exits with the command's own code |

## FAQ

**I have no API key.** Run `how key` and follow the link; Groq's key is free. Without a key, `how` stops with
a clear message. It never makes up an answer locally. The badge still works: `how explain "some command"` shows it
without a key.

**Does it work offline?** No. Every answer comes from the API. There is no offline fallback.

**The README pipes `curl` into `bash`, which `how` marks 🔴. Why?** Because it runs code from the network without
showing it. The installer is short and does one thing, but if you want to see it first, download it, read it, then run it.

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
