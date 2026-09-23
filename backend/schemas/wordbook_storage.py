from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.storage import build_passage_id
from backend.schemas.wordbook import WordbookRequest, WordbookResponse


class WordbookStorageMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(
        min_length=1,
        pattern=r"^backend/wordbooks/[a-f0-9]{16}/attempt_[0-9]{3,}\.json$",
        description="단어장 JSON 저장 경로",
    )


class SavedWordbookRecord(BaseModel):
    """"사용" 버튼으로 개인DB에 보관한 단어장 1건."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    wordbook_uid: str = Field(
        default_factory=lambda: uuid4().hex,
        pattern=r"^[a-f0-9]{32}$",
        description="단어장 저장 레코드 고유 식별자",
    )
    title: str = Field(
        default="",
        max_length=200,
        description="목록에 표시할 제목. 비우면 지문 앞부분으로 자동 생성합니다.",
    )
    passage_id: str = Field(
        pattern=r"^[a-f0-9]{16}$",
        description="정규화된 지문 해시 식별자",
    )
    attempt_no: int = Field(ge=1, description="같은 지문에서의 저장 순번(1부터)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_count: int = Field(default=0, ge=0, description="정리된 단어 수")
    request: WordbookRequest = Field(description="단어장 생성 요청 원본")
    result: WordbookResponse = Field(description="단어장 생성 결과")
    storage_meta: WordbookStorageMeta = Field(description="저장 메타 정보")

    @classmethod
    def from_generation(
        cls,
        *,
        attempt_no: int,
        request: WordbookRequest,
        result: WordbookResponse,
        file_path: str,
        title: str = "",
        wordbook_uid: str | None = None,
    ) -> "SavedWordbookRecord":
        payload: dict[str, object] = {
            "title": (title or default_wordbook_title(result.passage)).strip(),
            "passage_id": build_passage_id(request.passage),
            "attempt_no": attempt_no,
            "entry_count": len(result.entries),
            "request": request,
            "result": result,
            "storage_meta": WordbookStorageMeta(file_path=file_path),
        }
        if wordbook_uid is not None:
            payload["wordbook_uid"] = wordbook_uid
        return cls.model_validate(payload)


def default_wordbook_title(passage: str, *, max_words: int = 8) -> str:
    """제목을 안 주면 지문 앞부분으로 만듭니다."""
    words = (passage or "").split()
    if not words:
        return "제목 없는 단어장"
    title = " ".join(words[:max_words])
    return f"{title}..." if len(words) > max_words else title


class SaveWordbookRequest(BaseModel):
    """프론트가 "사용"을 눌렀을 때 보내는 저장 요청."""

    title: str = Field(default="", max_length=200, description="사용자가 지정한 제목(선택)")
    request: WordbookRequest = Field(description="단어장을 만들 때 사용한 요청")
    result: WordbookResponse = Field(description="화면에서 확인한 단어장 결과")


class SaveProblemRequest(BaseModel):
    """프론트가 "사용"을 눌렀을 때 보내는 문항 저장 요청.

    `result`는 런타임에 유형별 응답으로 검증합니다(`backend/main.py`).
    """

    model_config = ConfigDict(extra="forbid")

    request: dict = Field(description="문항을 만들 때 사용한 GenerateRequest 원본")
    result: dict = Field(description="화면에서 확인한 문항 결과")
