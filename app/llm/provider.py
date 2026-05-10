from app.core.config import Settings
from app.core.errors import GenerationError
from app.llm.client import CodexCliLLMClient, GeminiLLMClient, MockLLMClient, OpenAILLMClient


def build_llm_client(settings: Settings):
    if settings.app_env == "test":
        return MockLLMClient(settings=settings)

    provider = settings.normalized_llm_provider
    if provider == "gemini":
        return GeminiLLMClient(settings=settings)
    if provider == "openai":
        return OpenAILLMClient(settings=settings)
    if provider == "codex_cli":
        return CodexCliLLMClient(settings=settings)

    raise GenerationError("Unsupported LLM_PROVIDER. Use one of: gemini, openai, codex_cli.")
