"""Farms + fields + scouts CRUD scoped to the user's org."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_farms_initially_empty(auth_client: TestClient):
    r = auth_client.get("/api/farms")
    assert r.status_code == 200
    assert r.json() == []


def test_create_farm_then_field_then_scout(auth_client: TestClient):
    # 1. create farm
    f = auth_client.post(
        "/api/farms",
        json={"name": "Hartman Family", "client_name": None},
    )
    assert f.status_code == 201, f.text
    farm_id = f.json()["id"]

    # 2. create field on that farm
    field_resp = auth_client.post(
        f"/api/farms/{farm_id}/fields",
        json={"name": "North 80", "crop": "corn", "acres": 80.0},
    )
    assert field_resp.status_code == 201, field_resp.text
    field_id = field_resp.json()["id"]
    assert field_resp.json()["crop"] == "corn"

    # 3. list farms shows the new one
    r = auth_client.get("/api/farms")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Hartman Family"

    # 4. list fields under the farm
    r = auth_client.get(f"/api/farms/{farm_id}/fields")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "North 80"

    # 5. start a scout on the field
    s = auth_client.post("/api/scouts", json={"field_id": field_id})
    assert s.status_code == 201, s.text
    scout = s.json()
    assert scout["field_id"] == field_id
    assert scout["status"] == "in_progress"

    # 6. list scouts for the field
    r = auth_client.get(f"/api/fields/{field_id}/scouts")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_farm_create_requires_auth(client: TestClient):
    r = client.post("/api/farms", json={"name": "X"})
    assert r.status_code == 401


def test_cannot_see_other_orgs_farms(client: TestClient):
    # Org A
    r = client.post("/api/auth/magic", json={"email": "a@example.com", "name": "A"})
    import re
    token = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={token}")
    client.post("/api/farms", json={"name": "Org A Farm"})
    a_farms = client.get("/api/farms").json()
    assert len(a_farms) == 1

    # Switch to Org B
    client.post("/api/auth/logout")
    client.cookies.clear()
    r = client.post("/api/auth/magic", json={"email": "b@example.com", "name": "B"})
    token = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={token}")
    b_farms = client.get("/api/farms").json()
    assert b_farms == []   # B sees none of A's farms


def test_scout_create_rejects_field_from_other_org(client: TestClient):
    # Org A creates a field, captures its id, then logs out.
    import re
    r = client.post("/api/auth/magic", json={"email": "a@example.com", "name": "A"})
    token = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={token}")
    farm = client.post("/api/farms", json={"name": "A Farm"}).json()
    field = client.post(
        f"/api/farms/{farm['id']}/fields", json={"name": "A Field", "crop": "corn"}
    ).json()
    client.post("/api/auth/logout")
    client.cookies.clear()

    # Org B can't scout Org A's field.
    r = client.post("/api/auth/magic", json={"email": "b@example.com", "name": "B"})
    token = re.search(r"token=([A-Za-z0-9_\-]+)", r.json()["dev_link"]).group(1)
    client.get(f"/api/auth/verify?token={token}")
    resp = client.post("/api/scouts", json={"field_id": field["id"]})
    assert resp.status_code == 404
