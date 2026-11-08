#!/usr/bin/env python3
"""
Autonomous AI Maintainer & Closed-Loop ASI (`Code -> Gate -> PR`) for `how`.

Reviews the codebase and optionally applies bounded `<<<< SEARCH ... ==== ... >>>> REPLACE`
patches, enforcing 4 deterministic Hard Verification Gates before ever proposing a PR:
1. Rust AST Transpilation & Compilation (`scripts/transpile_rust.py`)
2. 5-Axis V&V Convergence Suite (`tests/test_vv_suite.py` == 100.0/100)
3. Safety, Sandbox & Static AST Suite (`tests/test_safety.py`)
4. A/B Latency & Parity Benchmark (`tests/test_ab_bench.py`)

If any verification gate fails, any proposed patch is automatically rolled back and discarded.
"""

import argparse
import datetime
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOW_PATH = os.path.join(REPO_ROOT, "how")
TRANSPILER_PATH = os.path.join(REPO_ROOT, "scripts", "transpile_rust.py")
TEST_SUITE_PATH = os.path.join(REPO_ROOT, "tests", "test_vv_suite.py")
SAFETY_SUITE_PATH = os.path.join(REPO_ROOT, "tests", "test_safety.py")
AB_BENCH_PATH = os.path.join(REPO_ROOT, "tests", "test_ab_bench.py")

SYSTEM_PROMPT = """You are a world-class Principal Systems Architect & Performance Lead maintaining the `how` CLI repository (an ultra-fast Linux & Omarchy CLI assistant).

CRITICAL PHILOSOPHY:
- End-user outcome is everything.
- Zero-friction, sub-5ms startup latency, minimalist terminal output, and ironclad behavior reliability.
- Ruthless reduction of bloat: eliminate unnecessary code, overcomplicated RAG, or slow abstractions.
- Verification & Validation (V&V) drives every change: every proposed patch must pass all 4 Hard Verification Gates (Rust compile, 100.0/100 V&V score, 100% safety suite, and A/B latency check).

YOUR TASK:
Analyze the code, review performance and behavior patterns, and generate a structured Architecture & Optimization Report.
If you have a concrete, surgical, safe code optimization for `how`, include a bounded SEARCH/REPLACE block:
<<<< SEARCH
exact existing lines
====
updated replacement lines
>>>> REPLACE

FORMAT:
## 1. Executive Summary & V&V Assessment
Concise verdict on the current architecture state and composite V&V score.

## 2. Ruthless Simplification & Code Removal
What code/layers can be cut or simplified without hurting user outcome?

## 3. Latency & Performance Breakthroughs
Startup time bottlenecks, memory, caching improvements, or Tier-0 reflex refinements.

## 4. Behavior Quality & V&V Evolution (Zero Bloat)
Concrete new behavioral checks and edge cases to guard real user workflows without slowing down CI.

## 5. Prioritized Action Plan (Ready to implement)
3-5 concrete steps with estimated impact.
"""


def extract_search_replace_blocks(proposal_text: str) -> list[tuple[str, str]]:
    """Extracts `(search_block, replace_block)` pairs from `<<<< SEARCH ... ==== ... >>>> REPLACE` markers."""
    if not proposal_text:
        return []
    pattern = re.compile(
        r"<<<<\s*SEARCH\r?\n(.*?)\r?\n====\r?\n(.*?)\r?\n>>>>\s*REPLACE",
        re.DOTALL,
    )
    return [(m.group(1), m.group(2)) for m in pattern.finditer(proposal_text)]


def apply_search_replace_blocks(source_text: str, proposal_text: str) -> str:
    """
    Applies bounded `<<<< SEARCH ... ==== ... >>>> REPLACE` blocks from `proposal_text` to `source_text`.
    Rejects blocks that do not match uniquely or that introduce forbidden `eval(` / `exec(` calls.
    Returns the updated source text (or original `source_text` if no valid blocks apply).
    """
    if not source_text or not proposal_text:
        return source_text

    blocks = extract_search_replace_blocks(proposal_text)
    if not blocks:
        return source_text

    updated = source_text
    for search_part, replace_part in blocks:
        if not search_part:
            continue
        if re.search(r"\b(?:eval|exec)\s*\(", replace_part):
            continue
        if updated.count(search_part) != 1:
            continue
        clean_replace = "\n".join(line.rstrip(" \t") for line in replace_part.splitlines())
        if replace_part.endswith("\n") and not clean_replace.endswith("\n"):
            clean_replace += "\n"
        updated = updated.replace(search_part, clean_replace, 1)

    return updated


