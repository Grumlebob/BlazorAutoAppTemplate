from __future__ import annotations

import shutil
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "Scripts" / "Test-DeployedSite.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


class AcceptanceHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str]] = []
    shell = (
        b'<!doctype html><html><head><script type="module" '
        b'src="/assets/app-12345678.js"></script></head><body>React</body></html>'
    )

    def log_message(self, *_args):
        pass

    def respond(self, status: int, body: bytes = b"", content_type: str = "text/plain", headers=None):
        AcceptanceHandler.requests.append((self.command, self.path))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        if self.path == "/" or self.path in ("/books", "/books/author/example"):
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'sha256-test'; object-src 'none'")
        if self.path == "/assets/app-12345678.js":
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health/ready":
            self.respond(200, b"Healthy")
        elif path == "/api/books":
            self.respond(401, b'{"error":"unauthorized"}', "application/json", {"Cache-Control": "private, no-store"})
        elif path == "/api/author-books":
            self.respond(200, b'{"books":[{"id":1,"title":"Public book"}]}', "application/json")
        elif path in ("/", "/books", "/books/author/example"):
            self.respond(200, self.shell, "text/html")
        elif path == "/assets/app-12345678.js":
            self.respond(200, b"console.log('public')", "text/javascript")
        else:
            self.respond(404, b"Not found")

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.respond(500, b"Writes are forbidden in this fixture")


@unittest.skipUnless(POWERSHELL, "PowerShell is required for deployed-site acceptance tests")
class DeployedSiteAcceptanceTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-File", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def test_mismatched_profiles_fail_before_network_access(self):
        result = self.run_script(
            "-FrontendProfile", "React",
            "-AcceptanceProfile", "BlazorAutoV1",
            "-BaseUrl", "http://127.0.0.1:1",
        )
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("FrontendProfile and AcceptanceProfile do not match", result.stdout + result.stderr)
        self.assertNotIn("PASS DNS", result.stdout)

    def test_react_acceptance_is_public_and_read_only(self):
        AcceptanceHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), AcceptanceHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = self.run_script(
                "-FrontendProfile", "React",
                "-AcceptanceProfile", "ReactPublicV1",
                "-BaseUrl", f"http://127.0.0.1:{server.server_port}",
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS React-public-data", result.stdout)
        self.assertIn("PASS React-no-cookie", result.stdout)
        self.assertIn("RESULT: PASS", result.stdout)
        methods = {method for method, _path in AcceptanceHandler.requests}
        self.assertLessEqual(methods, {"GET", "HEAD"})
        paths = {path.split("?", 1)[0] for _method, path in AcceptanceHandler.requests}
        self.assertIn("/api/author-books", paths)
        self.assertIn("/Account/Register", paths)
        self.assertNotIn("/Account/Register", {path for method, path in AcceptanceHandler.requests if method != "GET"})


if __name__ == "__main__":
    unittest.main()
