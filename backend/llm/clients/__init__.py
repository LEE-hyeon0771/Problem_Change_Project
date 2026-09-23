"""LLM provider 구현.

provider 를 추가할 때는 `BaseJSONLLMClient` 를 상속해 `_generate_raw` 만 구현하고,
여기와 `backend/llm/provider.py` 의 분기에 등록하세요.
"""

from backend.llm.clients.base import BaseJSONLLMClient, CallBudgetExceeded
from backend.llm.clients.codex_cli import CodexCliLLMClient
from backend.llm.clients.gemini import GeminiLLMClient
from backend.llm.clients.mock import MockLLMClient
from backend.llm.clients.openai import OpenAILLMClient

# 기존 import 경로 호환용 별칭. 기본 provider 를 가리킵니다.
LLMClient = GeminiLLMClient

__all__ = [
    "BaseJSONLLMClient",
    "CallBudgetExceeded",
    "CodexCliLLMClient",
    "GeminiLLMClient",
    "LLMClient",
    "MockLLMClient",
    "OpenAILLMClient",
]
