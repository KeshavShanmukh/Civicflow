"""HTTP contract tests for the same-origin local CivicFlow server."""

from __future__ import annotations

import http.cookiejar
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from backend.server import CivicFlowHTTPServer


class CivicFlowHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "http-test.sqlite3"
        self.server = CivicFlowHTTPServer(("127.0.0.1", 0), database_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.cookies = http.cookiejar.CookieJar()
        self.client = build_opener(HTTPCookieProcessor(self.cookies))

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, route: str, method: str = "GET", body: dict | None = None,
                headers: dict | None = None):
        payload = json.dumps(body).encode() if body is not None else None
        request = Request(
            self.base_url + route, data=payload, method=method,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = self.client.open(request, timeout=3)
        except HTTPError as error:
            return error.code, error.read(), error.headers
        return response.status, response.read(), response.headers

    def test_local_static_health_demo_session_and_role_filtered_state(self) -> None:
        status, body, _ = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True, "database": "sqlite"})
        status, body, _ = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"CivicFlow", body)
        status, body, _ = self.request("/api/state")
        self.assertEqual(status, 401)
        status, body, headers = self.request(
            "/api/auth/demo", "POST", {"role": "citizen"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["user"]["role"], "citizen")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        status, body, _ = self.request("/api/state")
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertEqual(state["user"]["id"], "demo-citizen")
        self.assertTrue(all(report["citizenId"] == "demo-citizen" for report in state["reports"]))

    def test_origin_check_blocks_cross_site_writes(self) -> None:
        status, _, _ = self.request(
            "/api/auth/demo", "POST", {"role": "admin"},
            {"Origin": "http://attacker.invalid"},
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
