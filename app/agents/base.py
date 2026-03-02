from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from abc import ABC, abstractmethod
from typing import Any, Sequence, TypeVar

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import InputValidationError
from app.llm.client import LLMClient
from app.llm.schema import SelfCheckResult
from app.prompts.loader import render_prompt
from app.schemas.analysis import CoreferenceCandidate, ParagraphAnalysis, PassageAnalysis
from app.schemas.base import Choice, GenerateRequest
from app.toolkit.discourse import find_markers, tag_paragraph_function
from app.toolkit.labels import choice_labels
from app.toolkit.text import (
    normalize_text,
    split_paragraphs,
    split_sentences,
    truncate_if_too_long,
    word_count,
)

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "to",
    "of",
    "in",
    "on",
    "for",
    "by",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "as",
    "it",
    "this",
    "that",
    "these",
    "those",
    "from",
    "at",
    "into",
    "than",
    "their",
    "they",
    "we",
    "you",
    "he",
    "she",
    "his",
    "her",
    "them",
    "our",
    "not",
    "can",
    "could",
    "should",
    "would",
}

TModel = TypeVar("TModel", bound=BaseModel)


class BaseAgent(ABC):
    problem_type: str
    prompt_name: str | None = None

    def __init__(self, llm_client: LLMClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client

    def preprocess(self, passage: str) -> str:
        normalized = truncate_if_too_long(normalize_text(passage))
        if word_count(normalized) < 60:
            raise InputValidationError("Passage must contain at least 60 words.")
        return normalized

    def analyze(self, passage: str) -> PassageAnalysis:
        paragraphs = split_paragraphs(passage) or [passage]
        sentence_pool = split_sentences(passage)

        paragraph_analysis: list[ParagraphAnalysis] = []
        for paragraph in paragraphs:
            sentences = split_sentences(paragraph)
            markers: list[str] = []
            for sentence in sentences:
                markers.extend(find_markers(sentence))
            paragraph_analysis.append(
                ParagraphAnalysis(
                    sentences=sentences,
                    function=tag_paragraph_function(paragraph),
                    markers=sorted(set(markers)),
                )
            )

        freq: dict[str, int] = {}
        for token in re.findall(r"[A-Za-z']+", passage.lower()):
            if token in _STOPWORDS or len(token) < 4:
                continue
            freq[token] = freq.get(token, 0) + 1
        keywords = [k for k, _ in sorted(freq.items(), key=lambda item: item[1], reverse=True)[:6]]

        thesis_candidates: list[str] = []
        for sentence in sentence_pool:
            lowered = sentence.lower()
            if any(marker in lowered for marker in ["therefore", "thus", "overall", "in short", "should"]):
                thesis_candidates.append(sentence)
        if not thesis_candidates and sentence_pool:
            thesis_candidates = [sentence_pool[0], sentence_pool[-1]]

        coref: list[CoreferenceCandidate] = []
        for idx, sentence in enumerate(sentence_pool):
            for pron in ["they", "it", "this", "that", "these", "those"]:
                if re.search(rf"\b{pron}\b", sentence, flags=re.IGNORECASE):
                    antecedent = keywords[0] if keywords else "the main idea"
                    coref.append(
                        CoreferenceCandidate(
                            mention=pron,
                            sentence_index=idx,
                            likely_antecedent=antecedent,
                        )
                    )

        topic = " ".join(keywords[:2]) if keywords else "main idea"
        return PassageAnalysis(
            topic=topic,
            thesis_candidates=thesis_candidates[:2],
            keywords=keywords,
            paragraphs=paragraph_analysis,
            coreference_candidates=coref[:5],
        )

    def _rng(self, request: GenerateRequest) -> random.Random:
        return random.Random(request.seed)

    def _build_choices(self, texts: Sequence[str], request: GenerateRequest) -> list[Choice]:
        labels = choice_labels(5)
        return [Choice(label=labels[i], text=texts[i]) for i in range(5)]

    def _llm_enabled(self) -> bool:
        return bool(self.settings.use_llm_generation and self.llm_client is not None and self.settings.resolved_api_key)

    def _prompt_context(
        self,
        request: GenerateRequest,
        passage: str,
        analysis: PassageAnalysis,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        context: dict[str, str] = {
            "passage": passage,
            "difficulty": request.difficulty,
            "style": request.style,
            "seed": "" if request.seed is None else str(request.seed),
            "explain": str(request.explain).lower(),
            "return_korean_stem": str(request.return_korean_stem).lower(),
            "analysis_json": json.dumps(analysis.model_dump(), ensure_ascii=False),
            "choices": str(request.choices),
        }
        if extra_context:
            for key, value in extra_context.items():
                if isinstance(value, str):
                    context[key] = value
                else:
                    context[key] = json.dumps(value, ensure_ascii=False)
        return context

    def _try_llm_generate(
        self,
        *,
        request: GenerateRequest,
        passage: str,
        analysis: PassageAnalysis,
        response_model: type[TModel],
        prompt_name: str | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> TModel | None:
        if not self._llm_enabled():
            logger.info(
                "LLM disabled for %s (use_llm_generation=%s, has_client=%s, has_api_key=%s). Using local fallback.",
                self.problem_type,
                self.settings.use_llm_generation,
                self.llm_client is not None,
                bool(self.settings.resolved_api_key),
            )
            return None

        name = prompt_name or self.prompt_name
        if not name:
            logger.info("No prompt configured for %s. Using local fallback.", self.problem_type)
            return None

        context = self._prompt_context(request=request, passage=passage, analysis=analysis, extra_context=extra_context)

        try:
            logger.info(
                "LLM generation start for %s (prompt=%s, model=%s).",
                self.problem_type,
                name,
                self.settings.gemini_model,
            )
            prompt = render_prompt(name, **context)
            schema = response_model.model_json_schema()
            generated = self.llm_client.generate_json(prompt=prompt, schema=schema)
            generated.setdefault("type", self.problem_type)
            problem = response_model.model_validate(generated)
            if not self._run_self_check(problem):
                logger.warning("LLM result rejected by self-check for %s. Using local fallback.", self.problem_type)
                return None
            logger.info("LLM generation success for %s.", self.problem_type)
            return problem
        except Exception as exc:
            logger.warning("LLM path failed for %s: %s. Using local fallback.", self.problem_type, exc)
            return None

    def _run_self_check(self, problem: BaseModel) -> bool:
        if not self.settings.enable_self_check or not self._llm_enabled():
            return True

        payload = json.dumps(problem.model_dump(), ensure_ascii=False)
        prompt = render_prompt("self_check", problem_json=payload)

        try:
            result = self.llm_client.generate_json(prompt=prompt, schema=SelfCheckResult.model_json_schema())
            checked = SelfCheckResult.model_validate(result)
            if not checked.ok:
                logger.warning("Self-check failed for %s: %s", self.problem_type, checked.reasons)
            return checked.ok
        except Exception as exc:
            logger.warning("Self-check parsing failed for %s: %s", self.problem_type, exc)
            return True

    def _meta(self, request: GenerateRequest, analysis: PassageAnalysis | None = None) -> dict:
        meta: dict = {"difficulty": request.difficulty, "seed": request.seed}
        if request.debug and analysis is not None:
            meta["debug"] = {
                "topic": analysis.topic,
                "thesis_candidates": analysis.thesis_candidates,
                "keywords": analysis.keywords,
            }
        return meta

    async def agenerate(self, request: GenerateRequest) -> BaseModel:
        # Agent internals are currently synchronous; run them off the event loop.
        return await asyncio.to_thread(self.generate, request)

    @abstractmethod
    def generate(self, request: GenerateRequest) -> BaseModel:
        raise NotImplementedError
