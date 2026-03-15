"""
Tests for AuthMiddleware in src/dashboard/server.py.

Verifies that:
- Unauthenticated requests are rejected with 401
- Wrong credentials are rejected with 401
- Correct Basic Auth credentials are accepted and a session cookie is issued
- Subsequent requests using that cookie are accepted without re-sending credentials
- An invalid/unknown cookie is rejected with 401
- Auth is disabled entirely when DASHBOARD_PASS is not set (local dev)
- WebSocket connections with a valid cookie are accepted
- WebSocket connections without auth are rejected

No OpenAI key required — the assembly generator is never called.
"""

import base64
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Make sure the repo root is on sys.path so imports resolve
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def basic_auth_header(username: str, password: str) -> str:
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded}"


def make_client(user: str = "admin", password: str = "secret") -> TestClient:
    """
    Build a fresh TestClient with the given DASHBOARD_USER / DASHBOARD_PASS.
    Importing server inside the function means each call gets a fresh app
    instance with a clean session store.
    """
    os.environ["DASHBOARD_USER"] = user
    os.environ["DASHBOARD_PASS"] = password

    # Force re-import so AuthMiddleware picks up the new env vars
    import importlib
    import src.dashboard.server as server_module
    importlib.reload(server_module)

    return TestClient(server_module.app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# HTTP auth tests
# ---------------------------------------------------------------------------

class TestHTTPAuth:

    def test_no_credentials_returns_401(self):
        client = make_client()
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 401

    def test_401_includes_www_authenticate_header(self):
        client = make_client()
        resp = client.get("/", follow_redirects=False)
        assert "www-authenticate" in resp.headers
        assert "Basic" in resp.headers["www-authenticate"]

    def test_wrong_password_returns_401(self):
        client = make_client(password="secret")
        resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("admin", "wrong")},
        )
        assert resp.status_code == 401

    def test_wrong_username_returns_401(self):
        client = make_client(user="admin", password="secret")
        resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("hacker", "secret")},
        )
        assert resp.status_code == 401

    def test_correct_credentials_returns_200(self):
        client = make_client(user="admin", password="secret")
        resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("admin", "secret")},
        )
        assert resp.status_code == 200

    def test_correct_credentials_sets_session_cookie(self):
        client = make_client(user="admin", password="secret")
        resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("admin", "secret")},
        )
        assert "assembly_session" in resp.cookies

    def test_valid_cookie_allows_access_without_credentials(self):
        client = make_client(user="admin", password="secret")

        # Authenticate once to get the cookie
        auth_resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("admin", "secret")},
        )
        token = auth_resp.cookies["assembly_session"]

        # Second request: cookie only, no Authorization header
        resp = client.get("/", cookies={"assembly_session": token})
        assert resp.status_code == 200

    def test_unknown_cookie_returns_401(self):
        client = make_client(user="admin", password="secret")
        resp = client.get(
            "/",
            cookies={"assembly_session": "not-a-real-token"},
        )
        assert resp.status_code == 401

    def test_api_route_also_protected(self):
        """Auth covers all routes, not just /."""
        client = make_client(user="admin", password="secret")
        resp = client.get("/api/sessions")
        assert resp.status_code == 401

    def test_api_route_accessible_with_credentials(self):
        client = make_client(user="admin", password="secret")
        resp = client.get(
            "/api/sessions",
            headers={"Authorization": basic_auth_header("admin", "secret")},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth disabled (local dev)
# ---------------------------------------------------------------------------

class TestAuthDisabled:

    def test_no_password_set_allows_all_requests(self):
        os.environ["DASHBOARD_USER"] = "admin"
        os.environ["DASHBOARD_PASS"] = ""  # disabled

        import importlib
        import src.dashboard.server as server_module
        importlib.reload(server_module)

        client = TestClient(server_module.app, raise_server_exceptions=False)
        resp = client.get("/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# WebSocket auth tests
# ---------------------------------------------------------------------------

class TestWebSocketAuth:

    def _get_session_cookie(self, client: TestClient) -> str:
        resp = client.get(
            "/",
            headers={"Authorization": basic_auth_header("admin", "secret")},
        )
        return resp.cookies["assembly_session"]

    def test_websocket_rejected_without_auth(self):
        from starlette.websockets import WebSocketDisconnect
        client = make_client(user="admin", password="secret")
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/fake-session-id"):
                pass
        assert exc_info.value.code == 4401

    def test_websocket_accepted_with_valid_cookie(self):
        client = make_client(user="admin", password="secret")
        token = self._get_session_cookie(client)

        # The WS route itself will send run_error for an unknown session_id,
        # but it should get past the middleware (status != close before accept)
        with client.websocket_connect(
            "/ws/fake-session-id",
            cookies={"assembly_session": token},
        ) as ws:
            msg = ws.receive_json()
            # Middleware passed — route responded (even if session unknown)
            assert msg.get("type") in ("run_error", "heartbeat")
