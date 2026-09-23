"""핵심단어장 생성과 보관·조회·삭제."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from backend.apis import deps
from backend.core.errors import PersistenceError
from backend.schemas.wordbook import WordbookRequest, WordbookResponse
from backend.schemas.wordbook_storage import SaveWordbookRequest, SavedWordbookRecord

router = APIRouter()


@router.post(
    "/api/v1/wordbook",
    response_model=WordbookResponse,
    summary="핵심단어장 생성",
    description=(
        "지문에서 학습할 핵심단어를 모두 추출하고, 뜻마다 품사·한국어 뜻·영어 정의와 "
        "그 뜻에 맞는 동의어/반의어를 정리해 돌려줍니다.\n\n"
        "추천 상황: 지문 학습 전 어휘 정리, 단어 시험 대비\n\n"
        "### 사용 방법\n"
        "- `passage`에 영어 지문 원문만 넣으면 기본 생성이 가능합니다.\n"
        "- `include_phrases=false`로 두면 숙어/연어를 제외합니다.\n"
        "- `max_related`로 한 뜻당 동의어/반의어 **최대** 개수를 제한합니다(1~8).\n"
        "- 단어장에는 난이도 옵션이 없습니다. 쉬운 동의어부터 정밀 근접어까지 한 목록에 담습니다.\n"
        "- 결과는 저장되지 않습니다. 보관하려면 `POST /api/v1/wordbooks`를 호출하세요."
    ),
)
async def generate_wordbook(request: WordbookRequest) -> WordbookResponse:
    return await deps.run_agent(deps.wordbook_agent, request)


@router.post(
    "/api/v1/wordbooks",
    response_model=SavedWordbookRecord,
    status_code=201,
    summary="생성한 단어장을 개인DB에 저장",
    description="단어장 화면에서 \"사용\"을 눌렀을 때 호출합니다. 이때만 개인DB에 보관됩니다.",
)
async def save_wordbook(payload: SaveWordbookRequest) -> SavedWordbookRecord:
    if not deps.settings.enable_problem_persistence:
        raise HTTPException(status_code=409, detail="저장이 비활성화되어 있습니다(ENABLE_PROBLEM_PERSISTENCE).")

    try:
        return await deps.run_sync(
            deps.wordbook_store.save,
            request=payload.request,
            result=payload.result,
            title=payload.title,
        )
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"단어장 저장 실패: {exc}") from exc


@router.get(
    "/api/v1/wordbooks",
    response_model=list[SavedWordbookRecord],
    summary="저장된 단어장 목록 조회",
    description="개인DB에 보관된 단어장을 최신순으로 조회합니다.",
)
async def list_saved_wordbooks(
    limit: int = Query(default=100, ge=1, le=500, description="최대 조회 개수"),
) -> list[SavedWordbookRecord]:
    try:
        return await deps.run_sync(deps.wordbook_store.list_records, limit=limit)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"단어장 조회 실패: {exc}") from exc


@router.get(
    "/api/v1/wordbooks/{wordbook_uid}",
    response_model=SavedWordbookRecord,
    summary="저장된 단어장 상세 조회",
)
async def get_saved_wordbook(wordbook_uid: str) -> SavedWordbookRecord:
    try:
        record = await deps.run_sync(deps.wordbook_store.get_record, wordbook_uid)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"단어장 조회 실패: {exc}") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="저장된 단어장을 찾을 수 없습니다.")
    return record


@router.delete(
    "/api/v1/wordbooks/{wordbook_uid}",
    status_code=204,
    summary="저장된 단어장 삭제",
)
async def delete_saved_wordbook(wordbook_uid: str) -> Response:
    try:
        deleted = await deps.run_sync(deps.wordbook_store.delete_record, wordbook_uid)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"단어장 삭제 실패: {exc}") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="저장된 단어장을 찾을 수 없습니다.")
    return Response(status_code=204)
