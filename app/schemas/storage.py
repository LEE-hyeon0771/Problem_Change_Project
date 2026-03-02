from __future__ import annotations

import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.base import GenerateRequest
from app.schemas.blank import BlankResponse
from app.schemas.grammar import GrammarResponse
from app.schemas.implicit import ImplicitResponse
from app.schemas.insertion import InsertionResponse
from app.schemas.irrelevant import IrrelevantResponse
from app.schemas.order import OrderResponse
from app.schemas.reference import ReferenceResponse
from app.schemas.summary import SummaryResponse
from app.schemas.title import TitleResponse
from app.schemas.topic import TopicResponse
from app.schemas.vocab import VocabResponse

_WHITESPACE_RE = re.compile(r"\s+")

ProblemType: TypeAlias = Literal[
    "title",
    "topic",
    "summary",
    "implicit",
    "insertion",
    "order",
    "irrelevant",
    "blank",
    "reference",
    "vocab",
    "grammar",
]

ProblemResult: TypeAlias = (
    TitleResponse
    | TopicResponse
    | SummaryResponse
    | ImplicitResponse
    | InsertionResponse
    | OrderResponse
    | IrrelevantResponse
    | BlankResponse
    | ReferenceResponse
    | VocabResponse
    | GrammarResponse
)


def normalize_passage_for_id(passage: str) -> str:
    return _WHITESPACE_RE.sub(" ", passage).strip().lower()


def build_passage_id(passage: str, *, length: int = 16) -> str:
    if length < 8 or length > 64:
        raise ValueError("length must be between 8 and 64.")

    normalized = normalize_passage_for_id(passage)
    if not normalized:
        raise ValueError("Passage must not be empty after normalization.")

    return sha256(normalized.encode("utf-8")).hexdigest()[:length]


class StorageMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(
        min_length=1,
        pattern=r"^app/problems/[a-z-]+/[a-f0-9]{16}/attempt_[0-9]{3,}\.json$",
        description="문제 JSON 저장 경로",
    )
    db_saved: bool = Field(
        default=False,
        description="DB 저장 성공 여부",
    )
    db_row_id: int | None = Field(
        default=None,
        description="DB 저장 row id",
    )


class SavedProblemRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "problem_uid": "f53e58ac1ce348f3a7c2fef2deca47fe",
                "problem_type": "title",
                "passage_id": "9f13ac82d4b167d1",
                "attempt_no": 2,
                "created_at": "2026-03-02T12:34:56Z",
                "request": {
                    "passage": "Since their start in the early 1950s U.S. television sitcoms ...",
                    "difficulty": "mid",
                    "choices": 5,
                    "seed": 123,
                    "style": "edu_office",
                    "explain": True,
                    "return_korean_stem": True,
                    "debug": False,
                },
                "result": {
                    "type": "title",
                    "passage": "Since their start in the early 1950s U.S. television sitcoms ...",
                    "question": "다음 글의 제목으로 가장 적절한 것은?",
                    "choices": [
                        {"label": "①", "text": "Choice A"},
                        {"label": "②", "text": "Choice B"},
                        {"label": "③", "text": "Choice C"},
                        {"label": "④", "text": "Choice D"},
                        {"label": "⑤", "text": "Choice E"},
                    ],
                    "answer": {"label": "③", "text": "Choice C"},
                    "explanation": "정답 근거 ...",
                    "meta": {"difficulty": "mid", "seed": 123},
                },
                "storage_meta": {
                    "file_path": "app/problems/title/9f13ac82d4b167d1/attempt_002.json",
                    "db_saved": False,
                    "db_row_id": None,
                },
            }
        }
    )

    schema_version: Literal["1.0.0"] = "1.0.0"
    problem_uid: str = Field(
        default_factory=lambda: uuid4().hex,
        pattern=r"^[a-f0-9]{32}$",
        description="문제 저장 레코드 고유 식별자",
    )
    problem_type: ProblemType = Field(description="문제 유형")
    passage_id: str = Field(
        pattern=r"^[a-f0-9]{16}$",
        description="정규화된 지문 해시 식별자",
    )
    attempt_no: int = Field(
        ge=1,
        description="같은 passage_id + problem_type 조합에서의 생성 순번(1부터 시작)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="저장 시각(UTC)",
    )
    request: GenerateRequest = Field(description="문제 생성 요청 원본")
    result: ProblemResult = Field(description="문제 생성 결과")
    storage_meta: StorageMeta = Field(description="저장 메타 정보")

    @model_validator(mode="after")
    def validate_problem_type_consistency(self) -> "SavedProblemRecord":
        if self.result.type != self.problem_type:
            raise ValueError(
                f"problem_type '{self.problem_type}' must match result.type '{self.result.type}'."
            )
        return self

    @classmethod
    def from_generation(
        cls,
        *,
        problem_type: ProblemType,
        attempt_no: int,
        request: GenerateRequest,
        result: ProblemResult,
        file_path: str,
        problem_uid: str | None = None,
    ) -> "SavedProblemRecord":
        payload: dict[str, object] = {
            "problem_type": problem_type,
            "passage_id": build_passage_id(request.passage),
            "attempt_no": attempt_no,
            "request": request,
            "result": result,
            "storage_meta": StorageMeta(file_path=file_path),
        }
        if problem_uid is not None:
            payload["problem_uid"] = problem_uid
        return cls.model_validate(payload)
