"""End-to-end in a real pseudo-terminal: asking only shows and copies; `how run` asks by badge."""

import os
import re
import select
import subprocess
import sys
import time
import unittest

from helpers import HOW, HowTestCase

# Makes the pty the child's controlling terminal (so Ctrl-C sends SIGINT), then runs `how`.
LAUNCHER = "import os,sys; os.close(os.open(os.ttyname(0), os.O_RDWR)); os.execv(sys.executable, sys.argv[1:])"


@unittest.skipUnless(sys.platform.startswith(("linux", "darwin")), "needs a pty")
class TestInteractive(HowTestCase):
    def spawn(self, *args, answer=None, then=(), stream=None):
        api = self.with_api()
        if stream:
            api.stream(*stream)
        for content in ([answer] if answer else []) + list(then):
            api.answer(content)
        self.api = api
        master, slave = os.openpty()
        self.proc = subprocess.Popen([sys.executable, "-c", LAUNCHER, sys.executable, str(HOW), *args],
                                     stdin=slave, stdout=slave, stderr=slave, env={**self.env, "TERM": "xterm"},
                                     start_new_session=True)
        os.close(slave)
        self.master, self.output = master, ""
        self.addCleanup(self.cleanup, self.proc, master)

    def ask_then_run(self, *args, answer, then=()):
        """Asks in the terminal (which must return to the shell without a prompt), then starts `how run`."""
        self.spawn(*args, answer=answer)
        self.assertEqual(self.finish(), 0)
        self.assertNotRegex(self.output, r"\] run|type run")
        self.asked = self.output
        self.spawn("run", then=then)

    @staticmethod
    def cleanup(proc, master):
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        os.close(master)

    def expect(self, pattern, timeout=10):
        deadline = time.time() + timeout
        while not re.search(pattern, self.output):
            if time.time() > deadline:
                self.fail(f"timed out waiting for {pattern!r}; got:\n{self.output}")
            if select.select([self.master], [], [], 0.05)[0]:
                try:
                    self.output += os.read(self.master, 4096).decode("utf-8", "replace")
                except OSError:  # child closed the terminal
                    break

    def plain_lines(self):
        text = re.sub(r"\x1b\[[0-9;]*m", "", self.output.replace("\r", ""))
        return [line.strip() for line in text.splitlines() if line.strip()]

    def send(self, keys):
        os.write(self.master, keys.encode())

    def finish(self):
        code = self.proc.wait(timeout=10)
        while select.select([self.master], [], [], 0.05)[0]:  # drain what the child printed before exiting
            try:
                chunk = os.read(self.master, 4096)
            except OSError:
                break
            if not chunk:
                break
            self.output += chunk.decode("utf-8", "replace")
        self.assertNotIn("Traceback", self.output)
        return code

    def test_asking_shows_two_quiet_lines_copies_and_returns_without_a_prompt(self):
        target = self.tmp / "made"
        self.spawn("to", "make", "a", "file", answer=f"```bash\ntouch {target}\n```\nCreates a file.")
        self.assertEqual(self.finish(), 0)
        lines = self.plain_lines()
        self.assertEqual(lines[0], f"touch {target}")
        self.assertRegex(lines[1], r"^unsafe \(.+\) · Creates a file\.$")
        self.assertEqual(len(lines), 2)
        self.assertNotRegex(self.output, r"\] run|type run|thinking|how ❯|Suggested")
        self.assertFalse(target.exists())
        self.assertEqual(self.clipboard.read_text(), f"touch {target}")
        self.assertEqual(sorted(e["event"] for e in self.log_entries()), ["answer", "copy"])

    def test_answer_is_streamed_command_first_then_badge_and_note(self):
        self.spawn("to", "list", "files", stream=["```bash\nls", " -la\n```\n", "Lists all files, ", "including hidden ones."])
        self.assertEqual(self.finish(), 0)
        self.assertTrue(self.api.requests[0]["body"]["stream"])
        lines = self.plain_lines()
        self.assertEqual(lines, ["ls -la", "safe · Lists all files, including hidden ones."])
        self.assertEqual(self.clipboard.read_text(), "ls -la")

    def test_a_clipboard_tool_that_stays_in_the_background_does_not_slow_the_answer(self):
        # wl-copy keeps a process alive to serve the selection; how must not wait for it.
        (self.bin / "wl-copy").write_text(f"#!/bin/sh\ncat > '{self.clipboard}'\nsleep 5 &\n")
        started = time.time()
        self.spawn("to", "list", answer="```bash\nls\n```\nLists files.")
        self.assertEqual(self.finish(), 0)
        self.assertLess(time.time() - started, 3)
        self.assertEqual(self.clipboard.read_text(), "ls")
        self.assertNotIn("not copied", self.output)

    def test_no_clipboard_tool_is_said_once(self):
        (self.bin / "wl-copy").unlink()
        self.spawn("to", "list", answer="```bash\nls\n```\nLists files.")
        self.assertEqual(self.finish(), 0)
        self.assertIn("not copied", self.output)

    def test_streamed_dont_know_is_not_shown_as_an_answer(self):
        self.spawn("to", "frobnicate", stream=["I don't", " know"])
        self.assertEqual(self.finish(), 2)
        self.assertNotIn("Suggested command", self.output)
        self.assertEqual(self.output.count("I don't know"), 1)  # only the error line

    def test_control_characters_from_the_model_are_dropped(self):
        self.spawn("to", "list", stream=["```bash\nls\n```\nLists \x1b[31mfiles\x07."])
        self.assertEqual(self.finish(), 0)
        self.assertIn("Lists [31mfiles.", self.output)

    def test_run_safe_runs_on_enter(self):
        self.ask_then_run("to", "say", "hi", answer="```bash\nprintf 'ran-%s\\n' ok\n```\nPrints a marker.")
        self.assertIn("safe", self.asked)
        self.expect(r"\[Enter\] run")
        self.send("\r")
        self.expect("ran-ok")
        self.assertEqual(self.finish(), 0)
        self.assertEqual(self.clipboard.read_text(), "printf 'ran-%s\\n' ok")
        self.assertEqual(self.log_entries()[-1]["event"], "run")
        self.assertEqual(self.log_entries()[-1]["exit_code"], 0)

    def test_run_unsafe_ignores_enter_and_runs_on_y(self):
        target = self.tmp / "made"
        self.ask_then_run("to", "make", "a", "file", answer=f"```bash\ntouch {target}\n```\nCreates a file.")
        self.expect(r"\[y\] run")
        self.send("\r")
        self.expect("press y")
        self.assertFalse(target.exists())
        self.send("y")
        self.assertEqual(self.finish(), 0)
        self.assertTrue(target.exists())

    def test_run_dangerous_needs_the_word_run(self):
        victim = self.tmp / "victim"
        victim.mkdir()
        answer = f"```bash\nrm -rf {victim}\n```\nDeletes it."
        self.ask_then_run("to", "delete", "it", answer=answer)
        self.assertIn("dangerous", self.asked)
        self.expect("type run")
        self.send("y\r")
        self.assertEqual(self.finish(), 0)
        self.assertTrue(victim.exists())

        self.spawn("run")
        self.expect("type run")
        self.send("run\r")
        self.assertEqual(self.finish(), 0)
        self.assertFalse(victim.exists())

    def test_yes_flag_auto_runs_only_safe(self):
        self.spawn("-y", "to", "say", "hi", answer="```bash\nprintf 'auto-%s\\n' ran\n```\nPrints.")
        self.expect("auto-ran")
        self.assertEqual(self.finish(), 0)

        target = self.tmp / "made"
        self.spawn("-y", "to", "make", "a", "file", answer=f"```bash\ntouch {target}\n```\nCreates.")
        self.assertEqual(self.finish(), 0)
        self.assertIn("unsafe", self.output)
        self.assertFalse(target.exists())

    def test_run_nonzero_exit_is_reported(self):
        self.ask_then_run("to", "fail", answer="```bash\nfalse\n```\nFails.")
        self.expect(r"\[Enter\] run")
        self.send("\r")
        self.expect("exited with 1")
        self.assertEqual(self.finish(), 1)

    def test_run_explain_then_quit(self):
        self.ask_then_run("to", "list", answer="```bash\nls -la\n```\nLists.", then=["-la — long listing\nEffect: none."])
        self.expect(r"\[Enter\] run")
        self.send("e")
        self.expect(r"Effect: none\.[\s\S]*\[Enter\] run")
        self.send("q")
        self.assertEqual(self.finish(), 0)
        self.assertEqual(self.log_entries()[-1]["action"], "quit")

    def test_ctrl_c_at_run_prompt_exits_130_quietly(self):
        self.ask_then_run("to", "list", answer="```bash\nls\n```\nLists.")
        self.expect(r"\[Enter\] run")
        self.send("\x03")
        self.assertEqual(self.finish(), 130)


if __name__ == "__main__":
    unittest.main()
