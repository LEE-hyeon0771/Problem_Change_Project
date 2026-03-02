from __future__ import annotations

import logging
import re

from app.agents.base import BaseAgent
from app.core.errors import GenerationError
from app.llm.schema import ImplicitDraft
from app.prompts.loader import render_prompt
from app.schemas.base import Choice, GenerateRequest
from app.schemas.implicit import ImplicitResponse
from app.toolkit.labels import choice_labels
from app.toolkit.text import assert_span_exists, replace_nth, split_sentences
from app.toolkit.validators import validate_common, validate_implicit_from_original

logger = logging.getLogger(__name__)

_IDIOM_PATTERNS = [
    re.compile(r"\blose(?:s|d|ing)? (?:their|his|her|my|our|your) marbles\b", re.I),
    re.compile(r"\bneedle in a haystack\b", re.I),
    re.compile(r"\bturn(?:ing)? lead into gold\b", re.I),
    re.compile(r"\bbreak the ice\b", re.I),
]

_CUE_MEANINGS = [
    ("by contrast", "It signals a contrast with what was stated earlier."),
    ("however", "It signals a contrast with what was stated earlier."),
    ("instead", "It replaces an expected choice with an alternative point."),
    ("therefore", "It marks a conclusion drawn from earlier reasons."),
    ("thus", "It marks a conclusion drawn from earlier reasons."),
    ("as a result", "It points to the consequence of previous conditions."),
    ("in this way", "It means 'by this method' and explains how the result is achieved."),
    ("in other words", "It restates the previous idea in clearer terms."),
]


