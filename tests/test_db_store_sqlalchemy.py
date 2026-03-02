from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.schemas.base import GenerateRequest
from app.schemas.title import TitleResponse
from app.storage.problem_store import LocalProblemStore
from tests.fixtures import PASSAGE


pytest.importorskip("sqlalchemy")
from app.storage.db_store import SQLAlchemyProblemStore


def _request() -> GenerateRequest:
    return GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        choices=5,
        seed=101,
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


def test_sqlalchemy_problem_store_persists_record(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    local_store = LocalProblemStore(root_dir=tmp_path / "app" / "problems")
    saved = local_store.save(request=_request(), result=_result())

    db_store = SQLAlchemyProblemStore(database_url=db_url)
    row_id = db_store.save(saved)

    assert row_id >= 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT problem_uid, problem_type, passage_id, attempt_no, file_path FROM problem_records WHERE id = ?",
            (row_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == saved.problem_uid
    assert row[1] == saved.problem_type
    assert row[2] == saved.passage_id
    assert row[3] == saved.attempt_no
    assert row[4] == saved.storage_meta.file_path
