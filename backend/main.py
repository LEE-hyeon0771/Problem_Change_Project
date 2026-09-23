"""FastAPI 앱 조립.

라우트는 여기에 두지 않습니다. `backend/apis/` 안의 파일에 API 별로 나뉘어 있고,
새 라우터는 `backend/apis/__init__.py` 의 `ROUTERS` 에만 등록하면 됩니다.

런타임 객체(에이전트·저장소·설정)는 `backend/apis/deps.py` 에 있습니다.
테스트에서 교체할 때도 `backend.apis.deps` 를 patch 하세요.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend import apis

app = FastAPI(
    title="Exam Item Generator",
    version="0.1.0",
    description=(
        "영어 지문 1개를 받아 학평 스타일 문제 JSON을 생성하는 API입니다.\n\n"
        "비전공자 사용자를 위해 Swagger 문서(`/docs`)에 유형별 설명을 제공합니다."
    ),
)

apis.register(app)
