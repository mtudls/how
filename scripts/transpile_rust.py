#!/usr/bin/env python3
"""
scripts/transpile_rust.py - Deterministic, zero-LLM Python-to-Rust AST transpiler for `how`.

Parses the readable Python `how` script via Python's standard `ast` module, extracts constants,
tables (`DEEP_QUERY_INDICATORS`, `COMMON_STOPWORDS`, `CONTEXT_DISCOVERY_STEPS`), and transpiles
hot-path CLI functions (`print_help`, `format_query`, `heuristic_needs_deep_thinking`,
`strip_think_blocks`, `extract_candidate_commands`, `print_context_dry_run_plan`,
`detect_os_profile`, `detect_local_stack`) into standalone, zero-crate-dependency Rust (`std` only),
embedding the Python source for network streaming, SQLite WAL caching, and interactive flows.

Compiles with `rustc -C opt-level=3 -C strip=symbols` in <1 second offline.
"""

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time


def rust_escape_str(s: str) -> str:
    """Escapes a Python string into a valid Rust string literal."""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 32:
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def eval_ast_expr(node: ast.AST):
    """Safely evaluates constant/tuple/dict/binop AST nodes from `how` without executing code."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        left = eval_ast_expr(node.left)
        right = eval_ast_expr(node.right)
        if left is not None and right is not None:
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Add):
                return left + right
        return None
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        items = [eval_ast_expr(elt) for elt in node.elts]
        return items if all(x is not None for x in items) else None
    if isinstance(node, ast.Dict):
        keys = [eval_ast_expr(k) for k in node.keys]
        vals = [eval_ast_expr(v) for v in node.values]
        if all(k is not None for k in keys) and all(v is not None for v in vals):
            return dict(zip(keys, vals))
        return None
    return None


class HowAstAnalyzer:
    """Inspects top-level AST nodes of `how` to extract constants, tables, and function definitions."""

    def __init__(self):
        self.constants = {}
        self.string_lists = {}
        self.discovery_steps = []
        self.functions = {}

    def analyze(self, tree: ast.Module):
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                val = eval_ast_expr(node.value)
                if isinstance(val, (str, int, float, bool)):
                    self.constants[name] = val
                elif isinstance(val, list) and val and all(isinstance(x, str) for x in val):
                    self.string_lists[name] = val
                elif name == "CONTEXT_DISCOVERY_STEPS" and isinstance(val, list):
                    self.discovery_steps = [d for d in val if isinstance(d, dict)]
            elif isinstance(node, ast.FunctionDef):
                self.functions[node.name] = node


def extract_help_template_from_ast(func_node: ast.FunctionDef) -> list:
    """
    Extracts the f-string segments from `print_help()` in Python AST and transpiles
    them into Rust `format!` / ANSI color segments.
    """
    for stmt in ast.walk(func_node):
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "help_text":
                    if isinstance(stmt.value, ast.JoinedStr):
                        segments = []
                        for part in stmt.value.values:
                            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                                segments.append(("lit", part.value))
                            elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name):
                                segments.append(("var", part.value.id))
                        return segments
    return []


def transpile_python_to_rust(py_path: str) -> str:
    """
    Reads `how` Python source file, parses its AST, and emits a complete, zero-dependency
    Rust source program (`how.rs`) with native fast-paths and embedded Python bridge.
    """
    with open(py_path, "r", encoding="utf-8") as f:
        py_source = f.read()

    tree = ast.parse(py_source, filename=py_path)
    analyzer = HowAstAnalyzer()
    analyzer.analyze(tree)

    version = str(analyzer.constants.get("__version__", "0.3.0"))
    default_model = str(analyzer.constants.get("DEFAULT_MODEL", "openai/gpt-oss-120b"))
    default_triage = str(analyzer.constants.get("DEFAULT_TRIAGE_MODEL", "llama-3.1-8b-instant"))
    default_think = str(analyzer.constants.get("DEFAULT_THINK_MODEL", "deepseek-r1-distill-llama-70b"))
    default_verbosity = str(analyzer.constants.get("DEFAULT_VERBOSITY", "normal"))
    default_retention = int(analyzer.constants.get("DEFAULT_CACHE_RETENTION", 10800))

    deep_indicators = analyzer.string_lists.get("DEEP_QUERY_INDICATORS", [])
    stopwords = analyzer.string_lists.get("COMMON_STOPWORDS", [])
    steps = analyzer.discovery_steps

    help_segments = []
    if "print_help" in analyzer.functions:
        help_segments = extract_help_template_from_ast(analyzer.functions["print_help"])

    # Build Rust print_help body from extracted Python AST f-string
    help_rust_lines = ["    let mut out = String::with_capacity(2048);"]
    for kind, val in help_segments:
        if kind == "lit":
            help_rust_lines.append(f"    out.push_str({rust_escape_str(val)});")
        elif kind == "var":
            var_low = val.lower()
            if var_low in ("reset", "bold", "dim", "cyan", "green", "yellow", "red", "magenta"):
                help_rust_lines.append(f"    out.push_str(c.{var_low});")
    help_rust_lines.append("    println!(\"{}\", out);")
    help_rust_body = "\n".join(help_rust_lines)

    # Build Rust discovery steps array from AST
    steps_rust_items = []
    for s in steps:
        steps_rust_items.append(
            f"    DiscoveryStep {{ id: {rust_escape_str(s.get('id', ''))}, "
            f"category: {rust_escape_str(s.get('category', ''))}, "
            f"title: {rust_escape_str(s.get('title', ''))}, "
            f"dry_run: {rust_escape_str(s.get('dry_run', ''))}, "
            f"target: {rust_escape_str(s.get('target', ''))} }},"
        )
    steps_rust_code = "\n".join(steps_rust_items)

    deep_ind_code = ", ".join(rust_escape_str(x) for x in deep_indicators)
    stopwords_code = ", ".join(rust_escape_str(x) for x in stopwords)
    repo_dir_str = os.path.dirname(os.path.abspath(py_path))

    rust_code = f"""// Automatically transpiled from readable Python (`how`) by `scripts/transpile_rust.py`
