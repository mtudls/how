# how

Ask in plain words. Get the exact terminal command.

Built for **Omarchy**, **Linux**, and your local project stack.

> **Document Guide:**
> - **Part 1 — `[LIVE • v0.5]`**: Features you can use right now (`✅`).
> - **Part 2 — `[ROADMAP • v0.6+]`**: Upcoming features in design (`⏳`).
> - *Technical details (**way / form**) are inside expandable `▸` sections.*

---

# Part 1 — `[LIVE • v0.5]` What `how` Does Today

## Quick Start

```bash
git clone https://github.com/mdsyseng/how.git && cd how
./install.sh      # Installs `how` locally
how auth login    # Free API key ($0, no card): console.groq.com/keys
```

## Everyday Use (Effect → Command)

| Status | Effect (What you get) | Command (What to type) |
| :---: | :--- | :--- |
| ✅ `LIVE` | **Command + short explanation + `🟢/🟡/🔴` safety badge** | `how to switch audio output` |
| ✅ `LIVE` | **Command only (no extra text)** | `how -0 to find largest files` |
| ✅ `LIVE` | **Offline `<1 ms` visual pipeline & flag breakdown** | `how explain` *(or `how explain "tar -xzvf a.tgz"`)* |
| ✅ `LIVE` | **Instant command repair & error diagnostics** | `how fix` *(or `how fix "permission denied"`)* |
| ✅ `LIVE` | **Run the last suggested command (with safety check)** | `how run` |
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
  2. **Step 2 (Smarter Model on Platform of Choice):** If still uncertain, reaches out to your configured reasoning provider (`gemini`, `anthropic`, `openai`, `openrouter`, `cli:claude`, or Groq's `deepseek-r1-distill-llama-70b` / `qwen-qwq-32b` pool). Uncertain `"I don't know"` responses are never cached.
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

# Part 2 — `[ROADMAP • v0.5+]` Planned Next

> [!NOTE]
> Everything in **Part 2** is **planned architecture (`⏳ PLANNED`)** and not yet active in the CLI.
> Proposed future commands are prefixed with `[PLANNED]` to distinguish them from live `v0.4` commands.

| Status | Planned Capability | Effect (What it will do for you) |
| :---: | :--- | :--- |
| ⏳ `v0.5` | **1. System-1 Offline Reflex (`basal` / `jev`)** | Answer everyday Linux/Omarchy commands in `<3 ms` offline without calling the cloud. |
| ⏳ `v0.5` | **2. Repeat-Question Memory** | Detect when you ask the same question twice and ask if the previous command failed. |
| ⏳ `v0.5` | **3. `where` + `om` Unified CLI** | Find *where* any file, config, log, or port is (`om where ...`) alongside `om how ...`. |
| ⏳ `v0.5` | **4. Normie Safety Traffic Lights** | Label every command `🟢 Safe`, `🟡 Modifies files`, or `🔴 Destructive / Admin` in plain words. |
| ⏳ `v0.5` | **5. Closed-Loop Autonomous ASI** | Automatically turn optimization ideas or broken model IDs into verified, benchmark-tested PRs. |

---

### ⏳ 1. System-1 Models (`basal`, `jev`) + Cloud LLM Hybrid
**Planned Effect:** Common everyday tasks resolve locally in `<3 ms` with zero internet needed, while novel or tricky questions automatically step up to fast or deep cloud LLMs.

<details>
<summary><b>▸ Way / Form: 3-Tier System-1 / System-2 routing architecture</b></summary>

- **Tier 0 — Local System-1 Reflex (`<3 ms`, offline `basal` / `jev` micro-model):**
  - Classifies user intent (`how` vs `where` vs `fix`).
  - Scores command danger (`read-only` vs `mutating` vs `destructive`).
  - Directly synthesizes canonical commands for the top ~500 Linux/Omarchy operations offline.
- **Tier 1 — Fast Cloud LPU (`~150 ms`, Groq):**
  - Combines local `tldr`/`man`/`omarchy-*` RAG with fast LPU generation for custom flags.
- **Tier 2 — Deep Thinking (`~1–3 s`, `-t` / `--think`):**
  - Routes multi-step debugging (bootloaders, kernel modules, Wayland/PipeWire) to reasoning models (`DeepSeek-R1`, `Claude`, `Gemini`, `OpenAI`).

</details>

### ⏳ 2. Repeat-Question Memory ("Did the previous answer not work?")
**Planned Effect:** If you ask the same question again within minutes, `how` won't blindly repeat the same cached command—it will ask if the first one failed and offer a deeper fix.

<details>
<summary><b>▸ Way / Form: SQLite `hit_count` tracking & interactive escalation prompt</b></summary>

- *(Already live in `v0.4`)*: Cache hits show a one-line tip: `💡 Didn't work? Re-run fresh with deep thinking: how -t --no-cache <query>`.
- *(Planned for `v0.5`)*: Track `hit_count` and `last_hit_at` in `~/.cache/how/cache.db`. When `hit_count >= 1` within 30 minutes in an interactive TTY:
  ```text
  [PLANNED] ? You asked this 2m ago. Did the previous command not work?
    [Y] Try a fresh Deep Thinking solution (-t --no-cache)
    [e] Attach last terminal error / exit code and fix it
    [n] Show the cached command again
  ```

</details>

### ⏳ 3. From `how` to `where` — and the Unified `om` CLI ("om!")
**Planned Effect:** Use one friendly 2-letter tool (**`om`**) to learn **how** to do anything, find **where** any file or config is stored, or **fix** your last failed command.

<details>
<summary><b>▸ Way / Form: `where` local probes + `om` wrapper syntax</b></summary>

```text
# [PLANNED SYNTAX — v0.5+]
om how to switch audio output          # Procedural: how to do X
om where is hyprland monitor config    # Spatial: locate file, config, log, binary, or port
om fix                                 # Diagnostic: inspect last failed command & propose fix
om !                                   # Action: preview & execute last suggested command
```

- **`where` Engine:** Combines fast read-only local probes (`fd`, `plocate`, `rg`, `ss`, `systemctl show`, XDG paths) with System-1/LLM ranking to return the exact file path and line number.

</details>

### ⏳ 4. Dual-Persona UX: Simplest "Normie" User × Systems Programmer
**Planned Effect:** Beginners get plain-English safety ratings and zero-jargon explanations, while systems programmers keep sub-millisecond native speed and strict sandboxing.

<details>
<summary><b>▸ Way / Form: Traffic-light risk classifier & flag explainer</b></summary>

- **Traffic-Light Risk Badges (`[PLANNED — v0.5]`):**
  - `🟢 Safe (read-only)` — only inspects info (`ls`, `df`, `ip`, `pacman -Si`)
  - `🟡 Modifies files/packages` — edits configs or installs packages (`pacman -S`, `cp`, `sed -i`)
  - `🔴 Destructive / Admin` — deletes data or alters boot/disks (`rm -rf`, `dd`, `mkfs`); requires explicit confirmation in `how run`.
- **Plain-English Flag Breakdown (`[PLANNED — v0.5]`):** Optional 1-line breakdown of each flag (`-r` = recursive, `-f` = force) so new Linux users learn naturally.

</details>

### ⏳ 5. Closed-Loop Autonomous Self-Improvement (ASI: `Code → Gate → PR`)
**Planned Effect:** Instead of just opening advisory GitHub Issues, `how` will test its own optimization patches and only open a Pull Request when every quality, safety, and speed check passes.

| ASI Tier | Status | Effect |
| :--- | :---: | :--- |
| **1. Human-Assisted Local Loop** (`how test`) | ✅ `LIVE` | Benchmarks `[A] Baseline` vs `[B] WIP`, runs V&V + safety checks, and gives a pass/fail verdict. |
| **2. Autonomous Cloud Reviewer** (`ai-architect.yml`) | 🟡 `ADVISORY` | Runs weekly on GitHub Actions, analyzes [`how`](how) + V&V scores, and opens a GitHub Issue with proposals. |
| **3. Closed-Loop Self-Patching** (`Code → Gate → PR`) | ⏳ `PLANNED` | Generates a patch, enforces hard V&V + latency gates, discards regressions, and opens a ready-to-merge PR. |

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
