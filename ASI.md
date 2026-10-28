# Automated Self-Improvement (ASI) & Verification Matrix

`how` incorporates continuous autonomous optimization and local A/B self-testing to evolve performance and behavior without regressions.

---

## 1. Local A/B Self-Testing (`how test`)

When iterating locally on `how`, developers can instantly compare their **work-in-progress (WIP)** against the version installed in `$PATH`:

```bash
how test
```

### Intelligent Mode Selection:
- **Identical Hash**: If the working copy matches the installed binary, runs a fast native Verification & Validation (V&V) check.
- **Divergent Hash (WIP detected)**: Automatically triggers an side-by-side **A/B Benchmark Matrix**:
  - **Startup Latency**: Sub-millisecond cold start comparison.
  - **Performance Score**: Normalized index (0–100).
  - **Code Quality**: Syntax & compile integrity check.
  - **Behavioral V&V**: Zero-verbosity compliance, uncertainty checks (`"I don't know"`), and sliding cache expiration.
  - **Ready-to-Ship Flow**: On success, outputs copy-pasteable Git and GitHub CLI commands (`git commit`, `git push`, `gh pr create`).

---

## 2. Cloud AI Architect Reviewer

On GitHub Actions, an autonomous reasoning workflow runs periodically to review the entire codebase:

- **Schedule**: Weekly cron (`.github/workflows/ai-architect.yml`) or on demand.
- **Philosophy**: End-user speed and outcome are absolute. Dead code, redundant RAG layers, and unnecessary abstractions are flagged for removal.
- **Output**: Generates a prioritized GitHub Issue with concrete refactoring recommendations.