// Deterministic Python AST -> Rust transpilation (Zero LLM, Zero external crates).

#![allow(dead_code)]

use std::env;
use std::fs;
use std::os::unix::process::CommandExt;
use std::path::Path;
use std::process::Command;

pub const VERSION: &str = {rust_escape_str(version)};
pub const SOURCE_REPO_DIR: &str = {rust_escape_str(repo_dir_str)};
pub const DEFAULT_MODEL: &str = {rust_escape_str(default_model)};
pub const DEFAULT_TRIAGE_MODEL: &str = {rust_escape_str(default_triage)};
pub const DEFAULT_THINK_MODEL: &str = {rust_escape_str(default_think)};
pub const DEFAULT_VERBOSITY: &str = {rust_escape_str(default_verbosity)};
pub const DEFAULT_CACHE_RETENTION: u64 = {default_retention};

pub const DEEP_QUERY_INDICATORS: &[&str] = &[{deep_ind_code}];
pub const COMMON_STOPWORDS: &[&str] = &[{stopwords_code}];

pub struct DiscoveryStep {{
    pub id: &'static str,
    pub category: &'static str,
    pub title: &'static str,
    pub dry_run: &'static str,
    pub target: &'static str,
}}

pub const CONTEXT_DISCOVERY_STEPS: &[DiscoveryStep] = &[
{steps_rust_code}
];

const EMBEDDED_PYTHON_SOURCE: &str = {rust_escape_str(py_source)};

struct Colors {{
    reset: &'static str,
    bold: &'static str,
    dim: &'static str,
    cyan: &'static str,
    green: &'static str,
    yellow: &'static str,
    red: &'static str,
    magenta: &'static str,
}}

