from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.base import GenerateRequest
from app.schemas.storage import SavedProblemRecord, build_passage_id
from app.schemas.title import TitleResponse
from tests.fixtures import PASSAGE


def _request() -> GenerateRequest:
    return GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        choices=5,
        seed=7,
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
        meta={"difficulty": "mid"},
    )


def test_build_passage_id_is_stable_for_same_passage() -> None:
    base = "Since their start in the early 1950s U.S. television sitcoms have charted social conflicts."
    spaced = "  Since   their start in the early 1950s U.S. television sitcoms   have charted social conflicts. "
    cased = "since their START in the EARLY 1950s u.s. television sitcoms have charted social conflicts."

    id_base = build_passage_id(base)
    assert id_base == build_passage_id(spaced)
    assert id_base == build_passage_id(cased)
    assert len(id_base) == 16


def test_saved_problem_record_from_generation() -> None:
    req = _request()
    result = _title_result()
    record = SavedProblemRecord.from_generation(
        problem_type="title",
        attempt_no=2,
        request=req,
        result=result,
        file_path="app/problems/title/abc123456789abcd/attempt_002.json",
    )

    assert record.problem_type == "title"
    assert record.result.type == "title"
    assert record.attempt_no == 2
    assert record.passage_id == build_passage_id(req.passage)


def test_saved_problem_record_rejects_mismatch_type() -> None:
    req = _request()
    result = _title_result()

    with pytest.raises(ValidationError):
        SavedProblemRecord.from_generation(
            problem_type="summary",
            attempt_no=1,
            request=req,
            result=result,
            file_path="app/problems/summary/abc123456789abcd/attempt_001.json",
        )
