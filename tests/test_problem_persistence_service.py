from __future__ import annotations

import json
from pathlib import Path

from app.schemas.base import GenerateRequest
from app.schemas.title import TitleResponse
from app.storage.persistence import ProblemPersistenceService
from app.storage.problem_store import LocalProblemStore
from tests.fixtures import PASSAGE


class FakeDBStore:
    def __init__(self) -> None:
        self.saved_problem_uid: str | None = None

    def save(self, record) -> int:
        self.saved_problem_uid = record.problem_uid
        return 7


def _request() -> GenerateRequest:
    return GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        choices=5,
        seed=13,
        style="edu_office",
        explain=True,
        return_korean_stem=True,
        debug=False,
    )


def _result() -> TitleResponse:
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
        meta={},
    )


def test_problem_persistence_service_updates_file_after_db_save(tmp_path: Path) -> None:
    local_store = LocalProblemStore(root_dir=tmp_path / "app" / "problems")
    fake_db = FakeDBStore()
    service = ProblemPersistenceService(local_store=local_store, db_store=fake_db)

    saved = service.persist(request=_request(), result=_result())

    assert saved.storage_meta.db_saved is True
    assert saved.storage_meta.db_row_id == 7
    assert fake_db.saved_problem_uid == saved.problem_uid

    payload_path = tmp_path / saved.storage_meta.file_path
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["storage_meta"]["db_saved"] is True
    assert payload["storage_meta"]["db_row_id"] == 7
