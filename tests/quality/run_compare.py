#!/usr/bin/env python3
"""Compare how versions in Docker; classify responses, check syntax, and execute safe commands in sandboxes."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUALITY = Path(__file__).resolve().parent
RESULTS = QUALITY / "results"
QUERIES = QUALITY / "queries_100.jsonl"
DOCKER_DIR = ROOT / "docker"

# Evaluated versions (newest first)
VERSIONS = [
    {"name": "0.5.0", "ref": "v0.5.0", "image": "how-v0.5.0", "flags": ["-0", "--no-cache", "--no-context"]},
    {"name": "0.4.0", "ref": "v0.4.0", "image": "how-v0.4.0", "flags": ["-0", "--no-cache", "--no-context"]},
    {"name": "0.3.0", "ref": "dc766ab", "image": "how-v0.3.0", "flags": ["-0", "--no-cache", "--no-context"]},
    {"name": "0.1.1", "ref": "v0.1.1", "image": "how-v0.1.1", "flags": ["-0", "--no-cache"]},
]

EXEC_IMAGE = "how-exec-sandbox"
GROQ_CALLS = {"how": 0, "retry": 0}
TIMEOUT_HOW = 45
TIMEOUT_EXEC = 5
MAX_OUT = 4096

# Commands requiring host daemons, root, display server, hardware, or network
SKIP_RE = re.compile(
    r"(?i)(\bsudo\b|\bdoas\b|\bpacman\b|\byay\b|\bparu\b|\bapk\b|\bapt(-get)?\b|\bdnf\b|"
    r"\bsystemctl\b|\bjournalctl\b|\bloginctl\b|\bhostnamectl\b|\btimedatectl\b|\blocalectl\b|"
    r"\bhyprctl\b|\bhyprland\b|\bomarchy\b|\bomarchy-|\bswaymsg\b|\bwayland\b|"
    r"\bwl-copy\b|\bwl-paste\b|\bxclip\b|\bxsel\b|\bgrim\b|\bslurp\b|\bxdg-settings\b|\bnotify-send\b|"
    r"\bnmcli\b|\bbluetoothctl\b|\bwifi\b|\biwctl\b|"
    r"\bdocker\b|\bpodman\b|\bkubectl\b|"
    r"\breboot\b|\bshutdown\b|\bpoweroff\b|\bsystemctl\s+suspend\b|\bsystemctl\s+hibernate\b|"
    r"\bmkfs\b|\bwipefs\b|\bdd\s+if=|\bparted\b|\bfdisk\b|\bcryptsetup\b|"
    r"\bmount\b|\bumount\b|\blsblk\b|\bsmartctl\b|"
    r"\bgh\b|\bgit\s+push\b|\bgit\s+remote\b|\bssh\b|\bssh-copy-id\b|\bscp\b|\brsync\b|"
    r"\bcurl\b|\bwget\b|\bping\b|\bdig\b|\bnslookup\b|\btraceroute\b|"
    r"\bpactl\b|\bpulseaudio\b|\bwpctl\b|\bpipewire\b|"
    r"\bxdg-open\b|\bfirefox\b|\bchromium\b|\bgoogle-chrome\b|"
    r"\bsnapper\b|\bbtrfs\b|\btimeshift\b|"
    r"\bcargo\s+uninstall\b|\bfuser\b|"
    r"\bpasswd\b|\bchfn\b|\busermod\b|\buseradd\b|\bgroupmod\b|\bchown\b|\bchmod\s+[0-7]{3,4}\s+/|"
    r"\brm\s+-rf\s+/|\bmktemp\b.*\b/\b)"
)

PLACEHOLDER_RE = re.compile(r"<[A-Za-z0-9_.-]+>")
BASH_BLOCK = re.compile(r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)```", re.S | re.I)
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
CLIP_CACHE_SUFFIX = re.compile(r"\s*\[(?:copied[^\]]*|cache)\]\s*$", re.I)

PROSE_PREFIX_RE = re.compile(
    r"^(?:Create\s+(?:a|key)|Install\s+plugins|Use\s+(?:a|Neovim|plugins)|Add\s+(?:custom|`alias)|"
    r"Edit\s+|Remove\s+its|Avoid\s+running|Copy\s+the|Save\s+the|No,\s+|Yes[—,-]\s*|"
    r"It\s+displays|The\s+console|Omarchy\s+(?:provides|authenticates)|Hyprland\s+does\s+not|"
    r"Terraform\s+cannot|Do\s+not\s+run|You\s+cannot\b)"
)


def load_api_key() -> str:
    env = os.environ.get("GROQ_API_KEY", "").strip()
    if env:
        return env
    cfg = Path.home() / ".config/how/config.json"
    if cfg.exists():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        key = (data.get("api_key") or "").strip()
        if key:
            return key
    raise SystemExit("No GROQ_API_KEY / config api_key")


def load_queries() -> list[dict]:
    rows = []
    for line in QUERIES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run(cmd: list[str], *, env: dict | None = None, timeout: int = 60, input_text: str | None = None):
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        input=input_text,
    )


def build_images() -> None:
    print("== building how images ==")
    for v in VERSIONS:
        print(f"  build {v['name']} from {v['ref']} ...")
        r = run([str(DOCKER_DIR / "build.sh"), v["ref"], v["image"]], timeout=300)
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            raise SystemExit(f"build failed for {v['name']}")
        print(f"  OK {v['image']}")
    print("== building exec sandbox ==")
    r = run(
        ["docker", "build", "-t", EXEC_IMAGE, "-f", str(DOCKER_DIR / "Dockerfile.exec"), str(DOCKER_DIR)],
        timeout=300,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        raise SystemExit("exec sandbox build failed")
    print(f"  OK {EXEC_IMAGE}")


def is_rate_limit_text(text: str) -> bool:
    low = (text or "").lower()
    return "429 rate limit" in low or "rate limit reached" in low or "too many requests" in low


def is_idk_text(text: str) -> bool:
    clean = (text or "").strip().lower().rstrip(".!?:")
    return clean in ("i don't know", "i dont know", "idk", "nie wiem")


def is_prose_sentence(line: str) -> bool:
    """Returns True if `line` is a natural-language prose sentence rather than a shell command."""
    s = line.strip()
    if not s:
        return True
    if PROSE_PREFIX_RE.search(s):
        return True
    # Prose with inline backticks and trailing period (e.g. "Use `git commit -m ...`.")
    if s.endswith(".") and "`" in s and s[0].isupper() and " " in s:
        return True
    # Multi-word sentence starting with an uppercase word and ending with a period, with no shell operators
    words = s.split()
    if (
        len(words) >= 5
        and s[0].isupper()
        and s.endswith(".")
        and not any(op in s for op in ("|", "&&", "||", ";", "--", " -"))
    ):
        return True
    return False


def classify_response(stdout: str, stderr: str = "", exit_code: int = 0) -> tuple[str, str | None, bool]:
    """
    Classifies `how` output into `(response_kind, command_or_text, is_real_command)`:
      - `rate_limit`: 429 rate limit banner
      - `error`: API / connection / runtime failure
      - `idk`: strict uncertainty refusal ("I don't know")
      - `prose`: conceptual natural-language sentence (not an executable command)
      - `command`: executable shell command
    """
    clean_out = ANSI.sub("", stdout or "").strip()
    clean_err = ANSI.sub("", stderr or "").strip()
    combined = f"{clean_out}\n{clean_err}"

    if is_rate_limit_text(combined):
        return "rate_limit", None, False

    if exit_code != 0 and not clean_out:
        return "error", None, False

    if any(k in combined for k in ("Groq API error", "Connection error:", "Verification error:")):
        return "error", None, False

    if not clean_out:
        return "error", None, False

    m = BASH_BLOCK.search(clean_out)
    if m:
        body = m.group(1).strip()
        lines = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if lines:
            cmd = " ".join(ln.rstrip("\\").rstrip() for ln in lines).strip()
            if cmd and not is_idk_text(cmd):
                return "command", cmd, True

    for ln in clean_out.splitlines():
        ln = CLIP_CACHE_SUFFIX.sub("", ln.strip()).strip()
        if not ln:
            continue
        if ln.startswith("!") or ln.lower().startswith("error"):
            continue
        if ln.startswith("Login") or "GROQ_API_KEY" in ln:
            continue
        if ln.startswith("$ "):
            ln = ln[2:].strip()
        if is_idk_text(ln):
            return "idk", ln, False
        if is_prose_sentence(ln):
            return "prose", ln, False
        return "command", ln, True

    return "error", None, False


def extract_command(text: str) -> str | None:
    """Extracts only a real executable shell command from `how` output, or None."""
    kind, cmd, is_real = classify_response(text)
    return cmd if (kind == "command" and is_real) else None


def normalize_placeholders_for_syntax(cmd: str) -> tuple[str, bool]:
    """
    Replaces `<placeholder>` tokens (e.g. `<repo-name>`, `<owner>/<repo>`) with a safe token
    so `bash -n` validates command syntax instead of failing on `<` file redirection.
    """
    if not cmd:
        return "", False
    has_ph = bool(PLACEHOLDER_RE.search(cmd))
    normalized = PLACEHOLDER_RE.sub("placeholder_arg", cmd)
    return normalized, has_ph


def bash_n_ok(cmd: str) -> bool:
    if not cmd or not cmd.strip():
        return False
    norm_cmd, _ = normalize_placeholders_for_syntax(cmd)
    try:
        r = run(["bash", "-n", "-c", norm_cmd], timeout=3)
        return r.returncode == 0
    except Exception:
        return False


def classify_exec(cmd: str | None, real_command: bool = True) -> tuple[str, str | None]:
    """Return `(action, skip_reason)` where `action` is `'execute'` or `'skip'`."""
    if not real_command or not cmd or not cmd.strip():
        return "skip", "no command"
    if SKIP_RE.search(cmd):
        return "skip", "needs host"
    if re.search(r"(?i)\b(vim|nvim|nano|micro|less|more|top|htop|btop|fzf|tmux\s+(?:attach|new))\b", cmd):
        return "skip", "needs host"
    if re.search(r">\s*/(etc|boot|usr|var|sys|proc|dev)/", cmd):
        return "skip", "needs host"
    if PLACEHOLDER_RE.search(cmd) or re.search(r"\b(your_command|/path/to/)\b", cmd):
        return "skip", "template placeholder"
    return "execute", None


def run_how(image: str, flags: list[str], query: str, api_key: str) -> dict:
    cmd = [
        "docker", "run", "--rm",
        "--network", "bridge",
        "--user", "10001:10001",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "512m",
        "--cpus", "1",
        "--pids-limit", "128",
        "-e", "GROQ_API_KEY",
        "-e", "HOW_NO_BROWSER=1",
        "-e", "HOW_NO_PROMPT=1",
        "-e", "CI=1",
        "-e", "TESTING=1",
        "-e", "HOME=/home/howuser",
        image,
        *flags,
        query,
    ]
    env = os.environ.copy()
    env["GROQ_API_KEY"] = api_key
    t0 = time.monotonic()
    try:
        r = run(cmd, env=env, timeout=TIMEOUT_HOW)
        elapsed = time.monotonic() - t0
        GROQ_CALLS["how"] += 1
        out = (r.stdout or "")[-MAX_OUT:]
        err = (r.stderr or "")[-MAX_OUT:]
        # Retry once on rate limit regardless of exit code (how prints 429 banner and exits 0)
        if is_rate_limit_text(out) or is_rate_limit_text(err) or (r.returncode != 0 and "429" in err):
            GROQ_CALLS["retry"] += 1
            time.sleep(8)
            t0 = time.monotonic()
            r = run(cmd, env=env, timeout=TIMEOUT_HOW)
            elapsed = time.monotonic() - t0
            GROQ_CALLS["how"] += 1
            out = (r.stdout or "")[-MAX_OUT:]
            err = (r.stderr or "")[-MAX_OUT:]
        return {
            "exit_code": r.returncode,
            "stdout": out,
            "stderr": err,
            "elapsed_s": round(elapsed, 3),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        GROQ_CALLS["how"] += 1
        raw_out = (e.stdout or b"") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
        return {
            "exit_code": 124,
            "stdout": raw_out,
            "stderr": "timeout",
            "elapsed_s": TIMEOUT_HOW,
            "timeout": True,
        }


def exec_in_sandbox(cmd: str) -> dict:
    docker_cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--user", "10001:10001",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--tmpfs", "/home/sandbox:rw,nosuid,size=16m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        EXEC_IMAGE,
        "bash", "-c", cmd,
    ]
    t0 = time.monotonic()
    try:
        r = run(docker_cmd, timeout=TIMEOUT_EXEC)
        elapsed = time.monotonic() - t0
        return {
            "status": "executed",
            "exit_code": r.returncode,
            "stdout": (r.stdout or "")[:MAX_OUT],
            "stderr": (r.stderr or "")[:MAX_OUT],
            "elapsed_s": round(elapsed, 3),
            "timeout": False,
            "ok": r.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "executed",
            "exit_code": 124,
            "stdout": "",
            "stderr": "timeout",
            "elapsed_s": TIMEOUT_EXEC,
            "timeout": True,
            "ok": False,
        }


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    real_cmds = [r for r in rows if r.get("real_command")]
    syn_ok = [r for r in real_cmds if r.get("syntax_ok")]
    idk_rows = [r for r in rows if r.get("response_kind") == "idk"]
    prose_rows = [r for r in rows if r.get("response_kind") == "prose"]
    err_rows = [
        r for r in rows
        if r.get("how_timeout") or r.get("response_kind") in ("rate_limit", "error")
    ]
    times = [r["how_elapsed_s"] for r in rows if r.get("how_elapsed_s") is not None]
    exec_rows = [r for r in rows if r.get("exec_status") == "executed"]
    skip_rows = [r for r in rows if r.get("exec_status") == "skipped"]
    exec_ok = [r for r in exec_rows if r.get("exec_ok")]
    exec_fail = [r for r in exec_rows if not r.get("exec_ok")]
    return {
        "n": n,
        "with_command": len(real_cmds),
        "pct_with_command": round(100 * len(real_cmds) / n, 1) if n else 0.0,
        "pct_syntax_ok": round(100 * len(syn_ok) / n, 1) if n else 0.0,
        "pct_syntax_ok_of_cmds": round(100 * len(syn_ok) / len(real_cmds), 1) if real_cmds else 0.0,
        "pct_idk": round(100 * len(idk_rows) / n, 1) if n else 0.0,
        "pct_prose": round(100 * len(prose_rows) / n, 1) if n else 0.0,
        "pct_how_error_timeout": round(100 * len(err_rows) / n, 1) if n else 0.0,
        "n_idk": len(idk_rows),
        "n_prose": len(prose_rows),
        "n_error_or_429": len(err_rows),
        "median_s": round(statistics.median(times), 3) if times else None,
        "p95_s": round(percentile(times, 0.95), 3) if times else None,
        "pct_exec_ok": round(100 * len(exec_ok) / n, 1) if n else 0.0,
        "pct_exec_ok_of_executed": round(100 * len(exec_ok) / len(exec_rows), 1) if exec_rows else 0.0,
        "pct_skipped": round(100 * len(skip_rows) / n, 1) if n else 0.0,
        "pct_exec_fail": round(100 * len(exec_fail) / n, 1) if n else 0.0,
        "n_exec": len(exec_rows),
        "n_skip": len(skip_rows),
        "n_exec_ok": len(exec_ok),
    }


def evaluate_row_from_raw(raw_row: dict) -> dict:
    """Re-classifies a raw progress.jsonl row using fixed command/prose/IDK/placeholder rules."""
    stdout = raw_row.get("raw_response_tail") or raw_row.get("command") or ""
    stderr = raw_row.get("how_stderr_tail") or ""
    exit_code = raw_row.get("how_exit", 0)
    kind, extracted, real_cmd = classify_response(stdout, stderr, exit_code)
    cmd = extracted if real_cmd else None
    syntax = bash_n_ok(cmd) if real_cmd and cmd else False
    action, skip_reason = classify_exec(cmd, real_command=real_cmd)

    row = dict(raw_row)
    row["response_kind"] = kind
    row["command"] = extracted or ""
    row["real_command"] = real_cmd
    row["syntax_ok"] = syntax
    if action == "skip":
        row["exec_status"] = "skipped"
        row["exec_skip_reason"] = skip_reason
        row["exec_ok"] = None
        row["exec_exit"] = None
    return row


def write_outputs(all_rows: list[dict], n_queries: int) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    by_ver = {}
    for v in VERSIONS:
        v_rows = [r for r in all_rows if r["version"] == v["name"]]
        if v_rows:
            by_ver[v["name"]] = summarize(v_rows)

    pairwise = {}
    names = [v["name"] for v in VERSIONS if v["name"] in by_ver]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            by_q_a = {r.get("query"): r for r in all_rows if r["version"] == a and r.get("query")}
            by_q_b = {r.get("query"): r for r in all_rows if r["version"] == b and r.get("query")}
            common_qs = sorted(set(by_q_a.keys()) & set(by_q_b.keys()))
            same = total = 0
            for qtext in common_qs:
                ra = by_q_a[qtext]
                rb = by_q_b[qtext]
                ca = ra.get("command") if (ra and ra.get("real_command")) else None
                cb = rb.get("command") if (rb and rb.get("real_command")) else None
                if ca or cb:
                    total += 1
                    if ca and cb and ca.strip() == cb.strip():
                        same += 1
            pairwise[f"{a}_vs_{b}"] = {
                "identical_pct": round(100 * same / total, 1) if total else None,
                "n": total,
                "identical": same,
            }

    summary = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "n_queries": n_queries,
        "versions": VERSIONS,
        "by_version": by_ver,
        "pairwise_identical_commands": pairwise,
        "groq_calls": GROQ_CALLS,
        "notes": [
            "Real shell commands are separated from 'I don't know', 429 rate-limit banners, and conceptual prose.",
            "Angle-bracket placeholders (<repo-name>, <name>) are normalized before bash -n syntax validation.",
            "Suggested commands execute only inside disposable --network none --read-only containers.",
        ],
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    csv_path = RESULTS / "results.csv"
    fields = [
        "version", "id", "query_source", "query", "response_kind", "command",
        "real_command", "syntax_ok", "how_exit", "how_elapsed_s", "how_timeout",
        "exec_status", "exec_skip_reason", "exec_ok", "exec_exit",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    lines = [
        "# Multi-Version `how` Quality Comparison (Docker)",
        "",
        f"Queries: **{n_queries}** | Evaluated in isolated Docker containers",
        "",
        "| Version | n | % Real Cmd | % Syntax OK (all) | % Syntax OK (of cmds) | % IDK | % Prose | % 429/Err | Median s | P95 s | % Exec OK (of run) | % Skipped |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for v in VERSIONS:
        if v["name"] not in by_ver:
            continue
        s = by_ver[v["name"]]
        lines.append(
            f"| {v['name']} ({v['ref']}) | {s['n']} | {s['pct_with_command']} | {s['pct_syntax_ok']} | "
            f"{s['pct_syntax_ok_of_cmds']} | {s['pct_idk']} | {s['pct_prose']} | "
            f"{s['pct_how_error_timeout']} | {s['median_s']} | {s['p95_s']} | "
            f"{s['pct_exec_ok_of_executed']} ({s['n_exec_ok']}/{s['n_exec']}) | {s['pct_skipped']} |"
        )
    lines += ["", "## Pairwise Identical Real Commands", ""]
    for k, v in pairwise.items():
        lines.append(f"- `{k}`: {v['identical_pct']}% identical ({v['identical']}/{v['n']})")
    lines += [
        "",
        "## Methodology Notes",
        "- `Real Cmd` excludes `\"I don't know\"`, HTTP 429 banners, and prose sentences.",
        "- `Syntax OK` normalizes `<placeholder>` tokens before running `bash -n` so CLI template notation is not misparsed as file redirection.",
        "- Commands execute only inside a disposable `--rm --network none --read-only --cap-drop ALL` sandbox container (5s timeout).",
        "- Groq API key is passed exclusively via environment variable to the `how` container and never written to images or results.",
        "",
    ]
    md = "\n".join(lines)
    (RESULTS / "table.md").write_text(md, encoding="utf-8")
    print("\n" + md)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare `how` versions in Docker or recompute metrics.")
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Recompute summary.json, results.csv, and table.md offline from existing progress.jsonl",
    )
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    progress_path = RESULTS / "progress.jsonl"

    if args.recompute:
        if not progress_path.exists():
            raise SystemExit(f"Cannot --recompute: {progress_path} not found")
        all_rows = []
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                all_rows.append(evaluate_row_from_raw(json.loads(line)))
        GROQ_CALLS["how"] = len(all_rows)
        n_q = len({r["id"] for r in all_rows})
        write_outputs(all_rows, n_queries=n_q)
        return

    api_key = load_api_key()
    queries = load_queries()
    limit = int(os.environ.get("HOW_QUALITY_LIMIT", "0") or 0)
    if limit > 0:
        queries = queries[:limit]
    print(f"queries: {len(queries)}")

    build_images()

    done = set()
    all_rows: list[dict] = []
    if progress_path.exists() and os.environ.get("HOW_QUALITY_RESUME", "1") == "1":
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = evaluate_row_from_raw(json.loads(line))
            done.add((row["version"], row["id"]))
            all_rows.append(row)
        print(f"resume: {len(done)} already done")

    mode = "a" if done else "w"
    with progress_path.open(mode, encoding="utf-8") as prog:
        for v in VERSIONS:
            print(f"\n== version {v['name']} ==")
            for q in queries:
                key = (v["name"], q["id"])
                if key in done:
                    continue
                print(f"  [{v['name']}] #{q['id']} {q['query'][:60]}...", flush=True)
                how = run_how(v["image"], v["flags"], q["query"], api_key)
                if isinstance(how["stdout"], (bytes, bytearray)):
                    how["stdout"] = how["stdout"].decode("utf-8", "replace")[-MAX_OUT:]
                kind, extracted, real_cmd = classify_response(
                    how["stdout"], how["stderr"], how["exit_code"]
                )
                cmd = extracted if real_cmd else None
                syntax = bash_n_ok(cmd) if (real_cmd and cmd) else False
                action, skip_reason = classify_exec(cmd, real_command=real_cmd)
                if action == "execute" and cmd:
                    ex = exec_in_sandbox(cmd)
                    exec_status = "executed"
                    exec_ok = ex["ok"]
                    exec_exit = ex["exit_code"]
                    exec_out = ex["stdout"]
                    exec_err = ex["stderr"]
                    exec_skip = None
                else:
                    exec_status = "skipped"
                    exec_ok = None
                    exec_exit = None
                    exec_out = ""
                    exec_err = ""
                    exec_skip = skip_reason

                row = {
                    "version": v["name"],
                    "ref": v["ref"],
                    "id": q["id"],
                    "query": q["query"],
                    "query_source": q.get("source"),
                    "response_kind": kind,
                    "how_exit": how["exit_code"],
                    "how_elapsed_s": how["elapsed_s"],
                    "how_timeout": how["timeout"],
                    "how_stderr_tail": (how.get("stderr") or "")[:500],
                    "raw_response_tail": (how.get("stdout") or "")[:800],
                    "command": extracted or "",
                    "real_command": real_cmd,
                    "syntax_ok": syntax,
                    "exec_status": exec_status,
                    "exec_skip_reason": exec_skip,
                    "exec_ok": exec_ok,
                    "exec_exit": exec_exit,
                    "exec_stdout_tail": (exec_out or "")[:500],
                    "exec_stderr_tail": (exec_err or "")[:500],
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                blob = json.dumps(row)
                if api_key and api_key in blob:
                    raise SystemExit("refusing to write row containing api key")
                prog.write(json.dumps(row, ensure_ascii=False) + "\n")
                prog.flush()
                all_rows.append(row)
                time.sleep(0.35)

    write_outputs(all_rows, n_queries=len(queries))


if __name__ == "__main__":
    main()
