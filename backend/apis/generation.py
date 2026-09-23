"""변형문항 생성 11종. 생성만 하고 저장하지 않습니다."""

from __future__ import annotations

from fastapi import APIRouter

from backend.apis import deps
from backend.schemas.base import GenerateRequest
from backend.schemas.title import TitleResponse
from backend.schemas.topic import TopicResponse
from backend.schemas.summary import SummaryResponse
from backend.schemas.implicit import ImplicitResponse
from backend.schemas.insertion import InsertionResponse
from backend.schemas.order import OrderResponse
from backend.schemas.irrelevant import IrrelevantResponse
from backend.schemas.blank import BlankResponse
from backend.schemas.reference import ReferenceResponse
from backend.schemas.vocab import VocabResponse
from backend.schemas.grammar import GrammarResponse

router = APIRouter()


@router.post(
    "/api/v1/title",
    response_model=TitleResponse,
    summary="제목 문제 생성",
    description=(
        "지문의 전체 주제를 가장 잘 나타내는 제목 고르기 문항을 생성합니다.\n\n"
        "추천 상황: 지문의 중심 생각 파악 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_title(request: GenerateRequest) -> TitleResponse:
    return await deps.run_agent(deps.title_agent, request)


@router.post(
    "/api/v1/topic",
    response_model=TopicResponse,
    summary="주제 문제 생성",
    description=(
        "지문의 핵심 논점(주제)을 고르는 문항을 생성합니다.\n"
        "추천 상황: 글 전체의 화제 범위 파악 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_topic(request: GenerateRequest) -> TopicResponse:
    return await deps.run_agent(deps.topic_agent, request)


@router.post(
    "/api/v1/summary",
    response_model=SummaryResponse,
    summary="요약문 문제 생성",
    description=(
        "(A)(B) 빈칸이 있는 요약 완성형 문항을 생성합니다.\n"
        "추천 상황: 글의 구조와 결론 압축 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_summary(request: GenerateRequest) -> SummaryResponse:
    return await deps.run_agent(deps.summary_agent, request)


@router.post(
    "/api/v1/implicit",
    response_model=ImplicitResponse,
    summary="함축의미추론 문제 생성",
    description=(
        "밑줄 친 표현의 함축 의미를 추론하는 문항을 생성합니다.\n"
        "추천 상황: 관용/비유/문맥 의미 해석 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_implicit(request: GenerateRequest) -> ImplicitResponse:
    return await deps.run_agent(deps.implicit_agent, request)


@router.post(
    "/api/v1/insertion",
    response_model=InsertionResponse,
    summary="문장 삽입 문제 생성",
    description=(
        "주어진 문장이 본문 어디(①~⑤)에 들어가야 자연스러운지 묻는 문항입니다.\n"
        "추천 상황: 연결어, 지시어, 문맥 흐름 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_insertion(request: GenerateRequest) -> InsertionResponse:
    return await deps.run_agent(deps.insertion_agent, request)


@router.post(
    "/api/v1/order",
    response_model=OrderResponse,
    summary="글의 순서 문제 생성",
    description=(
        "(A)(B)(C) 문단 배열 순서를 고르는 문항을 생성합니다.\n"
        "추천 상황: 글의 논리 전개 순서 파악 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_order(request: GenerateRequest) -> OrderResponse:
    return await deps.run_agent(deps.order_agent, request)


@router.post(
    "/api/v1/irrelevant",
    response_model=IrrelevantResponse,
    summary="흐름과 무관한 문장 찾기 문제 생성",
    description=(
        "지문 흐름과 맞지 않는 문장을 ①~⑤ 중에서 고르는 문항을 생성합니다.\n"
        "추천 상황: 문단 논리 축 파악 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_irrelevant(request: GenerateRequest) -> IrrelevantResponse:
    return await deps.run_agent(deps.irrelevant_agent, request)


@router.post(
    "/api/v1/blank",
    response_model=BlankResponse,
    summary="빈칸 추론 문제 생성",
    description=(
        "지문의 핵심 논리에 해당하는 부분을 빈칸으로 만들어 추론하는 문항입니다.\n"
        "추천 상황: 핵심 문장/결론 추론 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_blank(request: GenerateRequest) -> BlankResponse:
    return await deps.run_agent(deps.blank_agent, request)


@router.post(
    "/api/v1/reference",
    response_model=ReferenceResponse,
    summary="지칭 추론 문제 생성",
    description=(
        "(1)~(5) 지시어/대명사가 무엇을 가리키는지 파악하는 문항입니다.\n"
        "추천 상황: 대명사, 지시어 해석 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_reference(request: GenerateRequest) -> ReferenceResponse:
    return await deps.run_agent(deps.reference_agent, request)


@router.post(
    "/api/v1/vocab",
    response_model=VocabResponse,
    summary="어휘 쓰임 문제 생성",
    description=(
        "문맥상 어휘 쓰임이 부적절한 부분(①~⑤)을 찾는 문항을 생성합니다.\n"
        "추천 상황: 문맥 기반 어휘력 연습\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_vocab(request: GenerateRequest) -> VocabResponse:
    return await deps.run_agent(deps.vocab_agent, request)


@router.post(
    "/api/v1/grammar",
    response_model=GrammarResponse,
    summary="어법 문제 생성",
    description=(
        "밑줄 ①~⑤ 중 어법상 틀린 부분을 찾는 문항을 생성합니다.\n"
        "추천 상황: 수일치, 시제, 관계사 등 문법 점검\n"
        f"{deps.COMMON_USAGE}"
    ),
)
async def generate_grammar(request: GenerateRequest) -> GrammarResponse:
    return await deps.run_agent(deps.grammar_agent, request)
