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


if __name__ == "__main__":
    unittest.main()
