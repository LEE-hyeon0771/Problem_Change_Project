from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import GenerateRequest
from app.schemas.irrelevant import IrrelevantResponse
from app.toolkit.text import ensure_min_sentences
from app.toolkit.validators import validate_common


class IrrelevantAgent(BaseAgent):
    problem_type = "irrelevant"
    prompt_name = "irrelevant"

    def generate(self, request: GenerateRequest) -> IrrelevantResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=IrrelevantResponse,
        )
        if llm_problem is not None:
            validate_common(llm_problem)
            return llm_problem

        sentences = ensure_min_sentences(passage, min_sentences=6)

        related = sentences[:4]
        topic = analysis.topic or "the central issue"
        irrelevant = (
            f"By contrast, a historical timeline of unrelated inventions does not explain {topic} in this discussion."
        )

        rng = self._rng(request)
        odd_index = rng.randint(0, 4)
        options: list[str] = []
        rel_iter = iter(related)
        for idx in range(5):
            if idx == odd_index:
                options.append(irrelevant)
            else:
                options.append(next(rel_iter))

        choices = self._build_choices(options, request)
        answer = choices[odd_index]

        question = (
            "다음 글의 흐름으로 보아, 주어진 문장들 중 어색한 것은?"
            if request.return_korean_stem
            else "Which sentence is irrelevant to the overall flow?"
        )
        explanation = (
            f"정답 {answer.label} 문장은 일부 어휘는 비슷하지만, 글의 중심 논지 전개를 직접 지지하지 않는다. "
            "나머지 문장은 같은 주제 축에서 원인·근거·결론 흐름을 유지한다."
            if request.explain
            else ""
        )

        problem = IrrelevantResponse(
            type=self.problem_type,
            passage=" ".join(related),
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=self._meta(request, analysis),
        )
        validate_common(problem)
        return problem
