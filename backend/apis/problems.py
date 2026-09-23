"""저장된 변형문항의 보관·조회."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.apis import deps
from backend.core.errors import PersistenceError
from backend.schemas.base import GenerateRequest
from backend.schemas.storage import ProblemType, SavedProblemRecord
from backend.schemas.wordbook_storage import SaveProblemRequest

router = APIRouter()


@router.post(
    "/api/v1/problems",
    response_model=SavedProblemRecord,
    status_code=201,
    summary="생성한 문항을 개인DB에 저장",
    description=(
        "화면에서 \"사용\"을 눌렀을 때 호출합니다.\n\n"
        "생성 엔드포인트는 더 이상 자동 저장하지 않습니다. 이 엔드포인트를 호출해야만 개인DB에 들어갑니다.\n"
        "`request`는 생성에 사용한 요청 원본, `result`는 화면에서 확인한 결과를 그대로 넣습니다."
    ),
)
async def save_problem(payload: SaveProblemRequest) -> SavedProblemRecord:
    if not deps.settings.enable_problem_persistence:
        raise HTTPException(status_code=409, detail="문항 저장이 비활성화되어 있습니다(ENABLE_PROBLEM_PERSISTENCE).")

    problem_type = str(payload.result.get("type") or "")
    model = deps.PROBLEM_RESULT_MODELS.get(problem_type)
    if model is None:
        raise HTTPException(status_code=422, detail=f"알 수 없는 문항 유형입니다: {problem_type!r}")

    try:
        generate_request = GenerateRequest.model_validate(payload.request)
        result = model.model_validate(payload.result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"저장할 문항 형식이 올바르지 않습니다: {exc}") from exc

    try:
        return await deps.run_sync(deps.problem_persistence.persist, request=generate_request, result=result)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"문항 저장 실패: {exc}") from exc


@router.get(
    "/api/v1/problems",
    response_model=list[SavedProblemRecord],
    summary="저장된 문제 목록 조회",
    description="로컬 문제 저장소(`backend/problems`)에 저장된 변형문제를 최신순으로 조회합니다.",
)
async def list_saved_problems(
    problem_type: ProblemType | None = Query(default=None, description="특정 문제 유형만 조회"),
    limit: int = Query(default=100, ge=1, le=500, description="최대 조회 개수"),
) -> list[SavedProblemRecord]:
    try:
        return await deps.run_sync(deps.problem_store.list_records, problem_type=problem_type, limit=limit)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"Problem listing failed: {exc}") from exc


@router.get(
    "/api/v1/problems/{problem_uid}",
    response_model=SavedProblemRecord,
    summary="저장된 문제 상세 조회",
    description="문제 저장 레코드 고유 ID로 저장된 변형문제를 조회합니다.",
)
async def get_saved_problem(problem_uid: str) -> SavedProblemRecord:
    try:
        record = await deps.run_sync(deps.problem_store.get_record, problem_uid)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"Problem lookup failed: {exc}") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Saved problem not found.")
    return record
