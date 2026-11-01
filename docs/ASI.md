# Automated Testing & Self-Improvement (ASI)

**Effect:** Every change to `how` is automatically checked for speed, accuracy, and security before it reaches you—locally via `how test` and in the cloud via GitHub Actions.

| ASI Tier | Status | Effect (What happens) |
| :--- | :---: | :--- |
| **1. Human-Assisted Local Loop** (`how test`) | ✅ `LIVE` | Compares `[A] Baseline` vs `[B] WIP`, runs V&V + safety checks, and gives a pass/fail verdict. |
| **2. Autonomous Cloud Reviewer** (`ai-architect.yml`) | 🟡 `ADVISORY` | Runs weekly on GitHub Actions, audits [`how`](../how) + V&V scores, and opens a GitHub Issue with proposals. |
| **3. Closed-Loop Self-Patching** (`Code → Gate → PR`) | ⏳ `PLANNED` | Generates a patch, enforces hard V&V + latency gates, discards regressions, and opens a ready-to-merge PR. |

---

## 1. Local Self-Test (`how test`)

**Effect:** One command tells you if your local edits made `how` faster or slower, and verifies nothing broke.

```bash
how test          # Fast check + side-by-side speed comparison
how test --stats  # 10-round statistical benchmark
```

<details>
<summary><b>How `how test` works under the hood (way / form)</b></summary>

- **Automatic Baseline Detection:** Compares your work-in-progress [`how`](../how) (and transpiled Rust binary) against the committed `git HEAD` or installed `$PATH` binary.
- **4 Verification Axes ([`tests/test_vv_suite.py`](../tests/test_vv_suite.py)):**
  1. **Startup Latency:** Interleaved `AB/BA` cold-start measurements (`~1–5 ms` Rust vs `~45–200 ms` Python).
  2. **Cache & Local Docs:** Verifies SQLite WAL sliding expiration, retention units (`m`, `h`, `D`, `M`), and doc fingerprinting.
  3. **Behavior & UX:** Verifies `--help` structure, strict `"I don't know"` uncertainty refusal, graduated context modes (`careful`, `yolo`, `dry-run`), and triage routing.
  4. **Security & Sandbox ([`tests/test_safety.py`](../tests/test_safety.py)):** Verifies Bubblewrap (`bwrap`) isolation flags, non-execution of `omarchy-*` scripts, ANSI/OSC escape stripping, Rust binary parity, and AST static quality invariants.

</details>

---

## 2. Lean CI/CD & Autonomous Review

**Effect:** Every push and release is verified for code quality, leaked secrets, and security in under 2 minutes while staying well within the GitHub Actions Free Plan.

<details>
<summary><b>How the GitHub Actions pipelines are structured (way / form)</b></summary>

- **Free-Plan Optimizations across `.github/workflows/*.yml`:**
  - `concurrency` groups with `cancel-in-progress: true` immediately cancel superseded runs on rapid pushes.
  - Strict `timeout-minutes: 5` guards prevent hung jobs from consuming runner quota.
  - Consolidated single-VM V&V job ([`.github/workflows/vv.yml`](../.github/workflows/vv.yml)) runs Python V&V, safety unit tests, native Rust transpilation, and `install.sh` tests in one runner boot.
- **Static & Security Gates:**
  - [`.github/workflows/lint.yml`](../.github/workflows/lint.yml): `py_compile`, `ruff`, `flake8`, and `shellcheck install.sh`.
  - [`.github/workflows/security.yml`](../.github/workflows/security.yml): `bandit` SAST scan + sandbox unit suite.
  - [`.github/workflows/secret-scan.yml`](../.github/workflows/secret-scan.yml): Regex key guard + `gitleaks`.
  - [`.github/workflows/ai-architect.yml`](../.github/workflows/ai-architect.yml): Weekly scheduled AI maintainer review for latency and dead-code audits.
  - [`.github/workflows/release.yml`](../.github/workflows/release.yml): Compiles `how-linux-x86_64`, generates `SHA256SUMS.txt`, and publishes release artifacts on `v*.*.*` tags.

</details>
