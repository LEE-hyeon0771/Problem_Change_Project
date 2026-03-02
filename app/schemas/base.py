from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "passage": (
                    "People often rely on repeated routines because habits reduce cognitive load and free attention "
                    "for difficult tasks. However, habits can hide weak assumptions when people stop reflecting "
                    "on why they act in a certain way. Therefore, good decision making requires stable routines "
                    "and periodic review."
                ),
                "difficulty": "mid",
                "choices": 5,
                "seed": 123,
                "style": "edu_office",
                "explain": True,
                "return_korean_stem": True,
                "debug": False,
            }
        }
    )

    passage: str = Field(
        min_length=1,
        description="영어 지문 원문. 보통 60단어 이상을 권장합니다.",
    )
    difficulty: Literal["easy", "mid", "hard"] = Field(
        default="mid",
        description="난이도. easy(쉬움), mid(보통), hard(어려움)",
    )
    choices: int = Field(
        default=5,
        ge=5,
        le=5,
        description="선지 개수. 현재 버전은 5로 고정입니다.",
    )
    seed: int | None = Field(
        default=None,
        description="재현성 보조값. 같은 seed일수록 결과가 유사해질 수 있습니다.",
    )
    style: Literal["edu_office"] = Field(
        default="edu_office",
        description="문항 스타일. 현재 edu_office만 지원합니다.",
    )
    explain: bool = Field(
        default=True,
        description="해설 포함 여부",
    )
    return_korean_stem: bool = Field(
        default=True,
        description="문항 지시문을 한국어로 반환할지 여부",
    )
    debug: bool = Field(
        default=False,
        description="디버그 정보(meta.debug) 포함 여부",
    )


class Choice(BaseModel):
    label: str = Field(description="선지 번호 라벨(예: ①, ②)")
    text: str = Field(description="선지 내용")


class ProblemResponse(BaseModel):
    type: str = Field(description="문항 유형 식별자")
    passage: str = Field(description="문항에 사용된 지문(가공본 포함)")
    question: str = Field(description="문항 지시문")
    choices: list[Choice] = Field(description="5개 선지")
    answer: Choice = Field(description="정답 선지")
    explanation: str = Field(description="정답 해설")
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def coerce_choices_and_answer(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        labels = ["①", "②", "③", "④", "⑤"]

        raw_choices = payload.get("choices")
        normalized_choices: list[dict[str, str]] | None = None
        if isinstance(raw_choices, list):
            normalized_choices = []
            for idx, item in enumerate(raw_choices):
                default_label = labels[idx] if idx < len(labels) else str(idx + 1)
                if isinstance(item, Choice):
                    label = str(item.label or default_label)
                    text = str(item.text or "")
                elif isinstance(item, dict):
                    label = str(item.get("label") or default_label)
                    text = str(item.get("text") or "")
                elif hasattr(item, "label") and hasattr(item, "text"):
                    label = str(getattr(item, "label") or default_label)
                    text = str(getattr(item, "text") or "")
                else:
                    label = default_label
                    text = str(item)
                normalized_choices.append({"label": label, "text": text})
            payload["choices"] = normalized_choices

        answer = payload.get("answer")
        if normalized_choices is None:
            return payload

        def _match_choice(token: Any) -> dict[str, str] | None:
            token_str = str(token).strip()
            for choice in normalized_choices:
                if choice["label"] == token_str:
                    return choice
            for choice in normalized_choices:
                if choice["text"] == token_str:
                    return choice
            if token_str.isdigit():
                idx = int(token_str) - 1
                if 0 <= idx < len(normalized_choices):
                    return normalized_choices[idx]
            return None

        if isinstance(answer, str):
            matched = _match_choice(answer)
            if matched is not None:
                payload["answer"] = matched
            return payload

        if isinstance(answer, int):
            idx = answer - 1 if 1 <= answer <= len(normalized_choices) else answer
            if 0 <= idx < len(normalized_choices):
                payload["answer"] = normalized_choices[idx]
            return payload

        if isinstance(answer, Choice):
            matched = _match_choice(answer.label) or _match_choice(answer.text)
            if matched is not None:
                payload["answer"] = matched
            return payload

        if hasattr(answer, "label") and hasattr(answer, "text"):
            matched = _match_choice(getattr(answer, "label")) or _match_choice(getattr(answer, "text"))
            if matched is not None:
                payload["answer"] = matched
            return payload

        if isinstance(answer, dict):
            label = answer.get("label")
            text = answer.get("text")
            matched = None
            if label is not None:
                matched = _match_choice(label)
            if matched is None and text is not None:
                matched = _match_choice(text)
            if matched is not None:
                payload["answer"] = matched
        return payload

