from __future__ import annotations


def blank_span_type(difficulty: str) -> str:
    mapping = {"easy": "word", "mid": "phrase", "hard": "clause"}
    return mapping.get(difficulty, "phrase")
