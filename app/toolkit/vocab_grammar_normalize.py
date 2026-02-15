from __future__ import annotations

import re

from app.schemas.base import ProblemResponse


_CIRCLED_LABELS = ["①", "②", "③", "④", "⑤"]
_CIRCLED_TO_INDEX = {label: str(idx) for idx, label in enumerate(_CIRCLED_LABELS, start=1)}
_ALPHA_TO_INDEX = {chr(96 + idx): str(idx) for idx in range(1, 6)}

_OPEN_MARKER_RE = re.compile(r"\[\[\s*([1-5a-eA-E])\s*\]\]")
_CLOSE_MARKER_RE = re.compile(r"\[\[\s*/\s*([1-5a-eA-E])\s*\]\]")
_HTML_UNDERLINE_RE = re.compile(r"(\([1-5a-eA-E]\)|[①②③④⑤])\s*<u\b[^>]*>([\s\S]*?)</u>", flags=re.IGNORECASE)
_PLAIN_MARKER_RE = re.compile(r"(\([1-5a-eA-E]\)|[①②③④⑤])\s*([A-Za-z][A-Za-z'’-]*)")
_HTML_TAG_RE = re.compile(r"</?u\b[^>]*>", flags=re.IGNORECASE)


def _marker_to_index(raw: str) -> str | None:
    marker = str(raw).strip()
    if marker.startswith("(") and marker.endswith(")") and len(marker) == 3:
        marker = marker[1:-1]

    lowered = marker.lower()
    if lowered in _ALPHA_TO_INDEX:
        return _ALPHA_TO_INDEX[lowered]
    if marker in _CIRCLED_TO_INDEX:
        return _CIRCLED_TO_INDEX[marker]
    if marker in {"1", "2", "3", "4", "5"}:
        return marker
    return None


def _to_circled_label(raw: str) -> str:
    index = _marker_to_index(raw)
    if index is None:
        return str(raw)
    return _CIRCLED_LABELS[int(index) - 1]


def _replace_open_marker(match: re.Match[str]) -> str:
    marker = match.group(1)
    index = _marker_to_index(marker)
    if index is None:
        return match.group(0)
    return f"[[{index}]]"


def _replace_close_marker(match: re.Match[str]) -> str:
    marker = match.group(1)
    index = _marker_to_index(marker)
    if index is None:
        return match.group(0)
    return f"[[/{index}]]"


def _replace_html_underline(match: re.Match[str]) -> str:
    marker, token = match.group(1), match.group(2)
    index = _marker_to_index(marker)
    if index is None:
        return match.group(0)
    return f"[[{index}]]{token.strip()}[[/{index}]]"


def _replace_plain_marker(match: re.Match[str]) -> str:
    marker, token = match.group(1), match.group(2)
    index = _marker_to_index(marker)
    if index is None:
        return match.group(0)
    return f"[[{index}]]{token}[[/{index}]]"


def normalize_vocab_grammar_problem(problem: ProblemResponse) -> ProblemResponse:
    normalized_passage = _OPEN_MARKER_RE.sub(_replace_open_marker, problem.passage)
    normalized_passage = _CLOSE_MARKER_RE.sub(_replace_close_marker, normalized_passage)
    normalized_passage = _HTML_UNDERLINE_RE.sub(_replace_html_underline, normalized_passage)
    normalized_passage = _PLAIN_MARKER_RE.sub(_replace_plain_marker, normalized_passage)
    normalized_passage = _HTML_TAG_RE.sub("", normalized_passage)
    problem.passage = normalized_passage

    for choice in problem.choices:
        choice.label = _to_circled_label(choice.label)

    problem.answer.label = _to_circled_label(problem.answer.label)

    answer_by_label = {choice.label: choice for choice in problem.choices}
    matched = answer_by_label.get(problem.answer.label)
    if matched is None:
        answer_text = problem.answer.text.strip()
        for choice in problem.choices:
            if choice.text.strip() == answer_text:
                matched = choice
                break
    if matched is not None:
        problem.answer = matched

    return problem
