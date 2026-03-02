from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.base import Choice, GenerateRequest
from app.schemas.grammar import GrammarResponse
from app.toolkit.labels import choice_labels
from app.toolkit.validators import validate_underlines
from app.toolkit.vocab_grammar_normalize import normalize_vocab_grammar_problem


class GrammarAgent(BaseAgent):
    problem_type = "grammar"
    prompt_name = "grammar"

    def generate(self, request: GenerateRequest) -> GrammarResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=GrammarResponse,
        )
        if llm_problem is not None:
            normalize_vocab_grammar_problem(llm_problem)
            validate_underlines(llm_problem)
            return llm_problem

        topic = analysis.topic or "the argument"
        rendered = (
            f"{topic.title()} [[1]]shows[[/1]] why careful reasoning matters, "
            "and the supporting data [[2]]are[[/2]] consistent across examples. "
            f"Each participant [[3]]have[[/3]] a role in evaluating {topic}, "
            "while researchers [[4]]consider[[/4]] context and the final claim [[5]]remains[[/5]] stable."
        )

        labels = choice_labels(5)
        choices = [Choice(label=label, text=label) for label in labels]
        answer = choices[2]

        question = (
            "다음 중 어법상 틀린 것은?"
            if request.return_korean_stem
            else "Which underlined part is grammatically incorrect?"
        )
        explanation = (
            f"정답 {answer.label}는 주어-동사 수일치 오류이다. "
            "Each participant는 단수이므로 have가 아니라 has가 와야 한다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta["targets"] = [f"{idx}" for idx in range(1, 6)]

        problem = GrammarResponse(
            type=self.problem_type,
            passage=rendered,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        normalize_vocab_grammar_problem(problem)
        validate_underlines(problem)
        return problem
