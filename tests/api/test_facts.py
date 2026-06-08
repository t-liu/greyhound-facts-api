"""API tests for public facts endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from tests.conftest import ADMIN_API_KEY


def _seed_fact(client: TestClient, text: str = "Greyhounds can run 45 mph fast.") -> dict:
    """Helper: create a fact via the admin API and return the response JSON."""
    resp = client.post(
        "/v1/admin/facts",
        json={"text": text, "source": "AKC", "tags": ["speed"]},
        headers={"X-API-Key": ADMIN_API_KEY},
    )
    assert resp.status_code == 201
    return resp.json()


# ── GET /v1/health ────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_ok(self, test_client: TestClient) -> None:
        resp = test_client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "environment" in body

    def test_returns_request_id_header(self, test_client: TestClient) -> None:
        resp = test_client.get("/v1/health")
        assert "x-request-id" in resp.headers


# ── GET /v1/facts/random ──────────────────────────────────────────────────────


class TestGetRandomFact:
    def test_returns_fact_when_data_exists(self, test_client: TestClient) -> None:
        _seed_fact(test_client)
        resp = test_client.get("/v1/facts/random")
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert "text" in body

    def test_returns_404_when_empty(self, test_client: TestClient) -> None:
        resp = test_client.get("/v1/facts/random")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NO_FACTS_AVAILABLE"


# ── GET /v1/facts/{id} ────────────────────────────────────────────────────────


class TestGetFactById:
    def test_returns_existing_fact(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        fact_id = created["id"]

        resp = test_client.get(f"/v1/facts/{fact_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == fact_id
        assert body["text"] == "Greyhounds can run 45 mph fast."
        assert body["source"] == "AKC"
        assert body["tags"] == ["speed"]

    def test_returns_404_for_missing_id(self, test_client: TestClient) -> None:
        resp = test_client.get("/v1/facts/does-not-exist")
        assert resp.status_code == 404
        error = resp.json()["error"]
        assert error["code"] == "FACT_NOT_FOUND"

    def test_response_includes_timestamps(self, test_client: TestClient) -> None:
        created = _seed_fact(test_client)
        resp = test_client.get(f"/v1/facts/{created['id']}")
        body = resp.json()
        # Validate ISO-8601 timestamps
        datetime.fromisoformat(body["created_at"])
        datetime.fromisoformat(body["updated_at"])
