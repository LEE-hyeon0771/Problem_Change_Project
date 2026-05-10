from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import GenerationError
from app.llm.json import extract_first_json_object

logger = logging.getLogger(__name__)


class BaseJSONLLMClient:
    """Shared JSON parsing and retry behavior for LLM providers."""

    provider_label = "LLM"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
    ) -> str:
        raise NotImplementedError

    def _validate_required_fields(self, parsed: dict[str, Any], schema: dict | None) -> None:
        if not schema:
            return
        required = schema.get("required", [])
        if isinstance(required, list):
            missing = [field for field in required if field not in parsed]
            if missing:
                raise GenerationError(f"{self.provider_label} response missing required fields: {missing}")

    def _schema_less_prompt(self, prompt: str, schema: dict | None) -> str:
        required = []
        if schema:
            raw_required = schema.get("required", [])
            if isinstance(raw_required, list):
                required = [str(key) for key in raw_required]

        required_line = ", ".join(required) if required else "all required keys"
        suffix = (
            "\n\nReturn one COMPLETE JSON object only. "
            f"Include required keys: {required_line}. "
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
            raise GenerationError(f"{self.provider_label} JSON response root must be an object.")
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
                logger.info("%s JSON parse success on attempt %s.", self.provider_label, attempt + 1)
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

        raise GenerationError(f"{self.provider_label} JSON generation failed: {last_error}")

    def generate_text(self, prompt: str) -> str:
        return self._generate_raw(prompt=prompt, schema=None, json_mode=False)


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

        if response_payload.get("error"):
            raise GenerationError(f"OpenAI response error: {response_payload['error']}")
        if response_payload.get("status") == "incomplete":
            details = response_payload.get("incomplete_details") or {}
            raise GenerationError(f"OpenAI response incomplete: {details}")

        text = self._extract_output_text(response_payload)
        if not text.strip():
            raise GenerationError("OpenAI returned empty text response.")

        elapsed = (time.monotonic() - started) * 1000
        logger.info("OpenAI response received (chars=%s, elapsed_ms=%.1f).", len(text), elapsed)
        return text


class CodexCliLLMClient(BaseJSONLLMClient):
    """Experimental local provider that shells out to the logged-in Codex CLI."""

    provider_label = "Codex CLI"

    def _build_prompt(self, prompt: str, schema: dict | None, json_mode: bool) -> str:
        guardrail = (
            "You are being used as a pure JSON generation backend for an exam-item service.\n"
            "Do not edit files, do not inspect local files, and do not run shell commands.\n"
            "Return only the requested final answer.\n\n"
        )
        if schema or json_mode:
            guardrail += "The final answer must be one complete JSON object with no markdown fence.\n\n"
        return f"{guardrail}{prompt}"

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
    ) -> str:
        command = self.settings.codex_cli_command
        executable = shutil.which(command)
        if not executable:
            raise GenerationError(f"Codex CLI command not found: {command}")

        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="problem-change-codex-") as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "last-message.txt"
            cmd = [
                executable,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "--cd",
                temp_dir,
                "--color",
                "never",
                "-o",
                str(output_path),
            ]
            if self.settings.codex_cli_model:
                cmd.extend(["--model", self.settings.codex_cli_model])
            if schema:
                schema_path = temp_path / "schema.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                cmd.extend(["--output-schema", str(schema_path)])
            cmd.append("-")

            logger.info(
                "Codex CLI request start (model=%s, schema=%s, timeout=%ss).",
                self.settings.codex_cli_model or "default",
                bool(schema),
                self.settings.codex_cli_timeout_seconds,
            )
            try:
                result = subprocess.run(
                    cmd,
                    input=self._build_prompt(prompt=prompt, schema=schema, json_mode=json_mode),
                    text=True,
                    capture_output=True,
                    timeout=self.settings.codex_cli_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise GenerationError("Codex CLI request timed out.") from exc

            if result.returncode != 0:
                stderr = (result.stderr or result.stdout or "").strip()
                raise GenerationError(f"Codex CLI failed ({result.returncode}): {stderr[:500]}")

            if output_path.exists():
                text = output_path.read_text(encoding="utf-8").strip()
            else:
                text = result.stdout.strip()
            if not text:
                raise GenerationError("Codex CLI returned empty text response.")

            elapsed = (time.monotonic() - started) * 1000
            logger.info("Codex CLI response received (chars=%s, elapsed_ms=%.1f).", len(text), elapsed)
            return text


# Backwards-compatible name for existing imports and tests.
LLMClient = GeminiLLMClient


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
    ) -> str:
        logger.debug("MockLLMClient prompt: %s", prompt[:160])
        return json.dumps(self.payload)

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict[str, Any]:
        logger.info("MockLLMClient.generate_json called.")
        if isinstance(self.payload, dict):
            return dict(self.payload)
        return {"ok": True}
