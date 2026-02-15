from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from app.core.errors import GenerationError
from app.core.config import Settings
from app.llm.json import extract_first_json_object

logger = logging.getLogger(__name__)
FIXED_MAX_OUTPUT_TOKENS = 20_000


class LLMClient:
    """Gemini wrapper with JSON-first generation and recovery."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        self._types = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        api_key = self.settings.resolved_api_key or os.getenv("GEMINI_API_KEY", "")
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

    def _generate_raw(self, prompt: str, schema: dict | None = None, temperature: float | None = None) -> str:
        client = self._get_client()
        temp = self.settings.default_temperature if temperature is None else temperature
        max_tokens = FIXED_MAX_OUTPUT_TOKENS
        started = time.monotonic()

        config_kwargs: dict[str, Any] = {
            "temperature": temp,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
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
        if not text.strip():
            raise GenerationError("Gemini returned empty text response.")
        elapsed = (time.monotonic() - started) * 1000
        logger.info(
            "Gemini response received (chars=%s, elapsed_ms=%.1f, finish_reason=%s).",
            len(text),
            elapsed,
            finish_reason,
        )
        if finish_reason and any(
            token in finish_reason.upper() for token in ["MAX_TOKENS", "SAFETY", "RECITATION", "MALFORMED"]
        ):
            raise GenerationError(f"Gemini finish_reason={finish_reason}")
        return text

    def _validate_required_fields(self, parsed: dict[str, Any], schema: dict | None) -> None:
        if not schema:
            return
        required = schema.get("required", [])
        if isinstance(required, list):
            missing = [field for field in required if field not in parsed]
            if missing:
                raise GenerationError(f"Gemini response missing required fields: {missing}")

    def _schema_less_prompt(self, prompt: str, schema: dict | None) -> str:
        required = []
        if schema:
            raw_required = schema.get("required", [])
            if isinstance(raw_required, list):
                required = [str(key) for key in raw_required]

        required_line = ", ".join(required) if required else "all required keys"
        suffix = (
            "\\n\\nReturn one COMPLETE JSON object only. "\
            f"Include required keys: {required_line}. "\
            "Do not truncate the JSON."
        )
        return f"{prompt}{suffix}"

    def _try_parse_json(self, raw: str, schema: dict | None = None) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Direct JSON parse failed: %s. Trying structural recovery.",
                exc,
            )
            parsed = extract_first_json_object(raw)

        if not isinstance(parsed, dict):
            raise GenerationError("Gemini JSON response root must be an object.")
        self._validate_required_fields(parsed, schema)
        return parsed

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            if attempt == 0:
                temperature = self.settings.default_temperature
            elif attempt == 1:
                temperature = max(0.0, self.settings.default_temperature - 0.3)
            else:
                temperature = 0.0

            raw = ""
            try:
                raw = self._generate_raw(prompt=prompt, schema=schema, temperature=temperature)
                parsed = self._try_parse_json(raw, schema=schema)
                logger.info("Gemini JSON parse success on attempt %s.", attempt + 1)
                return parsed
            except Exception as exc:
                last_error = exc
                snippet = raw[:200].replace("\n", "\\n") if raw else ""
                if snippet:
                    logger.warning(
                        "LLM JSON generation attempt %s failed: %s | raw_snippet=%s",
                        attempt + 1,
                        exc,
                        snippet,
                    )
                else:
                    logger.warning("LLM JSON generation attempt %s failed: %s", attempt + 1, exc)

                if schema:
                    recovery_raw = ""
                    try:
                        logger.info("Trying schema-less JSON recovery on attempt %s.", attempt + 1)
                        recovery_raw = self._generate_raw(
                            prompt=self._schema_less_prompt(prompt, schema),
                            schema=None,
                            temperature=temperature,
                        )
                        recovered = self._try_parse_json(recovery_raw, schema=schema)
                        logger.info("Schema-less JSON recovery success on attempt %s.", attempt + 1)
                        return recovered
                    except Exception as recovery_exc:
                        last_error = recovery_exc
                        recovery_snippet = recovery_raw[:200].replace("\n", "\\n") if recovery_raw else ""
                        if recovery_snippet:
                            logger.warning(
                                "Schema-less recovery failed on attempt %s: %s | raw_snippet=%s",
                                attempt + 1,
                                recovery_exc,
                                recovery_snippet,
                            )
                        else:
                            logger.warning("Schema-less recovery failed on attempt %s: %s", attempt + 1, recovery_exc)

        raise GenerationError(f"Gemini JSON generation failed: {last_error}")

    def generate_text(self, prompt: str) -> str:
        return self._generate_raw(prompt=prompt, schema=None)


class MockLLMClient(LLMClient):
    def __init__(self, settings: Settings, payload: dict[str, Any] | None = None) -> None:
        super().__init__(settings)
        self.payload = payload or {"ok": True}

    def generate_text(self, prompt: str) -> str:
        logger.debug("MockLLMClient prompt: %s", prompt[:160])
        return json.dumps(self.payload)

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict[str, Any]:
        logger.info("MockLLMClient.generate_json called.")
        if isinstance(self.payload, dict):
            return dict(self.payload)
        return {"ok": True}
