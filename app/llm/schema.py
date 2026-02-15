from typing import Literal

from pydantic import BaseModel, Field


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
