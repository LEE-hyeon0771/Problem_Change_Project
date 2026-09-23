"""테스트용 provider. 실제 호출 없이 고정 payload 를 돌려줍니다."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.config import Settings
from backend.llm.clients.base import BaseJSONLLMClient

logger = logging.getLogger(__name__)


class MockLLMClient(BaseJSONLLMClient):
    provider_label = "MockLLM"

    def __init__(self, settings: Settings, payload: dict[str, Any] | None = None) -> None:
        super().__init__(settings=settings)
        self.payload = payload or {"ok": True}

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
        label: str = "-",
    ) -> str:
        logger.debug("MockLLMClient prompt: %s", prompt[:160])
        return json.dumps(self.payload)

    def generate_json(self, prompt: str, schema: dict | None = None, label: str = "-") -> dict[str, Any]:
        logger.info("MockLLMClient.generate_json called.")
        if isinstance(self.payload, dict):
            return dict(self.payload)
        return {"ok": True}
