from __future__ import annotations

import asyncio
import contextvars
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """스트리밍으로 내보낼 진행 상황 한 건."""

    phase: str
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"phase": self.phase}
        if self.message:
            payload["message"] = self.message
        if self.data:
            payload.update(self.data)
        return payload


class ProgressEmitter:
    """워커 스레드에서 이벤트 루프의 큐로 진행 상황을 밀어 넣습니다.

    에이전트는 동기 코드라 스레드에서 돌고, 소비자는 async 제너레이터입니다.
    그래서 `call_soon_threadsafe`로 넘겨야 합니다.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
        self._loop = loop
        self._queue = queue

    def emit(self, event: ProgressEvent) -> None:
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            # 루프가 이미 닫혔으면 진행 상황은 버립니다. 생성 자체는 계속됩니다.
            logger.debug("Progress event dropped after loop shutdown: %s", event.phase)


_current_emitter: contextvars.ContextVar[ProgressEmitter | None] = contextvars.ContextVar(
    "progress_emitter", default=None
)


def set_emitter(emitter: ProgressEmitter | None):
    return _current_emitter.set(emitter)


def reset_emitter(token) -> None:
    _current_emitter.reset(token)


def emit_progress(phase: str, message: str = "", **data: Any) -> None:
    """현재 요청이 스트리밍 중이면 진행 상황을 내보냅니다.

    스트리밍이 아니면 아무 일도 하지 않으므로, 에이전트 코드에서 조건 없이 불러도 됩니다.
    """
    emitter = _current_emitter.get()
    if emitter is None:
        return
    emitter.emit(ProgressEvent(phase=phase, message=message, data=data))
