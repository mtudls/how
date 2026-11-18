"""Drives the real script as a process (no terminal) against a local fake OpenAI-compatible API."""

import json
import socket
import unittest

from helpers import FAKE_KEY, HowTestCase

JSON_KEYS = {"schema_version", "ok", "question", "command", "note", "safety", "error", "version"}


class TestPipedOutput(HowTestCase):
    def test_stdout_is_exactly_the_command(self):
        api = self.with_api()
        api.answer("```bash\ndu -ah . | sort -rh | head -20\n```\nLists the 20 largest files.")
        p = self.how("to", "find", "largest", "files", "here")
        self.assertEqual((p.returncode, p.stdout), (0, "du -ah . | sort -rh | head -20\n"))
        self.assertIn("safe", p.stderr)
        self.assertIn("Lists the 20 largest files.", p.stderr)
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(api.requests[0]["body"]["messages"][1]["content"], "how to find largest files here")

    def test_piped_never_runs_or_prompts_or_copies(self):
        api = self.with_api()
        api.answer(f"```bash\ntouch {self.tmp}/ran\n```\nCreates a file.")
        p = self.how("-y", "to", "make", "a", "file")
        self.assertEqual(p.returncode, 0)
        self.assertFalse((self.tmp / "ran").exists())
        self.assertFalse(self.clipboard.exists())
        self.assertIn("changes", p.stderr)

    def test_no_run_flag_copies(self):
        self.with_api().answer("```bash\nls -la\n```\nLists.")
        p = self.how("-n", "to", "list")
        self.assertEqual(p.stdout, "ls -la\n")
        self.assertEqual(self.clipboard.read_text(), "ls -la")

    def test_non_task_answer_prints_sentence(self):
        self.with_api().answer("Hyprland is a tiling Wayland compositor.")
        p = self.how("is", "hyprland")
        self.assertEqual((p.returncode, p.stdout), (0, "Hyprland is a tiling Wayland compositor.\n"))

    def test_dont_know_exits_2(self):
        self.with_api().answer("I don't know")
        p = self.how("to", "frobnicate", "the", "quux")
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("don't know", p.stderr)


class TestErrors(HowTestCase):
    def assertCleanError(self, p, words):
        self.assertEqual(p.returncode, 1)
        self.assertEqual(p.stdout, "")
        self.assertIn(words, p.stderr)
        self.assertNotIn("Traceback", p.stderr)
        self.assertNotIn(FAKE_KEY, p.stderr)

    def test_no_key(self):
        p = self.how("to", "list", "files")
        self.assertCleanError(p, "how key")

    def test_rejected_key(self):
        self.with_api().answer("", status=401)
        self.assertCleanError(self.how("to", "list"), "rejected")

    def test_rate_limited(self):
        self.with_api().answer("", status=429, headers={"Retry-After": "12"})
        self.assertCleanError(self.how("to", "list"), "wait 12s")

    def test_server_error(self):
        self.with_api().answer("", status=503)
        self.assertCleanError(self.how("to", "list"), "HTTP 503")

    def test_offline(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()  # nothing listens here now
        self.env.update(GROQ_API_KEY=FAKE_KEY, HOW_API_URL=f"http://127.0.0.1:{port}/v1/chat/completions")
        self.assertCleanError(self.how("to", "list"), "cannot reach 127.0.0.1")

    def test_errors_are_logged(self):
        self.with_api().answer("", status=429)
        self.how("to", "list")
        entry = self.log_entries()[-1]
        self.assertEqual((entry["event"], entry["action"], entry["question"]), ("error", "rate_limited", "to list"))


class TestJson(HowTestCase):
    def test_success_shape(self):
        self.with_api().answer("```bash\nrm -rf build\n```\nDeletes the build dir.")
        p = self.how("--json", "to", "clean", "build")
        data = json.loads(p.stdout)
        self.assertEqual(set(data), JSON_KEYS)
        self.assertEqual(data["schema_version"], "1")
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "rm -rf build")
        self.assertEqual(data["note"], "Deletes the build dir.")
        self.assertEqual(data["safety"]["level"], "dangerous")
        self.assertIsNone(data["error"])
        self.assertEqual(p.returncode, 0)
        self.assertFalse(self.clipboard.exists())

    def test_error_shape(self):
        p = self.how("--json", "to", "list")
        data = json.loads(p.stdout)
        self.assertEqual(set(data), JSON_KEYS)
        self.assertFalse(data["ok"])
        self.assertIsNone(data["command"])
        self.assertEqual(data["error"]["code"], "no_key")
        self.assertTrue(data["error"]["message"] and data["error"]["hint"])
        self.assertEqual(p.returncode, 1)

    def test_dont_know_shape(self):
        self.with_api().answer("I don't know.")
        p = self.how("--json", "to", "x")
        data = json.loads(p.stdout)
        self.assertEqual((data["ok"], data["error"]["code"], p.returncode), (False, "dont_know", 2))


