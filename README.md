# how

> Instant Linux & Omarchy terminal commands from natural language. Zero runtime dependencies.

---

## What It Does

`how` translates natural language queries into copy-pasteable terminal commands directly inside your shell.

- **Instant Answers**: Sub-second streaming powered by Groq's LPU™ hardware.
- **Developer-Friendly**: $0 free API access provided by Groq (no credit card required). Kudos to Jonathan Ross & team!
- **Strict Verification**: If uncertain, answers strictly with `"I don't know"` — no hallucinated syntax.
- **Sliding Cache**: Repeated commands return in <1ms and extend their TTL on hit (`[cache]`).
- **Terminal Feedback**: Report broken commands or send suggestions directly from your terminal.

---

## Installation & Setup

```bash
curl -fsSL https://raw.githubusercontent.com/mdsyseng/how/main/install.sh | bash
how auth login  # Free key: console.groq.com/keys
```

Or manual link:
```bash
git clone https://github.com/mdsyseng/how.git ~/.local/share/how && ln -s ~/.local/share/how/how ~/.local/bin/how
```

---

## Everyday Commands

```bash
# Ask how to accomplish tasks
how to ping google
how to convert mov to mp4 with ffmpeg
how to switch gh user without logout

# Command-only output (clean, no explanations)
how -0 to find largest files in current directory
how --low to reload hyprland

# Force fresh response or override cache retention
how --no-cache to check open ports
how --retention 1M to install postgres on arch

# Send feedback directly from terminal
how feedback "pipewire switch command failed"
```

---

## Configuration

Adjust behavior and retention preferences:

```bash
# Model selection & latency test
how model
how model check

# Output verbosity (zero, low, normal)
how verbosity zero

# Cache control (m = minutes, h = hours, D = days, M = months)
how cache retention 7D
how cache clear
```

Paths:
- Config: `~/.config/how/config.json`
- Cache: `~/.cache/how/cache.db` (SQLite3)

---

## Local Verification & Testing

Run tests and checks locally:

```bash
# 1. Native test suite (sub-second performance & behavior checks)
python3 tests/test_vv_suite.py
how test  # Built-in self-test (runs A/B comparison if WIP differs from installed)

# 2. Containerized pipeline (lint, security, tests)
docker build -t how-test -f Dockerfile.test .
docker run --rm how-test

# 3. Local GitHub Actions simulation (via act)
gh act push -j quality
gh act push -j performance
```

---

## License

[MIT License](LICENSE) © 2026 Mateusz Dzieliński.
