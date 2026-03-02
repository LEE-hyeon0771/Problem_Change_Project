from __future__ import annotations

import logging
import re

from app.agents.base import BaseAgent
from app.core.errors import GenerationError
from app.schemas.base import GenerateRequest
from app.schemas.summary import SummaryResponse
from app.toolkit.text import split_sentences
from app.toolkit.validators import validate_summary

logger = logging.getLogger(__name__)

_PAIR_RE = re.compile(r"^\(\s*(.+?)\s*,\s*(.+?)\s*\)$", re.S)
_A_MARKER_RE = re.compile(r"^\(?\s*A\s*\)?\s*[:\-.)]?\s*", re.I)
_B_MARKER_RE = re.compile(r"^\(?\s*B\s*\)?\s*[:\-.)]?\s*", re.I)
_SUMMARY_HEADER_PATTERNS = [
    re.compile(r"\[\s*(summary(?:\s*sentence)?|요약문|요약)\s*\]\s*", re.I),
    re.compile(r"(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*[:：]\s*", re.I),
    re.compile(r"(?:^|\n)\s*(summary(?:\s*sentence)?|요약문|요약)\s*\n", re.I),
]
_SUMMARY_DIVIDER_RE = re.compile(r"(?:^|\n)\s*[↓↘↙↗↖→➜➡]+\s*|\s+[↓↘↙↗↖→➜➡]+\s*")
_GENERIC_A_TOKENS = {
    "more",
    "most",
    "less",
    "many",
    "much",
    "some",
    "well",
    "also",
    "such",
    "other",
    "others",
    "those",
    "these",
    "their",
    "there",
    "about",
}


