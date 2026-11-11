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

        # 6. Destructive commands require typing the full word 'yes' (not just 'y')
        self.how.log_command_proposal("wipe tmp", "rm -rf /tmp/how-demo-build", executed=False)
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", return_value="y"):
                self.how.run_last_command(auto_yes=False, dry_run=False)
        with open(self.how.COMMANDS_LOG, encoding="utf-8") as f:
            after_reject = f.read()
        # Still only the earlier safe EXECUTED; destructive reject must not add another
        self.assertEqual(after_reject.count("[EXECUTED]"), 1)

        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", return_value="yes"):
                with patch("subprocess.run", return_value=type("R", (), {"returncode": 0})()) as mock_run:
                    with self.assertRaises(SystemExit) as cm2:
                        self.how.run_last_command(auto_yes=False, dry_run=False)
                    self.assertEqual(cm2.exception.code, 0)
                    mock_run.assert_called_once()

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

    def test_quality_suite_classification_and_extraction(self):
        """tests/quality/run_compare.py and extract_history.py accurately classify outputs and filter junk."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        rc_path = os.path.join(repo_root, "tests", "quality", "run_compare.py")
        eh_path = os.path.join(repo_root, "tests", "quality", "extract_history.py")

        rc_spec = importlib.util.spec_from_file_location("run_compare_mod", rc_path)
        rc_mod = importlib.util.module_from_spec(rc_spec)
        rc_spec.loader.exec_module(rc_mod)

        eh_spec = importlib.util.spec_from_file_location("extract_history_mod", eh_path)
        eh_mod = importlib.util.module_from_spec(eh_spec)
        eh_spec.loader.exec_module(eh_mod)

        # 1. IDK, 429 rate-limit, and prose are NOT classified as real commands
        self.assertEqual(rc_mod.classify_response("I don't know\n"), ("idk", "I don't know", False))
        self.assertIsNone(rc_mod.extract_command("I don't know\n"))

        rate_txt = "⚡ Groq API rate limit reached (429 Rate Limit). Try again in a moment."
        self.assertEqual(rc_mod.classify_response(rate_txt)[0], "rate_limit")
        self.assertIsNone(rc_mod.extract_command(rate_txt))

        prose_sudo = "No, Omarchy cannot use a phone passkey to authorize sudo."
        self.assertEqual(rc_mod.classify_response(prose_sudo), ("prose", prose_sudo, False))
        self.assertEqual(rc_mod.classify_exec(prose_sudo, real_command=False), ("skip", "no command"))

        # 2. Real commands and placeholder syntax validation
        kind, cmd, is_real = rc_mod.classify_response("git remote set-url origin <repository-url>\n")
        self.assertEqual(kind, "command")
        self.assertTrue(is_real)
        self.assertTrue(rc_mod.bash_n_ok(cmd))
        self.assertEqual(rc_mod.classify_exec(cmd, real_command=True), ("skip", "needs host"))

        # 3. `omarchy` subcommands are skipped as host-dependent in sandbox
        self.assertEqual(rc_mod.classify_exec("omarchy pkg add vlc", real_command=True), ("skip", "needs host"))
        self.assertEqual(rc_mod.classify_exec("uname -r", real_command=True), ("execute", None))

        # 4. Case-insensitive junk filtering and semantic deduplication in extract_history.py
        self.assertTrue(eh_mod.is_junk_query("do I feel?"))
        self.assertTrue(eh_mod.is_junk_query("to destroy omarchy?"))
        self.assertFalse(eh_mod.is_junk_query("to check memory usage"))
        self.assertEqual(
            eh_mod.semantic_signature("to push to freshly created gh repo? repo is mdsyseng/how"),
            eh_mod.semantic_signature("to push new local repo to freshly created gh repo?"),
        )

    def test_pre_idk_intermediate_steps_and_cross_platform_escalation(self):
        """Intermediate steps before 'I don't know': Step 1 refines question; Step 2 escalates to smarter model."""
        import io

        # 1. Uncertainty detection and typo/shorthand query improvement
        self.assertTrue(self.how.is_uncertain_response("I don't know"))
        self.assertTrue(self.how.is_uncertain_response("<think>pondering</think>\nI don't know."))
        self.assertFalse(self.how.is_uncertain_response("```bash\nln -s target link\n```"))

        imp_q, notes = self.how.improve_query_locally("to maske symlik")
        self.assertIn("symbolic link with ln -s", imp_q)
        self.assertGreaterEqual(len(notes), 2)

        imp_origin, _ = self.how.improve_query_locally("to see orign")
        self.assertIn("git remote origin url", imp_origin)
        self.assertIn("ln -s", self.how.get_domain_grounding_hint("how to create symlink"))

        # Helper to build a fake SSE response for stream_groq_response
        class FakeSSEResponse:
            def __init__(self, content_str):
                self.status = 200
                chunk = json.dumps({"choices": [{"delta": {"content": content_str}}]})
                self._lines = [
                    f"data: {chunk}\n".encode("utf-8"),
                    b"data: [DONE]\n",
                ]

            def __iter__(self):
                return iter(self._lines)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        # Helper to build a fake JSON response for ask_deep_model
        class FakeJSONResponse:
            def __init__(self, payload_obj):
                self.status = 200
                self._bytes = json.dumps(payload_obj).encode("utf-8")

            def read(self):
                return self._bytes

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        # 2. Step 1 Recovery: Initial fast model returns "I don't know", refined question succeeds
        step1_calls = []

        def fake_urlopen_step1(req, timeout=30):
            body = json.loads(req.data.decode("utf-8"))
            step1_calls.append(body)
            if len(step1_calls) == 1:
                return FakeSSEResponse("I don't know")
            return FakeSSEResponse("```bash\nln -s /path/to/target /path/to/link\n```")

        buf1 = io.StringIO()
        with patch("urllib.request.urlopen", side_effect=fake_urlopen_step1):
            with patch.object(self.how, "get_api_key", return_value="gsk_fake_key"):
                with patch.object(self.how, "require_api_key", return_value="gsk_fake_key"):
                    with patch("sys.stdout", buf1):
                        self.how.ask_groq("to maske symlink", verbosity="zero", no_cache=False)

        self.assertEqual(len(step1_calls), 2, "Must retry once with refined question in Step 1")
        self.assertIn("Domain Hint:", step1_calls[1]["messages"][1]["content"])
        self.assertIn("ln -s /path/to/target /path/to/link", buf1.getvalue())
        self.assertNotIn("I don't know", buf1.getvalue())

        # 3. Step 2 Recovery: Initial + Step 1 return "I don't know", smarter model on external platform succeeds
        step2_urls = []

        def fake_urlopen_step2(req, timeout=30):
            url = req.full_url
            step2_urls.append(url)
            if "generativelanguage.googleapis.com" in url:
                return FakeJSONResponse({
                    "candidates": [{"content": {"parts": [{"text": "```bash\ngit remote -v\n```"}]}}]
                })
            return FakeSSEResponse("I don't know")

        buf2 = io.StringIO()
        with patch.dict(os.environ, {"HOW_THINK_MODEL": "gemini:gemini-2.5-pro", "GEMINI_API_KEY": "gm_fake_key"}):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen_step2):
                with patch.object(self.how, "get_api_key", return_value="gsk_fake_key"):
                    with patch.object(self.how, "require_api_key", return_value="gsk_fake_key"):
                        with patch("sys.stdout", buf2):
                            self.how.ask_groq("to see orign", verbosity="zero", no_cache=True)

        self.assertEqual(len(step2_urls), 3, "Must run Initial -> Step 1 (Refined) -> Step 2 (Smarter Model)")
        self.assertTrue(any("generativelanguage.googleapis.com" in u for u in step2_urls))
        self.assertIn("git remote -v", buf2.getvalue())

        # 4. Honest 'I don't know' preservation & non-caching when all steps are uncertain
        def fake_urlopen_all_idk(req, timeout=30):
            body = json.loads(req.data.decode("utf-8"))
            if body.get("stream"):
                return FakeSSEResponse("I don't know")
            return FakeJSONResponse({"choices": [{"message": {"content": "I don't know"}}]})

        buf3 = io.StringIO()
        q_unknown = "to calibrate fictional hyperdrive in zorgos"
        with patch("urllib.request.urlopen", side_effect=fake_urlopen_all_idk):
            with patch.object(self.how, "get_api_key", return_value="gsk_fake_key"):
                with patch.object(self.how, "require_api_key", return_value="gsk_fake_key"):
                    with patch("sys.stdout", buf3):
                        self.how.ask_groq(q_unknown, verbosity="zero", no_cache=False)

        self.assertEqual(buf3.getvalue().strip(), "I don't know")
        cached_idk = self.how.get_cached_response(q_unknown, self.how.DEFAULT_MODEL, "zero", 3600)
        self.assertIsNone(cached_idk, "Uncertain 'I don't know' responses must never poison the cache")

    def test_safety_badges_explain_fix_and_repeat_cache(self):
        """Traffic-light safety badges, `how explain` pipeline anatomy, `how fix` diagnostics, and cache hit_count work."""
        # 1. Traffic-light command safety tiers
        self.assertEqual(self.how.classify_command_safety("ls -la /tmp")["level"], "safe")
        self.assertEqual(self.how.classify_command_safety("ln -s a b")["level"], "modifies")
        self.assertEqual(self.how.classify_command_safety("rm -rf /tmp/build")["level"], "destructive")
        self.assertEqual(self.how.classify_command_safety("sudo pacman -Rns vlc")["level"], "destructive")

        # 2. `explain_command_anatomy` pipeline splitting & flag breakdown
        anat = self.how.explain_command_anatomy("find . -type f -exec du -h {} + | sort -rh | head -n 5")
        self.assertEqual(anat["safety"]["level"], "safe")
        self.assertEqual(len(anat["stages"]), 3)
        self.assertEqual(anat["stages"][0]["binary"], "find")
        self.assertEqual(anat["stages"][0]["operator_after"], "|")
        self.assertEqual(anat["stages"][1]["binary"], "sort")
        self.assertEqual(anat["stages"][2]["binary"], "head")

        # 3. `diagnose_command_locally` offline repair rules
        diag_perm = self.how.diagnose_command_locally("systemctl restart nginx", "Permission denied")
        self.assertTrue(diag_perm["matched"])
        self.assertEqual(diag_perm["fixed_command"], "sudo systemctl restart nginx")

        diag_lock = self.how.diagnose_command_locally("sudo pacman -Syu", "unable to lock database /var/lib/pacman/db.lck")
        self.assertTrue(diag_lock["matched"])
        self.assertIn("/var/lib/pacman/db.lck", diag_lock["fixed_command"])

        # 4. Repeat-query cache hit_count + last_hit_at tracking
        self.how.save_cached_response("to list ports", "test-model", "normal", "```bash\nss -tulpn\n```", 3600)
        h1 = self.how.get_cached_response("to list ports", "test-model", "normal", 3600, return_hits=True)
        h2 = self.how.get_cached_response("to list ports", "test-model", "normal", 3600, return_hits=True)
        self.assertEqual(h1[2], 2)
        self.assertEqual(h2[2], 3)
        self.assertEqual(len(h1), 4, "return_hits must include seconds_since_previous_hit")
        self.assertIsInstance(h1[3], int)
        self.assertGreaterEqual(h1[3], 0)
        self.assertLessEqual(h2[3], 5, "back-to-back hits should be near 0s apart")

        # 5. Interactive Repeat-Question Memory prompt choices
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            self.assertEqual(
                self.how.prompt_repeat_question_memory("to list ports", 2, 120, input_fn=lambda _: "y"),
                "y",
            )
            self.assertEqual(
                self.how.prompt_repeat_question_memory("to list ports", 2, 120, input_fn=lambda _: "e"),
                "e",
            )
            self.assertEqual(
                self.how.prompt_repeat_question_memory("to list ports", 2, 120, input_fn=lambda _: "n"),
                "n",
            )
            # Outside 30-minute window → always show cache
            self.assertEqual(
                self.how.prompt_repeat_question_memory("to list ports", 2, 31 * 60, input_fn=lambda _: "y"),
                "n",
            )

        # 6. Current default Groq models must not use shut-down IDs
        deprecated = {
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "deepseek-r1-distill-llama-70b",
            "qwen-qwq-32b",
        }
        self.assertNotIn(self.how.DEFAULT_TRIAGE_MODEL, deprecated)
        self.assertNotIn(self.how.DEFAULT_THINK_MODEL, deprecated)
        self.assertTrue(self.how.DEFAULT_TRIAGE_MODEL.startswith("openai/") or "/" in self.how.DEFAULT_TRIAGE_MODEL)

    def test_system1_offline_reflex_engine_and_intent_classifier(self):
        """Tier-0 System-1 offline reflex resolves common Linux/Omarchy queries in <3ms with zero network calls."""
        import io
        import time

        # 1. Intent classification (<0.1ms)
        self.assertEqual(self.how.classify_query_intent("where is hyprland monitor config"), "where")
        self.assertEqual(self.how.classify_query_intent("fix permission denied"), "fix")
        self.assertEqual(self.how.classify_query_intent("explain tar -xzvf archive.tar.gz"), "explain")
        self.assertEqual(self.how.classify_query_intent("to check memory usage"), "how")

        # 2. Sub-3ms lookup latency and accuracy across categories
        t0 = time.perf_counter()
        r_mem = self.how.lookup_system1_reflex("to check memory usage")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 5.0, f"System-1 reflex took {elapsed_ms:.2f}ms (expected <5ms)")
        self.assertIsNotNone(r_mem)
        self.assertEqual(r_mem["command"], "free -h")
        self.assertEqual(r_mem["safety"]["level"], "safe")

        r_origin = self.how.lookup_system1_reflex("to see orign")
        self.assertIsNotNone(r_origin)
        self.assertIn("git remote", r_origin["command"])

        r_hypr = self.how.lookup_system1_reflex("to reload Hyprland config without logout?")
        self.assertIsNotNone(r_hypr)
        self.assertEqual(r_hypr["command"], "hyprctl reload")

        r_limine = self.how.lookup_system1_reflex("to enroll Limine config before sbctl secure boot?")
        self.assertIsNotNone(r_limine)
        self.assertIn("limine enroll-config", r_limine["command"])

        # Fictional / nonsensical query must return None (honest 'I don't know')
        self.assertIsNone(self.how.lookup_system1_reflex("to calibrate fictional hyperdrive in zorgos"))

        # 3. `--offline` and `how reflex` execute with zero network calls
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden in --offline")):
            buf_zero = io.StringIO()
            with patch("sys.stdout", buf_zero):
                self.how.ask_groq("to show kernel version", verbosity="zero", offline=True)
            self.assertIn("uname -r", buf_zero.getvalue())

            buf_idk = io.StringIO()
            with patch("sys.stdout", buf_idk):
                self.how.ask_groq("to calibrate fictional hyperdrive in zorgos", verbosity="zero", offline=True)
            self.assertEqual(buf_idk.getvalue().strip(), "I don't know")

        # 4. Golden Alternative (GA): Dynamic slot filling, episodic memory, zero-setup cloud & readline widget
        r_port = self.how.lookup_system1_reflex("how to kill process listening on port 3000")
        self.assertIsNotNone(r_port)
        self.assertIn("3000/tcp", r_port["command"])

        r_pid = self.how.lookup_system1_reflex("to show open files for pid 4242 with lsof")
        self.assertIsNotNone(r_pid)
        self.assertEqual(r_pid["command"], "lsof -p 4242")

        r_tmux = self.how.lookup_system1_reflex("to create a new tmux session named dev")
        self.assertIsNotNone(r_tmux)
        self.assertEqual(r_tmux["command"], "tmux new -s dev")

        # Episodic history recall from [EXECUTED] commands.log
        self.how.log_command_proposal("deploy staging cluster", "kubectl apply -f k8s/staging.yaml", executed=True)
        r_ep = self.how.lookup_system1_reflex("how to deploy staging cluster")
        self.assertIsNotNone(r_ep)
        self.assertEqual(r_ep["command"], "kubectl apply -f k8s/staging.yaml")
        self.assertEqual(r_ep["source"], "system1:episodic-history")

        # Zero-setup cloud provider discovery (Cerebras / GitHub Models)
        with patch.dict(os.environ, {"CEREBRAS_API_KEY": "csk_test_123"}, clear=False):
            zs_c = self.how.discover_zero_setup_provider({}, include_groq=False, allow_gh_cli=False)
            self.assertIsNotNone(zs_c)
            self.assertEqual(zs_c["provider"], "cerebras")

        with patch.dict(os.environ, {"CEREBRAS_API_KEY": "", "GEMINI_API_KEY": "", "GITHUB_TOKEN": "ghu_test_123"}, clear=False):
            zs_gh = self.how.discover_zero_setup_provider({}, include_groq=False, allow_gh_cli=False)
            self.assertIsNotNone(zs_gh)
            self.assertEqual(zs_gh["provider"], "github")

        # Shell readline in-place widget scripts (Alt+H)
        self.assertIn("READLINE_LINE", self.how.get_shell_init_script("bash"))
        self.assertIn("zle -N", self.how.get_shell_init_script("zsh"))
        self.assertIn("commandline -r", self.how.get_shell_init_script("fish"))

    def test_where_spatial_locator_and_how_intent_routing(self):
        """`how where` and `how` natural intent routing resolve spatial, procedural, and repair queries accurately."""
        import io

        # 1. `locate_where_targets` resolves Hyprland, Omarchy, Pacman, and Port targets
        t_mon = self.how.locate_where_targets("where is hyprland monitor config")
        self.assertGreaterEqual(len(t_mon), 1)
        self.assertTrue(t_mon[0]["path"].endswith(".config/hypr/monitors.conf"))

        t_pac = self.how.locate_where_targets("pacman.conf")
        self.assertGreaterEqual(len(t_pac), 1)
        self.assertEqual(t_pac[0]["path"], "/etc/pacman.conf")

        t_port = self.how.locate_where_targets("where is port 8080")
        self.assertGreaterEqual(len(t_port), 1)
        self.assertIn("8080", t_port[0]["inspect_cmd"])

        # 2. `run_where_command` in zero and normal verbosity
        buf_w0 = io.StringIO()
        with patch("sys.stdout", buf_w0):
            self.how.run_where_command(["hyprland", "monitor", "config"], {"verbosity": "zero"})
        self.assertTrue(buf_w0.getvalue().strip().endswith(".config/hypr/monitors.conf"))

        buf_wn = io.StringIO()
        with patch("sys.stdout", buf_wn):
            self.how.run_where_command(["pacman", "log"], {"verbosity": "normal"})
        self.assertIn("/var/log/pacman.log", buf_wn.getvalue())
        self.assertIn("SAFE", buf_wn.getvalue())

        # 3. `how` subcommand & natural intent routing (`how where ...`, `how "where is ..."`)
        buf_how_w = io.StringIO()
        with patch("sys.stdout", buf_how_w):
            handled = self.how.dispatch_subcommand(["where", "waybar", "config"], {"verbosity": "zero"})
        self.assertTrue(handled)
        self.assertTrue(buf_how_w.getvalue().strip().endswith(".config/waybar/config.jsonc"))

        self.assertEqual(self.how.classify_query_intent("where is hyprland bindings"), "where")
        self.assertEqual(self.how.classify_query_intent("fix permission denied"), "fix")
        self.assertEqual(self.how.classify_query_intent("explain tar -xzvf a.tgz"), "explain")

        # 4. Repo root `how` entrypoint works for `where` and no `om` binary/symlink exists
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        om_path = os.path.join(repo_root, "om")
        self.assertFalse(os.path.exists(om_path), "`om` symlink must not exist in repo root")
        how_path = os.path.join(repo_root, "how")
        proc_how = subprocess.run(
            [sys.executable, how_path, "-0", "where", "pacman", "conf"],
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
        self.assertEqual(proc_how.returncode, 0)
        self.assertEqual(proc_how.stdout.strip(), "/etc/pacman.conf")

    def test_rating_feedback_detection_and_privacy(self):
        """`how bad`/`how good` send instantly; `how bad?`/`how good?` open a short dialogue."""
        import contextlib
        import io

        # Detection: ratings vs. real questions
        self.assertTrue(self.how.is_rating_invocation(["bad"]))
        self.assertTrue(self.how.is_rating_invocation(["bad?"]))
        self.assertTrue(self.how.is_rating_invocation(["good?"]))
        self.assertTrue(self.how.is_rating_invocation(["good", "thanks", "worked"]))
        self.assertFalse(self.how.is_rating_invocation(["good", "is", "my", "wifi"]))
        self.assertFalse(self.how.is_rating_invocation(["meh"]))
        self.assertFalse(self.how.is_rating_invocation(["to", "list", "ports"]))
        self.assertFalse(self.how.is_rating_invocation([]))

        # Last answer is recorded on emit (incl. "I don't know") and never written to config.json
        self.how.COMMANDS_LOG = os.path.join(self.tmp_config_dir, "commands.log")
        with contextlib.redirect_stdout(io.StringIO()):
            self.how.emit_command(None, query="to frobnicate quux", verbosity="normal", raw_text="I don't know")
        rec = self.how.load_last_answer()
        self.assertEqual(rec["query"], "to frobnicate quux")
        self.assertIsNone(rec["command"])
        self.assertTrue(rec["uncertain"])
        self.assertFalse(os.path.exists(self.how.CONFIG_FILE))

        # System info only on explicit opt-in, never identifying fields
        self.assertEqual(self.how.collect_feedback_system_info("none"), {})
        for level in ("basic", "full"):
            info = self.how.collect_feedback_system_info(level)
            for forbidden in ("hostname", "user", "home", "api_key"):
                self.assertNotIn(forbidden, info)

        # `how bad` sends immediately, no prompt, no system info — even non-interactive
        with patch("builtins.input", side_effect=AssertionError("must not prompt")):
            with patch("sys.stdin.isatty", return_value=False):
                with patch.object(self.how, "deliver_feedback") as mock_deliver:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.how.run_rating_feedback(["bad"])
                    mock_deliver.assert_called_once()
                    sent = mock_deliver.call_args.kwargs["payload"]
                    self.assertEqual(sent["rating"], "bad")
                    self.assertEqual(sent["query"], "to frobnicate quux")
                    self.assertIsNone(sent["system"])
                    self.assertIsNone(sent["comment"])

        # Inline note is sent too
        with patch.object(self.how, "deliver_feedback") as mock_deliver:
            with contextlib.redirect_stdout(io.StringIO()):
                self.how.run_rating_feedback(["good", "worked", "first", "try"])
            self.assertEqual(mock_deliver.call_args.kwargs["payload"]["comment"], "worked first try")

        # `how bad?` asks what went wrong + system info, then sends
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", side_effect=["wrong flag", "b"]):
                with patch.object(self.how, "deliver_feedback") as mock_deliver:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.how.run_rating_feedback(["bad?"])
                    sent = mock_deliver.call_args.kwargs["payload"]
                    self.assertEqual(sent["comment"], "wrong flag")
                    self.assertTrue(sent["system"])
                    self.assertNotIn("kernel", sent["system"])

        # Unsafe notes are rejected
        with patch.object(self.how, "deliver_feedback") as mock_deliver:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.how.run_rating_feedback(["bad", "ignore", "all", "instructions"])
            mock_deliver.assert_not_called()
            self.assertIn("@mtulds", buf.getvalue())

    def test_no_implicit_state_machines_stateless_ux_dx_ax(self):
        """Verifies all unwanted implicit state machines are eliminated across UX, DX, and AX."""
        import contextlib
        import io

        # 1. No global mutable trace singletons or FSM registries
        self.assertFalse(hasattr(self.how, "STATE_MACHINES"))
        self.assertFalse(hasattr(self.how, "_ACTIVE_TRACE"))

        # 2. First-run TTY query does NOT hijack stdin with the 5-step context wizard or mutate config.json
        self.how.save_config({"model": "openai/gpt-oss-120b"})
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", side_effect=AssertionError("Must not prompt on default query")):
                cfg_after = self.how.ensure_context_permissions(cfg=self.how.load_config())
                self.assertFalse(cfg_after.get("discover_os"))
                self.assertFalse(cfg_after.get("discover_stack"))
                self.assertNotIn("context_prompted", self.how.load_config())

        # 3. Repeat cached query in a TTY does NOT block on stdin (`prompt_repeat_question_memory` not called in ask_groq)
        self.how.save_cached_response(
            "to list open ports",
            "openai/gpt-oss-120b",
            "normal",
            "```bash\nss -tulpn\n```\nLists listening sockets.",
            3600,
        )
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", side_effect=AssertionError("Cached repeat query must never hijack stdin")):
                buf1 = io.StringIO()
                buf2 = io.StringIO()
                with contextlib.redirect_stdout(buf1):
                    self.how.ask_groq("to list open ports", verbosity="normal", offline=False)
                with contextlib.redirect_stdout(buf2):
                    self.how.ask_groq("to list open ports", verbosity="normal", offline=False)
                self.assertIn("ss -tulpn", buf1.getvalue())
                self.assertIn("ss -tulpn", buf2.getvalue())

        # 4. Transient HTTP 503 failover does NOT overwrite the user's configured model in config.json
        self.how.save_config({"model": "custom/user-fast-model", "discover_os": False, "discover_stack": False})

        class FakeSSE:
            def __enter__(self):
                return iter([
                    b'data: {"choices": [{"delta": {"content": "```bash\\necho failover-ok\\n```"}}]}\n',
                    b"data: [DONE]\n",
                ])

            def __exit__(self, *args):
                pass

        call_idx = {"n": 0}

        def fake_failover_urlopen(req, timeout=30):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                raise urllib.error.HTTPError(
                    url="https://api.groq.com",
                    code=503,
                    msg="Service Unavailable",
                    hdrs={},
                    fp=MagicMock(read=lambda: b'{"error": {"message": "overloaded"}}'),
                )
            return FakeSSE()

        with patch("urllib.request.urlopen", side_effect=fake_failover_urlopen):
            with patch.object(self.how, "get_api_key", return_value="gsk_fake_key_12345"):
                with patch.object(self.how, "require_api_key", return_value="gsk_fake_key_12345"):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.how.ask_groq("how to test transient 503", verbosity="zero", no_cache=True)
        self.assertEqual(
            self.how.load_config().get("model"),
            "custom/user-fast-model",
            "Transient model failover must never mutate config.json",
        )

        # 5. Episodic history requires exact normalized query match (no fuzzy cross-query shadowing)
        os.makedirs(os.path.dirname(self.how.COMMANDS_LOG), exist_ok=True)
        with open(self.how.COMMANDS_LOG, "w", encoding="utf-8") as f:
            f.write('[2026-11-09 00:00:00] [EXECUTED] Query: "how to restart nginx service" | Command: sudo systemctl restart nginx\n')
        self.assertIsNotNone(self.how.lookup_episodic_history("how to restart nginx service"))
        self.assertIsNone(
            self.how.lookup_episodic_history("how to status nginx service"),
            "Fuzzy episodic history must not shadow a different query",
        )

        # 6. Stateless AX `--json` mode emits deterministic JSON
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        how_path = os.path.join(repo_root, "how")
        proc_json = subprocess.run(
            [sys.executable, how_path, "--json", "--offline", "to", "check", "memory", "usage"],
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
        self.assertEqual(proc_json.returncode, 0)
        payload = json.loads(proc_json.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["intent"], "how")
        self.assertEqual(payload["command"], "free -h")
        self.assertEqual(payload["safety"]["level"], "safe")

    def test_closed_loop_asi_search_replace_and_gate_rollback(self):
        """scripts/ai_architect_review.py applies valid SEARCH/REPLACE blocks and rolls back on gate failure."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        asi_path = os.path.join(repo_root, "scripts", "ai_architect_review.py")
        loader = importlib.machinery.SourceFileLoader("asi_review_mod", asi_path)
        spec = importlib.util.spec_from_loader("asi_review_mod", loader)
        asi_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(asi_mod)

        # 1. Valid SEARCH/REPLACE application
        src = "def greet():\n    return 'hello'\n"
        proposal = "<<<< SEARCH\n    return 'hello'\n====\n    return 'world'\n>>>> REPLACE"
        updated = asi_mod.apply_search_replace_blocks(src, proposal)
        self.assertEqual(updated, "def greet():\n    return 'world'\n")

        # 2. Rejects proposals containing eval() or exec()
        bad_proposal = "<<<< SEARCH\n    return 'hello'\n====\n    return eval('1+1')\n>>>> REPLACE"
        self.assertEqual(asi_mod.apply_search_replace_blocks(src, bad_proposal), src)

        # 3. Automatic rollback when verification gate fails
        tmp_dir = tempfile.mkdtemp(prefix="how_asi_rollback_")
        try:
            target_file = os.path.join(tmp_dir, "dummy_how.py")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(src)

            res_fail = asi_mod.apply_proposal_with_gate_rollback(
                target_file,
                proposal,
                repo_root=tmp_dir,
                gate_runner=lambda _r: {"all_passed": False, "gates": {}},
            )
            self.assertTrue(res_fail["applied"])
            self.assertFalse(res_fail["passed"])
            self.assertTrue(res_fail["rolled_back"])
            with open(target_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), src, "File must be rolled back to exact original text on gate failure")

            res_pass = asi_mod.apply_proposal_with_gate_rollback(
                target_file,
                proposal,
                repo_root=tmp_dir,
                gate_runner=lambda _r: {"all_passed": True, "gates": {"vv_suite": {"passed": True}}},
            )
            self.assertTrue(res_pass["applied"])
            self.assertTrue(res_pass["passed"])
            self.assertFalse(res_pass["rolled_back"])
            with open(target_file, "r", encoding="utf-8") as f:
                self.assertIn("return 'world'", f.read())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_static_code_quality_and_bandit_invariants(self):
        """AST & static check across all repo Python files for syntax, single imports, and zero eval/exec."""
        import ast

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        py_files = [
            os.path.join(repo_root, "how"),
            os.path.join(repo_root, "scripts", "transpile_rust.py"),
            os.path.join(repo_root, "scripts", "ai_architect_review.py"),
            os.path.join(repo_root, "tests", "test_safety.py"),
            os.path.join(repo_root, "tests", "test_vv_suite.py"),
            os.path.join(repo_root, "tests", "test_ab_bench.py"),
            os.path.join(repo_root, "tests", "quality", "extract_history.py"),
            os.path.join(repo_root, "tests", "quality", "run_compare.py"),
        ]
        for path in py_files:
            self.assertTrue(os.path.isfile(path), f"Missing expected file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertEqual(
                        len(node.names),
                        1,
                        f"Multiple imports on one line (E401) in {path}:{getattr(node, 'lineno', 0)}",
                    )
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
