from __future__ import annotations

import contextvars
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

# 100만 토큰당 USD 단가.
#
# 출처/기준일을 반드시 같이 적어 주세요. 단가는 수시로 바뀌고, 바뀐 걸 모르면
# 로그에 남는 비용이 조용히 틀립니다. 확신이 없으면 .env에서
# LLM_INPUT_PRICE_PER_MTOK / LLM_OUTPUT_PRICE_PER_MTOK 로 덮어쓰세요.
#
# 조회일: 2026-09-16
# - gemini-3-flash-preview: pricepertoken.com 기준 Google 직판가 $0.25 / $1.50
#   (Google 공식 pricing 페이지에는 preview 모델이 별도로 표기되어 있지 않습니다.)
# - gemini-3.6/3.7/3.8-flash: ai.google.dev/gemini-api/docs/pricing 기준 $0.75 / $3.75
# - gemini-3.5-flash: 같은 페이지 기준 $1.50 / $9.00
MODEL_PRICES: dict[str, tuple[str, str]] = {
    "gemini-3-flash-preview": ("0.25", "1.50"),
    "gemini-3.8-flash": ("0.75", "3.75"),
    "gemini-3.7-flash": ("0.75", "3.75"),
    "gemini-3.6-flash": ("0.75", "3.75"),
    "gemini-3.5-flash": ("1.50", "9.00"),
}

_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class ModelPrice:
    """100만 토큰당 USD 단가."""

    input_per_mtok: Decimal
    output_per_mtok: Decimal
    source: str

    def cost_usd(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            Decimal(input_tokens) * self.input_per_mtok + Decimal(output_tokens) * self.output_per_mtok
        ) / _MILLION


def resolve_price(
    model: str,
    *,
    input_override: float = 0.0,
    output_override: float = 0.0,
) -> ModelPrice | None:
    """모델 단가를 찾습니다. 모르는 모델이면 None을 돌려 비용 계산을 생략합니다."""
    if input_override > 0 or output_override > 0:
        return ModelPrice(
            input_per_mtok=Decimal(str(input_override)),
            output_per_mtok=Decimal(str(output_override)),
            source="env_override",
        )

    normalized = (model or "").strip().lower()
    if normalized in MODEL_PRICES:
        raw_in, raw_out = MODEL_PRICES[normalized]
        return ModelPrice(Decimal(raw_in), Decimal(raw_out), source="table")

    # "gemini-3-flash-preview-09-2026" 처럼 접미사가 붙어도 잡히도록 접두 일치를 봅니다.
    for key, (raw_in, raw_out) in MODEL_PRICES.items():
        if normalized.startswith(key):
            return ModelPrice(Decimal(raw_in), Decimal(raw_out), source="table_prefix")

    return None


