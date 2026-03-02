from __future__ import annotations

import json
from pathlib import Path

from app.schemas.base import GenerateRequest
from app.schemas.title import TitleResponse
from app.storage.problem_store import LocalProblemStore
from tests.fixtures import PASSAGE


def _request(seed: int | None = 123) -> GenerateRequest:
    return GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        choices=5,
        seed=seed,
        style="edu_office",
        explain=True,
        return_korean_stem=True,
        debug=False,
    )


def _title_result() -> TitleResponse:
    return TitleResponse(
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
    )


def test_local_problem_store_increments_attempt_number(tmp_path: Path) -> None:
    root_dir = tmp_path / "app" / "problems"
    store = LocalProblemStore(root_dir=root_dir)

    first = store.save(request=_request(seed=1), result=_title_result())
    second = store.save(request=_request(seed=2), result=_title_result())

    assert first.attempt_no == 1
    assert second.attempt_no == 2
    assert first.passage_id == second.passage_id
    assert first.storage_meta.file_path.endswith("attempt_001.json")
    assert second.storage_meta.file_path.endswith("attempt_002.json")

    first_abs = tmp_path / first.storage_meta.file_path
    second_abs = tmp_path / second.storage_meta.file_path
    assert first_abs.exists()
    assert second_abs.exists()

    first_payload = json.loads(first_abs.read_text(encoding="utf-8"))
    second_payload = json.loads(second_abs.read_text(encoding="utf-8"))
    assert first_payload["attempt_no"] == 1
    assert second_payload["attempt_no"] == 2
