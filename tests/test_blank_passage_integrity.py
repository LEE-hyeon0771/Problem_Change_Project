from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures import PASSAGE


client = TestClient(app)


def _resolve_answer_text(data: dict) -> str:
    answer_label = data["answer"]["label"]
    for choice in data["choices"]:
        if choice["label"] == answer_label:
            return choice["text"]
    raise AssertionError("answer label not found in choices")


def test_blank_passage_integrity_three_calls() -> None:
    payload = {
        "passage": PASSAGE,
        "difficulty": "mid",
        "seed": 123,
        "return_korean_stem": True,
        "explain": True,
    }

    for _ in range(3):
        response = client.post("/api/v1/blank", json=payload)
        assert response.status_code == 200, response.text

        data = response.json()
        assert data["type"] == "blank"
        assert data["passage"].count("_____") == 1

        answer_text = _resolve_answer_text(data)
        restored = data["passage"].replace("_____", answer_text, 1)
        assert restored == PASSAGE
