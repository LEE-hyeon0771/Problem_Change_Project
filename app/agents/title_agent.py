from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import GenerateRequest
from app.schemas.title import TitleResponse
from app.toolkit.validators import validate_common


class TitleAgent(BaseAgent):
    problem_type = "title"
    prompt_name = "title"

    def generate(self, request: GenerateRequest) -> TitleResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=TitleResponse,
        )
        if llm_problem is not None:
            validate_common(llm_problem)
            return llm_problem

        topic = analysis.topic.replace("_", " ").strip() or "the central idea"
        thesis = analysis.thesis_candidates[0] if analysis.thesis_candidates else "The passage argues for balanced judgment."
        thesis_hint = " ".join(thesis.split()[:5]).strip(".,")

        correct = f"Why {topic.title()} Requires Balanced Action"
        distractors = [
            f"A Minor Detail About {topic.title()}",
            f"Everything About Human Progress",
            f"Why {topic.title()} Should Be Ignored",
            f"Historical Facts Unrelated to {thesis_hint}",
        ]

        texts = [correct, *distractors]
        rng = self._rng(request)
        rng.shuffle(texts)
        choices = self._build_choices(texts, request)
        answer = next(choice for choice in choices if choice.text == correct)

        question = (
            "다음 글의 제목으로 가장 적절한 것은?"
            if request.return_korean_stem
            else "Which title is most appropriate for the passage?"
        )
        explanation = (
            f"정답 {answer.label} '{answer.text}'은(는) 글의 핵심 주장과 글 전체의 범위를 함께 반영한다. "
            "오답은 세부 사례에만 집중하거나, 주장 방향을 뒤집거나, 지문과 다른 일반론으로 벗어난다."
            if request.explain
            else ""
        )

        problem = TitleResponse(
            type=self.problem_type,
            passage=passage,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=self._meta(request, analysis),
        )
        validate_common(problem)
        return problem
