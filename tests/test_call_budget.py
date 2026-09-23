"""요청 1건의 LLM 호출 상한 검증.

재시도가 중첩되면(에이전트 재시도 x generate_json 3시도 x 스키마리스 복구)
요청 하나가 수십 번 호출될 수 있습니다. 실패가 조용히 비싸지는 것을 막습니다.
"""

import pytest

from backend.core.config import Settings
from backend.core.usage import UsageRecorder, attempts_made, reset_recorder, set_recorder
from backend.llm.clients import CallBudgetExceeded
from backend.llm.clients.base import BaseJSONLLMClient
from backend.core.errors import GenerationError


class AlwaysBadJson(BaseJSONLLMClient):
    """항상 파싱 불가능한 응답을 주는 provider. 재시도를 최대로 유발합니다."""

    provider_label = "Broken"

    def __init__(self, settings):
        super().__init__(settings=settings)
        self.raw_calls = 0

    def _generate_raw(self, prompt, schema=None, temperature=None, json_mode=True, label="-"):
        self.raw_calls += 1
        return "not json at all"


# 기본 설정에서 generate_json 1건의 최대 호출 수:
#   최초 1회 + 재시도 1회 + 마지막 시도의 스키마리스 복구 1회 = 3회
CALLS_PER_GENERATE_JSON = 3


def _run(budget: int, retries: int = 1):
    settings = Settings(APP_ENV="test", LLM_MAX_CALLS_PER_REQUEST=budget, LLM_MAX_RETRIES=retries)
    client = AlwaysBadJson(settings)
    recorder = UsageRecorder(feature="test")
    token = set_recorder(recorder)
    try:
        with pytest.raises(GenerationError):
            client.generate_json(prompt="x", schema={"required": ["a"]})
    finally:
        reset_recorder(token)
    return client, recorder


def test_budget_caps_runaway_retries() -> None:
    """재시도 정책보다 예산이 낮으면 예산이 먼저 끊습니다.

    정책만으로는 3회까지 가지만, 예산 2를 주면 2회에서 멈춰야 합니다.
    """
    client, recorder = _run(budget=2)

    assert client.raw_calls == 2, f"상한 2회를 넘겨 {client.raw_calls}회 호출했습니다."
    assert recorder.attempts == 2


def test_budget_is_a_ceiling_not_a_quota() -> None:
    """예산이 정책보다 넉넉하면 정책대로만 호출합니다."""
    client, _ = _run(budget=99)

    assert client.raw_calls == CALLS_PER_GENERATE_JSON


def test_without_budget_retries_run_to_completion() -> None:
    """상한 0 = 무제한. 그래도 재시도 정책 자체가 3회로 묶여 있어야 합니다."""
    client, _ = _run(budget=0)

    assert client.raw_calls == CALLS_PER_GENERATE_JSON


def test_retry_setting_controls_attempt_count() -> None:
    """재시도 0 = 복구 포함 2회, 재시도 1 = 3회, 재시도 2 = 4회."""
    assert _run(budget=0, retries=0)[0].raw_calls == 2
    assert _run(budget=0, retries=1)[0].raw_calls == 3
    assert _run(budget=0, retries=2)[0].raw_calls == 4


def test_schema_less_recovery_runs_only_once() -> None:
    """복구를 매 시도마다 붙이면 호출 수가 두 배가 됩니다."""
    client, _ = _run(budget=0, retries=2)

    # 시도 3회 + 복구 1회 = 4. (시도마다 복구면 6회가 됩니다)
    assert client.raw_calls == 4


def test_budget_error_is_a_generation_error() -> None:
    """에이전트의 기존 실패 처리(로컬 폴백)를 그대로 타야 합니다."""
    assert issubclass(CallBudgetExceeded, GenerationError)


def test_generous_budget_does_not_interfere() -> None:
    client, _ = _run(budget=99)

    assert client.raw_calls == CALLS_PER_GENERATE_JSON, "상한이 넉넉하면 평소와 같아야 합니다."


def test_attempts_are_counted_per_request() -> None:
    settings = Settings(APP_ENV="test", LLM_MAX_CALLS_PER_REQUEST=0)
    client = AlwaysBadJson(settings)

    first = UsageRecorder()
    token = set_recorder(first)
    try:
        with pytest.raises(GenerationError):
            client.generate_json(prompt="x", schema={"required": ["a"]})
        assert first.attempts == CALLS_PER_GENERATE_JSON
    finally:
        reset_recorder(token)

    # 다음 요청은 0부터 다시 셉니다.
    second = UsageRecorder()
    token = set_recorder(second)
    try:
        assert attempts_made() == 0
    finally:
        reset_recorder(token)


def test_no_recorder_means_no_budget() -> None:
    """요청 스코프 밖(스크립트 실행 등)에서는 상한을 적용하지 않습니다."""
    settings = Settings(APP_ENV="test", LLM_MAX_CALLS_PER_REQUEST=1)
    client = AlwaysBadJson(settings)

    with pytest.raises(GenerationError):
        client.generate_json(prompt="x", schema={"required": ["a"]})

    assert client.raw_calls == CALLS_PER_GENERATE_JSON, "recorder 가 없으면 상한이 걸리지 않습니다."


def test_summary_reports_attempts() -> None:
    _, recorder = _run(budget=3)

    assert recorder.summary()["attempts"] == 3
