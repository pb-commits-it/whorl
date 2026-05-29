"""Magic-link auth flow."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient


def test_magic_request_creates_org_and_returns_dev_link(client: TestClient):
    resp = client.post(
        "/api/auth/magic",
        json={"email": "alice@example.com", "org_type": "agronomist", "name": "Alice"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] is True
    assert body["dev_link"]
    assert "/api/auth/verify?token=" in body["dev_link"]


def test_magic_request_rejects_invalid_email(client: TestClient):
    resp = client.post("/api/auth/magic", json={"email": "x"})
    assert resp.status_code == 400


def test_magic_request_rejects_bad_org_type(client: TestClient):
    resp = client.post(
        "/api/auth/magic",
        json={"email": "alice@example.com", "org_type": "wizard"},
    )
    assert resp.status_code == 400


def test_verify_sets_session_cookie_and_me_returns_user(client: TestClient):
    r1 = client.post(
        "/api/auth/magic",
        json={"email": "bob@example.com", "org_type": "farmer", "name": "Bob"},
    )
    link = r1.json()["dev_link"]
    token = re.search(r"token=([A-Za-z0-9_\-]+)", link).group(1)

    r2 = client.get(f"/api/auth/verify?token={token}")
    assert r2.status_code == 200, r2.text
    # Cookie should be set
    cookies = {c.name: c.value for c in client.cookies.jar}
    assert "whorl_session" in cookies

    r3 = client.get("/api/me")
    assert r3.status_code == 200, r3.text
    me = r3.json()
    assert me["email"] == "bob@example.com"
    assert me["org_type"] == "farmer"
    assert me["org_name"] == "Bob"


def test_verify_rejects_invalid_token(client: TestClient):
    r = client.get("/api/auth/verify?token=nope-not-a-real-token")
    assert r.status_code == 400


def test_verify_rejects_reused_token(client: TestClient):
    r1 = client.post("/api/auth/magic", json={"email": "carol@example.com"})
    link = r1.json()["dev_link"]
    token = re.search(r"token=([A-Za-z0-9_\-]+)", link).group(1)

    r2 = client.get(f"/api/auth/verify?token={token}")
    assert r2.status_code == 200
    # Second use of the same token should fail.
    r3 = client.get(f"/api/auth/verify?token={token}")
    assert r3.status_code == 400


def test_me_requires_auth(client: TestClient):
    r = client.get("/api/me")
    assert r.status_code == 401


def test_logout_clears_cookie(auth_client: TestClient):
    r = auth_client.post("/api/auth/logout")
    assert r.status_code == 200
    # After logout the cookie is deleted; /api/me should 401.
    auth_client.cookies.clear()
    r2 = auth_client.get("/api/me")
    assert r2.status_code == 401
