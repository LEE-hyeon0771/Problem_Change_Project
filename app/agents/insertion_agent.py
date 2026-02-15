from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import Choice, GenerateRequest
from app.schemas.insertion import InsertionResponse
from app.toolkit.labels import choice_labels
from app.toolkit.render import render_insertion_slots
from app.toolkit.text import ensure_min_sentences
from app.toolkit.validators import validate_insertion


class InsertionAgent(BaseAgent):
    problem_type = "insertion"
    prompt_name = "insertion"

    def generate(self, request: GenerateRequest) -> InsertionResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=InsertionResponse,
        )
        if llm_problem is not None:
            validate_insertion(llm_problem)
            return llm_problem

        sentences = ensure_min_sentences(passage, min_sentences=7)

        marker_idx = None
        for idx, sentence in enumerate(sentences[1:-1], start=1):
            lowered = sentence.lower()
            if any(m in lowered for m in ["however", "therefore", "for example", "this", "these", "they"]):
                marker_idx = idx
                break
        if marker_idx is None:
            marker_idx = len(sentences) // 2

        given_sentence = sentences[marker_idx]
        remaining = sentences[:marker_idx] + sentences[marker_idx + 1 :]

        boundaries = list(range(1, len(remaining)))
        correct_boundary = marker_idx
        if correct_boundary not in boundaries:
            correct_boundary = boundaries[len(boundaries) // 2]

        others = [b for b in boundaries if b != correct_boundary]
        others_sorted = sorted(others, key=lambda b: (abs(b - correct_boundary), b))
        selected_boundaries = sorted([correct_boundary, *others_sorted[:4]])
        if len(selected_boundaries) < 5:
            selected_boundaries = boundaries[:5]
            if correct_boundary not in selected_boundaries:
                selected_boundaries[-1] = correct_boundary
                selected_boundaries = sorted(selected_boundaries)

        rendered_passage = render_insertion_slots(remaining, selected_boundaries)

        labels = choice_labels(5)
        choices = [Choice(label=label, text=label) for label in labels]
        answer_position = selected_boundaries.index(correct_boundary) + 1
        answer = choices[answer_position - 1]

        question = (
            "주어진 문장이 들어가기에 가장 적절한 곳을 고르시오."
            if request.return_korean_stem
            else "Choose the most suitable position for the given sentence."
        )
        explanation = (
            f"정답 {answer.label} 위치에서만 주어진 문장의 연결어 기능과 지시어의 선행 정보가 자연스럽게 이어진다. "
            "다른 위치에 넣으면 문맥 전환 순서가 어긋나거나, 지시 대상이 불분명해진다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta["given_sentence"] = given_sentence
        meta["answer_position"] = answer_position

        problem = InsertionResponse(
            type=self.problem_type,
            passage=rendered_passage,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_insertion(problem)
        return problem
