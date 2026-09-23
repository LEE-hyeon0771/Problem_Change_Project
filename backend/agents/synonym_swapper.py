from __future__ import annotations

import logging

from backend.core.config import Settings, get_settings
from backend.core.progress import emit_progress
from backend.llm.clients import LLMClient
from backend.llm.schema import SynonymSwapDraft
from backend.prompts.loader import render_prompt_with_base
from backend.toolkit.synonym_swap import apply_swaps, target_swap_count

logger = logging.getLogger(__name__)

# 동의어 교체를 적용해도 안전한 유형만 허용합니다.
#
# 제외한 유형과 이유:
#   vocab   - "한 단어만 문맥상 부적절"이 문제인데, 교체된 단어가 어색하게 읽히면
#             정답이 둘이 됩니다. 이 유형의 생명인 정답 유일성을 직접 공격합니다.
#   grammar - 교체가 수일치/시제/연어를 건드리면 의도치 않은 어법 오류가 생깁니다.
#   insertion / order / irrelevant
#           - 연결어가 정답 근거인데, 교체 과정에서 문장 흐름 단서가 흔들릴 위험이 큽니다.
SUPPORTED_TYPES: frozenset[str] = frozenset({"title", "topic", "summary", "blank", "implicit"})


class SynonymSwapper:
    """문항 생성 "전"에 지문의 단어 몇 개를 동의어로 바꿔 놓습니다.

    생성 후에 바꾸면 `validate_blank_from_original` 같은 원문 복원 검증이 전부 깨집니다.
    전처리로 두면 바뀐 지문이 그 문항의 원문이 되므로 기존 검증이 그대로 살아납니다.
    """

    prompt_name = "synonym_swap"
    system_prompt_name = "synonym_swap_system"

    def __init__(self, llm_client: LLMClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client

    def _enabled(self) -> bool:
        return bool(
            self.settings.use_llm_generation
            and self.llm_client is not None
            and self.settings.has_llm_credentials
        )

    def swap(self, *, passage: str, difficulty: str, problem_type: str) -> tuple[str, list[dict]]:
        """(교체된 지문, 적용된 교체 목록)을 돌려줍니다.

        지원하지 않는 유형이거나 LLM이 꺼져 있으면 원문을 그대로 돌려줍니다.
        실패해도 문항 생성 자체는 막지 않습니다.
        """
        if problem_type not in SUPPORTED_TYPES:
            logger.info("Synonym swap skipped: %s is not a supported type.", problem_type)
            return passage, []

        if not self._enabled():
            logger.info("Synonym swap skipped: LLM disabled.")
            return passage, []

        count = target_swap_count(passage, difficulty)
        if count <= 0:
            return passage, []

        emit_progress("swapping", f"지문의 단어 {count}개를 동의어로 바꾸는 중...", swap_count=count)

        try:
            prompt = render_prompt_with_base(
                self.system_prompt_name,
                self.prompt_name,
                passage=passage,
                difficulty=difficulty,
                swap_count=str(count),
            )
            raw = self.llm_client.generate_json(
                prompt=prompt,
                schema=SynonymSwapDraft.model_json_schema(),
                label="synonym_swap",
            )
            draft = SynonymSwapDraft.model_validate(raw)
        except Exception as exc:
            logger.warning("Synonym swap failed: %s. Using the original passage.", exc)
            return passage, []

        swapped, applied = apply_swaps(passage, [item.model_dump() for item in draft.swaps])
        logger.info(
            "Synonym swap applied %s/%s proposed (target=%s).",
            len(applied),
            len(draft.swaps),
            count,
        )
        return swapped, applied
