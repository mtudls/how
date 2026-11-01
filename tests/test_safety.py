#!/usr/bin/env python3
"""
Safety & Sandbox Unit Tests for `how` CLI.
Standard library unittest, runnable via `python3 tests/test_safety.py`.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

HOW_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "how"))


def load_how_module():
    loader = importlib.machinery.SourceFileLoader("how_safety_mod", HOW_PATH)
    spec = importlib.util.spec_from_loader("how_safety_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class TestSafetyAndSandbox(unittest.TestCase):
    def setUp(self):
        self.tmp_config_dir = tempfile.mkdtemp(prefix="how_test_cfg_")
        self.tmp_cache_dir = tempfile.mkdtemp(prefix="how_test_cache_")
        self.orig_env = os.environ.copy()
        os.environ["HOW_CONFIG_DIR"] = self.tmp_config_dir
        os.environ["HOW_CACHE_DIR"] = self.tmp_cache_dir
        os.environ["NO_COLOR"] = "1"
        self.how = load_how_module()
        self.how.CONFIG_DIR = self.tmp_config_dir
        self.how.CONFIG_FILE = os.path.join(self.tmp_config_dir, "config.json")
        self.how.CACHE_DIR = self.tmp_cache_dir
        self.how.CACHE_DB_FILE = os.path.join(self.tmp_cache_dir, "cache.db")

    def tearDown(self):
        shutil.rmtree(self.tmp_config_dir, ignore_errors=True)
        shutil.rmtree(self.tmp_cache_dir, ignore_errors=True)
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_build_sandbox_argv(self):
        """build_sandbox_argv contains all required bubblewrap isolation flags and cmd."""
        cmd_path = "/usr/bin/python3"
        args = ["-c", "print(1)"]
        argv = self.how.build_sandbox_argv(cmd_path, args)

        required_flags = [
            "--ro-bind", "/", "/",
            "--tmpfs", "/run",
            "--tmpfs", "/tmp",
            "--unshare-all",
            "--new-session",
            "--die-with-parent",
            "--cap-drop", "ALL",
        ]
        for flag in required_flags:
            self.assertIn(flag, argv, f"Missing flag {flag} in sandbox argv")

        self.assertIn("timeout", argv)
        self.assertIn(cmd_path, argv)

    def test_omarchy_help_never_executes_subprocess(self):
        """get_cli_help for omarchy-* never executes subprocess."""
        tmp_bin_dir = tempfile.mkdtemp(prefix="how_omarchy_bin_")
        try:
            marker_file = os.path.join(tmp_bin_dir, "executed.marker")
            fake_with_hdr = os.path.join(tmp_bin_dir, "omarchy-fake")
            with open(fake_with_hdr, "w", encoding="utf-8") as f:
                f.write(f"#!/bin/bash\n# omarchy:summary=Test summary for fake\ntouch {marker_file}\n")
            os.chmod(fake_with_hdr, 0o755)

            fake_no_hdr = os.path.join(tmp_bin_dir, "omarchy-nohdr")
            with open(fake_no_hdr, "w", encoding="utf-8") as f:
                f.write(f"#!/bin/bash\ntouch {marker_file}\n")
            os.chmod(fake_no_hdr, 0o755)

            env_path = tmp_bin_dir + ":" + os.environ.get("PATH", "")
            with patch.dict(os.environ, {"PATH": env_path}):
                with patch("subprocess.run", side_effect=RuntimeError("Subprocess run was called!")):
                    with patch("subprocess.Popen", side_effect=RuntimeError("Subprocess Popen was called!")):
                        help_hdr = self.how.get_cli_help("omarchy-fake")
                        self.assertIsNotNone(help_hdr)
                        self.assertIn("Summary: Test summary for fake", help_hdr)

                        help_nohdr = self.how.get_cli_help("omarchy-nohdr")
                        self.assertIsNotNone(help_nohdr)
                        self.assertIn("exists on this system", help_nohdr)

            self.assertFalse(os.path.exists(marker_file), "Omarchy scripts must never be executed by get_cli_help")
        finally:
            shutil.rmtree(tmp_bin_dir, ignore_errors=True)

    def test_run_sandboxed_help_missing_or_disabled(self):
        """run_sandboxed_help returns None when bwrap missing or HOW_NO_SANDBOX_HELP=1."""
        with patch("shutil.which", return_value=None):
            self.assertIsNone(self.how.run_sandboxed_help("/bin/ls"))

        with patch.dict(os.environ, {"HOW_NO_SANDBOX_HELP": "1"}):
            self.assertIsNone(self.how.run_sandboxed_help("/bin/ls"))

    def test_model_fallback_bounded_and_config_unchanged_on_failure(self):
        """Model fallback is bounded and does not overwrite config on persistent failure."""
        initial_cfg = {"model": "openai/gpt-oss-120b", "discover_os": False, "discover_stack": False}
        self.how.save_config(initial_cfg)

        called_models = []
        created_errors = []

        def fake_urlopen(req, timeout=30):
            data = json.loads(req.data.decode("utf-8"))
            called_models.append(data.get("model"))
            err = urllib.error.HTTPError(
                url="https://api.groq.com",
                code=404,
                msg="Not Found",
                hdrs={},
                fp=MagicMock(read=lambda: b'{"error": {"message": "Model not found"}}'),
            )
            created_errors.append(err)
            raise err

        try:
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                with patch.object(self.how, "get_api_key", return_value="gsk_fake_key_12345"):
                    with patch.object(self.how, "require_api_key", return_value="gsk_fake_key_12345"):
                        self.how.ask_groq("how to test fallback", no_cache=True)
        finally:
            for err in created_errors:
                try:
                    err.close()
                except Exception:
                    pass

        fallback_pool = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        max_attempts = len(fallback_pool) + 1
        self.assertLessEqual(len(called_models), max_attempts)
        self.assertEqual(len(called_models), len(set(called_models)), "Each model must be tried at most once")

        cfg = self.how.load_config()
        self.assertEqual(cfg.get("model"), "openai/gpt-oss-120b")

    def test_feedback_consent_non_interactive(self):
        """With stdin not a TTY and auto_yes False, feedback is previewed but not sent."""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("subprocess.run") as mock_subproc:
                with patch.object(self.how, "open_feedback_url") as mock_open_url:
                    self.how.send_terminal_feedback("something is broken", auto_yes=False)
                    mock_subproc.assert_not_called()
                    mock_open_url.assert_not_called()

    def test_bash_history_opt_in(self):
        """save_to_bash_history writes only when opted in via HOW_BASH_HISTORY=1 or config."""
        tmp_home = tempfile.mkdtemp(prefix="how_test_home_")
        try:
            hist_file = os.path.join(tmp_home, ".bash_history")
            with patch.dict(os.environ, {"HOME": tmp_home}):
                with patch.dict(os.environ, {}, clear=False):
                    if "HOW_BASH_HISTORY" in os.environ:
                        del os.environ["HOW_BASH_HISTORY"]
                    self.how.save_to_bash_history("echo hello", query="ping")
                    self.assertFalse(os.path.exists(hist_file))

                with patch.dict(os.environ, {"HOW_BASH_HISTORY": "1"}):
                    self.how.save_to_bash_history("echo hello", query="ping")
                    self.assertTrue(os.path.exists(hist_file))
                    with open(hist_file, encoding="utf-8") as f:
                        lines = f.readlines()
                    self.assertEqual(len(lines), 2)
                    self.assertIn("# how: unverified AI suggestion", lines[0])
                    self.assertIn("ping", lines[0])
                    self.assertEqual(lines[1].strip(), "echo hello")
        finally:
            shutil.rmtree(tmp_home, ignore_errors=True)

    def test_strip_control_sequences(self):
        """strip_control_sequences removes ESC codes and OSC titles while preserving text and newlines."""
        raw = "\x1b[31mRed Alert\x1b[0m\n\x1b]0;Evil Window Title\x07Normal text\twith tab"
        cleaned = self.how.strip_control_sequences(raw)
        self.assertNotIn("\x1b[31m", cleaned)
        self.assertNotIn("\x1b]0;Evil Window Title\x07", cleaned)
        self.assertNotIn("\x1b", cleaned)
        self.assertIn("Red Alert\n", cleaned)
        self.assertIn("Normal text\twith tab", cleaned)

    def test_cli_version_and_invalid_verbosity(self):
        """--version prints __version__; verbosity bogus exits with code 2."""
        proc_ver = subprocess.run([sys.executable, HOW_PATH, "--version"], capture_output=True, text=True)
        self.assertEqual(proc_ver.returncode, 0)
        self.assertIn(self.how.__version__, proc_ver.stdout)

        proc_verb = subprocess.run([sys.executable, HOW_PATH, "verbosity", "bogus"], capture_output=True, text=True)
        self.assertEqual(proc_verb.returncode, 2)
        self.assertIn("Invalid verbosity level", proc_verb.stdout)

    def test_db_session_commits_and_persists_cache(self):
        """db_session commits transactions cleanly."""
        query = "test query persistence"
        model = "test-model"
        verbosity = "normal"
        response_text = "echo 'cache persisted'"
        retention = 3600

        self.how.save_cached_response(query, model, verbosity, response_text, retention)
        hit = self.how.get_cached_response(query, model, verbosity, retention)
        self.assertIsNotNone(hit)
        self.assertEqual(hit[0], response_text)

    def test_version_only_as_single_argument(self):
        """parse_cli_args keeps --version in args when part of a multi-word query."""
        raw_args = ["to", "check", "python", "--version"]
        opts, args = self.how.parse_cli_args(raw_args)
        self.assertFalse(opts.get("version_requested", False))
        self.assertIn("--version", args)
        self.assertEqual(args, ["to", "check", "python", "--version"])

        opts_single, args_single = self.how.parse_cli_args(["--version"])
        self.assertTrue(opts_single.get("version_requested"))
        self.assertEqual(args_single, [])

    def test_yes_flag_kept_for_normal_query_containing_bug(self):
        """-y flag is kept in arguments for a query that contains 'bug' but is not feedback context."""
        raw_args = ["to", "fix", "bug", "apt", "install", "-y"]
        opts, args = self.how.parse_cli_args(raw_args)
        self.assertFalse(opts.get("feedback_yes", False))
        self.assertIn("-y", args)
        self.assertEqual(args, ["to", "fix", "bug", "apt", "install", "-y"])

    def test_docs_fingerprint_does_not_spawn_subprocesses(self):
        """docs_fingerprint computes hash without spawning any subprocesses."""
        def fail_subprocess(*args, **kwargs):
            raise AssertionError("Subprocess execution is strictly forbidden in docs_fingerprint")

        with patch("subprocess.run", side_effect=fail_subprocess):
            with patch("subprocess.Popen", side_effect=fail_subprocess):
                fp = self.how.docs_fingerprint("how to fix git commit")
                self.assertIsInstance(fp, str)
                self.assertGreater(len(fp), 0)

    def test_context_permission_gate_respected(self):
        """Without permission, get_active_environment_context returns empty string."""
        cfg = {"discover_os": False, "discover_stack": False, "context_prompted": True}
        ctx = self.how.get_active_environment_context(cfg=cfg, no_context=False)
        self.assertEqual(ctx, "")

        # With discover_os=True, includes OS profile
        cfg_os = {"discover_os": True, "discover_stack": False, "context_prompted": True}
        ctx_os = self.how.get_active_environment_context(cfg=cfg_os, no_context=False)
        self.assertIn("OS:", ctx_os)

        # --no-context overrides even when permissions are True
        ctx_none = self.how.get_active_environment_context(cfg=cfg_os, no_context=True)
        self.assertEqual(ctx_none, "")

    def test_groq_triage_routing(self):
        """triage_query_with_groq routes short direct commands to fast and complex queries via Groq or heuristic."""
        res_fast = self.how.triage_query_with_groq("to ping google", api_key=None)
        self.assertEqual(res_fast["route"], "fast")

        res_deep = self.how.triage_query_with_groq(
            "why does secure boot cause black screen boot loop on limine", api_key=None
        )
        self.assertEqual(res_deep["route"], "deep")

    def test_graduated_context_step_by_step_and_yolo(self):
        """Graduated context discovery supports careful step-by-step approval, dry-run commands, and yolo receipt."""
        steps = self.how.get_context_dry_run_steps(query="how to use pacman")
        self.assertGreaterEqual(len(steps), 5)
        self.assertIn("cat /etc/os-release", steps[0]["dry_run"])

        # Step-by-step approval: approve os_release & kernel, deny desktop & shell_pkg, approve stack
        answers = iter(["y", "y", "n", "n", "y"])
        cfg = self.how.run_step_by_step_context_approval(
            cfg={},
            input_fn=lambda _prompt: next(answers),
        )
        self.assertEqual(cfg.get("context_mode"), "careful")
        self.assertTrue(cfg["context_steps"]["os_release"])
        self.assertTrue(cfg["context_steps"]["kernel"])
        self.assertFalse(cfg["context_steps"]["desktop"])
        self.assertFalse(cfg["context_steps"]["shell_pkg"])
        self.assertTrue(cfg["context_steps"]["stack"])
        self.assertEqual(cfg["os_profile"].get("desktop"), "")

        # YOLO mid-stream switch: step 1 'yolo' approves all remaining steps and reports what was read
        cfg_yolo = self.how.run_step_by_step_context_approval(
            cfg={},
            input_fn=lambda _prompt: "yolo",
        )
        self.assertEqual(cfg_yolo.get("context_mode"), "yolo")
        self.assertTrue(all(cfg_yolo["context_steps"].values()))
        receipt = self.how.format_context_read_receipt(os_prof=cfg_yolo.get("os_profile"))
        self.assertIn("OS[", receipt)

    def test_deterministic_rust_transpiler(self):
        """scripts/transpile_rust.py deterministically transpiles Python AST to Rust without any LLM."""
        transpiler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "transpile_rust.py"))
        loader = importlib.machinery.SourceFileLoader("transpile_rust_mod", transpiler_path)
        spec = importlib.util.spec_from_loader("transpile_rust_mod", loader)
        tr_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(tr_mod)

        rs_code = tr_mod.transpile_python_to_rust(HOW_PATH)
        self.assertIn(f'pub const VERSION: &str = "{self.how.__version__}";', rs_code)
        self.assertIn("pub fn heuristic_needs_deep_thinking", rs_code)
        self.assertIn("pub const CONTEXT_DISCOVERY_STEPS", rs_code)

    def test_graduated_context_all_branches(self):
        """run_step_by_step_context_approval handles dry-run preview, off/quit abort, and EOFError."""
        # 1. 'dry' on step 1 previews dry-run only (skips reading os_release),
        #    'y' on step 2 approves kernel, 'off' on step 3 disables remaining discovery
        seq = iter(["dry", "y", "off"])
        cfg1 = self.how.run_step_by_step_context_approval(
            cfg={},
            input_fn=lambda _p: next(seq),
        )
        self.assertEqual(cfg1.get("context_mode"), "off")
        self.assertFalse(cfg1["context_steps"]["os_release"])
        self.assertTrue(cfg1["context_steps"]["kernel"])
        self.assertFalse(cfg1["context_steps"]["desktop"])
        self.assertFalse(cfg1["context_steps"]["shell_pkg"])
        self.assertFalse(cfg1["context_steps"]["stack"])

        # 2. EOFError during step approval cancels cleanly and disables discovery
        def raise_eof(_p):
            raise EOFError()

        cfg_eof = self.how.run_step_by_step_context_approval(cfg={}, input_fn=raise_eof)
        self.assertEqual(cfg_eof.get("context_mode"), "off")
        self.assertFalse(cfg_eof.get("discover_os"))
        self.assertFalse(cfg_eof.get("discover_stack"))

        # 3. detect_local_stack in temp project directory records exact files_read
        tmp_proj = tempfile.mkdtemp(prefix="how_test_proj_")
        try:
            with open(os.path.join(tmp_proj, "Cargo.toml"), "w", encoding="utf-8") as f:
                f.write('[package]\nname = "demo"\n')
            with open(os.path.join(tmp_proj, "Dockerfile"), "w", encoding="utf-8") as f:
                f.write("FROM alpine:3.20\n")
            stack_info = self.how.detect_local_stack(cwd=tmp_proj)
            self.assertIn("Rust (cargo)", stack_info["summary"])
            self.assertIn("Docker", stack_info["summary"])
            self.assertIn("Cargo.toml", stack_info["files_read"])
            self.assertIn("Dockerfile", stack_info["files_read"])
        finally:
            shutil.rmtree(tmp_proj, ignore_errors=True)

    def test_dry_run_cli_and_query_mode(self):
        """--dry-run previews context discovery and triage route with zero network calls."""
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network call forbidden in --dry-run")):
            proc = subprocess.run(
                [sys.executable, HOW_PATH, "--dry-run", "to", "check", "python3", "version"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("[dry-run]", proc.stdout)
            self.assertIn("cat /etc/os-release", proc.stdout)
            self.assertIn("[Triage Preview]", proc.stdout)

    def test_yolo_flag_overrides_disabled_config(self):
        """--yolo flag forces OS and stack context discovery and prints Read receipt even when disabled in config."""
        self.how.save_config({
            "discover_os": False,
            "discover_stack": False,
            "context_mode": "off",
            "context_prompted": True,
        })
        ctx_str, receipt, os_prof, _ = self.how.get_active_environment_context(
            cfg=self.how.load_config(),
            no_context=False,
            force_context=True,
            context_mode_override="yolo",
            return_receipt=True,
        )
        self.assertIn("OS:", ctx_str)
        self.assertIn("OS[", receipt)
        self.assertIsNotNone(os_prof)

    def test_run_last_command_lifecycle(self):
        """how run supports empty log, --dry-run, non-TTY refusal, and -y execution."""
        # 1. Empty commands.log
        self.how.COMMANDS_LOG = os.path.join(self.tmp_config_dir, "commands.log")
        self.how.run_last_command(auto_yes=True, dry_run=False)

        # 2. Log a safe command proposal
        self.how.log_command_proposal("test echo", "echo how_run_ok", executed=False)
        self.assertTrue(os.path.exists(self.how.COMMANDS_LOG))

        # 3. Dry run does not mark EXECUTED
        self.how.run_last_command(auto_yes=False, dry_run=True)
        with open(self.how.COMMANDS_LOG, encoding="utf-8") as f:
            log_text = f.read()
        self.assertNotIn("[EXECUTED]", log_text)

        # 4. Non-interactive without auto_yes refuses execution
        with patch("sys.stdin.isatty", return_value=False):
            self.how.run_last_command(auto_yes=False, dry_run=False)
        with open(self.how.COMMANDS_LOG, encoding="utf-8") as f:
            log_text = f.read()
        self.assertNotIn("[EXECUTED]", log_text)

        # 5. auto_yes=True executes command, logs [EXECUTED], and exits with returncode 0
        with self.assertRaises(SystemExit) as cm:
            self.how.run_last_command(auto_yes=True, dry_run=False)
        self.assertEqual(cm.exception.code, 0)
        with open(self.how.COMMANDS_LOG, encoding="utf-8") as f:
            log_text = f.read()
        self.assertIn("[EXECUTED]", log_text)

    def test_rust_transpiler_binary_parity_and_safety(self):
        """Rust transpiler refuses source overwrite and produces an ELF binary with full CLI parity."""
        transpiler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "transpile_rust.py"))
        loader = importlib.machinery.SourceFileLoader("transpile_rust_mod2", transpiler_path)
        spec = importlib.util.spec_from_loader("transpile_rust_mod2", loader)
        tr_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(tr_mod)

        # Safety check: refusing to overwrite source Python file
        res_same = tr_mod.compile_rust_binary(HOW_PATH, HOW_PATH)
        self.assertFalse(res_same.get("ok"))
        self.assertIn("Refusing to overwrite", res_same.get("error", ""))

        rustc_bin = shutil.which("rustc")
        if not rustc_bin:
            cargo_rustc = os.path.expanduser("~/.cargo/bin/rustc")
            if os.path.isfile(cargo_rustc) and os.access(cargo_rustc, os.X_OK):
                rustc_bin = cargo_rustc
        if not rustc_bin:
            return

        tmp_bin_dir = tempfile.mkdtemp(prefix="how_rust_parity_")
        try:
            bin_path = os.path.join(tmp_bin_dir, "how-rs")
            env = os.environ.copy()
            env["PATH"] = os.path.dirname(rustc_bin) + ":" + env.get("PATH", "")
            with patch.dict(os.environ, env):
                res = tr_mod.compile_rust_binary(HOW_PATH, bin_path)
            self.assertTrue(res.get("ok"), f"Rust compile failed: {res.get('error')}")

            with open(bin_path, "rb") as f:
                magic = f.read(4)
            self.assertEqual(magic, b"\x7fELF", "Compiled binary must be a native ELF executable")

            # Native fast paths: --version, --help, context dry-run, --dry-run query
            p_ver = subprocess.run([bin_path, "--version"], capture_output=True, text=True, env=env)
            self.assertEqual(p_ver.returncode, 0)
            self.assertIn(f"how {self.how.__version__}", p_ver.stdout)

            p_help = subprocess.run([bin_path, "--help"], capture_output=True, text=True, env=env)
            self.assertEqual(p_help.returncode, 0)
            self.assertIn("Graduated OS & stack discovery", p_help.stdout)

            p_dry = subprocess.run([bin_path, "context", "dry-run"], capture_output=True, text=True, env=env)
            self.assertEqual(p_dry.returncode, 0)
            self.assertIn("cat /etc/os-release", p_dry.stdout)

            p_qdry = subprocess.run(
                [bin_path, "--dry-run", "why", "does", "limine", "fail", "secure", "boot"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(p_qdry.returncode, 0)
            self.assertIn("DEEP THINKING", p_qdry.stdout)

            # Delegated Python path: status
            p_status = subprocess.run([bin_path, "status"], capture_output=True, text=True, env=env)
            self.assertEqual(p_status.returncode, 0)
            self.assertIn("Unified Status Dashboard", p_status.stdout)
        finally:
            shutil.rmtree(tmp_bin_dir, ignore_errors=True)

    def test_install_sh_rust_and_python_only_modes(self):
        """install.sh supports both --python-only and default native Rust transpilation."""
        install_sh = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "install.sh"))
        tmp_inst_py = tempfile.mkdtemp(prefix="how_inst_py_")
        tmp_inst_rs = tempfile.mkdtemp(prefix="how_inst_rs_")
        try:
            env_py = os.environ.copy()
            env_py["HOW_INSTALL_DIR"] = tmp_inst_py
            p1 = subprocess.run(["bash", install_sh, "--python-only"], capture_output=True, text=True, env=env_py)
            self.assertEqual(p1.returncode, 0, f"install.sh --python-only failed: {p1.stderr}")
            installed_py = os.path.join(tmp_inst_py, "how")
            self.assertTrue(os.path.isfile(installed_py))
            with open(installed_py, "rb") as f:
                self.assertTrue(f.read(2) == b"#!")

            rustc_bin = shutil.which("rustc") or os.path.expanduser("~/.cargo/bin/rustc")
            if os.path.isfile(rustc_bin) and os.access(rustc_bin, os.X_OK):
                env_rs = os.environ.copy()
                env_rs["HOW_INSTALL_DIR"] = tmp_inst_rs
                env_rs["PATH"] = os.path.dirname(rustc_bin) + ":" + env_rs.get("PATH", "")
                p2 = subprocess.run(["bash", install_sh], capture_output=True, text=True, env=env_rs)
                self.assertEqual(p2.returncode, 0, f"install.sh failed: {p2.stderr}")
                installed_rs = os.path.join(tmp_inst_rs, "how")
                self.assertTrue(os.path.isfile(installed_rs))
                with open(installed_rs, "rb") as f:
                    self.assertEqual(f.read(4), b"\x7fELF")
        finally:
            shutil.rmtree(tmp_inst_py, ignore_errors=True)
            shutil.rmtree(tmp_inst_rs, ignore_errors=True)

    def test_static_code_quality_and_bandit_invariants(self):
        """AST & static check across all repo Python files for syntax, line-length <= 130, and zero eval/exec."""
        import ast

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        py_files = [
            os.path.join(repo_root, "how"),
            os.path.join(repo_root, "scripts", "transpile_rust.py"),
            os.path.join(repo_root, "scripts", "ai_architect_review.py"),
            os.path.join(repo_root, "tests", "test_safety.py"),
            os.path.join(repo_root, "tests", "test_vv_suite.py"),
            os.path.join(repo_root, "tests", "test_ab_bench.py"),
        ]
        for path in py_files:
            self.assertTrue(os.path.isfile(path), f"Missing expected file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(
                        node.func.id,
                        ("eval", "exec"),
                        f"Forbidden {node.func.id}() call in {path}:{getattr(node, 'lineno', 0)}",
                    )
            for lineno, line in enumerate(source.splitlines(), start=1):
                self.assertEqual(
                    line,
                    line.rstrip(" \t"),
                    f"Trailing whitespace in {os.path.relpath(path, repo_root)}:{lineno}",
                )


if __name__ == "__main__":
    unittest.main()
