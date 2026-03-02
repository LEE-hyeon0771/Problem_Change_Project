from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3-flash-preview", alias="GEMINI_MODEL")

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
    def resolved_api_key(self) -> str:
        return self.google_api_key or self.gemini_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
