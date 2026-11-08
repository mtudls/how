# Multi-Version `how` Quality Comparison (Docker)

Queries: **100** | Evaluated in isolated Docker containers

| Version | n | % Real Cmd | % Syntax OK (all) | % Syntax OK (of cmds) | % IDK | % Prose | % 429/Err | Median s | P95 s | % Exec OK (of run) | % Skipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5.0 (v0.5.0) | 100 | 99.0 | 98.0 | 99.0 | 1.0 | 0.0 | 0.0 | 1.734 | 3.154 | 26.9 (7/26) | 74.0 |
| 0.4.0 (v0.4.0) | 100 | 52.0 | 52.0 | 100.0 | 34.0 | 11.0 | 3.0 | 1.8 | 3.301 | 60.0 (3/5) | 95.0 |
| 0.3.0 (dc766ab) | 100 | 53.0 | 53.0 | 100.0 | 35.0 | 12.0 | 0.0 | 1.829 | 3.164 | 33.3 (2/6) | 94.0 |
| 0.1.1 (v0.1.1) | 100 | 70.0 | 70.0 | 100.0 | 14.0 | 16.0 | 0.0 | 1.891 | 3.233 | 60.0 (6/10) | 90.0 |

## Pairwise Identical Real Commands

- `0.5.0_vs_0.4.0`: 41.2% identical (21/51)
- `0.5.0_vs_0.3.0`: 35.3% identical (18/51)
- `0.5.0_vs_0.1.1`: 33.3% identical (17/51)
- `0.4.0_vs_0.3.0`: 57.1% identical (32/56)
- `0.4.0_vs_0.1.1`: 34.7% identical (25/72)
- `0.3.0_vs_0.1.1`: 25.0% identical (18/72)

## Methodology Notes
- `Real Cmd` excludes `"I don't know"`, HTTP 429 banners, and prose sentences.
- `Syntax OK` normalizes `<placeholder>` tokens before running `bash -n` so CLI template notation is not misparsed as file redirection.
- Commands execute only inside a disposable `--rm --network none --read-only --cap-drop ALL` sandbox container (5s timeout).
- Groq API key is passed exclusively via environment variable to the `how` container and never written to images or results.