@dataclass
class LLMCall:
    """LLM 호출 한 번의 사용량."""

    provider: str
    model: str
    label: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: float
    cost_usd: Decimal | None
    price_source: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class UsageRecorder:
    """요청 하나 동안의 LLM 호출을 모읍니다."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    feature: str = "-"
    calls: list[LLMCall] = field(default_factory=list)
    # provider 로 실제 나간 시도 횟수. `calls` 와 달리 응답을 못 받은 시도도 셉니다.
    # 요청 하나가 재시도로 폭주하는 것을 막는 예산 계산에 씁니다.
    attempts: int = 0

    def add(self, call: LLMCall) -> None:
        self.calls.append(call)

    @property
    def input_tokens(self) -> int:
        return sum(call.input_tokens for call in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(call.output_tokens for call in self.calls)

    @property
    def elapsed_ms(self) -> float:
        return sum(call.elapsed_ms for call in self.calls)

    @property
    def cost_usd(self) -> Decimal | None:
        priced = [call.cost_usd for call in self.calls if call.cost_usd is not None]
        if not priced:
            return None
        return sum(priced, Decimal("0"))

    def summary(self) -> dict:
        cost = self.cost_usd
        return {
            "request_id": self.request_id,
            "feature": self.feature,
            "calls": len(self.calls),
            "attempts": self.attempts,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": None if cost is None else float(cost),
            "elapsed_ms": round(self.elapsed_ms, 1),
        }


_current_recorder: contextvars.ContextVar[UsageRecorder | None] = contextvars.ContextVar(
    "llm_usage_recorder", default=None
)


def current_recorder() -> UsageRecorder | None:
    return _current_recorder.get()


def set_recorder(recorder: UsageRecorder | None):
    return _current_recorder.set(recorder)


def reset_recorder(token) -> None:
    _current_recorder.reset(token)


def note_attempt() -> int:
    """provider 호출을 한 번 더 시도했음을 기록하고 누적 시도 수를 돌려줍니다."""
    recorder = current_recorder()
    if recorder is None:
        return 0
    recorder.attempts += 1
    return recorder.attempts


def attempts_made() -> int:
    """현재 요청에서 지금까지 나간 provider 호출 시도 수."""
    recorder = current_recorder()
    return 0 if recorder is None else recorder.attempts


def record_call(
    *,
    provider: str,
    model: str,
    label: str,
    input_tokens: int | None,
    output_tokens: int | None,
    elapsed_ms: float,
    input_price_override: float = 0.0,
    output_price_override: float = 0.0,
) -> LLMCall | None:
    """현재 요청 스코프에 호출 하나를 기록합니다.

    토큰 수를 못 받았으면(=provider가 usage를 안 주면) 비용을 지어내지 않고 0으로 둡니다.
    """
    recorder = current_recorder()
    if recorder is None:
        return None

    tokens_in = int(input_tokens or 0)
    tokens_out = int(output_tokens or 0)

    price = resolve_price(
        model,
        input_override=input_price_override,
        output_override=output_price_override,
    )
    if price is None:
        cost = None
        price_source = "unknown_model"
        logger.warning(
            "No price entry for model %r. Token usage is logged but cost is left blank. "
            "Add it to MODEL_PRICES or set LLM_INPUT_PRICE_PER_MTOK/LLM_OUTPUT_PRICE_PER_MTOK.",
            model,
        )
    elif tokens_in == 0 and tokens_out == 0:
        cost = None
        price_source = "no_usage_metadata"
    else:
        cost = price.cost_usd(tokens_in, tokens_out)
        price_source = price.source

    call = LLMCall(
        provider=provider,
        model=model,
        label=label,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        elapsed_ms=elapsed_ms,
        cost_usd=cost,
        price_source=price_source,
    )
    recorder.add(call)
    return call


class UsageLogWriter:
    """`problem_log/` 아래에 날짜별 `.log` 파일로 사용량을 남깁니다."""

    def __init__(self, log_dir: str | Path, *, usd_krw_rate: float = 0.0) -> None:
        self.log_dir = Path(log_dir)
        self.usd_krw_rate = usd_krw_rate
        self._lock = threading.Lock()

    def _path_for(self, moment: datetime) -> Path:
        return self.log_dir / f"usage-{moment.strftime('%Y-%m-%d')}.log"

    def _money(self, cost: Decimal | None) -> str:
        if cost is None:
            return "cost_usd=- "
        text = f"cost_usd={cost:.6f}"
        if self.usd_krw_rate > 0:
            krw = cost * Decimal(str(self.usd_krw_rate))
            text += f" cost_krw={krw:.1f}"
        return text

    def write(self, recorder: UsageRecorder) -> None:
        if not recorder.calls:
            return

        moment = datetime.now(timezone.utc).astimezone()
        stamp = moment.isoformat(timespec="seconds")
        lines: list[str] = []

        for index, call in enumerate(recorder.calls, start=1):
            lines.append(
                f"{stamp} | call  | request_id={recorder.request_id}"
                f" feature={recorder.feature}"
                f" seq={index}/{len(recorder.calls)}"
                f" provider={call.provider}"
                f" model={call.model}"
                f" label={call.label}"
                f" input_tokens={call.input_tokens}"
                f" output_tokens={call.output_tokens}"
                f" {self._money(call.cost_usd)}"
                f" price_source={call.price_source}"
                f" elapsed_ms={call.elapsed_ms:.1f}"
            )

        summary = recorder.summary()
        lines.append(
            f"{stamp} | TOTAL | request_id={recorder.request_id}"
            f" feature={recorder.feature}"
            f" calls={summary['calls']}"
            f" input_tokens={summary['input_tokens']}"
            f" output_tokens={summary['output_tokens']}"
            f" total_tokens={summary['total_tokens']}"
            f" {self._money(recorder.cost_usd)}"
            f" elapsed_ms={summary['elapsed_ms']}"
        )

        payload = "\n".join(lines) + "\n"
        try:
            with self._lock:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                with self._path_for(moment).open("a", encoding="utf-8") as fp:
                    fp.write(payload)
        except OSError as exc:
            # 사용량 로깅 실패가 실제 요청을 깨뜨려서는 안 됩니다.
            logger.warning("Failed to write usage log: %s", exc)
