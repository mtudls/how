# Docker Multi-Version Quality & Sandbox Harness for `how`

Lightweight, isolated container setup for benchmarking `how` across git refs/tags and validating suggested shell commands inside a disposable `--network none` sandbox.

The Groq API key **never** enters image layers, logs, or saved results—it is passed solely as an ephemeral `GROQ_API_KEY` environment variable to the `how` container.

## Build Versioned Images

```bash
./docker/build.sh v0.4.0            # builds how-v0.4.0
./docker/build.sh dc766ab how-v0.3.0
```

## Run a Single Query in Container (Zero Host Mounts)

```bash
docker run --rm -e GROQ_API_KEY -e HOW_NO_PROMPT=1 how-v0.4.0 \
  -0 --no-cache --no-context "to ping google"
```

## Multi-Version Quality Comparison

```bash
# Recompute & audit metrics offline from existing progress.jsonl (<1s, 0 API calls):
python3 tests/quality/run_compare.py --recompute

# Run full live Docker comparison across versions:
python3 tests/quality/run_compare.py
```

### How `run_compare.py` Works
1. Builds versioned `how` images from git refs and the `how-exec-sandbox` image.
2. Runs each query from `tests/quality/queries_100.jsonl` inside the isolated `how` container.
3. Classifies output into `real_command`, `idk` (`"I don't know"`), `prose` (conceptual answer), or `rate_limit` / `error`.
4. Validates command syntax via `bash -n` (after normalizing `<placeholder>` tokens so template arguments are not misparsed as file redirections).
5. Executes safe, self-contained commands inside a disposable `--network none --read-only --cap-drop ALL` sandbox container while marking host/daemon/template commands as `skipped`.
6. Writes unified metrics to `tests/quality/results/` (`summary.json`, `results.csv`, `table.md`).
