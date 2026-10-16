from __future__ import annotations

import json
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
    requests: list[tuple[str, str, str]] = []
    accounts_enabled = False
    capability_status = 200
    capability_malformed = False
    shell = (
        b'<!doctype html><html><head><script type="module" '
        b'src="/assets/app-12345678.js"></script></head><body>React</body></html>'
    )

    def log_message(self, *_args):
        pass

    def respond(self, status: int, body: bytes = b"", content_type: str = "text/plain", headers=None):
        AcceptanceHandler.requests.append((self.command, self.path, self.headers.get("Cookie", "")))
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
        if path == "/api/client-config":
            payload = json.dumps({
                "schemaVersion": 1,
                "accountsEnabled": (
                    "true" if AcceptanceHandler.capability_malformed else AcceptanceHandler.accounts_enabled
                ),
                "applicationId": "1234567890abcdef1234567890abcdef",
            }).encode()
            self.respond(
                AcceptanceHandler.capability_status,
                payload if AcceptanceHandler.capability_status == 200 else b"Not found",
                "application/json",
                {"Cache-Control": "no-store"},
            )
        elif path == "/api/auth/session" and AcceptanceHandler.accounts_enabled:
            payload = json.dumps({
                "enabled": True,
                "registrationEnabled": False,
                "emailEnabled": True,
                "csrfToken": "fixture-csrf-token",
                "user": None,
            }).encode()
            self.respond(
                200,
                payload,
                "application/json",
                {
                    "Cache-Control": "private, no-store",
                    "Set-Cookie": "__Host-CSRF-1234567890abcdef1234567890abcdef=fixture; Path=/; HttpOnly; SameSite=Strict",
                },
            )
        elif path == "/api/auth/login" and AcceptanceHandler.accounts_enabled:
            self.respond(405, b'{"code":"MethodNotAllowed"}', "application/problem+json", {"Allow": "POST"})
        elif path == "/health/ready":
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

    def run_fixture(
        self,
        accounts_enabled: bool,
        capability_status: int = 200,
        capability_malformed: bool = False,
    ):
        AcceptanceHandler.requests = []
        AcceptanceHandler.accounts_enabled = accounts_enabled
        AcceptanceHandler.capability_status = capability_status
        AcceptanceHandler.capability_malformed = capability_malformed
        server = ThreadingHTTPServer(("127.0.0.1", 0), AcceptanceHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = self.run_script(
                "-FrontendProfile", "React",
                "-AcceptanceProfile", "ReactPublicV1",
                "-BaseUrl", f"http://127.0.0.1:{server.server_port}",
            )
            requests = list(AcceptanceHandler.requests)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
        return result, requests

    def test_mismatched_profiles_fail_before_network_access(self):
        result = self.run_script(
            "-FrontendProfile", "React",
            "-AcceptanceProfile", "BlazorAutoV1",
            "-BaseUrl", "http://127.0.0.1:1",
        )
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("FrontendProfile and AcceptanceProfile do not match", result.stdout + result.stderr)
        self.assertNotIn("PASS DNS", result.stdout)

    def test_react_disabled_acceptance_uses_explicit_capability_and_real_404s(self):
        result, requests = self.run_fixture(accounts_enabled=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS React-client-config", result.stdout)
        self.assertIn("PASS React-public-data", result.stdout)
        self.assertIn("PASS React-no-cookie", result.stdout)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertTrue(requests)
        self.assertEqual(("GET", "/api/client-config"), requests[0][:2])
        methods = {method for method, _path, _cookie in requests}
        self.assertLessEqual(methods, {"GET", "HEAD"})
        paths = {path.split("?", 1)[0] for _method, path, _cookie in requests}
        self.assertIn("/api/author-books", paths)
        self.assertIn("/api/auth/login", paths)
        self.assertIn("/api/auth/session", paths)
        self.assertIn("PASS React-inactive-route-/api/auth/session", result.stdout)
        self.assertTrue(all(not cookie for _method, _path, cookie in requests))

    def test_react_enabled_acceptance_checks_session_post_only_and_unknown_routes(self):
        result, requests = self.run_fixture(accounts_enabled=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS React-client-config", result.stdout)
        self.assertIn("PASS React-enabled-session", result.stdout)
        self.assertIn("PASS React-enabled-session-cache", result.stdout)
        self.assertIn("PASS React-enabled-session-cookie", result.stdout)
        self.assertIn("PASS React-enabled-post-only-GET", result.stdout)
        self.assertIn("PASS React-enabled-post-only-HEAD", result.stdout)
        self.assertIn("PASS React-enabled-unknown-api", result.stdout)
        self.assertIn("PASS React-no-cookie", result.stdout)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertEqual(("GET", "/api/client-config"), requests[0][:2])
        methods = {method for method, _path, _cookie in requests}
        self.assertLessEqual(methods, {"GET", "HEAD"})
        paths = {path.split("?", 1)[0] for _method, path, _cookie in requests}
        self.assertIn("/api/auth/session", paths)
        self.assertIn("/api/auth/login", paths)
        self.assertIn("/api/auth/not-a-real-operation", paths)
        self.assertTrue(all(not cookie for _method, _path, cookie in requests))

    def test_react_missing_or_malformed_capability_fails_before_other_requests(self):
        for options in (
            {"capability_status": 404},
            {"capability_malformed": True},
        ):
            with self.subTest(options=options):
                result, requests = self.run_fixture(accounts_enabled=False, **options)
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn("React client capability document is missing or invalid", result.stdout + result.stderr)
                self.assertNotIn("PASS health", result.stdout)
                self.assertNotIn("Not found", result.stdout + result.stderr)
                paths = {path.split("?", 1)[0] for _method, path, _cookie in requests}
                self.assertEqual({"/api/client-config"}, paths)


if __name__ == "__main__":
    unittest.main()
