from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import GenerateRequest
from app.schemas.reference import ReferenceResponse
from app.toolkit.labels import ref_labels
from app.toolkit.validators import validate_common


class ReferenceAgent(BaseAgent):
    problem_type = "reference"
    prompt_name = "reference"

    def generate(self, request: GenerateRequest) -> ReferenceResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=ReferenceResponse,
        )
        if llm_problem is not None:
            validate_common(llm_problem)
            return llm_problem

        main_target = analysis.keywords[0] if analysis.keywords else "the main strategy"
        alt_target = analysis.keywords[1] if len(analysis.keywords) > 1 else "an alternative perspective"

        rendered = (
            f"{main_target.title()} anchors the argument. (1) It introduces the main claim. "
            f"(2) This approach then guides later examples. (3) They reinforce the same conclusion. "
            f"Meanwhile, {alt_target} appears briefly. (4) It points to a different object. "
            f"Finally, (5) this line returns to the main claim."
        )

        labels = ref_labels(5)
        choices = self._build_choices(labels, request)
        odd = "(4)"
        answer = next(choice for choice in choices if choice.text == odd)

        question = (
            "다음 글에서 (1)~(5) 중 가리키는 대상이 나머지 넷과 다른 것은?"
            if request.return_korean_stem
            else "Which of (1)~(5) refers to a different target?"
        )
        explanation = (
            f"정답 {answer.label}는 본문에서 보조 대상을 가리키며, 나머지 표지는 공통된 주대상을 가리킨다. "
            "따라서 정답만 지칭 대상이 다른 예외에 해당한다."
            if request.explain
            else ""
        )

        problem = ReferenceResponse(
            type=self.problem_type,
            passage=rendered,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=self._meta(request, analysis),
        )
        validate_common(problem)
        return problem
