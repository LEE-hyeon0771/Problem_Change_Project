from decimal import Decimal
from pathlib import Path

from backend.core.usage import (
    MODEL_PRICES,
    UsageLogWriter,
    UsageRecorder,
    record_call,
    reset_recorder,
    resolve_price,
    set_recorder,
)


def _record(recorder: UsageRecorder, **kwargs):
    token = set_recorder(recorder)
    try:
        return record_call(**kwargs)
    finally:
        reset_recorder(token)


def _call_kwargs(**overrides):
    base = {
        "provider": "Gemini",
        "model": "gemini-3-flash-preview",
        "label": "wordbook",
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "elapsed_ms": 1200.0,
    }
    base.update(overrides)
    return base


def test_price_table_lookup_is_exact() -> None:
    price = resolve_price("gemini-3-flash-preview")

    assert price is not None
    assert price.input_per_mtok == Decimal("0.25")
    assert price.output_per_mtok == Decimal("1.50")
    assert price.source == "table"


def test_price_lookup_tolerates_version_suffix() -> None:
    price = resolve_price("gemini-3-flash-preview-09-2026")

    assert price is not None
    assert price.source == "table_prefix"
    assert price.input_per_mtok == Decimal("0.25")


def test_env_override_wins_over_table() -> None:
    price = resolve_price("gemini-3-flash-preview", input_override=1.0, output_override=2.0)

    assert price is not None
    assert price.source == "env_override"
    assert price.input_per_mtok == Decimal("1.0")


def test_cost_is_exact_for_one_million_tokens() -> None:
    price = resolve_price("gemini-3-flash-preview")

    # 100만 입력 + 100만 출력 = 단가 그대로 합산되어야 합니다.
    assert price.cost_usd(1_000_000, 1_000_000) == Decimal("1.75")
    assert price.cost_usd(0, 0) == Decimal("0")


def test_cost_uses_decimal_not_float() -> None:
    price = resolve_price("gemini-3-flash-preview")

    # float 누산이면 0.1+0.2 류의 오차가 끼어듭니다. Decimal이라 정확히 떨어져야 합니다.
    assert price.cost_usd(3, 7) == Decimal("3") * Decimal("0.25") / Decimal("1000000") + Decimal(
        "7"
    ) * Decimal("1.50") / Decimal("1000000")


def test_record_call_accumulates_into_recorder() -> None:
    recorder = UsageRecorder(feature="wordbook")
    _record(recorder, **_call_kwargs())
    _record(recorder, **_call_kwargs(label="wordbook_expand", input_tokens=500_000, output_tokens=0))

    summary = recorder.summary()
    assert summary["calls"] == 2
    assert summary["input_tokens"] == 1_500_000
    assert summary["output_tokens"] == 1_000_000
    assert summary["cost_usd"] == float(Decimal("1.75") + Decimal("0.125"))


def test_unknown_model_logs_tokens_but_no_cost() -> None:
    recorder = UsageRecorder()
    call = _record(recorder, **_call_kwargs(model="some-unreleased-model"))

    assert call.input_tokens == 1_000_000
    assert call.cost_usd is None
    assert call.price_source == "unknown_model"
    assert recorder.summary()["cost_usd"] is None


def test_missing_usage_metadata_does_not_fabricate_cost() -> None:
    recorder = UsageRecorder()
    call = _record(recorder, **_call_kwargs(input_tokens=None, output_tokens=None))

    assert call.input_tokens == 0
    assert call.cost_usd is None
    assert call.price_source == "no_usage_metadata"


def test_record_call_without_recorder_is_a_noop() -> None:
    # 요청 스코프 밖(스크립트 직접 실행 등)에서도 터지지 않아야 합니다.
    assert record_call(**_call_kwargs()) is None


