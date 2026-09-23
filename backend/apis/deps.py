"""라우터들이 공유하는 런타임 객체와 실행 헬퍼.

라우터는 반드시 `from backend.apis import deps` 로 가져와서 `deps.problem_store` 처럼
**모듈 속성으로** 접근하세요. `from ... import problem_store` 로 값을 바인딩하면
테스트에서 교체(monkeypatch)해도 라우터가 옛 객체를 계속 붙들고 있습니다.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException

from backend.agents.blank_agent import BlankAgent
from backend.agents.grammar_agent import GrammarAgent
from backend.agents.implicit_agent import ImplicitAgent
from backend.agents.insertion_agent import InsertionAgent
from backend.agents.irrelevant_agent import IrrelevantAgent
from backend.agents.order_agent import OrderAgent
from backend.agents.reference_agent import ReferenceAgent
from backend.agents.summary_agent import SummaryAgent
from backend.agents.synonym_swapper import SynonymSwapper
from backend.agents.title_agent import TitleAgent
from backend.agents.topic_agent import TopicAgent
from backend.agents.vocab_agent import VocabAgent
from backend.agents.wordbook_agent import WordbookAgent
from backend.core.config import get_settings
from backend.core.errors import GenerationError, InputValidationError, PersistenceError
from backend.core.logging import configure_logging
from backend.core.usage import UsageLogWriter
from backend.llm.provider import build_llm_client
from backend.schemas.base import GenerateRequest, ProblemResponse
from backend.schemas.blank import BlankResponse
from backend.schemas.grammar import GrammarResponse
from backend.schemas.implicit import ImplicitResponse
from backend.schemas.insertion import InsertionResponse
from backend.schemas.irrelevant import IrrelevantResponse
from backend.schemas.order import OrderResponse
from backend.schemas.reference import ReferenceResponse
from backend.schemas.summary import SummaryResponse
from backend.schemas.title import TitleResponse
from backend.schemas.topic import TopicResponse
from backend.schemas.vocab import VocabResponse
from backend.storage.persistence import ProblemPersistenceService
from backend.storage.problem_store import LocalProblemStore
from backend.storage.wordbook_store import LocalWordbookStore

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

llm_client = build_llm_client(settings)
logger.info(
    "LLM bootstrap: client=%s provider=%s app_env=%s use_llm_generation=%s credentials_set=%s model=%s",
    llm_client.__class__.__name__,
    settings.normalized_llm_provider,
    settings.app_env,
    settings.use_llm_generation,
    settings.has_llm_credentials,
    settings.active_model,
)

title_agent = TitleAgent(llm_client=llm_client, settings=settings)
topic_agent = TopicAgent(llm_client=llm_client, settings=settings)
summary_agent = SummaryAgent(llm_client=llm_client, settings=settings)
implicit_agent = ImplicitAgent(llm_client=llm_client, settings=settings)
insertion_agent = InsertionAgent(llm_client=llm_client, settings=settings)
order_agent = OrderAgent(llm_client=llm_client, settings=settings)
irrelevant_agent = IrrelevantAgent(llm_client=llm_client, settings=settings)
blank_agent = BlankAgent(llm_client=llm_client, settings=settings)
reference_agent = ReferenceAgent(llm_client=llm_client, settings=settings)
vocab_agent = VocabAgent(llm_client=llm_client, settings=settings)
grammar_agent = GrammarAgent(llm_client=llm_client, settings=settings)
wordbook_agent = WordbookAgent(llm_client=llm_client, settings=settings)
synonym_swapper = SynonymSwapper(llm_client=llm_client, settings=settings)

problem_store = LocalProblemStore()
wordbook_store = LocalWordbookStore()

PROBLEM_AGENTS: dict[str, Any] = {
    "title": title_agent,
    "topic": topic_agent,
    "summary": summary_agent,
    "implicit": implicit_agent,
    "insertion": insertion_agent,
    "order": order_agent,
    "irrelevant": irrelevant_agent,
    "blank": blank_agent,
    "reference": reference_agent,
    "vocab": vocab_agent,
    "grammar": grammar_agent,
}

# "사용" 저장 시 result JSON을 유형별 응답 모델로 되살리기 위한 표.
PROBLEM_RESULT_MODELS: dict[str, type[ProblemResponse]] = {
    "title": TitleResponse,
    "topic": TopicResponse,
    "summary": SummaryResponse,
    "implicit": ImplicitResponse,
    "insertion": InsertionResponse,
    "order": OrderResponse,
    "irrelevant": IrrelevantResponse,
    "blank": BlankResponse,
    "reference": ReferenceResponse,
    "vocab": VocabResponse,
    "grammar": GrammarResponse,
}

db_store = None
db_persistence_enabled = settings.enable_db_persistence and settings.app_env != "test"
if db_persistence_enabled:
    try:
        from backend.storage.db_store import SQLAlchemyProblemStore

        db_store = SQLAlchemyProblemStore(
            database_url=settings.database_url,
            echo=settings.database_echo,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "ENABLE_DB_PERSISTENCE=true but SQLAlchemy dependencies are missing. "
            "Install project dependencies first."
        ) from exc
elif settings.enable_db_persistence and settings.app_env == "test":
    logger.info("DB persistence is disabled in APP_ENV=test.")

problem_persistence = ProblemPersistenceService(local_store=problem_store, db_store=db_store)
usage_log_writer = UsageLogWriter(settings.usage_log_dir, usd_krw_rate=settings.usd_krw_rate)


# --------------------------------------------------------------------- 실행 헬퍼


async def run_sync(func: Any, *args: Any, **kwargs: Any):
    loop = asyncio.get_running_loop()
    # run_in_executor는 contextvars를 자동으로 넘기지 않습니다.
    # 명시적으로 복사해야 워커 스레드에서도 사용량 recorder가 보입니다.
    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, lambda: ctx.run(lambda: func(*args, **kwargs)))


def apply_synonym_swap(agent: Any, request: GenerateRequest) -> tuple[GenerateRequest, list[dict]]:
    """생성 전에 지문 단어 일부를 동의어로 교체합니다.

    생성 "후"에 바꾸면 원문 복원 검증(`validate_blank_from_original` 등)이 깨지므로
    반드시 전처리로 둡니다. 바뀐 지문이 그 문항의 원문이 됩니다.
    """
    if not getattr(request, "synonym_swap", False):
        return request, []

    problem_type = getattr(agent, "problem_type", "")
    swapped, applied = synonym_swapper.swap(
        passage=request.passage,
        difficulty=request.difficulty,
        problem_type=problem_type,
    )
    if not applied:
        return request, []

    return request.model_copy(update={"passage": swapped}), applied


def attach_swap_meta(problem: Any, swaps: list[dict]) -> None:
    """교사가 무엇이 바뀌었는지 확인하고 되돌릴 수 있도록 meta에 기록합니다."""
    meta = dict(getattr(problem, "meta", {}) or {})
    meta["synonym_swap"] = {"count": len(swaps), "swaps": swaps}
    problem.meta = meta


async def run_agent(agent: Any, request: GenerateRequest):
    """생성만 합니다. 저장은 사용자가 "사용"을 눌러 save 엔드포인트를 호출할 때만 일어납니다."""
    try:
        request, swaps = await run_sync(apply_synonym_swap, agent, request)

        if hasattr(agent, "agenerate"):
            problem = await agent.agenerate(request)
        else:
            problem = await run_sync(agent.generate, request)

        if swaps:
            attach_swap_meta(problem, swaps)
        return problem
    except InputValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail=f"Persistence failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc


COMMON_USAGE = """
### 사용 방법
- `passage`에 영어 지문 원문만 넣으면 기본 생성이 가능합니다.
- 난이도는 `difficulty`로 조절합니다: `easy`, `mid`, `hard`
- 해설은 `explain=true/false`로 켜고 끌 수 있습니다.
- 지시문 언어는 `return_korean_stem`으로 조절합니다.
- 현재 선지 수는 `choices=5`, 스타일은 `style=edu_office` 고정입니다.
- `synonym_swap=true`면 지문 단어 일부를 동의어로 바꿉니다(제목·주제·요약·빈칸·함축만).
- 생성 결과는 저장되지 않습니다. 보관하려면 `POST /api/v1/problems`를 호출하세요.
"""
