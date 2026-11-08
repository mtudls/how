# how

Ask in plain words. Get the exact terminal command.

Built for **Omarchy**, **Linux**, and your local project stack.

> **Document Guide:**
> - **Part 1 — `[LIVE • v0.6]`**: Everyday commands and core features you can use right now (`✅`).
> - **Part 2 — `[LIVE • v0.6]`**: System-1 Offline Reflex, Repeat-Question Memory, `where` + `om` Unified CLI, Traffic-Light Safety, and Closed-Loop ASI (`✅`).
> - *Technical details (**way / form**) are inside expandable `▸` sections.*

---

# Part 1 — `[LIVE • v0.6]` What `how` & `om` Do Today

## Quick Start (Zero-Setup Out of the Box)

```bash
git clone https://github.com/mdsyseng/how.git && cd how
./install.sh                    # Installs native Rust `how` & `om` — works immediately with 0 setup!
eval "$(how shell-init bash)"   # Optional: bind Alt+H to replace `# query` in-place in your shell prompt
how auth login                  # Optional: add free Groq LPU key ($0, no card): console.groq.com/keys
```

> **Zero-Setup Cascade (`v0.6`):** Even before you run `how auth login`, `how` and `om` work immediately out of the box using:
> 1. **Layer 1 (`<1 ms` Offline):** Personal episodic history (`commands.log`) + System-1 Reflex KB with dynamic parameter slot filling (`<port>`, `<PID>`, `<size>`, `<service>`) + local `# omarchy:*` & `tldr` recipe extraction.
> 2. **Layer 2 (`Zero-Key Cloud Auto-Discovery`):** Automatically reuses your existing `gh` CLI login (`~/.config/gh/hosts.yml` / `gh auth token` → GitHub Models), `CEREBRAS_API_KEY` (Cerebras WSE), or `GEMINI_API_KEY` (Gemini Flash-Lite + Google Search Grounding) if present.
> 3. **Layer 3 (`Alt+H` Readline Prompt Injection):** Type `# kill process on port 3000` in your prompt and press **`Alt+H`** to replace the prompt buffer in-place.

## Everyday Use (Effect → Command)

| Status | Effect (What you get) | Command (What to type) |
| :---: | :--- | :--- |
| ✅ `LIVE` | **Command + short explanation + `🟢/🟡/🔴` safety badge** | `how to switch audio output` |
| ✅ `LIVE` | **Command only (no extra text)** | `how -0 to find largest files` |
| ✅ `LIVE` | **In-place shell prompt replacement (`Alt+H` keybinding)** | `eval "$(how shell-init bash)"` *(then type `# query` + `Alt+H`)* |
| ✅ `LIVE` | **Offline `<3 ms` System-1 reflex (zero network)** | `how --offline to check memory usage` *(or `how reflex ...`)* |
| ✅ `LIVE` | **Offline `<5 ms` spatial locator for configs, logs & ports** | `how where hyprland monitor config` *(or `om where ...`)* |
| ✅ `LIVE` | **Offline `<1 ms` visual pipeline & flag breakdown** | `how explain` *(or `how explain "tar -xzvf a.tgz"`)* |
| ✅ `LIVE` | **Instant command repair & error diagnostics** | `how fix` *(or `om fix "permission denied"`)* |
| ✅ `LIVE` | **Run the last suggested command (with safety check)** | `how run` *(or `om !`)* |
| ✅ `LIVE` | **Solve a hard bug or boot issue** | `how -t why does suspend freeze my screen` |
| ✅ `LIVE` | **Preview what `how` would read (zero execution)** | `how --dry-run to update system` |
| ✅ `LIVE` | **Auto-read OS & project stack (with receipt)** | `how --yolo to run single test file` |
| ✅ `LIVE` | **See health, active models, and settings** | `how status` |
| ✅ `LIVE` | **Report a broken command or idea** | `how feedback "audio command failed"` |