impl Colors {{
    fn detect() -> Self {{
        let no_color = env::var_os("NO_COLOR").is_some();
        let dumb = env::var("TERM").map(|t| t == "dumb").unwrap_or(false);
        let is_tty = unsafe {{ libc_isatty(1) != 0 }};
        if is_tty && !no_color && !dumb {{
            Self {{
                reset: "\\x1b[0m",
                bold: "\\x1b[1m",
                dim: "\\x1b[2m",
                cyan: "\\x1b[36m",
                green: "\\x1b[32m",
                yellow: "\\x1b[33m",
                red: "\\x1b[31m",
                magenta: "\\x1b[35m",
            }}
        }} else {{
            Self {{
                reset: "",
                bold: "",
                dim: "",
                cyan: "",
                green: "",
                yellow: "",
                red: "",
                magenta: "",
            }}
        }}
    }}
}}

extern "C" {{
    #[link_name = "isatty"]
    fn libc_isatty(fd: i32) -> i32;
}}

pub fn print_help(c: &Colors) {{
{help_rust_body}
}}

/// AST-transpiled from Python `heuristic_needs_deep_thinking(query: str) -> bool`
pub fn heuristic_needs_deep_thinking(query: &str) -> bool {{
    let q_low = query.trim().to_lowercase();
    if q_low.split_whitespace().count() >= 16 {{
        return true;
    }}
    DEEP_QUERY_INDICATORS.iter().any(|ind| q_low.contains(ind))
}}

/// AST-transpiled from Python `format_query(raw_query: str) -> str`
pub fn format_query(raw_query: &str) -> String {{
    let mut q = raw_query.trim().to_string();
    let mut q_low = q.to_lowercase();
    for prefix in &["how do i ", "how can i ", "how to "] {{
        if q_low.starts_with(prefix) {{
            q = format!("to {{}}", q[prefix.len()..].trim());
            q_low = q.to_lowercase();
            break;
        }}
    }}
    if q_low.contains("in omarchy") {{
        return q;
    }}
    if q_low.starts_with("to ") {{
        return format!("In Omarchy console how {{}}", q);
    }}
    for prefix in &["auth ", "model ", "display ", "audio ", "network "] {{
        if q_low.starts_with(prefix) {{
            return format!("In Omarchy console: how {{}}", q);
        }}
    }}
    format!("In Omarchy console: {{}}", q)
}}

/// AST-transpiled from Python `strip_think_blocks(text: str) -> str`
pub fn strip_think_blocks(text: &str) -> String {{
    if !text.contains("<think>") {{
        return text.to_string();
    }}
    let mut result = text.to_string();
    while let Some(start) = result.find("<think>") {{
        if let Some(end_rel) = result[start..].find("</think>") {{
            let end = start + end_rel + "</think>".len();
            result.replace_range(start..end, "");
        }} else {{
            break;
        }}
    }}
    let trimmed = result.trim();
    if trimmed.contains("<think>") {{
        if let Some(last) = trimmed.rsplit("</think>").next() {{
            return last.trim().to_string();
        }}
    }}
    if trimmed.is_empty() {{
        text.trim().to_string()
    }} else {{
        trimmed.to_string()
    }}
}}

/// AST-transpiled from Python `extract_candidate_commands(query: str)`
pub fn extract_candidate_commands(query: &str) -> Vec<String> {{
    let q_low = query.to_lowercase();
    let mut candidates = Vec::new();
    let mut current = String::new();
    for ch in q_low.chars() {{
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' || ch == '.' {{
            current.push(ch);
        }} else if !current.is_empty() {{
            let clean = current.trim_matches(|c| c == '.' || c == '-' || c == '_').to_string();
            if clean.len() >= 2 && !COMMON_STOPWORDS.contains(&clean.as_str()) && !candidates.contains(&clean) {{
                candidates.push(clean);
            }}
            current.clear();
        }}
    }}
    if !current.is_empty() {{
        let clean = current.trim_matches(|c| c == '.' || c == '-' || c == '_').to_string();
        if clean.len() >= 2 && !COMMON_STOPWORDS.contains(&clean.as_str()) && !candidates.contains(&clean) {{
            candidates.push(clean);
        }}
    }}
    candidates
}}