def test_writer_emits_per_call_lines_and_a_total(tmp_path: Path) -> None:
    recorder = UsageRecorder(feature="wordbook")
    _record(recorder, **_call_kwargs())
    _record(recorder, **_call_kwargs(label="wordbook_expand"))

    UsageLogWriter(tmp_path).write(recorder)

    files = list(tmp_path.glob("usage-*.log"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert lines[0].count("| call  |") == 1
    assert "label=wordbook " in lines[0]
    assert "seq=1/2" in lines[0]
    assert lines[2].count("| TOTAL |") == 1
    assert "input_tokens=2000000" in lines[2]
    assert "cost_usd=3.500000" in lines[2]


def test_writer_appends_to_the_same_daily_file(tmp_path: Path) -> None:
    writer = UsageLogWriter(tmp_path)
    for _ in range(2):
        recorder = UsageRecorder(feature="wordbook")
        _record(recorder, **_call_kwargs())
        writer.write(recorder)

    files = list(tmp_path.glob("usage-*.log"))
    assert len(files) == 1
    assert len(files[0].read_text(encoding="utf-8").strip().split("\n")) == 4


def test_writer_adds_krw_only_when_rate_is_set(tmp_path: Path) -> None:
    recorder = UsageRecorder(feature="wordbook")
    _record(recorder, **_call_kwargs())

    UsageLogWriter(tmp_path / "off").write(recorder)
    UsageLogWriter(tmp_path / "on", usd_krw_rate=1400).write(recorder)

    off = next((tmp_path / "off").glob("*.log")).read_text(encoding="utf-8")
    on = next((tmp_path / "on").glob("*.log")).read_text(encoding="utf-8")
    assert "cost_krw" not in off
    assert "cost_krw=2450.0" in on


def test_writer_skips_requests_with_no_llm_calls(tmp_path: Path) -> None:
    UsageLogWriter(tmp_path).write(UsageRecorder(feature="problems"))

    assert list(tmp_path.glob("*.log")) == []


def test_configured_model_has_a_price_entry() -> None:
    # 기본 모델의 단가가 표에서 빠지면 비용이 조용히 비어버립니다.
    from backend.core.config import Settings

    assert resolve_price(Settings().gemini_model) is not None
    assert MODEL_PRICES


def test_usage_survives_the_thread_executor(tmp_path: Path, monkeypatch) -> None:
    """recorder는 contextvar로 전달됩니다.

    에이전트는 ThreadPoolExecutor에서 도는데 run_in_executor는 context를 자동으로
    넘기지 않습니다. copy_context() 처리가 빠지면 이 테스트가 먼저 깨집니다.
    """
    from fastapi.testclient import TestClient

    import backend.main as main_module

    from backend.apis import deps
    from backend.core.config import Settings
    from backend.llm.clients import MockLLMClient
    from tests.fixtures import PASSAGE

    settings = Settings(APP_ENV="test", USE_LLM_GENERATION=True, GOOGLE_API_KEY="k")

    class UsageReportingMock(MockLLMClient):
        """토큰 사용량을 돌려주는 provider 흉내."""

        provider_label = "Gemini"

        def generate_json(self, prompt: str, schema: dict | None = None, label: str = "-") -> dict:
            self._record_usage(
                model="gemini-3-flash-preview",
                label=label,
                input_tokens=1000,
                output_tokens=2000,
                elapsed_ms=10.0,
            )
            return dict(self.payload)

    agent = deps.WordbookAgent(
        llm_client=UsageReportingMock(
            settings=settings,
            payload={"entries": [{"headword": "evidence", "senses": []}]},
        ),
        settings=settings,
    )
    monkeypatch.setattr(deps, "wordbook_agent", agent)
    monkeypatch.setattr(deps, "usage_log_writer", UsageLogWriter(tmp_path))
    monkeypatch.setattr(deps.settings, "enable_usage_log", True)

    response = TestClient(main_module.app).post("/api/v1/wordbook", json={"passage": PASSAGE})
    assert response.status_code == 200

    written = list(tmp_path.glob("usage-*.log"))
    assert written, "워커 스레드의 LLM 호출이 사용량 로그에 잡히지 않았습니다."
    body = written[0].read_text(encoding="utf-8")
    assert "feature=wordbook" in body
    assert "| TOTAL |" in body
    assert "input_tokens=1000" in body
