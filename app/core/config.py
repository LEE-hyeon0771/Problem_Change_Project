from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3-flash-preview", alias="GEMINI_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_reasoning_effort: str = Field(default="", alias="OPENAI_REASONING_EFFORT")
    openai_timeout_seconds: int = Field(default=120, alias="OPENAI_TIMEOUT_SECONDS")
    codex_cli_command: str = Field(default="codex", alias="CODEX_CLI_COMMAND")
    codex_cli_model: str = Field(default="", alias="CODEX_CLI_MODEL")
    codex_cli_timeout_seconds: int = Field(default=300, alias="CODEX_CLI_TIMEOUT_SECONDS")

    default_temperature: float = Field(default=0.6, alias="DEFAULT_TEMPERATURE")
    default_max_output_tokens: int = Field(default=20000, alias="DEFAULT_MAX_OUTPUT_TOKENS")

    use_llm_generation: bool = Field(default=True, alias="USE_LLM_GENERATION")
    enable_self_check: bool = Field(default=False, alias="ENABLE_SELF_CHECK")
    self_check_max_retry: int = Field(default=1, alias="SELF_CHECK_MAX_RETRY")

    enable_problem_persistence: bool = Field(default=True, alias="ENABLE_PROBLEM_PERSISTENCE")
    enable_db_persistence: bool = Field(default=False, alias="ENABLE_DB_PERSISTENCE")
    database_url: str = Field(default="", alias="DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    @property
    def normalized_llm_provider(self) -> str:
        return self.llm_provider.strip().lower()

    @property
    def resolved_api_key(self) -> str:
        if self.normalized_llm_provider == "openai":
            return self.openai_api_key
        return self.google_api_key or self.gemini_api_key

    @property
    def active_model(self) -> str:
        if self.normalized_llm_provider == "openai":
            return self.openai_model
        if self.normalized_llm_provider == "codex_cli":
            return self.codex_cli_model or "codex-cli-default"
        return self.gemini_model

    @property
    def has_llm_credentials(self) -> bool:
        if self.normalized_llm_provider == "codex_cli":
            return bool(self.codex_cli_command)
        return bool(self.resolved_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
