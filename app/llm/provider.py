from app.core.config import Settings
from app.llm.client import LLMClient, MockLLMClient


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.app_env == "test":
        return MockLLMClient(settings=settings)
    return LLMClient(settings=settings)
