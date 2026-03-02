from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures import PASSAGE


client = TestClient(app)


ROUTES = [
    "/api/v1/title",
    "/api/v1/topic",
    "/api/v1/summary",
    "/api/v1/implicit",
    "/api/v1/insertion",
    "/api/v1/order",
    "/api/v1/irrelevant",
    "/api/v1/blank",
    "/api/v1/reference",
    "/api/v1/vocab",
    "/api/v1/grammar",
]


def _payload() -> dict:
    return {
        "passage": PASSAGE,
        "difficulty": "mid",
        "seed": 123,
        "debug": True,
        "return_korean_stem": False,
    }


def test_all_endpoints_smoke() -> None:
    for route in ROUTES:
        response = client.post(route, json=_payload())
        assert response.status_code == 200, f"{route} failed: {response.text}"

        data = response.json()
        assert "type" in data
        assert "choices" in data
        assert len(data["choices"]) == 5
        assert data["answer"]["label"] in {choice["label"] for choice in data["choices"]}


def test_long_endpoint_removed() -> None:
    response = client.post("/api/v1/long", json=_payload())
    assert response.status_code == 404
