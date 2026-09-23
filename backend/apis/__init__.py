"""HTTP 경계. FastAPI 를 import 하는 곳은 이 패키지 안으로 제한합니다.

라우터를 추가할 때는 이 파일의 `ROUTERS` 에만 등록하면 됩니다.
`main.py` 는 건드리지 마세요.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.apis import generation, health, problems, streaming, wordbooks
from backend.apis.middleware import register_middleware

# 등록 순서 = Swagger 문서에 표시되는 순서.
ROUTERS = (
    ("상태", health.router),
    ("문항 생성", generation.router),
    ("문항 보관", problems.router),
    ("핵심단어장", wordbooks.router),
    ("스트리밍", streaming.router),
)


def register(app: FastAPI) -> None:
    register_middleware(app)
    for _label, router in ROUTERS:
        app.include_router(router)


__all__ = ["ROUTERS", "register"]
