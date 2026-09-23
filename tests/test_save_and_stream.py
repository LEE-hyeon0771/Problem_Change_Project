import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.apis import deps
from backend.main import app
from backend.storage.problem_store import LocalProblemStore
from backend.storage.wordbook_store import LocalWordbookStore
from tests.fixtures import PASSAGE


client = TestClient(app)


@pytest.fixture
def stores(monkeypatch, tmp_path: Path):
    problem_store = LocalProblemStore(root_dir=tmp_path / "backend" / "problems")
    wordbook_store = LocalWordbookStore(root_dir=tmp_path / "backend" / "wordbooks")
    monkeypatch.setattr(deps, "problem_store", problem_store)
    monkeypatch.setattr(deps.problem_persistence, "local_store", problem_store)
    monkeypatch.setattr(deps, "wordbook_store", wordbook_store)
    monkeypatch.setattr(deps.settings, "enable_problem_persistence", True)
    return problem_store, wordbook_store


def _generate_problem() -> dict:
    response = client.post("/api/v1/title", json={"passage": PASSAGE})
    assert response.status_code == 200
    return response.json()


def _generate_wordbook() -> dict:
    response = client.post("/api/v1/wordbook", json={"passage": PASSAGE})
    assert response.status_code == 200
    return response.json()


def _read_sse(url: str, payload: dict) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    with client.stream("POST", url, json=payload) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    for block in body.strip().split("\n\n"):
        name = ""
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if name and data:
            events.append((name, json.loads(data)))
    return events


# --------------------------------------------------------------- 자동 저장 중단


def test_generation_no_longer_auto_saves(stores) -> None:
    """"사용"을 누르기 전에는 개인DB가 비어 있어야 합니다."""
    problem = _generate_problem()

    assert "storage" not in problem.get("meta", {})
    assert client.get("/api/v1/problems").json() == []


def test_wordbook_generation_no_longer_auto_saves(stores) -> None:
    _generate_wordbook()

    assert client.get("/api/v1/wordbooks").json() == []


# ------------------------------------------------------------------- 문항 저장


def test_save_problem_puts_it_in_the_library(stores) -> None:
    problem = _generate_problem()

    response = client.post("/api/v1/problems", json={"request": {"passage": PASSAGE}, "result": problem})

    assert response.status_code == 201
    saved = response.json()
    assert saved["problem_type"] == "title"
    library = client.get("/api/v1/problems").json()
    assert [record["problem_uid"] for record in library] == [saved["problem_uid"]]


def test_save_problem_rejects_unknown_type(stores) -> None:
    response = client.post(
        "/api/v1/problems",
        json={"request": {"passage": PASSAGE}, "result": {"type": "not-a-type"}},
    )

    assert response.status_code == 422


def test_save_problem_rejects_malformed_result(stores) -> None:
    response = client.post(
        "/api/v1/problems",
        json={"request": {"passage": PASSAGE}, "result": {"type": "title", "choices": "nope"}},
    )

    assert response.status_code == 422


def test_save_problem_blocked_when_persistence_disabled(stores, monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "enable_problem_persistence", False)
    problem = _generate_problem()

    response = client.post("/api/v1/problems", json={"request": {"passage": PASSAGE}, "result": problem})

    assert response.status_code == 409


def test_saving_twice_creates_separate_attempts(stores) -> None:
    problem = _generate_problem()
    payload = {"request": {"passage": PASSAGE}, "result": problem}

    first = client.post("/api/v1/problems", json=payload).json()
    second = client.post("/api/v1/problems", json=payload).json()

    assert first["attempt_no"] == 1
    assert second["attempt_no"] == 2
    assert first["problem_uid"] != second["problem_uid"]


# ----------------------------------------------------------------- 단어장 저장


def test_save_wordbook_roundtrip(stores) -> None:
    wordbook = _generate_wordbook()

    created = client.post(
        "/api/v1/wordbooks",
        json={"title": "3월 모의고사 지문", "request": {"passage": PASSAGE}, "result": wordbook},
    )
    assert created.status_code == 201
    record = created.json()
    assert record["title"] == "3월 모의고사 지문"
    assert record["entry_count"] == len(wordbook["entries"])

    listing = client.get("/api/v1/wordbooks").json()
    assert [item["wordbook_uid"] for item in listing] == [record["wordbook_uid"]]

    detail = client.get(f"/api/v1/wordbooks/{record['wordbook_uid']}")
    assert detail.status_code == 200
    assert detail.json()["result"]["type"] == "wordbook"


def test_wordbook_title_defaults_to_passage_head(stores) -> None:
    wordbook = _generate_wordbook()

    record = client.post(
        "/api/v1/wordbooks",
        json={"title": "", "request": {"passage": PASSAGE}, "result": wordbook},
    ).json()

    assert record["title"]
    assert record["title"].startswith("People often rely")


def test_delete_wordbook(stores) -> None:
    wordbook = _generate_wordbook()
    record = client.post(
        "/api/v1/wordbooks",
        json={"request": {"passage": PASSAGE}, "result": wordbook},
    ).json()

    assert client.delete(f"/api/v1/wordbooks/{record['wordbook_uid']}").status_code == 204
    assert client.get("/api/v1/wordbooks").json() == []
    assert client.delete(f"/api/v1/wordbooks/{record['wordbook_uid']}").status_code == 404


def test_missing_wordbook_returns_404(stores) -> None:
    assert client.get("/api/v1/wordbooks/" + "0" * 32).status_code == 404


# -------------------------------------------------------------------- 스트리밍


def test_problem_stream_emits_status_then_done() -> None:
    events = _read_sse("/api/v1/stream/title", {"passage": PASSAGE})

    names = [name for name, _ in events]
    assert names[0] == "status"
    assert names[-1] == "done"
    assert "error" not in names

    phases = [payload.get("phase") for name, payload in events if name == "status"]
    assert "start" in phases
    assert "analyze" in phases

    final = events[-1][1]
    assert final["type"] == "title"
    assert len(final["choices"]) == 5


def test_wordbook_stream_reports_candidate_count() -> None:
    events = _read_sse("/api/v1/stream-wordbook", {"passage": PASSAGE})

    names = [name for name, _ in events]
    assert names[-1] == "done"

    candidate_events = [payload for name, payload in events if payload.get("phase") == "candidates"]
    assert candidate_events, "후보 추출 진행 상황이 오지 않았습니다."
    assert candidate_events[0]["candidate_count"] > 0

    assert events[-1][1]["type"] == "wordbook"


def test_stream_reports_validation_error_as_event() -> None:
    """검증 실패는 스트림이 열린 뒤 error 이벤트로 전달됩니다."""
    events = _read_sse("/api/v1/stream/title", {"passage": "Too short."})

    assert events[-1][0] == "error"
    assert events[-1][1]["status"] == 422


def test_stream_rejects_unknown_problem_type() -> None:
    response = client.post("/api/v1/stream/nonsense", json={"passage": PASSAGE})

    assert response.status_code == 422


def test_stream_does_not_save(stores) -> None:
    _read_sse("/api/v1/stream/title", {"passage": PASSAGE})

    assert client.get("/api/v1/problems").json() == []
