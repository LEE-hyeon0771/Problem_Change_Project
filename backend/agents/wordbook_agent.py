from __future__ import annotations

import json
import logging

from backend.agents.base import BaseAgent
from backend.core.progress import emit_progress
from backend.llm.schema import WordbookDraft
from backend.prompts.loader import render_prompt_with_base
from backend.schemas.wordbook import (
    WordbookEntry,
    WordbookRequest,
    WordbookResponse,
    WordSense,
    pos_ko_label,
)
from backend.toolkit.lexicon import content_word_candidates, match_key, missing_candidates
from backend.toolkit.text import split_sentences

logger = logging.getLogger(__name__)

# 커버리지 보강 패스를 무한정 돌지 않도록 제한합니다.
MAX_EXPANSION_PASSES = 2
# 보강 패스를 한 번 더 돌 만한 누락 개수 하한.
MIN_MISSING_TO_EXPAND = 2


class WordbookAgent(BaseAgent):
    """지문 하나에서 핵심단어장을 만드는 에이전트.

    문항 생성 에이전트와 달리 선지/정답이 없으므로 `BaseAgent`의 문항용 LLM 경로
    (`_try_llm_generate`, `_run_self_check`)를 쓰지 않고 자체 경로를 사용합니다.
    대신 전처리/지문 분석/실행 래퍼는 그대로 공유합니다.
    """

    problem_type = "wordbook"
    prompt_name = "wordbook"
    system_prompt_name = "wordbook_system"

    # ---------------------------------------------------------------- helpers

    def _min_entries(self, candidates: list[str]) -> int:
        """후보 수 대비 최소 기대 항목 수.

        지문이 짧다고 2~3개만 뽑고 끝내는 것을 막기 위한 하한선입니다.
        """
        if not candidates:
            return 0
        return max(8, int(len(candidates) * 0.7))

    def _sentence_for(self, word: str, sentences: list[str]) -> str:
        key = match_key(word)
        if not key:
            return sentences[0] if sentences else ""
        for sentence in sentences:
            if key in {match_key(token) for token in sentence.split()}:
                return sentence
        lowered = word.lower()
        for sentence in sentences:
            if lowered in sentence.lower():
                return sentence
        return ""

    def _normalize_entries(self, entries: list[WordbookEntry], sentences: list[str]) -> list[WordbookEntry]:
        """표제어 중복 제거 + 서버가 채울 수 있는 빈 칸 보완."""
        normalized: list[WordbookEntry] = []
        seen: set[str] = set()

        for entry in entries:
            headword = (entry.headword or "").strip()
            if not headword:
                continue
            key = match_key(headword) or headword.lower()
            if key in seen:
                continue
            seen.add(key)

            senses: list[WordSense] = []
            for sense in entry.senses:
                senses.append(sense.model_copy(update={"pos_ko": pos_ko_label(sense.pos)}))

            normalized.append(
                entry.model_copy(
                    update={
                        "headword": headword,
                        "surface_form": entry.surface_form or headword,
                        "example_sentence": entry.example_sentence or self._sentence_for(headword, sentences),
                        "senses": senses,
                    }
                )
            )

        return normalized

    def _wordbook_context(self, request: WordbookRequest, passage: str, analysis, candidates: list[str]) -> dict[str, str]:
        return {
            "passage": passage,
            "analysis_json": json.dumps(analysis.to_prompt_payload(), ensure_ascii=False),
            "include_phrases": str(request.include_phrases).lower(),
            "max_related": str(request.max_related),
            "candidate_words": ", ".join(candidates) if candidates else "(none detected)",
            "min_entries": str(self._min_entries(candidates)),
        }

    # -------------------------------------------------------------- llm paths

    def _request_entries(self, prompt_name: str, context: dict[str, str]) -> list[WordbookEntry]:
        prompt = render_prompt_with_base(self.system_prompt_name, prompt_name, **context)
        raw = self.llm_client.generate_json(
            prompt=prompt, schema=WordbookDraft.model_json_schema(), label=prompt_name
        )
        return WordbookDraft.model_validate(raw).entries

    def _expand_coverage(
        self,
        *,
        request: WordbookRequest,
        passage: str,
        entries: list[WordbookEntry],
        candidates: list[str],
    ) -> tuple[list[WordbookEntry], list[str]]:
        """누락된 후보를 추가 패스로 채웁니다. 실패해도 기존 항목은 그대로 둡니다."""
        for attempt in range(MAX_EXPANSION_PASSES):
            covered = [word for entry in entries for word in entry.covered_words]
            missing = missing_candidates(candidates, covered)
            if len(missing) < MIN_MISSING_TO_EXPAND:
                return entries, missing

            logger.info(
                "Wordbook coverage pass %s: %s/%s candidates still missing.",
                attempt + 1,
                len(missing),
                len(candidates),
            )
            emit_progress(
                "expanding",
                f"빠진 단어 {len(missing)}개를 보강하고 있습니다...",
                missing_count=len(missing),
            )
            try:
                extra = self._request_entries(
                    "wordbook_expand",
                    {
                        "passage": passage,
                        "max_related": str(request.max_related),
                        "covered_words": ", ".join(sorted({entry.headword for entry in entries})),
                        "missing_words": ", ".join(missing),
                    },
                )
            except Exception as exc:
                logger.warning("Wordbook coverage pass %s failed: %s", attempt + 1, exc)
                return entries, missing

            if not extra:
                return entries, missing
            entries = entries + extra

        covered = [word for entry in entries for word in entry.covered_words]
        return entries, missing_candidates(candidates, covered)

    def _try_llm_wordbook(
        self,
        *,
        request: WordbookRequest,
        passage: str,
        analysis,
        candidates: list[str],
    ) -> tuple[list[WordbookEntry], list[str]] | None:
        if not self._llm_enabled():
            logger.info(
                "LLM disabled for wordbook (use_llm_generation=%s, has_client=%s, has_api_key=%s). "
                "Falling back to extraction only.",
                self.settings.use_llm_generation,
                self.llm_client is not None,
                self.settings.has_llm_credentials,
            )
            return None

        context = self._wordbook_context(request=request, passage=passage, analysis=analysis, candidates=candidates)

        try:
            logger.info(
                "Wordbook generation start (candidates=%s, model=%s).",
                len(candidates),
                self.settings.active_model,
            )
            emit_progress(
                "generating",
                f"후보 {len(candidates)}개를 바탕으로 단어를 정리하고 있습니다...",
                candidate_count=len(candidates),
            )
            entries = self._request_entries(self.prompt_name or "wordbook", context)
        except Exception as exc:
            logger.warning("Wordbook LLM path failed: %s. Falling back to extraction only.", exc)
            return None

        if not entries:
            logger.warning("Wordbook LLM returned no entries. Falling back to extraction only.")
            return None

        emit_progress(
            "partial",
            f"1차 정리 완료 — {len(entries)}단어",
            entries=[entry.model_dump(mode="json") for entry in entries],
        )

        entries, missing = self._expand_coverage(
            request=request,
            passage=passage,
            entries=entries,
            candidates=candidates,
        )
        logger.info("Wordbook generation success (entries=%s, uncovered=%s).", len(entries), len(missing))
        return entries, missing

    # --------------------------------------------------------------- fallback

    def _fallback_entries(self, candidates: list[str], sentences: list[str]) -> list[WordbookEntry]:
        """LLM이 꺼져 있을 때의 추출 전용 결과.

        뜻과 동의어/반의어는 LLM 없이 지어낼 수 없으므로 비워 두고,
        `meta.notice`로 반쪽짜리 결과임을 알립니다.
        """
        return [
            WordbookEntry(
                headword=word,
                surface_form=word,
                importance="core",
                example_sentence=self._sentence_for(word, sentences),
                senses=[],
            )
            for word in candidates
        ]

    # ------------------------------------------------------------------- main

    def generate(self, request: WordbookRequest) -> WordbookResponse:
        passage = self.preprocess(request.passage)
        analysis = self.analyze(passage)
        sentences = split_sentences(passage)
        candidates = content_word_candidates(passage)
        emit_progress(
            "candidates",
            f"핵심단어 후보 {len(candidates)}개를 찾았습니다.",
            candidate_count=len(candidates),
        )

        meta: dict = {
            "candidate_count": len(candidates),
            "min_entries": self._min_entries(candidates),
        }

        generated = self._try_llm_wordbook(
            request=request,
            passage=passage,
            analysis=analysis,
            candidates=candidates,
        )

        if generated is None:
            entries = self._normalize_entries(self._fallback_entries(candidates, sentences), sentences)
            meta.update(
                {
                    "generation_mode": "local_fallback",
                    "entry_count": len(entries),
                    "uncovered_candidates": [],
                    "notice": (
                        "LLM이 비활성화되어 있어 핵심단어 후보만 추출했습니다. "
                        "뜻·동의어·반의어를 채우려면 LLM 설정을 확인해 주세요."
                    ),
                }
            )
            return WordbookResponse(passage=passage, entries=entries, meta=meta)

        raw_entries, missing = generated
        entries = self._normalize_entries(raw_entries, sentences)
        meta.update(
            {
                "generation_mode": "llm",
                "entry_count": len(entries),
                "uncovered_candidates": missing,
            }
        )
        return WordbookResponse(passage=passage, entries=entries, meta=meta)
