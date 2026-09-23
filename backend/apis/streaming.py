"""SSE 스트리밍 생성. 진행 상황을 흘려보냅니다."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.apis import deps
import asyncio
import contextvars
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncIterator

from fastapi.responses import StreamingResponse

from backend.core.errors import GenerationError, InputValidationError, PersistenceError
from backend.core.progress import ProgressEmitter, reset_emitter, set_emitter
from backend.schemas.base import GenerateRequest
from backend.schemas.storage import ProblemType
from backend.schemas.wordbook import WordbookRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse(event: str, payload: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_agent(agent: Any, request: Any) -> AsyncIterator[str]:
    """에이전트를 워커 스레드에서 돌리며 진행 상황을 SSE로 흘려보냅니다.

    생성 자체는 LLM 호출 한두 번이라 토큰 단위 스트리밍이 불가능합니다.
    대신 단계별 진행 상황과 중간 결과를 내보내 체감 대기 시간을 줄입니다.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    emitter = ProgressEmitter(loop, queue)

    def run() -> Any:
        token = set_emitter(emitter)
        try:
            # 비스트리밍 경로(_run_agent)와 동일한 전처리를 반드시 거쳐야 합니다.
            # 여기서 빠뜨리면 UI가 쓰는 경로에서만 동의어 교체가 조용히 무시됩니다.
            prepared, swaps = deps.apply_synonym_swap(agent, request)
            problem = agent.generate(prepared)
            if swaps:
                deps.attach_swap_meta(problem, swaps)
            return problem
        finally:
            reset_emitter(token)

    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, lambda: ctx.run(run))
        task = asyncio.ensure_future(future)

        yield _sse("status", {"phase": "start", "message": "요청을 시작했습니다..."})

        while True:
            drain = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({task, drain}, return_when=asyncio.FIRST_COMPLETED)

            if drain in done:
                event = drain.result()
                yield _sse("partial" if event.phase == "partial" else "status", event.to_payload())
                continue

            drain.cancel()
            # 생성이 끝났습니다. 큐에 남은 진행 상황을 먼저 비웁니다.
            while not queue.empty():
                event = queue.get_nowait()
                yield _sse("partial" if event.phase == "partial" else "status", event.to_payload())
            break

        try:
            result = task.result()
        except InputValidationError as exc:
            yield _sse("error", {"detail": str(exc), "status": 422})
            return
        except (GenerationError, PersistenceError) as exc:
            yield _sse("error", {"detail": str(exc), "status": 500})
            return
        except Exception as exc:  # pragma: no cover
            logger.exception("Streaming generation failed.")
            yield _sse("error", {"detail": f"생성 실패: {exc}", "status": 502})
            return

        yield _sse("done", result.model_dump(mode="json"))


_STREAM_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # nginx 등 프록시가 SSE를 버퍼링하면 스트리밍 효과가 사라집니다.
    "X-Accel-Buffering": "no",
}


@router.post(
    "/api/v1/stream/{problem_type}",
    summary="문항 생성(스트리밍)",
    description=(
        "문항을 생성하면서 진행 상황을 SSE로 흘려보냅니다.\n\n"
        "이벤트: `status`(진행 단계), `done`(최종 결과), `error`(실패).\n"
        "결과는 자동 저장되지 않습니다. `POST /api/v1/problems`로 따로 저장하세요."
    ),
)
async def stream_problem(problem_type: ProblemType, request: GenerateRequest) -> StreamingResponse:
    agent = deps.PROBLEM_AGENTS.get(problem_type)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"지원하지 않는 문항 유형입니다: {problem_type}")
    return StreamingResponse(
        _stream_agent(agent, request),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )


@router.post(
    "/api/v1/stream-wordbook",
    summary="핵심단어장 생성(스트리밍)",
    description=(
        "단어장을 만들면서 진행 상황을 SSE로 흘려보냅니다.\n\n"
        "이벤트: `status`(후보 추출/생성/보강 단계), `partial`(1차 정리 결과), `done`(최종), `error`.\n"
        "결과는 자동 저장되지 않습니다. `POST /api/v1/wordbooks`로 따로 저장하세요."
    ),
)
async def stream_wordbook(request: WordbookRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_agent(deps.wordbook_agent, request),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )
