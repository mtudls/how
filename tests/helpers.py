"""Shared test helpers: load the `how` script as a module, run it as a process, fake the API."""

import http.server
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOW = ROOT / "how"
FAKE_KEY = "gsk_test_secret_key_1234567890WXYZ"


def load_how():
    """Imports the extension-less `how` script as a module."""
    loader = importlib.machinery.SourceFileLoader("how_cli", str(HOW))
    spec = importlib.util.spec_from_loader("how_cli", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def reply(content):
    """An OpenAI-compatible chat completion body."""
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


class FakeAPI:
    """A local OpenAI-compatible endpoint. Queue (status, body, headers) responses; inspect `requests`."""

    def __init__(self):
        self.responses = []
        self.requests = []
        api = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                api.requests.append({"path": self.path, "headers": dict(self.headers),
                                     "body": json.loads(self.rfile.read(length) or b"{}")})
                status, body, headers = api.responses.pop(0) if api.responses else (500, {}, {})
                data = json.dumps(body).encode() if not isinstance(body, bytes) else body
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat/completions"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    def answer(self, content, status=200, headers=None):
        self.responses.append((status, reply(content) if status == 200 else {"error": "x"}, headers or {}))

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class HowTestCase(unittest.TestCase):
    """Gives each test a private HOME, config and state dir, and a fake clipboard tool on PATH."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="how-test-"))
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        self.config_dir, self.state_dir = self.tmp / "config", self.tmp / "state"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.clipboard = self.tmp / "clipboard.txt"
        fake_copy = self.bin / "wl-copy"
        fake_copy.write_text(f"#!/bin/sh\ncat > '{self.clipboard}'\n")
        fake_copy.chmod(0o755)
        self.env = {
            "HOME": str(self.tmp / "home"), "PATH": f"{self.bin}:/usr/bin:/bin", "SHELL": "/bin/sh",
            "HOW_CONFIG_DIR": str(self.config_dir), "HOW_STATE_DIR": str(self.state_dir),
            "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8",
        }

    def with_api(self, key=FAKE_KEY):
        api = FakeAPI()
        self.addCleanup(api.close)
        self.env["HOW_API_URL"] = api.url
        if key:
            self.env["GROQ_API_KEY"] = key
        return api

    def how(self, *args, stdin=""):
        """Runs the real script without a terminal; returns the CompletedProcess."""
        return subprocess.run([sys.executable, str(HOW), *args], input=stdin, capture_output=True, text=True,
                              env=self.env, timeout=20)

    def log_entries(self):
        path = self.state_dir / "how.log"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def environ(env):
    """Context manager that temporarily replaces os.environ (for in-process tests)."""
    from unittest import mock
    return mock.patch.dict(os.environ, env, clear=True)
