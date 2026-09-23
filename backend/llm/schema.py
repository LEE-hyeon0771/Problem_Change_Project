from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.wordbook import WordbookEntry


class SelfCheckResult(BaseModel):
    ok: bool
    reasons: list[str] = Field(default_factory=list)
    suggested_fix: str = ""


class BlankDraft(BaseModel):
    blank_span: str = Field(min_length=1)
    occurrence: int = Field(default=1, ge=1)
    blank_span_type: Literal["word", "phrase", "clause"]
    blank_role: Literal["thesis", "contrast_pivot", "causal_conclusion", "generalization"]
    choices: list[str] = Field(min_length=5, max_length=5)
    answer_label: Literal["①", "②", "③", "④", "⑤"]
    explanation: str = Field(min_length=1)


class BlankUniquenessCheckResult(BaseModel):
    ok: bool
    reasons: list[str] = Field(default_factory=list)


class BlankChoiceRepair(BaseModel):
    choices: list[str] = Field(min_length=5, max_length=5)
    answer_label: Literal["①", "②", "③", "④", "⑤"]
    explanation: str = Field(min_length=1)


class ImplicitDraft(BaseModel):
    underlined_span: str = Field(min_length=1)
    occurrence: int = Field(default=1, ge=1)
    choices: list[str] = Field(min_length=5, max_length=5)
    answer_label: Literal["①", "②", "③", "④", "⑤"]
    explanation: str = Field(min_length=1)


class WordbookDraft(BaseModel):
    """지문을 그대로 되돌려받지 않도록 항목만 받는 단어장 초안."""

    entries: list[WordbookEntry] = Field(default_factory=list)


class SynonymSwapItem(BaseModel):
    original: str = Field(description="지문에서 그대로 복사한 원래 단어")
    replacement: str = Field(description="바꿔 넣을 동의어")
    note: str = Field(default="", description="이 교체가 안전한 이유(한국어)")


class SynonymSwapDraft(BaseModel):
    """지문 동의어 교체 제안. 서버가 다시 검증한 뒤 적용합니다."""

    swaps: list[SynonymSwapItem] = Field(default_factory=list)
