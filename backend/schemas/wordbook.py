from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PartOfSpeech = Literal[
    "noun",
    "verb",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "pronoun",
    "determiner",
    "phrase",
    "idiom",
    "other",
]

POS_KO: dict[str, str] = {
    "noun": "명사",
    "verb": "동사",
    "adjective": "형용사",
    "adverb": "부사",
    "preposition": "전치사",
    "conjunction": "접속사",
    "pronoun": "대명사",
    "determiner": "한정사",
    "phrase": "구",
    "idiom": "숙어",
    "other": "기타",
}


def pos_ko_label(pos: str) -> str:
    return POS_KO.get(pos, POS_KO["other"])


class WordbookRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "passage": (
                    "People often rely on repeated routines because habits reduce cognitive load and free attention "
                    "for difficult tasks. However, habits can hide weak assumptions when people stop reflecting "
                    "on why they act in a certain way. Therefore, good decision making requires stable routines "
                    "and periodic review."
                ),
                "include_phrases": True,
                "max_related": 4,
            }
        }
    )

    passage: str = Field(
        min_length=1,
        description="영어 지문 원문. 보통 60단어 이상을 권장합니다.",
    )
    include_phrases: bool = Field(
        default=True,
        description="숙어/연어(phrase, idiom)도 항목으로 포함할지 여부",
    )
    max_related: int = Field(
        default=4,
        ge=1,
        le=8,
        description="한 뜻당 제시할 동의어/반의어 최대 개수",
    )


class RelatedWord(BaseModel):
    word: str = Field(description="관련 단어(영어)")
    meaning_ko: str = Field(default="", description="관련 단어의 한국어 뜻")
    pos: PartOfSpeech = Field(default="other", description="관련 단어의 품사")
    nuance: str = Field(default="", description="원 단어와의 뉘앙스 차이(선택)")

    @field_validator("word", "meaning_ko", "nuance", mode="before")
    @classmethod
    def blank_when_missing(cls, value: Any) -> Any:
        return "" if value is None else value


class WordSense(BaseModel):
    """한 단어의 뜻 하나. 품사는 뜻마다 따로 붙습니다."""

    pos: PartOfSpeech = Field(description="이 뜻에 해당하는 품사")
    pos_ko: str = Field(default="", description="품사 한국어 표기. 서버가 채웁니다.")
    meaning_ko: str = Field(default="", description="한국어 뜻")
    meaning_en: str = Field(default="", description="영어 정의")
    synonyms: list[RelatedWord] = Field(default_factory=list, description="이 뜻에 대한 동의어")
    antonyms: list[RelatedWord] = Field(default_factory=list, description="이 뜻에 대한 반의어")
    usage_note: str = Field(default="", description="사용 시 주의점(선택)")

    @field_validator("pos_ko", "meaning_ko", "meaning_en", "usage_note", mode="before")
    @classmethod
    def blank_when_missing(cls, value: Any) -> Any:
        return "" if value is None else value


class WordbookEntry(BaseModel):
    headword: str = Field(description="표제어(원형)")
    surface_form: str = Field(default="", description="지문에 실제로 등장한 형태")
    importance: Literal["core", "supporting"] = Field(
        default="core",
        description="core=반드시 외워야 할 핵심어, supporting=보조 어휘",
    )
    cefr: Literal["A1", "A2", "B1", "B2", "C1", "C2", ""] = Field(
        default="",
        description="CEFR 난이도 추정(선택)",
    )
    passage_meaning_ko: str = Field(
        default="",
        description="여러 뜻 중 이 지문에서 실제로 쓰인 뜻",
    )
    example_sentence: str = Field(
        default="",
        description="지문에서 이 단어가 등장한 문장",
    )
    senses: list[WordSense] = Field(default_factory=list, description="뜻 목록(뜻마다 품사 포함)")

    @field_validator("surface_form", "passage_meaning_ko", "example_sentence", mode="before")
    @classmethod
    def blank_when_missing(cls, value: Any) -> Any:
        return "" if value is None else value

    @property
    def covered_words(self) -> list[str]:
        return [word for word in (self.headword, self.surface_form) if word]


class WordbookResponse(BaseModel):
    type: Literal["wordbook"] = Field(default="wordbook", description="응답 유형 식별자")
    passage: str = Field(description="분석에 사용된 지문")
    entries: list[WordbookEntry] = Field(default_factory=list, description="핵심단어 목록")
    meta: dict[str, Any] = Field(default_factory=dict)