def run_hard_verification_gates(repo_root: str = REPO_ROOT) -> dict:
    """
    Runs the 4 deterministic Hard Verification Gates for Closed-Loop ASI:
      Gate 1 (`rust_transpile`): Deterministic Python AST -> Rust transpilation & compilation
      Gate 2 (`vv_suite`):       5-Axis V&V Convergence Suite (`tests/test_vv_suite.py` == 100.0/100)
      Gate 3 (`safety_suite`):   Safety, Sandbox & Static AST Suite (`tests/test_safety.py`)
      Gate 4 (`ab_bench`):       A/B Startup Latency & Parity Benchmark (`tests/test_ab_bench.py`)
    """
    how_file = os.path.join(repo_root, "how")
    tr_file = os.path.join(repo_root, "scripts", "transpile_rust.py")
    vv_file = os.path.join(repo_root, "tests", "test_vv_suite.py")
    sf_file = os.path.join(repo_root, "tests", "test_safety.py")
    ab_file = os.path.join(repo_root, "tests", "test_ab_bench.py")

    gates = {
        "rust_transpile": {"passed": False, "details": ""},
        "vv_suite": {"passed": False, "score": 0.0, "details": ""},
        "safety_suite": {"passed": False, "details": ""},
        "ab_bench": {"passed": False, "details": ""},
    }

    # Gate 1: Rust AST transpilation & compilation
    tmp_dir = tempfile.mkdtemp(prefix="how_asi_gate_")
    try:
        loader = importlib.machinery.SourceFileLoader("asi_tr_mod", tr_file)
        spec = importlib.util.spec_from_loader("asi_tr_mod", loader)
        tr_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(tr_mod)

        rs_code = tr_mod.transpile_python_to_rust(how_file)
        rustc_bin = tr_mod.find_rustc()
        if rustc_bin:
            out_bin = os.path.join(tmp_dir, "how_gate_bin")
            comp = tr_mod.compile_rust_binary(how_file, out_bin)
            if comp.get("ok"):
                gates["rust_transpile"] = {
                    "passed": True,
                    "details": f"rustc compiled ok ({comp.get('size_kb', 0):.0f} KB)",
                }
            else:
                gates["rust_transpile"] = {
                    "passed": False,
                    "details": f"rustc failed: {comp.get('error', 'unknown')}",
                }
        elif "pub const VERSION" in rs_code:
            gates["rust_transpile"] = {
                "passed": True,
                "details": "AST transpiled cleanly (rustc not installed)",
            }
    except Exception as e:
        gates["rust_transpile"] = {"passed": False, "details": str(e)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["HOW_NO_BROWSER"] = "1"

    # Gate 2: V&V Suite (must exit 0 and reach 100.0 / 100)
    try:
        vv_proc = subprocess.run(
            [sys.executable, vv_file],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=60,
        )
        m = re.search(r"Composite V&V Score:\s*([0-9.]+)\s*/\s*100", vv_proc.stdout)
        score = float(m.group(1)) if m else 0.0
        passed = vv_proc.returncode == 0 and score >= 100.0
        gates["vv_suite"] = {
            "passed": passed,
            "score": score,
            "details": f"Composite V&V Score: {score:.1f}/100",
            "stdout": vv_proc.stdout,
        }
    except Exception as e:
        gates["vv_suite"] = {"passed": False, "score": 0.0, "details": str(e), "stdout": ""}

    # Gate 3: Safety & Static AST Suite
    try:
        sf_proc = subprocess.run(
            [sys.executable, sf_file],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=60,
        )
        gates["safety_suite"] = {
            "passed": sf_proc.returncode == 0,
            "details": "100% safety & static checks passed" if sf_proc.returncode == 0 else sf_proc.stderr[-300:],
        }
    except Exception as e:
        gates["safety_suite"] = {"passed": False, "details": str(e)}

    # Gate 4: A/B Latency & Parity Benchmark
    try:
        ab_proc = subprocess.run(
            [sys.executable, ab_file, "--stats"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=60,
        )
        gates["ab_bench"] = {
            "passed": ab_proc.returncode == 0,
            "details": "A/B benchmark passed" if ab_proc.returncode == 0 else ab_proc.stderr[-300:],
        }
    except Exception as e:
        gates["ab_bench"] = {"passed": False, "details": str(e)}

    all_passed = all(g.get("passed", False) for g in gates.values())
    return {"all_passed": all_passed, "gates": gates}


def apply_proposal_with_gate_rollback(
    target_path: str,
    proposal_text: str,
    repo_root: str = REPO_ROOT,
    gate_runner=None,
) -> dict:
    """
    Applies a bounded SEARCH/REPLACE proposal to `target_path` and runs all 4 Hard Verification Gates.
    If any gate fails, automatically rolls back `target_path` to its exact original contents.
    """
    runner = gate_runner or run_hard_verification_gates
    if not os.path.isfile(target_path):
        return {"applied": False, "passed": False, "rolled_back": False, "reason": "target file not found"}

    with open(target_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    updated_text = apply_search_replace_blocks(original_text, proposal_text)
    if updated_text == original_text:
        return {
            "applied": False,
            "passed": False,
            "rolled_back": False,
            "reason": "no matching SEARCH/REPLACE blocks",
        }

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(updated_text)

        gate_res = runner(repo_root)
        if not gate_res.get("all_passed", False):
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(original_text)
            return {
                "applied": True,
                "passed": False,
                "rolled_back": True,
                "gates": gate_res,
                "reason": "verification gate failed; patch rolled back automatically",
            }

        return {
            "applied": True,
            "passed": True,
            "rolled_back": False,
            "gates": gate_res,
            "reason": "all 4 hard verification gates passed",
        }
    except Exception as e:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(original_text)
        return {
            "applied": True,
            "passed": False,
            "rolled_back": True,
            "reason": f"exception during gate verification ({e}); rolled back",
        }


def get_code_context():
    context = []
    if os.path.exists(HOW_PATH):
        with open(HOW_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            context.append(f"=== File: how (length: {len(lines)} lines) ===\n")
            context.append("".join(lines[:900]))
    return "\n".join(context)


def call_ai_architect():
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    code_content = get_code_context()
    user_prompt = f"Analyze the current implementation of `how` CLI:\n\n{code_content}"

    if gemini_key:
        print("Using Google Gemini API for Architect Review...")
        model = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 3000,
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]

    if groq_key:
        print("Using Groq API for Architect Review...")
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 3000,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "how-ai-architect/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in environment.")


def create_verified_pull_request(report_text: str, gate_results: dict, repo_root: str = REPO_ROOT) -> dict:
    """
    Delivers a verified Closed-Loop ASI patch as a GitHub Pull Request on branch `asi/auto-<date>`
    only after all 4 Hard Verification Gates pass.
    """
    if not gate_results.get("all_passed", False):
        return {"ok": False, "reason": "gates did not pass"}

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    branch_name = f"asi/auto-{today}"
    title = f"🤖 [ASI Closed-Loop] Verified Optimization Patch ({today})"
    gates_summary = "\n".join(
        f"- **{k}**: `{'PASS' if v.get('passed') else 'FAIL'}` ({v.get('details', '')})"
        for k, v in (gate_results.get("gates") or {}).items()
    )
    body = f"""# Closed-Loop Autonomous Self-Improvement (`Code -> Gate -> PR`)

## Hard Verification Gate Results
{gates_summary}

---

{report_text}
"""
    if not shutil.which("gh") or not os.environ.get("GITHUB_TOKEN"):
        return {"ok": False, "branch": branch_name, "reason": "gh CLI or GITHUB_TOKEN not configured"}

    try:
        subprocess.run(["git", "checkout", "-B", branch_name], cwd=repo_root, check=True)
        subprocess.run(["git", "add", "how"], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", title], cwd=repo_root, check=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name, "--force"], cwd=repo_root, check=True)
        pr_proc = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body, "--label", "asi-verified"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return {"ok": True, "branch": branch_name, "pr_url": pr_proc.stdout.strip()}
    except Exception as e:
        return {"ok": False, "branch": branch_name, "reason": str(e)}


def create_github_issue(report_text, vv_output=""):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY not set. Printing report to stdout:")
        print(report_text)
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    title = f"🤖 [AI Architect] Autonomous Review & Optimization Proposals ({today})"
    body = f"""# Autonomous AI Architecture & V&V Report

> **Automated review generated on `{today}`** based on behavior & performance analysis.

### V&V Test Matrix Results
```
{vv_output}
```

---

{report_text}
"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "how-architect-bot",
    }
    payload = {
        "title": title,
        "body": body,
        "labels": ["automated-review", "optimization"],
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Created Issue #{data.get('number')}: {data.get('html_url')}")
    except Exception as e:
        print(f"Failed to create GitHub Issue: {e}")


def main():
    parser = argparse.ArgumentParser(description="Autonomous AI Architect & Closed-Loop ASI Gate Runner")
    parser.add_argument(
        "--verify-gates",
        action="store_true",
        help="Run the 4 deterministic Hard Verification Gates offline and print JSON summary",
    )
    parser.add_argument(
        "--closed-loop",
        action="store_true",
        help="Enable Closed-Loop ASI (apply bounded SEARCH/REPLACE patch, gate-check, rollback on failure, or PR)",
    )
    args = parser.parse_args()

    if args.verify_gates:
        res = run_hard_verification_gates(REPO_ROOT)
        summary = {
            "all_passed": res["all_passed"],
            "gates": {
                k: {"passed": v.get("passed"), "details": v.get("details")}
                for k, v in res["gates"].items()
            },
        }
        print(json.dumps(summary, indent=2))
        sys.exit(0 if res["all_passed"] else 1)

    gate_res = run_hard_verification_gates(REPO_ROOT)
    vv_output = gate_res["gates"]["vv_suite"].get("stdout", "")

    try:
        report = call_ai_architect()
        closed_loop = args.closed_loop or os.environ.get("ASI_CLOSED_LOOP") in ("1", "true", "yes")
        if closed_loop and extract_search_replace_blocks(report):
            patch_res = apply_proposal_with_gate_rollback(HOW_PATH, report, repo_root=REPO_ROOT)
            if patch_res.get("passed"):
                pr_res = create_verified_pull_request(report, patch_res["gates"], repo_root=REPO_ROOT)
                if pr_res.get("ok"):
                    print(f"Created Verified ASI PR: {pr_res.get('pr_url')}")
                    return
        create_github_issue(report, vv_output=vv_output)
    except Exception as e:
        print(f"Error during AI Architect review: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
