from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.agents.blank_agent import BlankAgent
from app.agents.grammar_agent import GrammarAgent
from app.agents.implicit_agent import ImplicitAgent
from app.agents.insertion_agent import InsertionAgent
from app.agents.irrelevant_agent import IrrelevantAgent
from app.agents.order_agent import OrderAgent
from app.agents.reference_agent import ReferenceAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.title_agent import TitleAgent
from app.agents.topic_agent import TopicAgent
from app.agents.vocab_agent import VocabAgent
from app.core.config import get_settings
from app.core.errors import GenerationError, InputValidationError
from app.core.logging import configure_logging
from app.llm.provider import build_llm_client
from app.schemas.base import GenerateRequest
from app.schemas.blank import BlankResponse
from app.schemas.grammar import GrammarResponse
from app.schemas.implicit import ImplicitResponse
from app.schemas.insertion import InsertionResponse
from app.schemas.irrelevant import IrrelevantResponse
from app.schemas.order import OrderResponse
from app.schemas.reference import ReferenceResponse
from app.schemas.summary import SummaryResponse
from app.schemas.title import TitleResponse
from app.schemas.topic import TopicResponse
from app.schemas.vocab import VocabResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

COMMON_USAGE = """
### 사용 방법
- `passage`에 영어 지문 원문만 넣으면 기본 생성이 가능합니다.
- 난이도는 `difficulty`로 조절합니다: `easy`, `mid`, `hard`
- 해설은 `explain=true/false`로 켜고 끌 수 있습니다.
- 지시문 언어는 `return_korean_stem`으로 조절합니다.
- 현재 선지 수는 `choices=5` 고정입니다.
"""

app = FastAPI(
    title="Exam Item Generator",
    version="0.1.0",
    description=(
        "영어 지문 1개를 받아 학평 스타일 문제 JSON을 생성하는 API입니다.\n\n"
        "비전공자 사용자를 위해 Swagger 문서(`/docs`)에 유형별 설명을 제공합니다."
    ),
)

llm_client = build_llm_client(settings)
logger.info(
    "LLM bootstrap: client=%s app_env=%s use_llm_generation=%s api_key_set=%s model=%s",
    llm_client.__class__.__name__,
    settings.app_env,
    settings.use_llm_generation,
    bool(settings.resolved_api_key),
    settings.gemini_model,
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


@app.get(
    "/health",
    summary="서버 상태 확인",
    description="서버가 살아있는지 확인합니다. 정상일 때 `{ \"status\": \"ok\" }`를 반환합니다.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _run_agent(agent: Any, request: GenerateRequest):
    try:
        if hasattr(agent, "agenerate"):
            return await agent.agenerate(request)
        return await run_in_threadpool(agent.generate, request)
    except InputValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc


@app.post(
    "/api/v1/title",
    response_model=TitleResponse,
    summary="제목 문제 생성",
    description=(
        "지문의 전체 주제를 가장 잘 나타내는 제목 고르기 문항을 생성합니다.\n\n"
        "추천 상황: 지문의 중심 생각 파악 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_title(request: GenerateRequest) -> TitleResponse:
    return await _run_agent(title_agent, request)


@app.post(
    "/api/v1/topic",
    response_model=TopicResponse,
    summary="주제 문제 생성",
    description=(
        "지문의 핵심 논점(주제)을 고르는 문항을 생성합니다.\n"
        "추천 상황: 글 전체의 화제 범위 파악 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_topic(request: GenerateRequest) -> TopicResponse:
    return await _run_agent(topic_agent, request)


@app.post(
    "/api/v1/summary",
    response_model=SummaryResponse,
    summary="요약문 문제 생성",
    description=(
        "(A)(B) 빈칸이 있는 요약 완성형 문항을 생성합니다.\n"
        "추천 상황: 글의 구조와 결론 압축 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_summary(request: GenerateRequest) -> SummaryResponse:
    return await _run_agent(summary_agent, request)


@app.post(
    "/api/v1/implicit",
    response_model=ImplicitResponse,
    summary="함축의미추론 문제 생성",
    description=(
        "밑줄 친 표현의 함축 의미를 추론하는 문항을 생성합니다.\n"
        "추천 상황: 관용/비유/문맥 의미 해석 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_implicit(request: GenerateRequest) -> ImplicitResponse:
    return await _run_agent(implicit_agent, request)


@app.post(
    "/api/v1/insertion",
    response_model=InsertionResponse,
    summary="문장 삽입 문제 생성",
    description=(
        "주어진 문장이 본문 어디(①~⑤)에 들어가야 자연스러운지 묻는 문항입니다.\n"
        "추천 상황: 연결어, 지시어, 문맥 흐름 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_insertion(request: GenerateRequest) -> InsertionResponse:
    return await _run_agent(insertion_agent, request)


@app.post(
    "/api/v1/order",
    response_model=OrderResponse,
    summary="글의 순서 문제 생성",
    description=(
        "(A)(B)(C) 문단 배열 순서를 고르는 문항을 생성합니다.\n"
        "추천 상황: 글의 논리 전개 순서 파악 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_order(request: GenerateRequest) -> OrderResponse:
    return await _run_agent(order_agent, request)


@app.post(
    "/api/v1/irrelevant",
    response_model=IrrelevantResponse,
    summary="흐름과 무관한 문장 찾기 문제 생성",
    description=(
        "지문 흐름과 맞지 않는 문장을 ①~⑤ 중에서 고르는 문항을 생성합니다.\n"
        "추천 상황: 문단 논리 축 파악 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_irrelevant(request: GenerateRequest) -> IrrelevantResponse:
    return await _run_agent(irrelevant_agent, request)


@app.post(
    "/api/v1/blank",
    response_model=BlankResponse,
    summary="빈칸 추론 문제 생성",
    description=(
        "지문의 핵심 논리에 해당하는 부분을 빈칸으로 만들어 추론하는 문항입니다.\n"
        "추천 상황: 핵심 문장/결론 추론 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_blank(request: GenerateRequest) -> BlankResponse:
    return await _run_agent(blank_agent, request)


@app.post(
    "/api/v1/reference",
    response_model=ReferenceResponse,
    summary="지칭 추론 문제 생성",
    description=(
        "(1)~(5) 지시어/대명사가 무엇을 가리키는지 파악하는 문항입니다.\n"
        "추천 상황: 대명사, 지시어 해석 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_reference(request: GenerateRequest) -> ReferenceResponse:
    return await _run_agent(reference_agent, request)


@app.post(
    "/api/v1/vocab",
    response_model=VocabResponse,
    summary="어휘 쓰임 문제 생성",
    description=(
        "문맥상 어휘 쓰임이 부적절한 부분(①~⑤)을 찾는 문항을 생성합니다.\n"
        "추천 상황: 문맥 기반 어휘력 연습\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_vocab(request: GenerateRequest) -> VocabResponse:
    return await _run_agent(vocab_agent, request)


@app.post(
    "/api/v1/grammar",
    response_model=GrammarResponse,
    summary="어법 문제 생성",
    description=(
        "밑줄 ①~⑤ 중 어법상 틀린 부분을 찾는 문항을 생성합니다.\n"
        "추천 상황: 수일치, 시제, 관계사 등 문법 점검\n"
        f"{COMMON_USAGE}"
    ),
)
async def generate_grammar(request: GenerateRequest) -> GrammarResponse:
    return await _run_agent(grammar_agent, request)