class TestSubcommands(HowTestCase):
    def test_version_and_help(self):
        for args in (["--version"], ["-V"], ["version"]):
            self.assertRegex(self.how(*args).stdout, r"^how \d+\.\d+\.\d+\n$")
        for args in (["--help"], ["-h"], ["help"], []):
            p = self.how(*args)
            self.assertEqual(p.returncode, 0)
            self.assertIn("how explain", p.stdout)

    def test_unknown_flag_is_usage_error(self):
        self.assertEqual(self.how("--frob", "x").returncode, 2)

    def test_run_without_terminal_prints_last_command(self):
        self.with_api().answer(f"```bash\ntouch {self.tmp}/ran\n```\nMakes a file.")
        self.how("to", "make", "a", "file")
        p = self.how("run")
        self.assertEqual(p.stdout, f"touch {self.tmp}/ran\n")
        self.assertFalse((self.tmp / "ran").exists())

    def test_run_and_rate_with_nothing_asked(self):
        for args in (["run"], ["good"], ["bad", "wrong"]):
            p = self.how(*args)
            self.assertEqual((p.returncode, p.stdout), (1, ""))
            self.assertIn("nothing asked yet", p.stderr)

    def test_explain_without_key_shows_local_badge(self):
        p = self.how("explain", "rm -rf /tmp/x")
        self.assertEqual(p.returncode, 1)
        self.assertIn("dangerous", p.stdout)
        self.assertIn("rm -rf /tmp/x", p.stdout)
        self.assertIn("needs an API key", p.stderr)

    def test_explain_with_key(self):
        api = self.with_api()
        api.answer("tar — archive tool\nEffect: extracts files.")
        p = self.how("explain", "tar -xzf a.tgz")
        self.assertEqual(p.returncode, 0)
        self.assertIn("Effect: extracts files.", p.stdout)
        self.assertEqual(api.requests[0]["body"]["messages"][1]["content"], "tar -xzf a.tgz")

    def test_rating_shows_payload_and_sends_nothing(self):
        api = self.with_api()
        api.answer("```bash\nls\n```\nLists.")
        self.how("to", "list")
        p = self.how("bad", "wrong", "flag")
        self.assertEqual(p.returncode, 0)
        self.assertIn("Note: wrong flag", p.stdout)
        self.assertIn("github.com/mtudls/how/issues/new?", p.stdout)
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(self.log_entries()[-1]["action"], "bad")

    def test_log(self):
        self.with_api().answer("```bash\nls\n```\nLists.")
        self.how("to", "list")
        self.assertIn("ls", self.how("log").stdout)
        self.assertEqual(self.how("log", "--path").stdout.strip(), str(self.state_dir / "how.log"))
        self.assertEqual(self.how("log", "0").returncode, 0)

    def test_key_from_stdin(self):
        p = self.how("key", stdin=FAKE_KEY + "\n")
        self.assertEqual(p.returncode, 0)
        self.assertNotIn(FAKE_KEY, p.stdout)
        self.assertEqual(json.loads((self.config_dir / "config.json").read_text())["api_key"], FAKE_KEY)

    def test_unwritable_config_dir(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("")
        self.env["HOW_CONFIG_DIR"] = str(blocker / "how")
        p = self.how("key", stdin=FAKE_KEY + "\n")
        self.assertEqual(p.returncode, 1)
        self.assertIn("cannot write", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_info_commands_run_nothing_and_succeed(self):
        for args in (["privacy"], ["update"], ["uninstall"]):
            with self.subTest(args=args):
                p = self.how(*args)
                self.assertEqual(p.returncode, 0)
                self.assertNotIn("Traceback", p.stderr)
        self.assertIn("script", self.how("update").stdout)
        self.assertIn("rm -f", self.how("uninstall").stdout)

    def test_doctor_reports_and_uses_only_the_api_host(self):
        api = self.with_api()
        p = self.how("doctor")
        self.assertIn("API key", p.stdout)
        self.assertIn("127.0.0.1", p.stdout)
        self.assertNotIn(FAKE_KEY, p.stdout)
        self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(api.requests, [])  # doctor GETs /models; the fake only records POSTs


if __name__ == "__main__":
    unittest.main()
