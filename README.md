# how

> Fast, concise, direct CLI tool to learn **"how to do sht in ..."** — built for Omarchy, Linux & your local stack. Zero runtime dependencies.

---

## Why `how`?

`how` translates natural language into copy-pasteable terminal commands directly inside your shell:

- **Sub-Second Speed**: Instant answers streamed via Groq LPU™ hardware, with `<30ms` cold CLI startup and `<1ms` SQLite WAL cache hits (`[cache]`).
- **Permission-Gated Environment & Stack Discovery**: Optionally detects your exact OS, Omarchy/Hyprland version, package manager, and the current directory's software stack (`uv`, `Cargo`, `pnpm`, `Bun`, `Rails`, `Go`, `Docker`) so `how to run single test` gives the exact command for *your* project.
- **Groq Triage + Deep Thinking Tier**: Fast lookups resolve instantly on Groq; complex troubleshooting or multi-step debugging is automatically triaged to a slower, higher-reasoning model (`--think` / `-t`), supporting Groq Reasoning (`DeepSeek-R1` / `QwQ`), Gemini, Claude, OpenAI, OpenRouter, or local CLI agents (`claude`, `gemini`, `codex`).
- **Strict Honesty**: Never hallucinates flags — if uncertain, replies strictly with `"I don't know"`.
- **Sandboxed Local RAG**: Reads `# omarchy:*` script headers, `tldr`, `man`, and `bwrap`-isolated `--help` output automatically.

---

## Installation & Setup

```bash
curl -fsSL https://raw.githubusercontent.com/mdsyseng/how/main/install.sh | bash
how auth login  # Free key: console.groq.com/keys
```

Or manual symlink:
```bash
git clone https://github.com/mdsyseng/how.git ~/.local/share/how && ln -sf ~/.local/share/how/how ~/.local/bin/how
```

---

## Everyday Usage

```bash
# Instant Omarchy & Linux commands
how to switch audio output in omarchy
how to unlock user after failed sudo tries
how to switch gh user without logout

# Stack-aware commands in your project folder
how to run a single test file
how to check outdated dependencies

# Command-only output (clean, zero explanation)
how -0 to find largest files in current directory
how --low to reload hyprland

# Force deep thinking for complex debugging or architecture
how -t to fix limine secure boot black screen
how triage why is my trackpad freezing after suspend
```

---

## Context, Triage & Configuration

```bash
# Permission-gated OS & project stack discovery
how context                 # View permissions & detected OS / project stack
how context on              # Enable both OS and directory stack discovery
how context os on           # Toggle OS/version profile discovery only
how context stack on        # Toggle current-directory stack discovery only

# Question triage & Deep Thinking model configuration
how triage                  # View triage & deep-thinking configuration
how triage on               # Enable automatic Groq question triage
how model                   # Select or latency-test fast Groq models
how model check             # Benchmark all available Groq models
how model think gemini:gemini-2.5-pro  # Configure deep-thinking provider

# Output verbosity & sliding cache (m = minutes, h = hours, D = days, M = months)
how verbosity zero
how cache retention 7D
how cache clear

# Terminal feedback
how feedback "pipewire sink switch command failed"
```

Paths:
- Config: `~/.config/how/config.json` (permissions `0600`)
- Cache: `~/.cache/how/cache.db` (SQLite3 WAL)

---

## Verification & Automated Self-Improvement (ASI)

```bash
how test                        # Built-in self-test & A/B benchmark matrix
python3 tests/test_vv_suite.py  # Fast V&V behavioral & latency suite
python3 tests/test_safety.py    # Sandbox & security unit tests
```

See [docs/ASI.md](docs/ASI.md) for details on the A/B benchmarking matrix and autonomous review workflow.

---

## License

[MIT License](LICENSE) © 2026 Mateusz Dzieliński.
