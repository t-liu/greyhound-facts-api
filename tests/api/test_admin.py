"""API tests for admin facts endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ADMIN_API_KEY


def _seed_fact(client: TestClient, text: str = "Greyhounds can run up to 45 mph.") -> dict:
    resp = client.post(
        "/v1/admin/facts",
        json={"text": text, "tags": ["speed"]},
        headers={"X-API-Key": ADMIN_API_KEY},
    )
    assert resp.status_code == 201
    return resp.json()


# ── POST /v1/admin/facts ──────────────────────────────────────────────────────


class TestCreateFact:
    def test_creates_fact_returns_201(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/v1/admin/facts",
            json={"text": "Greyhounds have a 270-degree field of view.", "tags": ["vision"]},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["text"] == "Greyhounds have a 270-degree field of view."

    def test_missing_api_key_returns_401(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/v1/admin/facts",
            json={"text": "Greyhounds are the fastest dog breed worldwide."},
        )
        assert resp.status_code == 401

    def test_wrong_api_key_returns_403(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/v1/admin/facts",
            json={"text": "Greyhounds are gentle and affectionate dogs."},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 403

    def test_invalid_payload_returns_422(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/v1/admin/facts",
            json={"text": "Short"},  # too short
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 422

    def test_creates_fact_without_optional_fields(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/v1/admin/facts",
            json={"text": "Greyhounds are one of the oldest dog breeds."},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 201
        assert resp.json()["tags"] == []


# ── PUT /v1/admin/facts/{id} ──────────────────────────────────────────────────


class TestUpdateFact:
    def test_updates_text(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        fact_id = created["id"]

        resp = test_client.put(
            f"/v1/admin/facts/{fact_id}",
            json={"text": "Updated: Greyhounds are the fastest land dogs."},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "Updated: Greyhounds are the fastest land dogs."

    def test_partial_update_preserves_tags(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        resp = test_client.put(
            f"/v1/admin/facts/{created['id']}",
            json={"source": "Updated Source"},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 200

    def test_update_missing_fact_returns_404(self, test_client: TestClient) -> None:
        resp = test_client.put(
            "/v1/admin/facts/nonexistent-id",
            json={"text": "This fact does not exist in the database."},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 404

    def test_update_missing_api_key_returns_401(self, test_client: TestClient) -> None:
        resp = test_client.put(
            "/v1/admin/facts/some-id",
            json={"text": "Some updated fact text that is long enough."},
        )
        assert resp.status_code == 401


# ── DELETE /v1/admin/facts/{id} ───────────────────────────────────────────────


class TestDeleteFact:
    def test_deletes_existing_fact(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        fact_id = created["id"]

        resp = test_client.delete(
            f"/v1/admin/facts/{fact_id}",
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = test_client.get(f"/v1/facts/{fact_id}")
        assert get_resp.status_code == 404

    def test_delete_missing_fact_returns_404(self, test_client: TestClient) -> None:
        resp = test_client.delete(
            "/v1/admin/facts/nonexistent-id",
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert resp.status_code == 404

    def test_delete_missing_api_key_returns_401(self, test_client: TestClient) -> None:
        resp = test_client.delete("/v1/admin/facts/some-id")
        assert resp.status_code == 401

    def test_delete_and_random_returns_404(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        test_client.delete(
            f"/v1/admin/facts/{created['id']}",
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        resp = test_client.get("/v1/facts/random")
        assert resp.status_code == 404
