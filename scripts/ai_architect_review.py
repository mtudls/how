#!/usr/bin/env python3
"""
Autonomous AI Maintainer & Architect Reviewer for `how`.

Reviews the codebase against:
1. Performance & startup latency (zero-lag, sub-100ms startup).
2. Elimination of dead/unnecessary code & bloat.
3. System behavior verification & score regression analysis.
4. Radical architecture evolutions (e.g. Go/Rust single-binary vs Python stdlib).

Runs within rate limits (free-tier friendly: 1 call per run).
Outputs:
- GitHub Issue with architectural analysis & proposed optimizations.
"""

import sys
import os
import json
import urllib.request
import urllib.error

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOW_PATH = os.path.join(REPO_ROOT, "how")
TEST_SUITE_PATH = os.path.join(REPO_ROOT, "tests", "test_vv_suite.py")

SYSTEM_PROMPT = """You are a world-class Principal Systems Architect & Performance Lead reviewing the `how` CLI repository (an ultra-fast Linux & Omarchy CLI assistant).

CRITICAL PHILOSOPHY:
- End-user outcome is everything. The form can change arbitrarily (Python stdlib, Rust, Go, Zig, shell).
- Zero-friction, sub-50ms startup latency, minimalist terminal output, and ironclad behavior reliability.
- Ruthless reduction of bloat: eliminate unnecessary code, overcomplicated RAG, or slow abstractions.
- Continuous V&V Evolution WITHOUT Bloat: The Verification & Validation test suite must continuously evolve to capture modern tools, edge cases, and user regression patterns, but CI test execution must remain lightning fast (<1-2 seconds total). Any test that adds heavy latency or bloat must be rejected.
- Verification & Validation (V&V) must drive changes: every proposed change must preserve or improve behavioral score and performance.

YOUR TASK:
Analyze the code, review performance and behavior patterns, and generate a structured Architecture & Optimization Report.

FORMAT:
## 1. Executive Summary & V&V Assessment
Concise verdict on the current architecture state and composite V&V score.

## 2. Ruthless Simplification & Code Removal
What code/layers can be cut or simplified without hurting user outcome?

## 3. Latency & Performance Breakthroughs
Startup time bottlenecks, memory, caching improvements, or language rewrite analysis (e.g. Go/Rust vs Python stdlib).

## 4. Behavior Quality & V&V Evolution (Zero Bloat)
Concrete new behavioral checks and edge cases to add to `tests/test_vv_suite.py` that guard real user workflows without slowing down CI.

## 5. Prioritized Action Plan (Ready to implement)
3-5 concrete steps with estimated impact.
"""

def get_code_context():
    context = []
    if os.path.exists(HOW_PATH):
        with open(HOW_PATH, "r", encoding="utf-8", errors="replace") as f:
            context.append(f"=== File: how (length: {len(f.readlines())} lines) ===\n")
            f.seek(0)
            context.append(f.read())
    return "\n".join(context)

def call_ai_architect():
    # 1. Try Gemini Free API first
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    code_content = get_code_context()
    user_prompt = f"Analyze the current implementation of `how` CLI:\n\n{code_content}"

    if gemini_key:
        print("Using Google Gemini API for Architect Review...")
        model = "gemini-2.5-flash"  # Free-tier, high intelligence & speed
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 3000
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]

    elif groq_key:
        print("Using Groq API for Architect Review...")
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 3000
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "how-ai-architect/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    else:
        raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in environment.")

def create_github_issue(report_text, vv_output=""):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY not set. Printing report to stdout:")
        print(report_text)
        return

    import datetime
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
        "User-Agent": "how-architect-bot"
    }
    payload = {
        "title": title,
        "body": body,
        "labels": ["automated-review", "optimization"]
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Created Issue #{data.get('number')}: {data.get('html_url')}")
    except Exception as e:
        print(f"Failed to create GitHub Issue: {e}")

def main():
    # 1. Run local V&V suite first to get score
    import subprocess
    vv_proc = subprocess.run(
        [sys.executable, TEST_SUITE_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    vv_output = vv_proc.stdout

    # 2. Call AI Architect
    try:
        report = call_ai_architect()
        # 3. Post as issue
        create_github_issue(report, vv_output=vv_output)
    except Exception as e:
        print(f"Error during AI Architect review: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
