"""요청 단위 미들웨어."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from backend.apis import deps
from backend.core.usage import UsageRecorder, reset_recorder, set_recorder

logger = logging.getLogger(__name__)


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def track_llm_usage(request: Request, call_next):
        """요청 하나 동안의 LLM 토큰 사용량과 비용을 모아 `problem_log/`에 남깁니다."""
        if not deps.settings.enable_usage_log:
            return await call_next(request)

        recorder = UsageRecorder(feature=request.url.path.rsplit("/", 1)[-1] or "-")
        token = set_recorder(recorder)
        try:
            return await call_next(request)
        finally:
            reset_recorder(token)
            if recorder.calls:
                deps.usage_log_writer.write(recorder)
                logger.info("LLM usage: %s", recorder.summary())
