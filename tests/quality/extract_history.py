#!/usr/bin/env python3
"""Extract and curate a 100-question `how` quality benchmark set without secrets or personal identifiers."""

import argparse
import json
import re
import sqlite3
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OUT = Path(__file__).resolve().parent

META_FIRST = {
    "auth", "model", "config", "feedback", "test", "cache", "bash-history",
    "status", "help", "verbosity", "history", "run", "build", "context",
    "triage", "explain", "fix", "--help", "--version", "-V", "-h",
}

SECRET_PAT = re.compile(
    r"(api[_-]?key|token|password|passwd|secret|Bearer\s+\S+|sk-[A-Za-z0-9]{10,}|gsk_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+)",
    re.I,
)

JUNK = {
    "dare you", "dare you?", "to be me?", "are you?", "to do shit", "to know why?",
    "to be cool?", "to be smart?", "to think", "do i feel?", "to be happy?",
    "much for a kilo?", "far is sun from earth?", "good is groq", "fast is groq",
    "how help", "how --help", "help auth", "init", "autl logout", "verbosity",
    "verbosity 0", "verbosity 3", "how ?", "to lear how?",
    "feedback jest to testowy feedback od md #01",
    "to destroy omarchy?", "not to destroy omarchy?",
    "to terraform entire computer?", "to contact with dhh?",
    "to install x", "to ping someone", "omarchy described it's values?",
    "to logout from antugracity account and login to anotherone?",
}

JUNK_PATTERNS = re.compile(
    r"(?i)(\bgrok\s*bot\b|\bantugracity\b|\bdestroy\s+omarchy\b|\bcontact\s+with\s+dhh\b|"
    r"\bterraform\s+entire\s+computer\b|\bdo\s+i\s+feel\b|\btestowy\s+feedback\b)"
)

SYNTHETIC = [
    "to list open Hyprland windows?",
    "to reload Hyprland config without logout?",
    "to change Omarchy theme?",
    "to update all packages with pacman?",
    "to find which package owns a file?",
    "to show disk usage by directory?",
    "to kill process listening on port 8080?",
    "to enable bluetooth and connect headphones?",
    "to take a screenshot of active window in Wayland?",
    "to mirror displays in Hyprland?",
    "to set default browser in Omarchy?",
    "to install paru AUR helper?",
    "to clean pacman cache?",
    "to show systemd failed units?",
    "to restart NetworkManager?",
    "to create a new tmux session named work?",
    "to copy ssh public key to remote host?",
    "to generate ed25519 ssh key?",
    "to squash last 3 git commits interactively?",
    "to undo last git commit keeping changes?",
    "to stash untracked files too?",
    "to compare two branches with git?",
    "to set git pull to rebase by default?",
    "to list listening TCP ports?",
    "to test DNS resolution for example.com?",
    "to show my public IP address?",
    "to mount a USB drive read-only?",
    "to check SMART status of NVMe disk?",
    "to compress a folder to tar.xz?",
    "to extract a .tar.gz archive?",
    "to find large files over 1GB?",
    "to watch GPU usage on AMD?",
    "to switch audio output sink with pactl?",
    "to mute microphone from CLI?",
    "to set keyboard layout to pl?",
    "to disable touchpad while typing?",
    "to lock screen from terminal?",
    "to suspend the system?",
    "to list cron jobs for current user?",
    "to follow journalctl logs for a service?",
    "to open a floating terminal in Hyprland?",
    "to move window to workspace 3 in Hyprland?",
    "to toggle fullscreen in Hyprland?",
    "to install docker and add user to docker group?",
    "to prune unused docker images?",
    "to run a one-off alpine container interactively?",
    "to check openssl certificate expiry for a host?",
    "to convert markdown to PDF?",
    "to search recursively for TODO in code?",
    "to replace text in many files with sed?",
    "to enroll Limine config before sbctl secure boot?",
    "to reset faillock password lockout for current user?",
    "to check Hyprland config syntax errors from terminal?",
    "to list all available Omarchy CLI commands?",
    "to switch font in Omarchy?",
    "to record screen region in Omarchy?",
    "to scan a QR code from screen in Omarchy?",
    "to list orphan packages in pacman?",
    "to remove orphan packages in Arch Linux?",
    "to show systemd boot blame times?",
    "to create a btrfs snapshot with snapper?",
    "to show open files for a PID with lsof?",
    "to benchmark disk read speed with fio or dd?",
    "to watch network bandwidth per process?",
    "to forward local port 3000 to remote 80 over ssh?",
    "to switch GitHub CLI active account without logging out?",
    "to check PipeWire audio status and default sink?",
    "to reload systemd daemon after editing unit files?",
    "to view kernel ring buffer messages in real time?",
    "to list all block devices with filesystem UUIDs?",
    "to check battery health and charge cycles on Linux?",
]


