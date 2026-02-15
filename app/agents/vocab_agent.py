from __future__ import annotations

import re

from app.agents.base import BaseAgent
from app.schemas.base import Choice, GenerateRequest
from app.schemas.vocab import VocabResponse
from app.toolkit.labels import choice_labels
from app.toolkit.render import render_underlines
from app.toolkit.validators import validate_underlines
from app.toolkit.vocab_grammar_normalize import normalize_vocab_grammar_problem


class VocabAgent(BaseAgent):
    problem_type = "vocab"
    prompt_name = "vocab"

    def _mismatch_word(self, token: str) -> str:
        lowered = token.lower()
        if lowered in {"increase", "improve", "benefit", "effective", "support"}:
            return "deteriorate"
        if lowered in {"decrease", "limit", "harm", "decline"}:
            return "strengthen"
        return "misalign"

    def generate(self, request: GenerateRequest) -> VocabResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        llm_problem = self._try_llm_generate(
            request=request,
            passage=passage,
            analysis=analysis,
            response_model=VocabResponse,
        )
        if llm_problem is not None:
            normalize_vocab_grammar_problem(llm_problem)
            validate_underlines(llm_problem)
            return llm_problem

        candidates = [w for w in re.findall(r"[A-Za-z']+", passage) if len(w) >= 5]
        if len(candidates) < 5:
            candidates = ["context", "pattern", "process", "support", "outcome"]

        selected = []
        for token in candidates:
            if token not in selected:
                selected.append(token)
            if len(selected) == 5:
                break

        wrong_slot = 3
        wrong_original = selected[wrong_slot - 1]
        wrong_word = self._mismatch_word(wrong_original)

        altered_passage = passage.replace(wrong_original, wrong_word, 1)
        targets = []
        for idx, token in enumerate(selected, start=1):
            marker_token = wrong_word if idx == wrong_slot else token
            targets.append((str(idx), marker_token))
        rendered = render_underlines(altered_passage, targets)

        labels = choice_labels(5)
        choices = [Choice(label=label, text=label) for label in labels]
        answer = choices[wrong_slot - 1]

        question = (
            "다음 밑줄 친 낱말의 쓰임이 적절하지 않은 것은?"
            if request.return_korean_stem
            else "Which underlined word is contextually inappropriate?"
        )
        explanation = (
            f"정답 {answer.label}는 문법 형태는 가능하지만 해당 문맥의 의미 방향과 충돌한다. "
            "같은 자리에는 지문의 주장 흐름과 일치하는 의미의 어휘가 와야 한다."
            if request.explain
            else ""
        )

        meta = self._meta(request, analysis)
        meta["targets"] = [f"{idx}" for idx in range(1, 6)]

        problem = VocabResponse(
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
