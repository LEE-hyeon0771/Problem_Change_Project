"""서버 상태 확인."""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get(
    "/health",
    summary="서버 상태 확인",
    description="서버가 살아있는지 확인합니다. 정상일 때 `{ \"status\": \"ok\" }`를 반환합니다.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
