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

    def to_prompt_payload(self) -> dict:
        """프롬프트에 실어 보낼 형태.

        `paragraphs[].sentences` 는 지문을 문장 단위로 쪼개 담고 있어서,
        이어붙이면 `$passage` 로 이미 보낸 원문과 **글자 단위로 동일**합니다.
        같은 내용을 두 번 보내는 셈이라 프롬프트에서는 제외합니다.
        (143단어 지문 기준 호출당 약 233토큰 절감)

        `function` 과 `markers` 는 grammar/order/reference/vocab 프롬프트가 참조하므로
        반드시 남겨야 합니다. `paragraphs` 를 통째로 빼지 마세요.

        문장 목록이 실제로 필요한 에이전트는 `extra_context` 로 따로 넘기세요.
        """
        payload = self.model_dump()
        for paragraph in payload["paragraphs"]:
            paragraph.pop("sentences", None)
        return payload