<details>
<summary><b>▸ Way / Form: All CLI commands, flags & file paths</b></summary>

```bash
# Output style & command anatomy
how -0 <query>                    # Command only (also copied to clipboard)
how --low <query>                 # Command + 1-sentence note
how verbosity [zero|low|normal]   # Set default output style
how explain [command...]          # Offline <1ms pipeline & flag breakdown + safety badge
how fix [error...]                # Diagnose & repair the last command (offline rules + AI fallback)
how run [-y|--dry-run]            # Preview safety badge or execute the last suggested command

# Privacy & system context
how context                       # View current context permissions
how context careful               # Ask step-by-step with [dry-run] preview (default)
how context yolo                  # Auto-read OS/stack and print what was read (🔎 Read: ...)
how context dry-run               # Show exact read-only commands without running them
how context off                   # Disable all OS and project discovery

# Speed vs. Deep Thinking
how --fast <query>                # Force instant response
how -t <query>                    # Force deep reasoning model (--think / --deep)
how triage [on|off|<query>]       # Auto-route hard questions to deep thinking
how model                         # Pick or benchmark fast models
how model think <provider:model>  # Pick deep model (groq, gemini, anthropic, openai, cli)

# Cache & history
how cache [30m|3h|7D|1M|off]      # Set how long answers are remembered
how cache clear                   # Wipe saved answers
how --no-cache <query>            # Ask fresh, ignoring saved answers
how history [filter]              # View past suggested commands
how bash-history [on|off]         # Append suggestions to ~/.bash_history

# Build & self-test
how build                         # Rebuild native Rust binary from Python source
how test [--stats]                # Run self-test and speed benchmark
```

**Local files:**
- Settings: `~/.config/how/config.json` (`0600` permissions)
- Command log: `~/.config/how/commands.log`
- Answer cache: `~/.cache/how/cache.db` (SQLite WAL)

</details>

---

## Core Capabilities (`[LIVE • v0.5]`)

### ✅ 1. Instant Startup (`~1 ms`) with Readable Code
**Effect:** Starts the moment you press Enter, while keeping the source code a single, readable Python file anyone can edit.

<details>
<summary><b>▸ Way / Form: Deterministic Python AST → Rust transpilation</b></summary>

- Source of truth: [`how`](how) (zero-dependency Python standard library).
- During `./install.sh` or `how build`, [`scripts/transpile_rust.py`](scripts/transpile_rust.py) parses the Python AST and compiles a native Rust binary (`rustc -C opt-level=3 -C strip=symbols`) with **zero LLM calls** and **zero external crates**.
- Common paths (`--help`, `--version`, `context dry-run`, `--dry-run`) execute in native Rust (`~1 ms`); stateful network/SQLite flows delegate to the embedded Python source.
- Use `./install.sh --python-only` to skip Rust compilation.

</details>

### ✅ 2. System-Aware — On Your Terms
**Effect:** Gives commands that match your Linux distro, package manager, and project folder—asking permission before reading anything.

<details>
<summary><b>▸ Way / Form: Graduated context modes (`careful` / `yolo` / `dry-run`)</b></summary>

- **5 read-only checks:** `os_release`, `kernel`, `desktop`, `shell_pkg`, and `stack`.
- **`careful` (default):** Prompts step-by-step and shows the `[dry-run] $ ...` shell command before reading.
- **`yolo` (`how context yolo` / `--yolo`):** Reads OS, project manifests, and local CLI docs immediately and prints a receipt:
  `🔎 Read: OS[/etc/os-release, uname], Stack[Cargo.toml], Docs[tldr:pacman]`
- **`dry-run` (`how context dry-run` / `--dry-run`):** Prints every check and triage route with zero execution and zero network calls.
- Never reads `.env`, secrets, or private keys.

</details>

