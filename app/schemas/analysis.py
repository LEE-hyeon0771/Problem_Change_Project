from __future__ import annotations

from pydantic import BaseModel, Field


class ParagraphAnalysis(BaseModel):
    sentences: list[str] = Field(default_factory=list)
    function: str = "expansion"
    markers: list[str] = Field(default_factory=list)


class CoreferenceCandidate(BaseModel):
    mention: str
    sentence_index: int
    likely_antecedent: str


class PassageAnalysis(BaseModel):
    topic: str = ""
    thesis_candidates: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    paragraphs: list[ParagraphAnalysis] = Field(default_factory=list)
    coreference_candidates: list[CoreferenceCandidate] = Field(default_factory=list)
