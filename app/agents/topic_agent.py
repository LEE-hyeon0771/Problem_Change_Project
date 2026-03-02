from __future__ import annotations

import re

from app.agents.base import BaseAgent
from app.schemas.base import GenerateRequest
from app.schemas.topic import TopicResponse
from app.toolkit.validators import validate_common


class TopicAgent(BaseAgent):
    problem_type = "topic"
    prompt_name = "topic"

    def _topic_phrase(self, raw_topic: str) -> str:
        cleaned = re.sub(r"[^A-Za-z\s'-]+", " ", raw_topic).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned:
            return "the main issue"
        words = cleaned.split()
        return " ".join(words[:6])

    def generate(self, request: GenerateRequest) -> TopicResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=TopicResponse,
        )
        if llm_problem is not None:
            validate_common(llm_problem)
            return llm_problem

        topic = self._topic_phrase(analysis.topic.replace("_", " "))
        correct = f"The role of {topic} in shaping sound decisions"
        distractors = [
            f"A single anecdote about {topic}",
            "Universal advice for every life situation",
            f"Why {topic} should be dismissed as unnecessary",
            "A historical survey of unrelated inventions",
        ]

        texts = [correct, *distractors]
        rng = self._rng(request)
        rng.shuffle(texts)
        choices = self._build_choices(texts, request)
        answer = next(choice for choice in choices if choice.text == correct)

        question = (
            "다음 글의 주제로 가장 적절한 것은?"
            if request.return_korean_stem
            else "Which topic is most appropriate for the passage?"
        )
        explanation = (
            f"정답 {answer.label} '{answer.text}'은(는) 글 전체에서 반복되는 핵심 논점을 가장 넓고 정확하게 묶는다. "
            "오답은 사례 하나로 범위를 좁히거나, 지나치게 일반화하거나, 주장 방향을 반대로 바꿔 제시한다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta["distractor_patterns"] = ["too_narrow", "too_broad", "polarity_flip", "topic_drift"]

        problem = TopicResponse(
            type=self.problem_type,
            passage=passage,
            question=question,
            choices=choices,
            answer=answer,
            explanation=explanation,
            meta=meta,
        )
        validate_common(problem)
        return problem
