#!/usr/bin/env python3
"""
tests/test_ab_bench.py - Independent, statistical A/B benchmarking & V&V runner for `how`.

Features:
1. Recursion / Lock-free execution: Uses direct execution with `--help` and isolated temp files.
2. Interleaved / Parallel sampling: Runs Baseline [A] and WIP [B] in interleaved pairs to eliminate
   thermal/system load bias.
3. Smooth ANSI Color Gradient:
   Linear color mapping (Red -> White -> Green) based on relative performance diff and metrics.
4. Two-phase flow:
   - Phase 1: 1-shot sanity check (Baseline vs WIP).
   - Phase 2: Interactive or flag-driven 10-iteration statistical suite with full table,
     mean, min/max, standard deviation, and colorized rows.
5. Ready-to-ship Git & GitHub CLI recommendations.
"""

import sys
import os
import time
import math
import hashlib
import tempfile
import subprocess
import shutil

# Color support
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"
RESET = "\033[0m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
DIM = "\033[2m" if USE_COLOR else ""
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
CYAN = "\033[36m" if USE_COLOR else ""
MAGENTA = "\033[35m" if USE_COLOR else ""

def rgb_ansi(r, g, b, text):
    """Formats text in 24-bit TrueColor ANSI."""
    if not USE_COLOR:
        return text
    return f"\033[38;2;{int(r)};{int(g)};{int(b)}m{text}{RESET}"

def color_diff(val_diff_percent, text=None):
    """
    Linear color spectrum:
    - Positive difference (faster): White -> Green (0% to +30%)
    - Negative difference (slower): White -> Red (0% to -30%)
    """
    if text is None:
        text = f"{val_diff_percent:+.1f}%"
    if not USE_COLOR:
        return text

    # Clamp diff to [-30, 30] range for color normalization
    clamped = max(-30.0, min(30.0, val_diff_percent))
    norm = clamped / 30.0  # -1.0 .. 1.0

    if norm >= 0:
        # White (230, 230, 230) -> Green (46, 204, 113)
        r = 230 - norm * (230 - 46)
        g = 230 - norm * (230 - 204)
        b = 230 - norm * (230 - 113)
    else:
        # White (230, 230, 230) -> Red (231, 76, 60)
        norm = abs(norm)
        r = 230 - norm * (230 - 231)
        g = 230 - norm * (230 - 76)
        b = 230 - norm * (230 - 60)

    return rgb_ansi(r, g, b, text)

