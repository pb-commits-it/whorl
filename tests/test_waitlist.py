"""Public waitlist signup — no auth, idempotent on duplicates."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_waitlist_signup_creates_entry(client: TestClient):
    r = client.post("/api/waitlist", json={"email": "farmer@example.com"})
    assert r.status_code == 200, r.text
    assert r.json() == {"subscribed": True}


def test_waitlist_signup_is_idempotent(client: TestClient):
    client.post("/api/waitlist", json={"email": "same@example.com"})
    r = client.post("/api/waitlist", json={"email": "same@example.com"})
    assert r.status_code == 200
    assert r.json()["subscribed"] is True


def test_waitlist_signup_normalizes_email_case(client: TestClient):
    client.post("/api/waitlist", json={"email": "Mixed@Case.COM"})
    # Lower-cased dup is the same row
    r = client.post("/api/waitlist", json={"email": "mixed@case.com"})
    assert r.status_code == 200
    assert r.json()["subscribed"] is True


def test_waitlist_rejects_garbage(client: TestClient):
    r = client.post("/api/waitlist", json={"email": "not-an-email"})
    assert r.status_code == 400
    r = client.post("/api/waitlist", json={"email": "  "})
    assert r.status_code == 400


def test_waitlist_works_unauthenticated(client: TestClient):
    # Public endpoint — no cookie required
    assert "whorl_session" not in client.cookies
    r = client.post("/api/waitlist", json={"email": "anon@x.com", "source": "landing"})
    assert r.status_code == 200
