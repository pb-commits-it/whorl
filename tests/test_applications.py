"""Applications — log a spray, list for a field, cross-org isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _seed_field(client: TestClient) -> str:
    farm = client.post("/api/farms", json={"name": "Demo Farm"}).json()
    field = client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "North 80", "crop": "corn"},
    ).json()
    return field["id"]


def test_log_and_list_application(auth_client: TestClient):
    field_id = _seed_field(auth_client)
    when = (datetime.now(tz=timezone.utc) - timedelta(days=14)).isoformat()

    r = auth_client.post(
        "/api/applications",
        json={
            "field_id": field_id,
            "applied_at": when,
            "product_name": "Brigade 2EC",
            "active_ingredient": "bifenthrin",
            "moa_class": "IRAC",
            "moa_group": "3A",
            "pest_target": "Helicoverpa zea",
            "rate": "6.4 oz/ac",
            "rei_hours": 12,
            "phi_days": 1,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["product_name"] == "Brigade 2EC"
    assert body["moa_group"] == "3A"

    listing = auth_client.get(f"/api/fields/{field_id}/applications").json()
    assert len(listing) == 1
    assert listing[0]["active_ingredient"] == "bifenthrin"


def test_application_requires_auth(client: TestClient):
    r = client.post(
        "/api/applications",
        json={"field_id": "00000000-0000-0000-0000-000000000000",
              "applied_at": "2026-01-01T00:00:00Z",
              "product_name": "X"},
    )
    assert r.status_code == 401


def test_cannot_log_application_on_other_org_field(client: TestClient):
    import re

    # Org A: create a field, capture id.
    r = client.post("/api/auth/magic", json={"email": "a@example.com", "name": "A"})
    tok = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={tok}")
    a_field = _seed_field(client)
    client.post("/api/auth/logout")
    client.cookies.clear()

    # Org B: try to log against A's field.
    r = client.post("/api/auth/magic", json={"email": "b@example.com", "name": "B"})
    tok = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={tok}")
    r = client.post(
        "/api/applications",
        json={"field_id": a_field, "applied_at": "2026-01-01T00:00:00Z",
              "product_name": "Brigade", "moa_class": "IRAC", "moa_group": "3A"},
    )
    assert r.status_code == 404
