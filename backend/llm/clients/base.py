"""provider 공통 동작: JSON 파싱, 재시도, 사용량 기록."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.config import Settings
from backend.core.errors import GenerationError
from backend.core.usage import attempts_made, note_attempt, record_call
from backend.llm.json import extract_first_json_object

logger = logging.getLogger(__name__)


def _attempt_label(label: str, attempt: int) -> str:
    """재시도까지 로그에서 구분되도록 시도 번호를 붙입니다."""
    return label if attempt == 0 else f"{label}#retry{attempt}"


class CallBudgetExceeded(GenerationError):
    """요청 하나의 provider 호출 상한을 넘었습니다.

    `GenerationError` 를 상속하므로 에이전트의 기존 실패 처리(로컬 폴백)를 그대로 탑니다.
    새로운 실패 형태를 만들지 않기 위한 의도적인 선택입니다.
    """


class BaseJSONLLMClient:
    """Shared JSON parsing and retry behavior for LLM providers."""

    provider_label = "LLM"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _record_usage(
        self,
        *,
        model: str,
        label: str,
        input_tokens: int | None,
        output_tokens: int | None,
        elapsed_ms: float,
    ) -> None:
        """호출 사용량을 현재 요청 스코프에 기록합니다. 실패해도 생성은 계속합니다."""
        try:
            record_call(
                provider=self.provider_label,
                model=model,
                label=label,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                elapsed_ms=elapsed_ms,
                input_price_override=self.settings.llm_input_price_per_mtok,
                output_price_override=self.settings.llm_output_price_per_mtok,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to record LLM usage: %s", exc)

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
        label: str = "-",
    ) -> str:
        raise NotImplementedError

    def _guarded_generate_raw(self, **kwargs: Any) -> str:
        """예산을 확인하고 한 번 호출합니다.

        재시도가 중첩되면(에이전트 재시도 x generate_json 재시도 x 스키마리스 복구)
        요청 하나가 수십 번 호출될 수 있습니다. 실패가 조용히 비싸지는 것을 막습니다.
        """
        budget = self.settings.llm_max_calls_per_request
        if budget > 0 and attempts_made() >= budget:
            raise CallBudgetExceeded(
                f"요청당 LLM 호출 상한({budget}회)을 초과했습니다. "
                "로컬 폴백으로 전환합니다. 상한은 LLM_MAX_CALLS_PER_REQUEST 로 조절합니다."
            )
        note_attempt()
        return self._generate_raw(**kwargs)

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

    def generate_json(self, prompt: str, schema: dict | None = None, label: str = "-") -> dict[str, Any]:
        last_error: Exception | None = None
        # 최초 1회 + 재시도 N회. 기본은 재시도 1회(총 2번)입니다.
        total_attempts = 1 + self.settings.llm_max_retries
        for attempt in range(total_attempts):
            is_last = attempt == total_attempts - 1
            # 재시도할수록 온도를 낮춰 형식을 지킬 확률을 올립니다.
            if attempt == 0:
                temperature = self.settings.default_temperature
            elif is_last:
                temperature = 0.0
            else:
                temperature = max(0.0, self.settings.default_temperature - 0.3)

            raw = ""
            try:
                raw = self._guarded_generate_raw(
                    prompt=prompt,
                    schema=schema,
                    temperature=temperature,
                    label=_attempt_label(label, attempt),
                )
                parsed = self._try_parse_json(raw, schema=schema)
                logger.info("%s JSON parse success on attempt %s.", self.provider_label, attempt + 1)
                return parsed
            except CallBudgetExceeded:
                raise
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

                # 스키마리스 복구는 마지막 시도에서 한 번만 씁니다.
                # 매 시도마다 붙이면 호출 수가 두 배가 됩니다.
                if schema and is_last:
                    recovery_raw = ""
                    try:
                        logger.info("Trying schema-less JSON recovery on attempt %s.", attempt + 1)
                        recovery_raw = self._guarded_generate_raw(
                            prompt=self._schema_less_prompt(prompt, schema),
                            schema=None,
                            temperature=temperature,
                            label=f"{_attempt_label(label, attempt)}+recovery",
                        )
                        recovered = self._try_parse_json(recovery_raw, schema=schema)
                        logger.info("Schema-less JSON recovery success on attempt %s.", attempt + 1)
                        return recovered
                    except CallBudgetExceeded:
                        raise
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

    def generate_text(self, prompt: str, label: str = "-") -> str:
        return self._guarded_generate_raw(prompt=prompt, schema=None, json_mode=False, label=label)