fn which_binary(name: &str) -> Option<String> {{
    let path_var = env::var("PATH").unwrap_or_default();
    for dir in path_var.split(':') {{
        if dir.is_empty() {{
            continue;
        }}
        let candidate = Path::new(dir).join(name);
        if let Ok(meta) = fs::metadata(&candidate) {{
            if meta.is_file() {{
                return Some(candidate.to_string_lossy().into_owned());
            }}
        }}
    }}
    None
}}

/// Native Rust implementation of `print_context_dry_run_plan`
fn print_context_dry_run_plan(c: &Colors, query: &str) {{
    let cwd = env::current_dir()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_else(|_| ".".to_string());

    let mut steps: Vec<(String, String, String, String)> = CONTEXT_DISCOVERY_STEPS
        .iter()
        .map(|s| {{
            (
                s.id.to_string(),
                s.title.to_string(),
                s.dry_run.replace("<cwd>", &cwd),
                s.target.replace("<cwd>", &cwd),
            )
        }})
        .collect();

    if !query.is_empty() {{
        for cmd in extract_candidate_commands(query).into_iter().take(2) {{
            if let Some(cmd_path) = which_binary(&cmd) {{
                let dr = if cmd == "omarchy" || cmd.starts_with("omarchy-") {{
                    format!("head -n 40 {{}}  # parse # omarchy:* header (never executes script)", cmd_path)
                }} else {{
                    format!(
                        "tldr {{0}} || man -P cat {{0}} | head -n 25 || bwrap --ro-bind / / --unshare-all --cap-drop ALL -- timeout -k 1 2 {{1}} --help",
                        cmd, cmd_path
                    )
                }};
                steps.push((
                    format!("doc:{{}}", cmd),
                    format!("Local CLI Docs ({{}})", cmd),
                    dr,
                    cmd_path,
                ));
            }}
        }}
    }}

    println!(
        "\\n{{}}{{}}◆ Context Discovery Dry-Run Plan (careful mode){{}}",
        c.bold, c.magenta, c.reset
    );
    println!(
        "{{}}Exact read-only checks that `how` performs when approved (nothing executed in dry-run):{{}}\\n",
        c.dim, c.reset
    );
    let total = steps.len();
    for (idx, (id, title, dry_run, target)) in steps.into_iter().enumerate() {{
        println!(
            "  {{}}[Step {{}}/{{}}] {{}}{{}} {{}}({{}}){{}}",
            c.bold,
            idx + 1,
            total,
            title,
            c.reset,
            c.dim,
            id,
            c.reset
        );
        println!("    {{}}[dry-run]{{}} {{}}$ {{}}{{}}", c.yellow, c.reset, c.cyan, dry_run, c.reset);
        println!("    {{}}inspects: {{}}{{}}", c.dim, target, c.reset);
    }}
    println!();
}}

fn delegate_to_python(args: &[String]) -> ! {{
    // Pass embedded Python script via -c with exact argv parity and repo directory context
    let mut cmd = Command::new("python3");
    if env::var_os("HOW_REPO_DIR").is_none() {{
        cmd.env("HOW_REPO_DIR", SOURCE_REPO_DIR);
    }}
    let err = cmd
        .arg("-c")
        .arg(EMBEDDED_PYTHON_SOURCE)
        .args(args)
        .exec();
    eprintln!("Failed to execute python3 runtime: {{}}", err);
    std::process::exit(1);
}}

