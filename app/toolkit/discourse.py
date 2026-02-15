from __future__ import annotations

from typing import Literal


MARKERS = {
    "contrast": ["however", "but", "yet", "nevertheless", "on the contrary"],
    "cause_effect": ["therefore", "thus", "as a result", "consequently"],
    "example": ["for example", "for instance", "such as"],
    "addition": ["moreover", "furthermore", "in addition"],
}


def find_markers(sentence: str) -> list[str]:
    lowered = sentence.lower()
    hits: list[str] = []
    for marker_group in MARKERS.values():
        for marker in marker_group:
            if marker in lowered:
                hits.append(marker)
    return hits


def tag_paragraph_function(
    paragraph: str,
) -> Literal["claim", "example", "contrast", "conclusion", "definition", "expansion"]:
    lowered = paragraph.lower()
    if any(x in lowered for x in MARKERS["contrast"]):
        return "contrast"
    if any(x in lowered for x in MARKERS["cause_effect"]):
        return "conclusion"
    if any(x in lowered for x in MARKERS["example"]):
        return "example"
    if " is " in lowered and " refers to " in lowered:
        return "definition"
    if any(x in lowered for x in ["should", "must", "need to"]):
        return "claim"
    return "expansion"


def score_insertion_fit(given_sentence: str, prev: str, nxt: str) -> float:
    score = 0.0
    gs = given_sentence.lower()
    prev_l = prev.lower()
    next_l = nxt.lower()

    if any(m in gs for m in MARKERS["contrast"]) and any(
        t in prev_l for t in ["problem", "limitation", "challenge", "however", "but"]
    ):
        score += 0.8

    if any(m in gs for m in MARKERS["cause_effect"]) and any(
        t in prev_l for t in ["because", "reason", "due", "cause"]
    ):
        score += 0.8

    for pron in ["this", "that", "these", "those", "they", "it"]:
        if pron in gs and pron in prev_l:
            score += 0.4

    shared_words = set(prev_l.split()) & set(next_l.split()) & set(gs.split())
    score += min(0.8, len(shared_words) * 0.05)
    return score