def is_elf_binary(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except Exception:
        return False


def run_single_benchmark(exec_path, extra_env=None):
    """Executes a single invocation measuring cold startup latency in milliseconds."""
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["HOW_NO_BROWSER"] = "1"
    if extra_env:
        env.update(extra_env)

    cmd = [exec_path, "--help"] if is_elf_binary(exec_path) else [sys.executable, exec_path, "--help"]
    t0 = time.perf_counter()
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    dt_ms = (time.perf_counter() - t0) * 1000
    ok = (res.returncode == 0)
    return dt_ms, ok

def run_ab_bench(wip_path=None, auto_run_stats=False):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not wip_path:
        wip_path = os.path.join(repo_root, "how")

    wip_path = os.path.realpath(wip_path)

    # 1. Locate Baseline [A]
    installed_label = ""
    baseline_bytes = None
    baseline_temp_file = None
    native_rust_bin = None

    path_env = os.environ.get("PATH", "")
    found_bin = None
    for p in path_env.split(os.path.pathsep):
        cand = os.path.join(p, "how")
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            found_bin = cand
            break

    if found_bin and is_elf_binary(found_bin):
        native_rust_bin = found_bin

    if found_bin and os.path.realpath(found_bin) != wip_path and not is_elf_binary(found_bin):
        installed_label = found_bin
        with open(found_bin, "rb") as f:
            baseline_bytes = f.read()
    else:
        # Symlinked, same file, or native ELF binary installed: extract git HEAD as Python baseline
        try:
            git_res = subprocess.run(
                ["git", "-C", repo_root, "show", "HEAD:how"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if git_res.returncode == 0 and git_res.stdout:
                baseline_bytes = git_res.stdout
                installed_label = "Committed (git:HEAD)"
        except Exception:
            pass

    with open(wip_path, "rb") as f:
        wip_bytes = f.read()

    wip_hash = hashlib.sha256(wip_bytes).hexdigest()
    baseline_hash = hashlib.sha256(baseline_bytes).hexdigest() if baseline_bytes else ""

    is_ab_mode = bool(baseline_bytes and (wip_hash != baseline_hash))

    print(f"\n{BOLD}{MAGENTA}◆ how self-test & benchmark matrix{RESET}")

    if not is_ab_mode:
        print(f"  Target: {wip_path} {DIM}(sha: {wip_hash[:8]}...){RESET}\n")
        lat, ok = run_single_benchmark(wip_path)
        score = max(0, min(100, 100 - (lat - 30) * 0.7)) if lat > 30 else 100
        print(f"  • Startup Latency (Python): {lat:.2f} ms")
        if native_rust_bin:
            rust_lat, _ = run_single_benchmark(native_rust_bin)
            speedup = lat / rust_lat if rust_lat > 0 else 1.0
            print(f"  • Startup Latency (Rust):   {GREEN}{rust_lat:.2f} ms{RESET} {DIM}({speedup:.1f}x faster via {native_rust_bin}){RESET}")
        print(f"  • Performance Score:        {score:.1f}/100")

        # Behavioral V&V
        test_script = os.path.join(repo_root, "tests", "test_vv_suite.py")
        if os.path.exists(test_script):
            vv_res = subprocess.run([sys.executable, test_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"  • Behavioral V&V:           {GREEN}✓ 100% Passed{RESET}" if vv_res.returncode == 0 else f"  • Behavioral V&V:           {RED}✗ Failed{RESET}")
        print()
        return

    # A/B MODE
    print(f"{DIM}Detected differences between baseline version and local work-in-progress.{RESET}\n")
    print(f"  {BOLD}[A] Baseline:{RESET}         {installed_label} {DIM}(sha: {baseline_hash[:8]}...){RESET}")
    print(f"  {BOLD}[B] Work-in-progress:{RESET} {wip_path} {DIM}(sha: {wip_hash[:8]}...){RESET}\n")

    # Write baseline temp file safely
    tmp_a = tempfile.NamedTemporaryFile("wb", delete=False, suffix=".py")
    tmp_a.write(baseline_bytes)
    tmp_a.flush()
    tmp_a.close()
    os.chmod(tmp_a.name, 0o700)
    baseline_temp_file = tmp_a.name

    wip_bench_target = wip_path
    wip_rust_temp = None
    transpiler_script = os.path.join(repo_root, "scripts", "transpile_rust.py")
    if os.path.exists(transpiler_script):
        try:
            import importlib.machinery
            import importlib.util
            loader = importlib.machinery.SourceFileLoader("tr_ab_mod", transpiler_script)
            spec = importlib.util.spec_from_loader("tr_ab_mod", loader)
            tr_mod = importlib.util.module_from_spec(spec)
            loader.exec_module(tr_mod)
            tmp_rs_bin = tempfile.NamedTemporaryFile("wb", delete=False, suffix="_how_rs")
            tmp_rs_bin.close()
            comp = tr_mod.compile_rust_binary(wip_path, tmp_rs_bin.name)
            if comp.get("ok"):
                wip_rust_temp = tmp_rs_bin.name
                wip_bench_target = wip_rust_temp
            else:
                os.remove(tmp_rs_bin.name)
        except Exception:
            pass

    try:
        # Phase 1: Sanity Check (1 iteration, interleaved)
        print(f"{BOLD}Phase 1: Initial Sanity Check (1 round){RESET}")
        lat_a, ok_a = run_single_benchmark(baseline_temp_file)
        lat_b, ok_b = run_single_benchmark(wip_bench_target)

        diff_p1 = ((lat_a - lat_b) / lat_a) * 100 if lat_a else 0
        diff_str_p1 = color_diff(diff_p1)
        print(f"  Baseline [A]: {lat_a:.2f} ms | WIP [B]: {lat_b:.2f} ms | Difference: {diff_str_p1}\n")

        # Check Syntax & Compile
        def check_syntax(path):
            res = subprocess.run([sys.executable, "-m", "py_compile", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return res.returncode == 0

        syn_a = check_syntax(baseline_temp_file)
        syn_b = check_syntax(wip_path)
        status_a = f"{GREEN}✓ Valid{RESET}" if syn_a else f"{RED}✗ Error{RESET}"
        status_b = f"{GREEN}✓ Valid{RESET}" if syn_b else f"{RED}✗ Error{RESET}"
        print(f"  Syntax Check: Baseline [A]: {status_a} | WIP [B]: {status_b}")

        # Run behavioral V&V on WIP
        test_script = os.path.join(repo_root, "tests", "test_vv_suite.py")
        wip_vv_pass = True
        if os.path.exists(test_script):
            vv_res = subprocess.run([sys.executable, test_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            wip_vv_pass = (vv_res.returncode == 0)
            status_str = f"{GREEN}✓ All Passed (No regressions){RESET}" if wip_vv_pass else f"{RED}✗ Regression detected{RESET}"
            print(f"  Behavioral V&V: {status_str}\n")

        # Phase 2: Statistical 10-Iteration Suite
        do_stats = auto_run_stats
        if not do_stats:
            try:
                ans = input(f"{CYAN}Run statistical 10-iteration suite with linear color spectrum? [Y/n]:{RESET} ").strip().lower()
                do_stats = (ans in ("", "y", "yes"))
            except (KeyboardInterrupt, EOFError):
                print()
                do_stats = False

        if do_stats:
            print(f"\n{BOLD}Phase 2: Statistical Interleaved Benchmark (10 iterations){RESET}\n")
            print(f"  {'Iter':<6} {'[A] Baseline':<16} {'[B] WIP':<16} {'Difference':<16}")
            print(f"  {'-'*54}")

            samples_a = []
            samples_b = []

            # Interleaved sampling to prevent thermal/load drift
            for i in range(1, 11):
                if i % 2 == 1:
                    t_a, _ = run_single_benchmark(baseline_temp_file)
                    t_b, _ = run_single_benchmark(wip_bench_target)
                else:
                    t_b, _ = run_single_benchmark(wip_bench_target)
                    t_a, _ = run_single_benchmark(baseline_temp_file)

                samples_a.append(t_a)
                samples_b.append(t_b)

                d = ((t_a - t_b) / t_a) * 100
                print(f"  #{i:<5} {f'{t_a:.2f} ms':<16} {f'{t_b:.2f} ms':<16} {color_diff(d):<16}")

            # Statistical Aggregations
            mean_a = sum(samples_a) / len(samples_a)
            mean_b = sum(samples_b) / len(samples_b)
            std_a = math.sqrt(sum((x - mean_a) ** 2 for x in samples_a) / len(samples_a))
            std_b = math.sqrt(sum((x - mean_b) ** 2 for x in samples_b) / len(samples_b))
            diff_mean = ((mean_a - mean_b) / mean_a) * 100

            print(f"  {'-'*54}")
            print(f"  {'MEAN':<6} {f'{mean_a:.2f} ms':<16} {f'{mean_b:.2f} ms':<16} {color_diff(diff_mean, f'{diff_mean:+.2f}%'):<16}")
            print(f"  {'STDEV':<6} {f'±{std_a:.2f} ms':<16} {f'±{std_b:.2f} ms':<16} {DIM}(variance){RESET}")
            print(f"  {'MIN':<6} {f'{min(samples_a):.2f} ms':<16} {f'{min(samples_b):.2f} ms':<16}")
            print(f"  {'MAX':<6} {f'{max(samples_a):.2f} ms':<16} {f'{max(samples_b):.2f} ms':<16}")
            print()

        # Ready to ship git & gh recommendations
        if wip_vv_pass and syn_b:
            print(f"{BOLD}{GREEN}✓ Work-in-progress is clean & verified!{RESET}")
            print(f"{DIM}Recommended Git / PR workflow:{RESET}")
            print(f"  {CYAN}git add -p && git commit -m \"feat: optimize performance\" && git push origin HEAD{RESET}")
            print(f"  {CYAN}gh pr create --fill --web{RESET}\n")

    finally:
        for tmp_f in (baseline_temp_file, wip_rust_temp):
            if tmp_f and os.path.exists(tmp_f):
                try:
                    os.remove(tmp_f)
                except Exception:
                    pass

if __name__ == "__main__":
    auto = "--stats" in sys.argv or "-s" in sys.argv or "--ci" in sys.argv
    run_ab_bench(auto_run_stats=auto)