class ImplicitAgent(BaseAgent):
    problem_type = "implicit"
    prompt_name = "implicit"

    def _normalize_choice_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip()
        for _ in range(2):
            normalized = re.sub(r"^\s*(?:[①②③④⑤]|\(?[1-5]\)?)[\.\):\-]?\s*", "", normalized).strip()
        if not normalized:
            raise GenerationError("Implicit choice text became empty after normalization.")
        return normalized

    def _build_question(self, request: GenerateRequest, underlined_span: str) -> str:
        display_span = re.sub(r"\s+", " ", underlined_span).strip()
        if request.return_korean_stem:
            return f"밑줄 친 부분 '{display_span}'이 의미하는 바로 가장 적절한 것은?"
        return f"Which option best captures the implied meaning of '{display_span}'?"

    def _build_choices(self, texts: list[str]) -> list[Choice]:
        if len(texts) != 5:
            raise GenerationError("Implicit choices must be exactly 5.")
        labels = choice_labels(5)
        return [Choice(label=labels[idx], text=self._normalize_choice_text(texts[idx])) for idx in range(5)]

    def _resolve_answer(self, choices: list[Choice], answer_label: str) -> Choice:
        for choice in choices:
            if choice.label == answer_label:
                return choice
        raise GenerationError("answer_label is not inside choices labels.")

    def _build_passage_with_underline(self, original_passage: str, underlined_span: str, occurrence: int) -> str:
        try:
            assert_span_exists(original_passage, underlined_span)
            marked = replace_nth(
                original_passage,
                underlined_span,
                f"[[1]]{underlined_span}[[/1]]",
                occurrence=occurrence,
            )
        except ValueError as exc:
            raise GenerationError(str(exc)) from exc

        if marked.count("[[1]]") != 1 or marked.count("[[/1]]") != 1:
            raise GenerationError("Implicit passage must include exactly one underlined marker pair.")
        return marked

    def _build_problem_from_draft(
        self,
        *,
        request: GenerateRequest,
        passage: str,
        analysis,
        draft: ImplicitDraft,
    ) -> ImplicitResponse:
        passage_with_marker = self._build_passage_with_underline(
            original_passage=passage,
            underlined_span=draft.underlined_span,
            occurrence=draft.occurrence,
        )

        choices = self._build_choices(list(draft.choices))
        answer = self._resolve_answer(choices, draft.answer_label)
        question = self._build_question(request, draft.underlined_span)
        explanation = draft.explanation if request.explain else ""

        meta = self._meta(request, analysis)
        meta.update(
            {
                "underlined_span": draft.underlined_span,
                "occurrence": draft.occurrence,
                "generation_mode": "llm_span_only",
                "distractor_patterns": [
                    "literal_trap",
                    "partial_meaning",
                    "polarity_flip",
                    "topic_injection",
                ],
            }
        )

        problem = ImplicitResponse(
            type=self.problem_type,
            passage=passage_with_marker,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_implicit_from_original(problem, passage)
        validate_common(problem)
        return problem

    def _try_llm_implicit_generate(self, request: GenerateRequest, passage: str, analysis) -> ImplicitResponse | None:
        if not self._llm_enabled():
            return None

        excluded_spans: list[str] = []
        retry_hint = ""

        for attempt in range(2):
            draft: ImplicitDraft | None = None
            extra_context = {
                "retry_hint": retry_hint,
                "excluded_spans": excluded_spans,
            }
            context = self._prompt_context(
                request=request,
                passage=passage,
                analysis=analysis,
                extra_context=extra_context,
            )

            try:
                prompt = render_prompt(self.prompt_name or "implicit", **context)
                draft_json = self.llm_client.generate_json(prompt=prompt, schema=ImplicitDraft.model_json_schema())
                draft = ImplicitDraft.model_validate(draft_json)
                if draft.underlined_span in excluded_spans:
                    raise GenerationError("LLM reused an excluded underlined_span.")

                problem = self._build_problem_from_draft(
                    request=request,
                    passage=passage,
                    analysis=analysis,
                    draft=draft,
                )
                if not self._run_self_check(problem):
                    raise GenerationError("Implicit item was rejected by self-check.")
                logger.info("LLM span-only implicit generation success.")
                return problem
            except Exception as exc:
                if draft is not None and draft.underlined_span not in excluded_spans:
                    excluded_spans.append(draft.underlined_span)
                retry_hint = (
                    "Previous attempt failed. Re-select underlined_span from the ORIGINAL passage exactly, "
                    "or change occurrence if the span appears multiple times. "
                    f"Failure detail: {exc}"
                )
                logger.warning("LLM span-only implicit attempt %s failed: %s", attempt + 1, exc)

        return None

    def _find_underlined_span(self, passage: str) -> str:
        for pattern in _IDIOM_PATTERNS:
            match = pattern.search(passage)
            if match:
                return match.group(0)

        lower_passage = passage.lower()
        for cue, _ in _CUE_MEANINGS:
            idx = lower_passage.find(cue)
            if idx >= 0:
                return passage[idx : idx + len(cue)]

        sentences = split_sentences(passage)
        target_sentence = sentences[-1] if sentences else passage
        words = list(re.finditer(r"[A-Za-z']+", target_sentence))
        if not words:
            return target_sentence[: min(12, len(target_sentence))].strip() or "the point"

        start_idx = max(0, len(words) // 2 - 2)
        end_idx = min(len(words) - 1, start_idx + 3)
        return target_sentence[words[start_idx].start() : words[end_idx].end()]

    def _meaning_for_span(self, span: str) -> str:
        lower = span.lower()
        for cue, meaning in _CUE_MEANINGS:
            if cue in lower:
                return meaning
        if any(pattern.search(span) for pattern in _IDIOM_PATTERNS):
            return "It conveys a figurative meaning rather than a literal action."
        return "It conveys the writer's implied intention rather than a literal wording."

    def generate(self, request: GenerateRequest) -> ImplicitResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)

        llm_problem = self._try_llm_implicit_generate(request=request, passage=passage, analysis=analysis)
        if llm_problem is not None:
            validate_implicit_from_original(llm_problem, passage)
            return llm_problem

        underlined_span = self._find_underlined_span(passage)
        if underlined_span not in passage:
            underlined_span = passage.split()[0]
        passage_with_marker = self._build_passage_with_underline(passage, underlined_span, occurrence=1)

        correct = self._meaning_for_span(underlined_span)
        texts = [
            correct,
            "It should be interpreted literally, word for word.",
            "It refers only to a minor detail, not the broader implication.",
            "It suggests the opposite stance from the writer's intent.",
            "It simply introduces a new topic unrelated to the argument.",
        ]

        rng = self._rng(request)
        rng.shuffle(texts)
        choices = self._build_choices(texts)
        answer = next(choice for choice in choices if choice.text == correct)

        question = self._build_question(request, underlined_span)
        explanation = (
            f"정답 {answer.label} '{answer.text}'은(는) 밑줄 표현의 문맥적 의미를 반영한다. "
            "오답은 직역에 머물거나, 일부 의미만 취하거나, 글의 논지와 반대/무관한 방향으로 해석한다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta.update(
            {
                "underlined_span": underlined_span,
                "occurrence": 1,
                "generation_mode": "local_fallback",
                "distractor_patterns": [
                    "literal_trap",
                    "partial_meaning",
                    "polarity_flip",
                    "topic_injection",
                ],
            }
        )

        problem = ImplicitResponse(
            type=self.problem_type,
            passage=passage_with_marker,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_implicit_from_original(problem, passage)
        validate_common(problem)
        return problem
