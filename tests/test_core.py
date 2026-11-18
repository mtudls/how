"""In-process tests: answer parsing, API errors, logging, privacy and install-method detection."""

import io
import json
import os
import socket
import stat
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from helpers import FAKE_KEY, environ, load_how, reply

how = load_how()


class TestParseAnswer(unittest.TestCase):
    def test_fenced_command_and_note(self):
        a = how.parse_answer("```bash\ndu -ah . | sort -rh | head -20\n```\nLists the largest files.")
        self.assertEqual(a, how.Answer("du -ah . | sort -rh | head -20", "Lists the largest files."))

    def test_multiple_lines_join_with_and_comments_and_prompts_dropped(self):
        a = how.parse_answer("```sh\n# update\n$ sudo pacman -Syu\nyay -Syu\n```\nUpdates everything.")
        self.assertEqual(a.command, "sudo pacman -Syu && yay -Syu")

    def test_backslash_continuation_joins_with_space(self):
        a = how.parse_answer("```\nfind . \\\n  -name x\n```\nFinds x.")
        self.assertEqual(a.command, "find . -name x")

    def test_note_before_block(self):
        self.assertEqual(how.parse_answer("Do this:\n```bash\nls\n```").note, "Do this:")

    def test_non_task_answer_has_no_command(self):
        a = how.parse_answer("Hyprland is a Wayland compositor.")
        self.assertEqual((a.command, a.note, a.unknown), (None, "Hyprland is a Wayland compositor.", False))

    def test_dont_know(self):
        for text in ("I don't know", "I don't know.", "i dont know", ""):
            with self.subTest(text=text):
                self.assertTrue(how.parse_answer(text).unknown)

    def test_empty_block(self):
        self.assertIsNone(how.parse_answer("```bash\n# nothing\n```\nhm").command)


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {"HOME": self.tmp.name, "HOW_CONFIG_DIR": f"{self.tmp.name}/c", "HOW_STATE_DIR": f"{self.tmp.name}/s",
               "GROQ_API_KEY": FAKE_KEY, "SHELL": "/bin/zsh", "PATH": os.environ.get("PATH", "")}
        patcher = environ(env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.log = Path(self.tmp.name) / "s" / "how.log"

    def run_main(self, *argv):
        out, errs = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(errs):
            try:
                code = how.main(list(argv))
            except how.HowError as e:
                code = e.exit_code
        return code, out.getvalue(), errs.getvalue()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestChatErrors(ApiTestCase):
    def raises(self, exc):
        with mock.patch.object(how.urllib.request, "urlopen", side_effect=exc):
            with self.assertRaises(how.HowError) as ctx:
                how.chat([{"role": "user", "content": "x"}])
        return ctx.exception

    def http(self, code, headers=None):
        return urllib.error.HTTPError(how.API_URL, code, "x", headers or {}, None)

    def test_error_codes(self):
        cases = [
            (self.http(401), "bad_key"), (self.http(403), "bad_key"), (self.http(429), "rate_limited"),
            (self.http(500), "api_error"), (urllib.error.URLError("Name or service not known"), "offline"),
            (urllib.error.URLError(socket.timeout("timed out")), "timeout"), (TimeoutError(), "timeout"),
        ]
        for exc, code in cases:
            with self.subTest(code=code):
                e = self.raises(exc)
                self.assertEqual((e.code, e.exit_code), (code, 1))
                self.assertTrue(e.hint)

    def test_rate_limit_hint_uses_retry_after(self):
        self.assertIn("7s", self.raises(self.http(429, {"retry-after": "7"})).hint)

    def test_no_key(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.assertEqual(self.raises(AssertionError("no network expected")).code, "no_key")

    def test_garbage_response(self):
        with mock.patch.object(how.urllib.request, "urlopen", return_value=FakeResponse(b"<html>")):
            with self.assertRaises(how.HowError) as ctx:
                how.chat([])
        self.assertEqual(ctx.exception.code, "bad_response")


class TestPrivacy(ApiTestCase):
    """Only the question + machine string leave the machine, to exactly one host."""

    def test_request_contains_only_question_and_machine(self):
        sent = []

        def fake_urlopen(request, timeout):
            sent.append(request)
            return FakeResponse(json.dumps(reply("```bash\nls\n```\nLists files.")).encode())

        def no_sockets(*a, **k):
            raise AssertionError("unexpected network connection")

        with mock.patch.object(how.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(socket, "create_connection", no_sockets), \
                mock.patch.object(socket.socket, "connect", no_sockets), \
                mock.patch.object(how, "machine", return_value="Arch Linux (Omarchy), zsh"):
            code, out, _ = self.run_main("-n", "to list files")
        self.assertEqual((code, out), (0, "ls\n"))
        self.assertEqual(len(sent), 1)
        request = sent[0]
        self.assertEqual(request.full_url, how.API_URL)
        self.assertEqual(how.urllib.parse.urlsplit(request.full_url).hostname, "api.groq.com")
        body = json.loads(request.data)
        self.assertEqual(set(body) - {"reasoning_effort"}, {"model", "messages", "temperature"})
        self.assertEqual(body["messages"], [
            {"role": "system", "content": how.PROMPT.format(machine="Arch Linux (Omarchy), zsh")},
            {"role": "user", "content": "how to list files"},
        ])
        self.assertEqual(request.get_header("Authorization"), f"Bearer {FAKE_KEY}")

    def test_machine_string_is_os_and_shell_only(self):
        self.assertTrue(how.machine().endswith(", zsh"))
        self.assertEqual(how.machine().count(","), 1 + how.machine().split(",")[0].count(","))

    def test_privacy_command_names_host_and_files(self):
        code, out, _ = self.run_main("privacy")
        self.assertEqual(code, 0)
        for text in ("api.groq.com", "config.json", "how.log", "last.json", how.machine()):
            self.assertIn(text, out)
        self.assertNotIn(FAKE_KEY, out)


class TestLogging(ApiTestCase):
    def test_fields_permissions_and_no_key(self):
        how.log_event("answer", question="to x", command="ls", safety="safe", latency_ms=5, model="m")
        entry = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(set(entry), {"ts", "event", "question", "command", "safety", "action", "exit_code",
                                      "latency_ms", "model", "version"})
        self.assertTrue(entry["ts"].endswith("+00:00"))
        self.assertEqual(entry["version"], how.__version__)
        self.assertEqual(stat.S_IMODE(self.log.stat().st_mode), 0o600)

    def test_full_flow_never_logs_the_key(self):
        with mock.patch.object(how, "chat", return_value="```bash\nls\n```\nLists."):
            self.run_main("-n", "to list")
        with mock.patch.object(how, "chat", side_effect=how.HowError("bad_key", "rejected")):
            self.run_main("to list")
        with mock.patch.object(how.sys, "stdin", io.StringIO(FAKE_KEY[::-1] + "\n")):
            self.run_main("key")
        text = self.log.read_text()
        self.assertEqual([json.loads(x)["event"] for x in text.splitlines()], ["answer", "error", "key"])
        self.assertNotIn(FAKE_KEY, text)
        self.assertNotIn(FAKE_KEY[::-1], text)
        self.assertNotIn(FAKE_KEY[-4:], text)

    def test_rotation_keeps_one_old_file(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_text("x" * how.LOG_MAX_BYTES)
        how.log_event("answer")
        self.assertEqual(len(self.log.read_text().splitlines()), 1)
        self.assertEqual(self.log.with_name("how.log.1").stat().st_size, how.LOG_MAX_BYTES)

    def test_unwritable_state_dir_never_breaks_a_query(self):
        blocker = Path(self.tmp.name) / "file"
        blocker.write_text("")
        with mock.patch.dict(os.environ, {"HOW_STATE_DIR": str(blocker / "state")}), \
                mock.patch.object(how, "chat", return_value="```bash\nls\n```\nLists."):
            code, out, err = self.run_main("-n", "to list")
        self.assertEqual((code, out, err.count("Traceback")), (0, "ls\n", 0))


class TestKeyAndConfig(ApiTestCase):
    def test_key_saved_0600_and_only_last_four_shown(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": ""}), \
                mock.patch.object(how.sys, "stdin", io.StringIO(FAKE_KEY + "\n")):
            code, out, _ = self.run_main("key")
        self.assertEqual(code, 0)
        path = Path(self.tmp.name) / "c" / "config.json"
        self.assertEqual(json.loads(path.read_text())["api_key"], FAKE_KEY)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn(FAKE_KEY, out)
        self.assertIn(FAKE_KEY[-4:], out)

    def test_empty_key_is_rejected(self):
        with mock.patch.object(how.sys, "stdin", io.StringIO("\n")):
            self.assertEqual(self.run_main("key")[0], 1)

    def test_env_key_wins_and_model_override(self):
        self.assertEqual(how.api_key(), (FAKE_KEY, "GROQ_API_KEY"))
        with mock.patch.dict(os.environ, {"HOW_MODEL": "llama-x"}):
            self.assertEqual(how.model(), "llama-x")

    def test_corrupt_config_is_ignored(self):
        path = Path(self.tmp.name) / "c" / "config.json"
        path.parent.mkdir()
        path.write_text("{not json")
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.assertEqual(how.api_key(), ("", ""))


class TestRouting(unittest.TestCase):
    def test_subcommands_vs_questions(self):
        cases = {
            ("run",): "run", ("run", "a", "server"): "ask", ("good",): "good", ("bad", "wrong", "flag"): "bad",
            ("good", "is", "my", "wifi"): "ask", ("log",): "log", ("log", "50"): "log", ("log", "--path"): "log",
            ("log", "out", "of", "ssh"): "ask", ("update",): "update", ("update", "my", "mirrors"): "ask",
            ("explain",): "explain", ("explain", "tar", "-xzf", "a"): "explain", ("explain", "to", "me"): "ask",
            ("key",): "key", ("to", "find", "files"): "ask",
        }
        for words, name in cases.items():
            with self.subTest(words=words):
                self.assertEqual(how.route(list(words))[0], name)

    def test_flags(self):
        opts, words = how.parse_flags(["-y", "--json", "to", "-x"])
        self.assertTrue(opts["yes"] and opts["json"] and not opts["no_run"])
        self.assertEqual(words, ["to", "-x"])
        with self.assertRaises(how.HowError):
            how.parse_flags(["--nope"])


class TestInstallMethod(unittest.TestCase):
    def test_paths(self):
        self.assertEqual(how.install_method("/usr/bin/how")[0], "package")
        self.assertEqual(how.install_method("/home/u/.config/omarchy/plugins/how/how")[0], "plugin")
        self.assertEqual(how.install_method("/home/u/.local/bin/how")[0], "script")

    def test_symlink_into_plugin_checkout_is_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp, "omarchy", "plugins", "how")
            checkout.mkdir(parents=True)
            (checkout / "how").write_text("")
            link = Path(tmp, "bin", "how")
            link.parent.mkdir()
            link.symlink_to(checkout / "how")
            self.assertEqual(how.install_method(str(link)), ("plugin", str((checkout / "how").resolve())))


class TestVersionParity(unittest.TestCase):
    """how, PKGBUILD and manifest.json must carry the same version (set together at release)."""

    def test_versions_match(self):
        root = Path(how.__file__).resolve().parent
        pkgver = next(line.split("=", 1)[1].strip() for line in (root / "PKGBUILD").read_text().splitlines()
                      if line.startswith("pkgver="))
        manifest = json.loads((root / "manifest.json").read_text())["version"]
        self.assertEqual((pkgver, manifest), (how.__version__, how.__version__))


if __name__ == "__main__":
    unittest.main()
