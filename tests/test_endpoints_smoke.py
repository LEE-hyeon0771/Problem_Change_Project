from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.schemas.base import GenerateRequest
from app.schemas.title import TitleResponse
from app.storage.problem_store import LocalProblemStore
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


def test_saved_problem_library_endpoints(monkeypatch, tmp_path) -> None:
    store = LocalProblemStore(root_dir=tmp_path / "app" / "problems")
    saved = store.save(
        request=GenerateRequest(**_payload()),
        result=TitleResponse(
            type="title",
            passage=PASSAGE,
            question="다음 글의 제목으로 가장 적절한 것은?",
            choices=[
                {"label": "①", "text": "A"},
                {"label": "②", "text": "B"},
                {"label": "③", "text": "C"},
                {"label": "④", "text": "D"},
                {"label": "⑤", "text": "E"},
            ],
            answer={"label": "③", "text": "C"},
            explanation="해설",
            meta={"difficulty": "mid", "seed": 123},
        ),
    )
    monkeypatch.setattr(main_module, "problem_store", store)

    list_response = client.get("/api/v1/problems")
    assert list_response.status_code == 200
    assert list_response.json()[0]["problem_uid"] == saved.problem_uid

    detail_response = client.get(f"/api/v1/problems/{saved.problem_uid}")
    assert detail_response.status_code == 200
    assert detail_response.json()["result"]["type"] == "title"