def sanitize_query(q: str) -> str:
    """Normalizes whitespace, strips trailing typo punctuation, and scrubs personal repo names."""
    q = (q or "").strip()
    q = re.sub(r"\?>+$", "?", q)
    q = re.sub(r"\bmd(?:sys|ysy)eng/how\b", "myorg/myrepo", q, flags=re.I)
    q = re.sub(r"\s+", " ", q)
    return q


def is_junk_query(q: str) -> bool:
    """Returns True if the query is non-actionable junk, joke, or meta-command noise."""
    ql = q.lower().strip()
    ql_no_q = ql.rstrip("?!.")
    junk_low = {j.lower().strip().rstrip("?!.") for j in JUNK}
    if ql in junk_low or ql_no_q in junk_low:
        return True
    if JUNK_PATTERNS.search(q):
        return True
    if len(ql_no_q) < 6 or len(ql_no_q.split()) < 2:
        return True
    return False


def norm(q: str) -> str:
    """Normalizes typos and punctuation for exact/near deduplication."""
    q_clean = sanitize_query(q).lower().strip().rstrip("?!.")
    q_clean = (
        q_clean.replace("pricate", "private")
        .replace("orign", "origin")
        .replace("unistall", "uninstall")
        .replace("claudflare", "cloudflare")
        .replace("jetrbrains", "jetbrains")
        .replace("vlca", "vlc")
        .replace("otput", "output")
        .replace("crate ", "create ")
        .replace("maske ", "make ")
        .replace("nad ", "and ")
    )
    q_clean = re.sub(r"[,();:]", " ", q_clean)
    return re.sub(r"\s+", " ", q_clean).strip()


def semantic_signature(q: str) -> str:
    """Maps known repetitive history clusters onto a single canonical intent key."""
    n = norm(q)
    if ("intellij" in n) and any(k in n for k in ("neovim", "nvim", "terminal editor", "anotherone")):
        if "backup" in n or "save current" in n:
            return "cluster:nvim_backup_intellij"
        return "cluster:nvim_intellij_keymap"
    if "claude code" in n and "run" in n:
        return "cluster:run_claude_code"
    if ("push" in n) and any(k in n for k in ("fresh", "freshly", "new local repo", "already created")):
        if "origin is not set" in n:
            return "cluster:push_fresh_gh_no_origin"
        return "cluster:push_fresh_gh_repo"
    if "omarchy" in n and "quattro" in n:
        return "cluster:omarchy_version_quattro"
    if "switch gh user" in n:
        return "cluster:switch_gh_user"
    if n in ("to display git origin", "to see git origin", "to see origin"):
        return "cluster:git_origin_view"
    if n in ("to change gh repo to private", "to change repo visibility to private with gh"):
        return "cluster:gh_repo_visibility_private"
    if n in ("to display active users", "to display active users by their names"):
        return "cluster:display_active_users"
    if n.startswith("to ping ") and ("internet" in n or "google" in n):
        return "cluster:ping_host"
    return n


def classify_category(q: str) -> str:
    """Assigns a functional domain category to a benchmark query."""
    ql = q.lower()
    if any(k in ql for k in ("hypr", "wayland", "workspace", "floating terminal", "frames")):
        return "hyprland"
    if any(k in ql for k in ("omarchy", "limine", "faillock")):
        return "omarchy"
    if re.search(r"\b(git|gh|github|commit|branch|stash)\b", ql):
        return "git"
    if re.search(r"\b(pacman|yay|paru|pkg|install|uninstall)\b", ql):
        return "packages"
    if re.search(r"\b(docker|alpine|podman|container)\b", ql):
        return "containers"
    if re.search(r"\b(neovim|nvim|micro|intellij|editor)\b", ql):
        return "editor"
    if re.search(r"\b(audio|pactl|microphone|bluetooth|screenshot|gpu)\b", ql):
        return "media"
    if re.search(r"\b(ping|dns|tcp|port|ssh|ip|networkmanager|openssl|bandwidth)\b", ql):
        return "network"
    if re.search(r"\b(tar|disk|files|sed|todo|markdown|clipboard|shortcut|alias)\b", ql):
        return "files"
    return "system"


