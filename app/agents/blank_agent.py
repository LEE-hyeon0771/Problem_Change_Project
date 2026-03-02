from __future__ import annotations

import json
import logging
import re

from app.agents.base import BaseAgent
from app.core.errors import GenerationError
from app.llm.schema import BlankChoiceRepair, BlankDraft, BlankUniquenessCheckResult
from app.prompts.loader import render_prompt
from app.schemas.base import Choice, GenerateRequest
from app.schemas.blank import BlankResponse
from app.toolkit.difficulty import blank_span_type
from app.toolkit.labels import choice_labels
from app.toolkit.render import render_blank
from app.toolkit.text import split_sentences
from app.toolkit.validators import validate_blank, validate_blank_from_original, validate_common

logger = logging.getLogger(__name__)


class BlankAgent(BaseAgent):
    problem_type = "blank"
    prompt_name = "blank"

    def _build_passage_with_blank(self, original_passage: str, blank_span: str, occurrence: int) -> str:
        if not blank_span:
            raise GenerationError("blank_span must not be empty.")
        if occurrence < 1:
            raise GenerationError("occurrence must be >= 1.")

        search_start = 0
        target_idx = -1
        for _ in range(occurrence):
            target_idx = original_passage.find(blank_span, search_start)
            if target_idx < 0:
                raise GenerationError("blank_span occurrence was not found in original passage.")
            search_start = target_idx + len(blank_span)

        if target_idx < 0:
            raise GenerationError("blank_span occurrence was not found in original passage.")

        passage_with_blank = (
            original_passage[:target_idx] + "_____" + original_passage[target_idx + len(blank_span) :]
        )
        if passage_with_blank.count("_____") != 1:
            raise GenerationError("Passage with blank must contain exactly one blank token.")
        return passage_with_blank

    def _build_choices(self, texts: list[str]) -> list[Choice]:
        if len(texts) != 5:
            raise GenerationError("Blank choices must be exactly 5.")
        labels = choice_labels(5)
        return [Choice(label=labels[idx], text=texts[idx]) for idx in range(5)]

    def _resolve_answer(self, choices: list[Choice], answer_label: str) -> Choice:
        for choice in choices:
            if choice.label == answer_label:
                return choice
        raise GenerationError("answer_label is not inside choices labels.")

    def _build_problem_from_draft(
        self,
        *,
        request: GenerateRequest,
        passage: str,
        analysis,
        draft: BlankDraft,
    ) -> BlankResponse:
        passage_with_blank = self._build_passage_with_blank(
            original_passage=passage,
            blank_span=draft.blank_span,
            occurrence=draft.occurrence,
        )

        labels = choice_labels(5)
        answer_idx = labels.index(draft.answer_label)
        choices_texts = list(draft.choices)
        # Ensure exact restorability to original passage.
        choices_texts[answer_idx] = draft.blank_span

        choices = self._build_choices(choices_texts)
        answer = self._resolve_answer(choices, draft.answer_label)

        question = (
            "다음 빈칸에 들어갈 말로 가장 적절한 것은?"
            if request.return_korean_stem
            else "Which option best fits the blank?"
        )

        explanation = draft.explanation if request.explain else ""

        meta = self._meta(request, analysis)
        meta.update(
            {
                "blank_span_type": draft.blank_span_type,
                "blank_role": draft.blank_role,
                "blank_span": draft.blank_span,
                "occurrence": draft.occurrence,
                "generation_mode": "llm_span_only",
            }
        )

        problem = BlankResponse(
            type=self.problem_type,
            passage=passage_with_blank,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_blank_from_original(problem, passage)
        validate_common(problem)
        return problem

    def _run_blank_uniqueness_check(self, problem: BlankResponse, original_passage: str) -> tuple[bool, list[str]]:
        if not self._llm_enabled():
            return True, []

        payload = {
            "original_passage": original_passage,
            "passage_with_blank": problem.passage,
            "choices": [choice.model_dump() for choice in problem.choices],
            "answer": problem.answer.model_dump(),
        }

        prompt = render_prompt("blank_uniqueness_check", check_input_json=json.dumps(payload, ensure_ascii=False))
        try:
            result = self.llm_client.generate_json(
                prompt=prompt,
                schema=BlankUniquenessCheckResult.model_json_schema(),
            )
            checked = BlankUniquenessCheckResult.model_validate(result)
            if not checked.ok:
                logger.warning("Blank uniqueness check failed: %s", checked.reasons)
            return checked.ok, checked.reasons
        except Exception as exc:
            logger.warning("Blank uniqueness check parsing failed: %s", exc)
            # Do not block generation on checker parse failure.
            return True, []

    def _repair_choices_only(
        self,
        *,
        request: GenerateRequest,
        passage: str,
        problem: BlankResponse,
        failure_reasons: list[str],
    ) -> BlankResponse | None:
        if not self._llm_enabled():
            return None

        blank_span = problem.answer.text
        payload = {
            "original_passage": passage,
            "passage_with_blank": problem.passage,
            "blank_span": blank_span,
            "current_choices": [choice.model_dump() for choice in problem.choices],
            "current_answer_label": problem.answer.label,
            "failure_reasons": failure_reasons,
        }

        prompt = render_prompt("blank_choices_repair", repair_input_json=json.dumps(payload, ensure_ascii=False))

        try:
            repaired = self.llm_client.generate_json(prompt=prompt, schema=BlankChoiceRepair.model_json_schema())
            parsed = BlankChoiceRepair.model_validate(repaired)

            labels = choice_labels(5)
            answer_idx = labels.index(parsed.answer_label)
            choices_texts = list(parsed.choices)
            choices_texts[answer_idx] = blank_span

            choices = self._build_choices(choices_texts)
            answer = self._resolve_answer(choices, parsed.answer_label)
            explanation = parsed.explanation if request.explain else ""

            updated = problem.model_copy(update={"choices": choices, "answer": answer, "explanation": explanation})
            validate_blank_from_original(updated, passage)
            validate_common(updated)

            ok, reasons = self._run_blank_uniqueness_check(updated, passage)
            if ok:
                return updated

            logger.warning("Blank choices-only repair failed uniqueness check again: %s", reasons)
            return None
        except Exception as exc:
            logger.warning("Blank choices-only repair failed: %s", exc)
            return None

    def _try_llm_blank_generate(self, request: GenerateRequest, passage: str, analysis) -> BlankResponse | None:
        if not self._llm_enabled():
            return None

        excluded_spans: list[str] = []
        retry_hint = ""

        for attempt in range(2):
            draft: BlankDraft | None = None
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
                prompt = render_prompt(self.prompt_name or "blank", **context)
                draft_json = self.llm_client.generate_json(prompt=prompt, schema=BlankDraft.model_json_schema())
                draft = BlankDraft.model_validate(draft_json)

                if draft.blank_span in excluded_spans:
                    raise GenerationError("LLM reused an excluded blank_span.")

                problem = self._build_problem_from_draft(
                    request=request,
                    passage=passage,
                    analysis=analysis,
                    draft=draft,
                )

                if not self._run_self_check(problem):
                    raise GenerationError("Blank item was rejected by self-check.")

                unique_ok, reasons = self._run_blank_uniqueness_check(problem, passage)
                if not unique_ok:
                    repaired = self._repair_choices_only(
                        request=request,
                        passage=passage,
                        problem=problem,
                        failure_reasons=reasons,
                    )
                    if repaired is None:
                        raise GenerationError("Blank uniqueness failed and choices-only repair also failed.")
                    problem = repaired

                logger.info("LLM span-only blank generation success.")
                return problem
            except Exception as exc:
                if draft is not None and draft.blank_span not in excluded_spans:
                    excluded_spans.append(draft.blank_span)

                retry_hint = (
                    "Previous attempt failed. Re-select blank_span from the ORIGINAL passage exactly, "
                    "or change occurrence if the span appears multiple times. "
                    f"Failure detail: {exc}"
                )
                logger.warning("LLM span-only blank attempt %s failed: %s", attempt + 1, exc)

        return None

    def _pick_span(self, sentence: str, span_type: str) -> str:
        words = re.findall(r"[A-Za-z']+", sentence)
        if not words:
            return "core idea"

        if span_type == "word":
            return max(words, key=len)

        if span_type == "clause":
            lowered = sentence.lower()
            for marker in ["that", "because", "when", "if", "while"]:
                idx = lowered.find(f" {marker} ")
                if idx > 0:
                    return sentence[idx + 1 :].strip(" .,")
            return " ".join(words[: min(8, len(words))])

        pivot = min(len(words) - 1, max(1, len(words) // 2))
        left = max(0, pivot - 2)
        right = min(len(words), pivot + 2)
        return " ".join(words[left:right])

    def _distractors(self, span: str, span_type: str) -> list[str]:
        if span_type == "word":
            return ["uncertainty", "novelty", "rigidity", "distraction"]

        if span_type == "clause":
            return [
                "because short-term comfort always predicts success",
                "that institutional pressure alone resolves every issue",
                "when personal preference replaces evidence",
                "because isolated cases represent the whole trend",
            ]

        return [
            "short-term comfort over reflection",
            "institutional pressure without context",
            "surface similarity with weak evidence",
            "individual anecdotes as general proof",
        ]

    def generate(self, request: GenerateRequest) -> BlankResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)

        llm_problem = self._try_llm_blank_generate(request=request, passage=passage, analysis=analysis)
        if llm_problem is not None:
            validate_blank_from_original(llm_problem, passage)
            return llm_problem

        sentences = split_sentences(passage)

        target_sentence = None
        for sentence in sentences:
            lowered = sentence.lower()
            if any(marker in lowered for marker in ["therefore", "thus", "overall", "however", "should"]):
                target_sentence = sentence
                break
        if target_sentence is None:
            target_sentence = sentences[min(len(sentences) - 1, max(0, len(sentences) // 2))]

        span_type = blank_span_type(request.difficulty)
        answer_text = self._pick_span(target_sentence, span_type)
        blanked = render_blank(passage, answer_text)
        if blanked == passage:
            answer_text = " ".join(target_sentence.split()[:3])
            blanked = render_blank(passage, answer_text)

        choices_text = [answer_text, *self._distractors(answer_text, span_type)]
        rng = self._rng(request)
        rng.shuffle(choices_text)
        choices = self._build_choices(choices_text)
        answer = next(choice for choice in choices if choice.text == answer_text)

        question = (
            "다음 빈칸에 들어갈 말로 가장 적절한 것은?"
            if request.return_korean_stem
            else "Which option best fits the blank?"
        )
        explanation = (
            f"정답 {answer.label} '{answer.text}'은(는) 빈칸 앞뒤의 핵심 논리와 가장 정확히 연결된다. "
            "다른 선택지는 주제는 비슷해 보여도 의미 방향(원인-결과, 찬반)이나 적용 범위가 어긋난다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta["blank_span_type"] = span_type
        meta["generation_mode"] = "local_fallback"

        problem = BlankResponse(
            type=self.problem_type,
            passage=blanked,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_blank_from_original(problem, passage)
        validate_blank(problem)
        return problem
