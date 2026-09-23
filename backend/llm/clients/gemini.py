"""Gemini provider."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from backend.core.config import Settings
from backend.core.errors import GenerationError
from backend.llm.clients.base import BaseJSONLLMClient

logger = logging.getLogger(__name__)


class GeminiLLMClient(BaseJSONLLMClient):
    """Gemini wrapper with JSON-first generation and recovery."""

    provider_label = "Gemini"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings=settings)
        self._client = None
        self._types = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        api_key = self.settings.google_api_key or self.settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise GenerationError("Missing GOOGLE_API_KEY/GEMINI_API_KEY for Gemini access.")

        try:
            from google import genai
            from google.genai import types as genai_types
        except Exception as exc:  # pragma: no cover
            raise GenerationError(
                "google-genai is not installed. Install dependencies with `uv sync --group dev`."
            ) from exc

        self._client = genai.Client(api_key=api_key)
        self._types = genai_types
        logger.info("Gemini client initialized (model=%s).", self.settings.gemini_model)
        return self._client

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
        label: str = "-",
    ) -> str:
        client = self._get_client()
        temp = self.settings.default_temperature if temperature is None else temperature
        max_tokens = self.settings.default_max_output_tokens
        started = time.monotonic()

        config_kwargs: dict[str, Any] = {
            "temperature": temp,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json" if json_mode else "text/plain",
        }
        if schema:
            config_kwargs["response_json_schema"] = schema
        config_fields = getattr(self._types.GenerateContentConfig, "model_fields", {})
        if "automatic_function_calling" in config_fields and hasattr(self._types, "AutomaticFunctionCallingConfig"):
            try:
                config_kwargs["automatic_function_calling"] = self._types.AutomaticFunctionCallingConfig(disable=True)
            except Exception:
                pass
        config = self._types.GenerateContentConfig(**config_kwargs)
        try:
            dumped = config.model_dump(by_alias=True, exclude_none=True)
            resolved_max_tokens = dumped.get("maxOutputTokens")
            if resolved_max_tokens is None:
                resolved_max_tokens = dumped.get("max_output_tokens")
            logger.info(
                "Gemini generation config resolved (maxOutputTokens=%s, hasResponseJsonSchema=%s).",
                resolved_max_tokens,
                "responseJsonSchema" in dumped,
            )
            if resolved_max_tokens is None:
                logger.warning("Gemini generation config does not expose maxOutputTokens explicitly.")
        except Exception:
            logger.info("Gemini generation config resolved (max_output_tokens=%s).", max_tokens)

        logger.info(
            "Gemini request start (model=%s, schema=%s, temperature=%.2f, max_tokens=%s).",
            self.settings.gemini_model,
            bool(schema),
            temp,
            max_tokens,
        )
        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=config,
        )
        text = getattr(response, "text", "") or ""
        finish_reason = None
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                raw_reason = getattr(candidates[0], "finish_reason", None)
                if raw_reason is not None:
                    finish_reason = getattr(raw_reason, "name", None) or str(raw_reason)
        except Exception:
            finish_reason = None
        # 비용 추적용. 글자 수만으로는 과금량을 알 수 없어 토큰 사용량을 함께 남깁니다.
        # 빈 응답으로 예외를 던지기 전에 먼저 기록해야 실패한 호출의 비용도 새지 않습니다.
        prompt_tokens = output_tokens = total_tokens = None
        try:
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                prompt_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
        except Exception:
            pass

        elapsed = (time.monotonic() - started) * 1000
        self._record_usage(
            model=self.settings.gemini_model,
            label=label,
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            elapsed_ms=elapsed,
        )

        if not text.strip():
            raise GenerationError("Gemini returned empty text response.")

        logger.info(
            "Gemini response received (chars=%s, elapsed_ms=%.1f, finish_reason=%s, "
            "input_tokens=%s, output_tokens=%s, total_tokens=%s).",
            len(text),
            elapsed,
            finish_reason,
            prompt_tokens,
            output_tokens,
            total_tokens,
        )
        if finish_reason and any(
            token in finish_reason.upper() for token in ["MAX_TOKENS", "SAFETY", "RECITATION", "MALFORMED"]
        ):
            raise GenerationError(f"Gemini finish_reason={finish_reason}")
        return text