def score_candidate(meta: dict) -> tuple:
    q = meta["query"]
    s = 0
    if q.lower().startswith("to "):
        s += 2
    if q.endswith("?"):
        s += 1
    if any(k in q.lower() for k in ("omarchy", "hypr", "git", "gh ", "pacman", "install", "neovim", "alias", "systemd")):
        s += 2
    if 15 <= len(q) <= 75:
        s += 2
    # Penalize queries with obvious typos so clean phrasing wins its semantic cluster
    if any(typo in q.lower() for typo in ("pricate", "orign", "unistall", "claudflare", "jetrbrains", "vlca", "otput", "crate ", "maske ", "nad ")):
        s -= 3
    return (-s, len(q), meta.get("date") or "")


def extract_and_curate(dump_raw: bool = False) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    queries = OrderedDict()

    def add(q, source, date=None, sample_cmd=None):
        q = sanitize_query(q)
        if not q:
            return
        if q not in queries:
            queries[q] = {"query": q, "source": source, "date": date, "sample_cmd": sample_cmd}

    # 1. ~/.config/how/commands.log (supports both English 'Query:' and legacy Polish 'Pytanie:')
    log = HOME / ".config/how/commands.log"
    log_re = re.compile(r'^\[([^\]]+)\]\s+\[[^\]]+\]\s+(?:Query|Pytanie):\s+"(.*)"\s+\|\s+(?:Command|Komenda):\s+(.*)$')
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = log_re.match(line.strip())
            if m:
                add(m.group(2), "history", m.group(1), m.group(3))

    # 2. ~/.bash_history
    bash = HOME / ".bash_history"
    if bash.exists():
        for line in bash.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("how "):
                continue
            rest = line[4:].strip()
            if not rest:
                continue
            parts = rest.split()
            while parts and parts[0].startswith("-"):
                parts = parts[1:]
            if not parts:
                continue
            first = parts[0].lower()
            q = " ".join(parts)
            if first in META_FIRST and (len(parts) <= 2 or ("?" not in q and "works" not in q.lower())):
                continue
            if first in ("auth", "autl") and len(parts) <= 2:
                continue
            add(q, "history")

    # 3. ~/.cache/how/cache.db
    db = HOME / ".cache/how/cache.db"
    if db.exists():
        try:
            con = sqlite3.connect(db)
            for q, created in con.execute(
                "SELECT DISTINCT query, MIN(created_at) FROM response_cache GROUP BY query"
            ):
                try:
                    date = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date = None
                add(q, "history", date)
            con.close()
        except Exception:
            pass

    removed_secret = 0
    removed_junk = 0
    kept = OrderedDict()
    for q, meta in queries.items():
        if SECRET_PAT.search(q) or SECRET_PAT.search(meta.get("sample_cmd") or ""):
            removed_secret += 1
            continue
        if is_junk_query(q):
            removed_junk += 1
            continue
        kept[q] = meta

    # Sort candidates by quality score first so the best phrasing wins each semantic cluster
    ranked_history = sorted(kept.values(), key=score_candidate)
    seen_sigs = set()
    selected = []
    for meta in ranked_history:
        sig = semantic_signature(meta["query"])
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        selected.append({
            "query": meta["query"],
            "source": "history",
            "category": classify_category(meta["query"]),
            "date": None,
            "sample_cmd": None,
        })

    curated = list(selected[:100])
    i = 0
    while len(curated) < 100 and i < len(SYNTHETIC):
        q = sanitize_query(SYNTHETIC[i])
        i += 1
        sig = semantic_signature(q)
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        curated.append({
            "query": q,
            "source": "synthetic",
            "category": classify_category(q),
            "date": None,
            "sample_cmd": None,
        })

    with (OUT / "queries_100.jsonl").open("w", encoding="utf-8") as f:
        for idx, row in enumerate(curated, 1):
            entry = dict(row)
            entry["id"] = idx
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if dump_raw:
        with (OUT / "history_queries_full.jsonl").open("w", encoding="utf-8") as f:
            for meta in kept.values():
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    stats = {
        "raw_unique": len(queries),
        "kept_history_unique": len(kept),
        "after_semantic_dedup": len(selected),
        "curated": len(curated),
        "history_in_curated": sum(1 for r in curated if r["source"] == "history"),
        "synthetic_in_curated": sum(1 for r in curated if r["source"] == "synthetic"),
        "removed_secret": removed_secret,
        "removed_junk": removed_junk,
    }
    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract and curate 100 benchmark queries for `how`.")
    parser.add_argument("--dump-raw", action="store_true", help="Also write raw history JSONL for local debugging")
    args = parser.parse_args()
    stats = extract_and_curate(dump_raw=args.dump_raw)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
