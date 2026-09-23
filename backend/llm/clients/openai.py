"""OpenAI Responses API provider. 별도 SDK 없이 urllib 만 씁니다."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from backend.core.errors import GenerationError
from backend.llm.clients.base import BaseJSONLLMClient

logger = logging.getLogger(__name__)


class OpenAILLMClient(BaseJSONLLMClient):
    """OpenAI Responses API client without an extra SDK dependency."""

    provider_label = "OpenAI"

    def _api_key(self) -> str:
        api_key = self.settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise GenerationError("Missing OPENAI_API_KEY for OpenAI access.")
        return api_key

    def _format_config(self, schema: dict | None, json_mode: bool) -> dict[str, Any] | None:
        if schema:
            return {
                "type": "json_schema",
                "name": "problem_response",
                "schema": schema,
                "strict": False,
            }
        if json_mode:
            return {"type": "json_object"}
        return None

    def _extract_error_message(self, body: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body[:500]
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        return body[:500]

    def _extract_output_text(self, payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        chunks: list[str] = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                content_type = content.get("type")
                if content_type in {"output_text", "text"} and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
                elif content_type == "refusal" and isinstance(content.get("refusal"), str):
                    raise GenerationError(f"OpenAI refused the request: {content['refusal']}")

        return "\n".join(chunks)

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
        label: str = "-",
    ) -> str:
        api_key = self._api_key()
        temp = self.settings.default_temperature if temperature is None else temperature
        max_tokens = self.settings.default_max_output_tokens
        started = time.monotonic()

        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "input": prompt,
            "max_output_tokens": max_tokens,
            "temperature": temp,
        }
        format_config = self._format_config(schema=schema, json_mode=json_mode)
        if format_config:
            payload["text"] = {"format": format_config}
        reasoning_effort = self.settings.openai_reasoning_effort.strip()
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}

        body = json.dumps(payload).encode("utf-8")
        base_url = self.settings.openai_base_url.rstrip("/")
        request = urllib.request.Request(
            url=f"{base_url}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        logger.info(
            "OpenAI request start (model=%s, schema=%s, temperature=%.2f, max_tokens=%s).",
            self.settings.openai_model,
            bool(schema),
            temp,
            max_tokens,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.openai_timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise GenerationError(f"OpenAI request failed ({exc.code}): {self._extract_error_message(response_body)}")
        except urllib.error.URLError as exc:
            raise GenerationError(f"OpenAI request failed: {exc}") from exc

        try:
            response_payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise GenerationError("OpenAI returned a non-JSON API response.") from exc

        # 실패 응답이어도 과금은 발생하므로 예외를 던지기 전에 먼저 기록합니다.
        usage = response_payload.get("usage") or {}
        elapsed = (time.monotonic() - started) * 1000
        self._record_usage(
            model=self.settings.openai_model,
            label=label,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            elapsed_ms=elapsed,
        )

        if response_payload.get("error"):
            raise GenerationError(f"OpenAI response error: {response_payload['error']}")
        if response_payload.get("status") == "incomplete":
            details = response_payload.get("incomplete_details") or {}
            raise GenerationError(f"OpenAI response incomplete: {details}")

        text = self._extract_output_text(response_payload)
        if not text.strip():
            raise GenerationError("OpenAI returned empty text response.")

        logger.info(
            "OpenAI response received (chars=%s, elapsed_ms=%.1f, input_tokens=%s, output_tokens=%s).",
            len(text),
            elapsed,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
        )
        return text
