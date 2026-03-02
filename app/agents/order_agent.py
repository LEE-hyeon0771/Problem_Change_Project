from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import GenerateRequest
from app.schemas.order import OrderResponse
from app.toolkit.render import render_order_blocks
from app.toolkit.text import ensure_min_sentences
from app.toolkit.validators import validate_order


class OrderAgent(BaseAgent):
    problem_type = "order"
    prompt_name = "order"

    def generate(self, request: GenerateRequest) -> OrderResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=OrderResponse,
        )
        if llm_problem is not None:
            validate_order(llm_problem)
            return llm_problem

        sentences = ensure_min_sentences(passage, min_sentences=7)

        intro = " ".join(sentences[:2])
        block_a = " ".join(sentences[2:4])
        block_b = " ".join(sentences[4:6])
        block_c = " ".join(sentences[6:])

        rendered = render_order_blocks(intro, block_a, block_b, block_c)

        correct = "A-B-C"
        candidates = [correct, "A-C-B", "B-A-C", "B-C-A", "C-A-B"]

        rng = self._rng(request)
        rng.shuffle(candidates)
        choices = self._build_choices(candidates, request)
        answer = next(choice for choice in choices if choice.text == correct)

        question = (
            "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"
            if request.return_korean_stem
            else "What is the most logical order of (A), (B), and (C)?"
        )
        explanation = (
            f"정답 {answer.label} 순서는 문단 기능(개념 제시→근거/예시→정리)에 맞게 자연스럽게 이어진다. "
            "다른 순서는 연결어의 역할이나 지시어의 선행 관계가 끊겨 논리 흐름이 어색해진다."
            if request.explain
            else ""
        )

        problem = OrderResponse(
            type=self.problem_type,
            passage=rendered,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=self._meta(request, analysis),
        )
        validate_order(problem)
        return problem
