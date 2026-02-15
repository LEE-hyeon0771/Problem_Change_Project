from __future__ import annotations

import re

from app.core.errors import GenerationError
from app.schemas.base import ProblemResponse

_ORDER_PERM_RE = re.compile(r"^\(?\s*([ABC])\s*\)?\s*-\s*\(?\s*([ABC])\s*\)?\s*-\s*\(?\s*([ABC])\s*\)?$", re.I)
_SUMMARY_PAIR_RE = re.compile(r"^\(\s*.+\s*,\s*.+\s*\)$")
_IMPLICIT_MARKER_RE = re.compile(r"\[\[1\]\]([\s\S]*?)\[\[/1\]\]")
_SUMMARY_HEADER_PATTERNS = [
    re.compile(r"\[\s*(summary(?:\s*sentence)?|요약문|요약)\s*\]\s*", re.I),
    re.compile(r"(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*[:：]\s*", re.I),
    re.compile(r"(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*\n", re.I),
]
_SUMMARY_DIVIDER_RE = re.compile(r"(?:^|\n)\s*[↓↘↙↗↖→➜➡]+\s*|\s+[↓↘↙↗↖→➜➡]+\s*")
_CIRCLED_SLOT_TO_INDEX = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}


def _normalize_order_perm(value: str) -> str | None:
    match = _ORDER_PERM_RE.match(value.strip())
    if not match:
        return None
    tokens = [token.upper() for token in match.groups()]
    if len(set(tokens)) != 3:
        return None
    return "-".join(tokens)


def _slot_to_index(value: str) -> int | None:
    token = value.strip()
    if token in _CIRCLED_SLOT_TO_INDEX:
        return _CIRCLED_SLOT_TO_INDEX[token]

    match = re.match(r"^\(?\s*([1-5])\s*\)?$", token)
    if match:
        return int(match.group(1))

    return None


def _summary_target_text(passage: str) -> str:
    source = passage.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not source:
        return source

    for pattern in _SUMMARY_HEADER_PATTERNS:
        match = pattern.search(source)
        if not match:
            continue
        trailing = source[match.end() :].strip()
        if trailing:
            source = trailing
        break

    divider = _SUMMARY_DIVIDER_RE.search(source)
    if divider:
        trailing = source[divider.end() :].strip()
        if trailing:
            source = trailing
    return source


def validate_common(problem: ProblemResponse) -> None:
    if not problem.passage.strip() or not problem.question.strip():
        raise GenerationError("Passage or question is empty.")

    if len(problem.choices) != 5:
        raise GenerationError("Choices must be exactly 5.")

    labels = {choice.label for choice in problem.choices}
    if problem.answer.label not in labels:
        raise GenerationError("Answer label is not inside choices.")


def validate_blank(problem: ProblemResponse) -> None:
    validate_common(problem)
    if problem.passage.count("_____") != 1:
        raise GenerationError("Blank passage must include exactly one blank token.")


def validate_blank_from_original(problem: ProblemResponse, original_passage: str) -> None:
    validate_blank(problem)
    restored = problem.passage.replace("_____", problem.answer.text, 1)
    if restored != original_passage:
        raise GenerationError("Blank passage must be reconstructable to the original passage using the answer text.")


def validate_insertion(problem: ProblemResponse) -> None:
    validate_common(problem)
    answer_position = problem.meta.get("answer_position")
    if answer_position not in {1, 2, 3, 4, 5}:
        raise GenerationError("Insertion answer_position should be in 1..5.")

    has_circled_slots = all(problem.passage.count(marker) == 1 for marker in _CIRCLED_SLOT_TO_INDEX)
    has_parenthesized_slots = all(
        len(re.findall(rf"\(\s*{idx}\s*\)", problem.passage)) == 1 for idx in range(1, 6)
    )
    if not (has_circled_slots or has_parenthesized_slots):
        raise GenerationError("Insertion passage must include exactly five slot markers (①~⑤ or (1)~(5)).")

    slot_indices = [_slot_to_index(choice.text) for choice in problem.choices]
    if any(idx is None for idx in slot_indices):
        raise GenerationError("Insertion choice text must be a slot label (①~⑤ or (1)~(5)).")
    if set(slot_indices) != {1, 2, 3, 4, 5}:
        raise GenerationError("Insertion choices must cover all five slot positions exactly once.")

    answer_index = _slot_to_index(problem.answer.text)
    if answer_index is None:
        raise GenerationError("Insertion answer text must be a valid slot label.")
    if answer_index != answer_position:
        raise GenerationError("Insertion answer_position must match answer slot label.")


def validate_order(problem: ProblemResponse) -> None:
    validate_common(problem)
    for marker in ("(A)", "(B)", "(C)"):
        if marker not in problem.passage:
            raise GenerationError("Order passage must include labeled blocks (A), (B), and (C).")

    normalized = []
    for choice in problem.choices:
        perm = _normalize_order_perm(choice.text)
        if perm is None:
            raise GenerationError("Order choices must be valid A/B/C permutations like '(A)-(C)-(B)'.")
        normalized.append(perm)

    if len(set(normalized)) != 5:
        raise GenerationError("Order choices must be unique permutations.")


def validate_summary(problem: ProblemResponse) -> None:
    validate_common(problem)
    target = _summary_target_text(problem.passage)

    if len(re.findall(r"\(\s*A\s*\)", target, flags=re.I)) != 1:
        raise GenerationError("Summary passage must include exactly one (A) blank.")
    if len(re.findall(r"\(\s*B\s*\)", target, flags=re.I)) != 1:
        raise GenerationError("Summary passage must include exactly one (B) blank.")

    choice_texts = []
    for choice in problem.choices:
        text = choice.text.strip()
        if not _SUMMARY_PAIR_RE.match(text):
            raise GenerationError("Summary choices must be pair format like '(termA, termB)'.")
        choice_texts.append(text)

    if len(set(choice_texts)) != 5:
        raise GenerationError("Summary choices must be unique.")


def validate_implicit(problem: ProblemResponse) -> None:
    validate_common(problem)
    matches = list(_IMPLICIT_MARKER_RE.finditer(problem.passage))
    if len(matches) != 1:
        raise GenerationError("Implicit passage must include exactly one [[1]]...[[/1]] marker.")
    if not matches[0].group(1).strip():
        raise GenerationError("Implicit underlined span must not be empty.")


def validate_implicit_from_original(problem: ProblemResponse, original_passage: str) -> None:
    validate_implicit(problem)
    match = _IMPLICIT_MARKER_RE.search(problem.passage)
    if match is None:
        raise GenerationError("Implicit marker is missing.")
    restored = problem.passage[: match.start()] + match.group(1) + problem.passage[match.end() :]
    if restored != original_passage:
        raise GenerationError("Implicit passage must be reconstructable to the original passage using marker removal.")


def validate_underlines(problem: ProblemResponse) -> None:
    validate_common(problem)
    for i in range(1, 6):
        marker = f"[[{i}]]"
        if marker not in problem.passage:
            raise GenerationError("Underlined target markers are missing.")