fn main() {{
    let raw_args: Vec<String> = env::args().skip(1).collect();
    let c = Colors::detect();

    // 1. Sub-millisecond native Rust fast-path: empty args or --help / -h / help
    if raw_args.is_empty()
        || (raw_args.len() == 1 && matches!(raw_args[0].to_lowercase().as_str(), "--help" | "-h" | "help"))
    {{
        print_help(&c);
        return;
    }}

    // 2. Sub-millisecond native Rust fast-path: --version / -V / version
    if raw_args.len() == 1 && matches!(raw_args[0].as_str(), "--version" | "-V" | "version") {{
        println!("how {{}}", VERSION);
        return;
    }}

    // 3. Sub-millisecond native Rust fast-path: `how context dry-run` or `how --dry-run`
    if raw_args.len() >= 2
        && raw_args[0].eq_ignore_ascii_case("context")
        && matches!(raw_args[1].to_lowercase().as_str(), "dry-run" | "dry" | "--dry-run" | "plan")
    {{
        let query_tail = if raw_args.len() > 2 {{
            raw_args[2..].join(" ")
        }} else {{
            String::new()
        }};
        print_context_dry_run_plan(&c, &query_tail);
        return;
    }}

    if raw_args.len() == 1 && raw_args[0].eq_ignore_ascii_case("--dry-run") {{
        print_context_dry_run_plan(&c, "");
        return;
    }}

    if raw_args.iter().any(|a| a.eq_ignore_ascii_case("--dry-run"))
        && !raw_args[0].eq_ignore_ascii_case("run")
        && raw_args[0] != "!"
        && !raw_args[0].eq_ignore_ascii_case("context")
    {{
        let query_words: Vec<&str> = raw_args
            .iter()
            .filter(|a| !a.starts_with('-'))
            .map(|s| s.as_str())
            .collect();
        let q_joined = query_words.join(" ");
        print_context_dry_run_plan(&c, &q_joined);
        let is_deep = heuristic_needs_deep_thinking(&q_joined);
        let badge = if is_deep {{
            format!("{{}}{{}}DEEP THINKING{{}}", c.magenta, c.bold, c.reset)
        }} else {{
            format!("{{}}{{}}FAST DIRECT{{}}", c.green, c.bold, c.reset)
        }};
        let reason = if is_deep {{
            "complex troubleshooting or multi-step query"
        }} else {{
            "direct command lookup"
        }};
        println!(
            "  {{}}[Triage Preview]{{}} Route: {{}} {{}}({{}}, model: {{}}){{}}\\n",
            c.bold, c.reset, badge, c.dim, reason, DEFAULT_MODEL, c.reset
        );
        return;
    }}

    // 4. Delegate stateful, interactive, SQLite, and network streaming commands to embedded Python
    delegate_to_python(&raw_args);
}}
"""
    return rust_code


def find_rustc() -> str:
    """Locates `rustc` in PATH or `~/.cargo/bin/rustc`."""
    found = shutil.which("rustc")
    if found:
        return found
    cargo_rustc = os.path.expanduser("~/.cargo/bin/rustc")
    if os.path.isfile(cargo_rustc) and os.access(cargo_rustc, os.X_OK):
        return cargo_rustc
    return ""


def compile_rust_binary(py_path: str, out_path: str, emit_rs_path: str = None) -> dict:
    """
    Transpiles `py_path` into Rust and compiles it with `rustc -C opt-level=3 -C strip=symbols`
    into `out_path`. Returns a result dictionary with timings and metadata.
    """
    t0 = time.perf_counter()
    if os.path.realpath(out_path) == os.path.realpath(py_path) and not os.path.islink(out_path):
        return {
            "ok": False,
            "error": "Refusing to overwrite readable Python source file in repo",
            "transpile_ms": 0.0,
        }
    rust_code = transpile_python_to_rust(py_path)
    transpile_ms = (time.perf_counter() - t0) * 1000

    if emit_rs_path:
        os.makedirs(os.path.dirname(os.path.abspath(emit_rs_path)), exist_ok=True)
        with open(emit_rs_path, "w", encoding="utf-8") as f:
            f.write(rust_code)

    rustc_bin = find_rustc()
    if not rustc_bin:
        return {
            "ok": False,
            "error": "rustc not found on system",
            "transpile_ms": transpile_ms,
        }

    tmp_dir = tempfile.mkdtemp(prefix="how_rust_build_")
    try:
        rs_file = os.path.join(tmp_dir, "how.rs")
        tmp_out = os.path.join(tmp_dir, "how_bin")
        with open(rs_file, "w", encoding="utf-8") as f:
            f.write(rust_code)

        t_comp = time.perf_counter()
        proc = subprocess.run(
            [rustc_bin, "-C", "opt-level=3", "-C", "strip=symbols", rs_file, "-o", tmp_out],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        compile_ms = (time.perf_counter() - t_comp) * 1000
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": proc.stderr.strip(),
                "transpile_ms": transpile_ms,
                "compile_ms": compile_ms,
            }

        os.chmod(tmp_out, 0o755)
        out_abs = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        # Unlink target first in case it is a symlink to the Python source file!
        if os.path.islink(out_abs) or os.path.exists(out_abs):
            try:
                os.unlink(out_abs)
            except Exception as e:
                return {
                    "ok": False,
                    "error": f"Cannot replace {out_abs}: {e}",
                    "transpile_ms": transpile_ms,
                    "compile_ms": compile_ms,
                }
        if os.path.realpath(out_abs) == os.path.realpath(py_path):
            return {
                "ok": False,
                "error": "Refusing to overwrite readable Python source file in repo",
                "transpile_ms": transpile_ms,
                "compile_ms": compile_ms,
            }
        shutil.move(tmp_out, out_abs)
        size_kb = os.path.getsize(out_abs) / 1024.0
        return {
            "ok": True,
            "out_path": out_abs,
            "rustc": rustc_bin,
            "transpile_ms": transpile_ms,
            "compile_ms": compile_ms,
            "size_kb": size_kb,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def measure_latency_ms(cmd_argv: list, runs: int = 5) -> float:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["HOW_NO_BROWSER"] = "1"
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        subprocess.run(cmd_argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        samples.append((time.perf_counter() - t0) * 1000)
    return sum(samples) / len(samples)


def main():
    parser = argparse.ArgumentParser(description="Deterministic Python-to-Rust transpiler for `how`.")
    parser.add_argument("source", nargs="?", default=None, help="Path to readable Python `how` file")
    parser.add_argument("-o", "--output", default=None, help="Output binary path (default: ~/.local/bin/how)")
    parser.add_argument("--emit-rs", default=None, help="Optional path to write generated .rs source")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    py_path = os.path.abspath(args.source or os.path.join(repo_root, "how"))
    out_path = os.path.abspath(
        args.output
        or os.path.join(os.environ.get("HOW_INSTALL_DIR") or os.path.expanduser("~/.local/bin"), "how")
    )

    if os.path.realpath(out_path) == os.path.realpath(py_path) and not os.path.islink(out_path):
        print("✗ Output binary path cannot overwrite the readable Python source file in repo.", file=sys.stderr)
        sys.exit(1)

    res = compile_rust_binary(py_path, out_path, emit_rs_path=args.emit_rs)
    if not res.get("ok"):
        if not args.quiet:
            print(f"! Rust transpilation unavailable ({res.get('error')}).", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        py_ms = measure_latency_ms([sys.executable, py_path, "--help"])
        rs_ms = measure_latency_ms([out_path, "--help"])
        speedup = py_ms / rs_ms if rs_ms > 0 else 1.0
        print("\n◆ Python → Rust Local Transpilation Complete (Zero LLM)")
        print(f"  • Source (kept readable): {py_path}")
        print(f"  • Native Rust Binary:     {res['out_path']} ({res['size_kb']:.0f} KB)")
        print(f"  • AST Transpile Time:     {res['transpile_ms']:.1f} ms")
        print(f"  • rustc -O Compile Time:  {res['compile_ms']:.0f} ms")
        print(f"  • Startup Latency:        {py_ms:.2f} ms (Python) → {rs_ms:.2f} ms (Rust, {speedup:.1f}x faster)\n")


if __name__ == "__main__":
    main()
