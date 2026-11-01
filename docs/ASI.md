# Automated Self-Improvement (ASI) & Verification Matrix

`how` incorporates continuous autonomous optimization, safety verification, and local A/B self-testing to evolve performance and behavior without regressions.

---

## 1. Local A/B Self-Testing (`how test`)

When iterating locally on `how`, developers can compare their **work-in-progress (WIP)** against the baseline version (`$PATH` or `git HEAD`):

```bash
how test
how test --stats
```

### Intelligent Mode Selection:
- **Identical Hash**: Runs a fast Verification & Validation (V&V) check.
- **Divergent Hash (WIP detected)**: Triggers a side-by-side **A/B Benchmark Matrix**:
  - **Startup Latency**: Interleaved `AB/BA` cold-start sampling with TrueColor ANSI diff spectrum.
  - **Code Quality**: Syntax & compile integrity check.
  - **Behavioral V&V**: Zero-verbosity compliance, uncertainty refusal (`"I don't know"`), permission-gated OS/stack discovery, Groq triage routing, and sliding cache expiration.
  - **Safety Suite (`tests/test_safety.py`)**: Verifies `bwrap` sandbox isolation, terminal control sequence stripping, non-execution of `omarchy-*` scripts, and non-interactive consent guards.

---

## 2. Cloud AI Architect Reviewer

On GitHub Actions (`.github/workflows/ai-architect.yml`), an autonomous review workflow periodically audits the codebase for latency bottlenecks, dead code removal, and V&V coverage.