class SummaryAgent(BaseAgent):
    problem_type = "summary"
    prompt_name = "summary"

    def _has_ab_blanks(self, text: str) -> bool:
        return bool(re.search(r"\(\s*A\s*\)", text, flags=re.I) and re.search(r"\(\s*B\s*\)", text, flags=re.I))

    def _sentence_key(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def _extract_summary_sentence(self, passage_text: str, source_passage: str = "") -> str:
        source = str(passage_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not source:
            return ""

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

        source = re.sub(r"\s+", " ", source).strip()

        # Remove duplicated leading source sentences when LLM echoes the original passage.
        if source_passage.strip():
            source_sentence_keys = {self._sentence_key(sentence) for sentence in split_sentences(source_passage)}
            summary_sentences = split_sentences(source)
            while len(summary_sentences) > 1 and self._sentence_key(summary_sentences[0]) in source_sentence_keys:
                summary_sentences.pop(0)
            if summary_sentences:
                source = " ".join(summary_sentences).strip()

        # Keep the final sentence containing both blanks as the target summary sentence.
        sentences_with_blanks = [sentence for sentence in split_sentences(source) if self._has_ab_blanks(sentence)]
        if sentences_with_blanks:
            source = sentences_with_blanks[-1].strip()

        return source

    def _compose_display_passage(self, source_passage: str, summary_sentence: str) -> str:
        body = source_passage.strip()
        summary = summary_sentence.strip()
        if not summary:
            return body
        return f"{body}\n\n[Summary Sentence]\n{summary}"

    def _strip_marker(self, text: str, marker: str) -> str:
        pattern = _A_MARKER_RE if marker.upper() == "A" else _B_MARKER_RE
        return pattern.sub("", text.strip()).strip(" \t\n,;/|")

    def _normalize_pair_text(self, text: str) -> str | None:
        original = str(text or "").strip()
        raw = re.sub(r"\s+", " ", original).strip()
        if not raw:
            return None

        direct = _PAIR_RE.match(raw)
        if direct:
            left = self._strip_marker(direct.group(1), "A")
            right = self._strip_marker(direct.group(2), "B")
            if left and right:
                return f"({left}, {right})"
            return None

        labeled = re.search(r"\(\s*A\s*\)\s*(.+?)\s*\(\s*B\s*\)\s*(.+)$", raw, flags=re.I)
        if labeled:
            left = self._strip_marker(labeled.group(1), "A")
            right = self._strip_marker(labeled.group(2), "B")
            if left and right:
                return f"({left}, {right})"

        split_two = re.split(r"\s*[,/;|]\s*", raw, maxsplit=1)
        if len(split_two) == 2:
            left = self._strip_marker(split_two[0], "A")
            right = self._strip_marker(split_two[1], "B")
            if left and right:
                return f"({left}, {right})"

        lines = [line.strip() for line in original.splitlines() if line.strip()]
        if len(lines) >= 2:
            left = self._strip_marker(lines[0], "A")
            right = self._strip_marker(" ".join(lines[1:]), "B")
            if left and right:
                return f"({left}, {right})"

        return None

    def _normalize_llm_problem(self, problem: SummaryResponse) -> SummaryResponse:
        normalized_choices = []
        for choice in problem.choices:
            normalized_text = self._normalize_pair_text(choice.text)
            if normalized_text is None:
                return problem
            normalized_choices.append(choice.model_copy(update={"text": normalized_text}))

        normalized_answer = next((choice for choice in normalized_choices if choice.label == problem.answer.label), None)
        if normalized_answer is None:
            answer_text = self._normalize_pair_text(problem.answer.text)
            if answer_text is not None:
                normalized_answer = next((choice for choice in normalized_choices if choice.text == answer_text), None)
        if normalized_answer is None:
            return problem

        return problem.model_copy(update={"choices": normalized_choices, "answer": normalized_answer})

    def generate(self, request: GenerateRequest) -> SummaryResponse:
        source_passage = self.preprocess(request.passage)
        analysis = self.analyze(source_passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=source_passage,
            analysis=analysis,
            response_model=SummaryResponse,
        )
        if llm_problem is not None:
            normalized = self._normalize_llm_problem(llm_problem)
            summary_sentence = self._extract_summary_sentence(normalized.passage, source_passage=source_passage)
            if summary_sentence:
                normalized = normalized.model_copy(
                    update={"passage": self._compose_display_passage(source_passage, summary_sentence)}
                )
            try:
                validate_summary(normalized)
                return normalized
            except GenerationError as exc:
                logger.warning("Invalid LLM summary output; falling back to template generator: %s", exc)

        noun_candidates = [kw for kw in analysis.keywords if kw.lower() not in _GENERIC_A_TOKENS]
        nouns = noun_candidates[:3] or ["behavior", "change", "context"]
        a_correct = nouns[0]
        b_correct = "supports long-term consistency"

        summary_line = (
            "The passage explains that (A) shapes decisions and ultimately (B) in daily practice."
        )

        correct = f"({a_correct}, {b_correct})"
        pairs = [
            correct,
            f"({a_correct}, weakens long-term consistency)",
            f"(surface trends, {b_correct})",
            "(institutional pressure, personal mood swings)",
            "(short-term comfort, blocks reflective judgment)",
        ]

        rng = self._rng(request)
        rng.shuffle(pairs)
        choices = self._build_choices(pairs, request)
        answer = next(choice for choice in choices if choice.text == correct)

        question = (
            "다음 요약문의 빈칸 (A), (B)에 들어갈 말로 가장 적절한 것은?"
            if request.return_korean_stem
            else "Which pair best completes (A) and (B)?"
        )
        explanation = (
            f"정답 {answer.label} '{answer.text}'은(는) (A)에 들어갈 핵심 대상과 (B)에 들어갈 결론 방향을 동시에 맞춘다. "
            "오답은 대상은 맞아도 결론이 반대이거나, 결론은 비슷해도 지문의 중심 대상에서 벗어난다."
            if request.explain
            else ""
        )

        problem = SummaryResponse(
            type=self.problem_type,
            passage=self._compose_display_passage(source_passage, summary_line),
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=self._meta(request, analysis),
        )
        validate_summary(problem)
        return problem
