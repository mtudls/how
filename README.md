# how

Ultra-fast AI CLI assistant powered by Groq for Omarchy & Linux.

Zero dependencies (pure Python standard library). Delivers instant, copy-pasteable terminal commands directly in your shell.

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/mdsyseng/how/main/install.sh | bash
```

Or clone and link directly into your `$PATH`:
```bash
git clone https://github.com/mdsyseng/how.git ~/.local/share/how
ln -s ~/.local/share/how/how ~/.local/bin/how
```

---

## Quickstart

Authenticate with your Groq API key:
```bash
how auth login
```
> [!NOTE]
> Groq API keys are completely free ($0, no credit card required). Get yours at [console.groq.com/keys](https://console.groq.com/keys).

---

## Usage

```bash
# Ask any command
how to ping google
how to convert mov to mp4 with ffmpeg
how to switch gh user without logout

# Command-only mode (ultra-minimal, no explanations)
how -0 to find largest files in current directory
how --low to reload hyprland

# Select and test AI models
how model
how model check

# Response cache & retention (m = minutes, h = hours, D = days, M = months)
how cache
how cache retention 7D
how cache 30m
how cache clear

# Temporary flags
how --no-cache to check open ports
how --retention 1M to install postgres on arch

# Effortless feedback & bug reporting
how feedback
how feedback "bluetooth pairing fails with pipewire"
how --bug to mount btrfs subvolume
```

---

## Configuration & Cache

`how` adheres to XDG Base Directory standards:

- **Config**: `~/.config/how/config.json` (or `$HOW_CONFIG_DIR`)
- **Cache**: `~/.cache/how/cache.db` (SQLite3 with automatic TTL expiration)

### Cache Retention Units

Configure retention globally with `how cache retention <duration>`:
- `m` — Minutes (e.g. `30m`)
- `h` — Hours (e.g. `3h` — default)
- `D` — Days (e.g. `7D`)
- `M` — Months (e.g. `1M` = 30 days)

Cached responses return near-instantly (<1ms) and are tagged with `[cache]`.

---

## License

[MIT](LICENSE) © 2026 Mateusz Dzieliński
