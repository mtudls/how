# how

> Fast, concise, direct CLI tool to learn **"how to do sht in ..."** — built for Omarchy, Linux & your local stack. Zero runtime dependencies.

---

## Why `how`?

`how` translates natural language into copy-pasteable terminal commands directly inside your shell:

- **Sub-Millisecond Native Speed**: Kept as readable, zero-dependency Python in the repo, and automatically transpiled via Python AST to a `<1ms` native Rust binary (`rustc -O`, no LLM needed) during local installation (`./install.sh` or `how build`).
- **Graduated, Transparent Context Discovery**:
  - **`careful` (default)**: Step-by-step user approval showing the exact `[dry-run]` command (`cat /etc/os-release`, `uname -sr`, `ls -1 <cwd>`) before reading any source.
  - **`yolo` (`how context yolo` / `how --yolo`)**: Goes straight ahead, reads OS, project stack & local docs without prompts, and prints a transparent receipt of exactly what it read (`🔎 Read: ...`).
  - **`dry-run` (`how context dry-run` / `how --dry-run <query>`)**: Prints every read-only check and local doc inspection command without executing them.
- **Groq Triage + Deep Thinking Tier**: Fast lookups resolve instantly on Groq; complex troubleshooting or multi-step debugging is automatically triaged to a slower, higher-reasoning model (`--think` / `-t`), supporting Groq Reasoning (`DeepSeek-R1` / `QwQ`), Gemini, Claude, OpenAI, OpenRouter, or local CLI agents (`claude`, `gemini`, `codex`).
- **Strict Honesty**: Never hallucinates flags — if uncertain, replies strictly with `"I don't know"`.
- **Sandboxed Local RAG**: Reads `# omarchy:*` script headers, `tldr`, `man`, and `bwrap`-isolated `--help` output automatically.

---

## Installation & Local Rust Transpilation

```bash
git clone https://github.com/mdsyseng/how.git && cd how
./install.sh    # Automatically transpiles readable Python -> native Rust binary (~0.9ms startup)
how auth login  # Free key: console.groq.com/keys
```

Or rebuild the native Rust binary anytime:
```bash
how build                                   # Transpile `how` (Python AST -> Rust) and install to ~/.local/bin/how
python3 scripts/transpile_rust.py --help    # Standalone deterministic AST transpiler (zero LLM, zero crates)
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
# Graduated OS & project stack discovery
how context                 # View mode (careful/yolo/off), permissions & read receipt
how context careful         # Step-by-step approval with [dry-run] commands (default)
how context dry-run         # Preview exact dry-run inspection commands without reading
how context yolo            # Auto-discover OS/stack & print what was read (🔎 Read: ...)
how --yolo <query>          # Run a single query in YOLO mode and show what was read
how --dry-run <query>       # Preview context, doc & triage plan for a query without running
how context on / off        # Enable or disable all context discovery

# Unified dashboard & last-command runner
how status                  # Single-screen overview (engine, auth, models, context, cache)
how run                     # Preview [dry-run] and confirm executing last suggested command

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