### ✅ 3. Multi-Step Pre-IDK Escalation, Local RAG & Traffic-Light Safety
**Effect:** Repairs typos, grounds commands in your local `man`/`tldr` docs, escalates to a smarter reasoning model on your platform of choice before ever saying `"I don't know"`, and labels every command `🟢 SAFE`, `🟡 MODIFIES`, or `🔴 DESTRUCTIVE / ADMIN`.

<details>
<summary><b>▸ Way / Form: Pre-IDK escalation, Bubblewrap (`bwrap`) sandbox, `explain`/`fix` & repeat-aware cache</b></summary>

- **2-Step Escalation Before `"I don't know"`:**
  1. **Step 1 (Question Refinement & Domain Grounding):** Repairs CLI typos (`maske symlik` → `create a symbolic link with ln -s`), expands terse shorthand (`to see origin` → `to see git remote origin url`), attaches Linux/Arch/Hyprland/Omarchy domain hints, and pulls newly matched local `tldr`/`man` pages.
  2. **Step 2 (Smarter Model on Platform of Choice):** If still uncertain, reaches out to your configured reasoning provider (`gemini`, `anthropic`, `openai`, `openrouter`, `cli:claude`, or Groq's `openai/gpt-oss-120b` / `openai/gpt-oss-20b` / `qwen/qwen3.8-27b` pool). Uncertain `"I don't know"` responses are never cached.
- **Traffic-Light Command Safety & `how explain` / `how fix` (`<1 ms` offline):**
  - `classify_command_safety` badges every command as `🟢 SAFE (read-only)`, `🟡 MODIFIES`, or `🔴 DESTRUCTIVE / ADMIN`.
  - `how explain [cmd]` splits pipelines (`|`, `&&`, `||`, `;`) into stages and explains each binary and flag offline in `<1 ms`.
  - `how fix [error]` diagnoses common failures offline (`permission denied`, `/var/lib/pacman/db.lck`, missing git upstream, Limine Secure Boot, port conflicts) or escalates to deep mode.
- **Local documentation priority (<5 ms):**
  1. `# omarchy:*` header comments in `/usr/bin/omarchy-*` scripts (parsed as text, never executed).
  2. Local `tldr` pages.
  3. System `man -P cat <cmd>` synopsis.
  4. Isolated Bubblewrap sandbox (`bwrap --ro-bind / / --unshare-all --cap-drop ALL -- timeout 2 <cmd> --help`).
- **Repeat-Aware Sliding SQLite Cache:** Stores verified answers in `~/.cache/how/cache.db` (`3h` default TTL, renewed on hit) and tracks `hit_count` to surface `how explain` / `how fix` / `how -t` tips when a query is repeated.
- **Output Sanitization:** Strips ANSI/OSC terminal escape sequences from model outputs.

</details>

### ✅ 4. 5-Axis Product Convergence Suite (`how test`)
**Effect:** One command checks speed, Pre-IDK intelligence, UX safety badges, cache memory, and 100-query benchmark convergence locally before you commit—backed by automated GitHub Actions gates.

<details>
<summary><b>▸ Way / Form: 5-axis V&V scorecard & Free-Plan CI pipelines</b></summary>

- Run `how test --stats`, `python3 tests/test_vv_suite.py`, or `python3 tests/test_safety.py -v`.
- CI workflows (`.github/workflows/*.yml`) use `concurrency` (`cancel-in-progress: true`), `timeout-minutes: 5`, and single-VM consolidation to run V&V, `ruff`, `flake8`, `shellcheck`, `bandit`, `gitleaks`, and native `how-linux-x86_64` release builds.
- See [`docs/ASI.md`](docs/ASI.md) and [`docs/requirements.md`](docs/requirements.md) for historical details.

</details>

---
---

# Part 2 — `[LIVE • v0.6]` System-1 Reflex, `where` + `om` CLI & Closed-Loop ASI

| Status | Capability | Effect (What it does for you) |
| :---: | :--- | :--- |
| ✅ `LIVE` | **1. System-1 Offline Reflex (`basal` / `jev`)** | Answers everyday Linux/Omarchy commands in `<3 ms` offline (`how --offline` / `how reflex` / `--reflex`). |
| ✅ `LIVE` | **2. Repeat-Question Memory** | Detects when you ask the same question twice and asks if the previous command failed (`[Y]`/`[e]`/`[n]` in TTY, 30m window). |
| ✅ `LIVE` | **3. `where` + `om` Unified CLI** | Finds *where* any file, config, log, binary, or port is (`om where ...` / `how where ...`) alongside `om how`, `om fix`, and `om !`. |
| ✅ `LIVE` | **4. Normie Safety Traffic Lights** | Labels every command `🟢 Safe`, `🟡 Modifies files`, or `🔴 Destructive / Admin` (`how run` requires typing `yes` for 🔴). |
| ✅ `LIVE` | **5. Closed-Loop Autonomous ASI** | Validates bounded `SEARCH/REPLACE` patches against 4 hard gates, rolls back regressions, and opens verified PRs. |

---

### ✅ 1. System-1 Models (`basal`, `jev`) + Cloud LLM Hybrid (`[LIVE — v0.6]`)
**Effect:** Common everyday tasks resolve locally in `<3 ms` with zero internet needed, while novel or tricky questions automatically step up to fast or deep cloud LLMs.

<details>
<summary><b>▸ Way / Form: 3-Tier System-1 / System-2 routing architecture</b></summary>

- **Tier 0 — Local System-1 Reflex (`<3 ms`, `lookup_system1_reflex`):**
  - Classifies user intent (`classify_query_intent`: `how` vs `where` vs `fix` vs `explain`).
  - Scores command danger (`read-only` vs `mutating` vs `destructive`).
  - Synthesizes canonical commands for 75+ common Linux, Arch/pacman, systemd, Git, Docker, Hyprland, and Omarchy operations offline (`how --offline <query>` or `how reflex <query>`).
- **Tier 1 — Fast Cloud LPU (`~150 ms`, Groq):**
  - Combines local `tldr`/`man`/`omarchy-*` RAG with fast LPU generation for custom flags.
- **Tier 2 — Deep Thinking (`~1–3 s`, `-t` / `--think`):**
  - Routes multi-step debugging (bootloaders, kernel modules, Wayland/PipeWire) to reasoning models (`openai/gpt-oss-120b`, `Claude`, `Gemini`, `OpenAI`).

</details>

### ✅ 2. Repeat-Question Memory ("Did the previous answer not work?") (`[LIVE — v0.5+]`)
**Effect:** If you ask the same question again within minutes, `how` won't blindly repeat the same cached command—it will ask if the first one failed and offer a deeper fix.

<details>
<summary><b>▸ Way / Form: SQLite `hit_count` tracking & interactive escalation prompt</b></summary>

- Tracks `hit_count` and `last_hit_at` in `~/.cache/how/cache.db`. When re-asked within 30 minutes in an interactive TTY:
  ```text
  ? You asked this 2m ago. Did the previous command not work?
    [Y] Try a fresh Deep Thinking solution (-t --no-cache)
    [e] Attach last terminal error / exit code and fix it
    [n] Show the cached command again
  ```
  Non-interactive shells and `HOW_NO_REPEAT_PROMPT=1` keep the tip-only behavior.

</details>

### ✅ 3. From `how` to `where` — and the Unified `om` CLI ("om!") (`[LIVE — v0.6]`)
**Effect:** Use one friendly 2-letter tool (**`om`**) to learn **how** to do anything, find **where** any file or config is stored, or **fix** your last failed command.

<details>
<summary><b>▸ Way / Form: `where` local probes + `om` wrapper syntax</b></summary>

```bash
om how to switch audio output          # Procedural: how to do X
om where is hyprland monitor config    # Spatial: locate file, config, log, binary, or port (<5ms)
om -0 where pacman.conf                # Path only (/etc/pacman.conf)
om fix                                 # Diagnostic: inspect last failed command & propose fix
om !                                   # Action: preview & execute last suggested command
```

- **`where` Engine (`locate_where_targets`):** Combines curated Omarchy/Hyprland/Arch config & log paths with live read-only local probes (`~/.config/*`, `$PATH` via `shutil.which`, and socket ports) to return the exact path and a `🟢 SAFE` inspect command in `<5 ms`.

</details>

### ✅ 4. Dual-Persona UX: Simplest "Normie" User × Systems Programmer (`[LIVE — v0.5+]`)
**Effect:** Beginners get plain-English safety ratings and zero-jargon explanations, while systems programmers keep sub-millisecond native speed and strict sandboxing.

<details>
<summary><b>▸ Way / Form: Traffic-light risk classifier & flag explainer</b></summary>

- **Traffic-Light Risk Badges:**
  - `🟢 Safe (read-only)` — only inspects info (`ls`, `df`, `ip`, `pacman -Si`)
  - `🟡 Modifies files/packages` — edits configs or installs packages (`pacman -S`, `cp`, `sed -i`)
  - `🔴 Destructive / Admin` — deletes data or alters boot/disks (`rm -rf`, `dd`, `mkfs`); requires typing `yes` in `how run` / `om !`.
- **Plain-English Flag Breakdown (`how explain`):** Offline `<1 ms` breakdown of each pipeline stage and flag (`-r` = recursive, `-f` = force).

</details>

### ✅ 5. Closed-Loop Autonomous Self-Improvement (ASI: `Code → Gate → PR`) (`[LIVE — v0.6]`)
**Effect:** Instead of just opening advisory GitHub Issues, `how` tests its own optimization patches against 4 hard verification gates and rolls back any regression automatically.

| ASI Tier | Status | Effect |
| :--- | :---: | :--- |
| **1. Human-Assisted Local Loop** (`how test`) | ✅ `LIVE` | Benchmarks `[A] Baseline` vs `[B] WIP`, runs V&V + safety checks, and gives a pass/fail verdict. |
| **2. Autonomous Cloud Reviewer** (`ai-architect.yml`) | ✅ `LIVE` | Runs weekly on GitHub Actions, analyzes [`how`](how) + V&V scores, and opens a GitHub Issue with proposals. |
| **3. Closed-Loop Self-Patching** (`Code → Gate → PR`) | ✅ `LIVE` | Applies bounded `SEARCH/REPLACE` patches, enforces 4 hard gates, rolls back regressions, and opens a verified PR. |

<details>
<summary><b>▸ Way / Form: Propose → Hard Gate → Verified PR pipeline</b></summary>

1. **Propose (Bounded Diff):** [`scripts/ai_architect_review.py`](scripts/ai_architect_review.py) proposes a minimal SEARCH/REPLACE patch on [`how`](how) (or updates deprecated model IDs / adds regression tests from user `how feedback` issues).
2. **Hard Verification Gate (Zero Human Trust Required):**
   - Must transpile and compile via [`scripts/transpile_rust.py`](scripts/transpile_rust.py) with `0` errors.
   - Must score **`100.0 / 100`** on [`tests/test_vv_suite.py`](tests/test_vv_suite.py).
   - Must pass **100%** of [`tests/test_safety.py`](tests/test_safety.py) (sandbox, no `eval`/`exec`, no trailing whitespace).
   - Must pass [`tests/test_ab_bench.py`](tests/test_ab_bench.py) (`Latency <= Baseline`).
   - *If any gate fails, the patch is automatically reverted and discarded.*
3. **Deliver (Verified PR):** Only when all 4 gates pass, pushes branch `asi/auto-<date>` and opens a Pull Request with the A/B benchmark table attached.

</details>

---

## License

[MIT License](LICENSE) © 2026 Mateusz Dzieliński.
