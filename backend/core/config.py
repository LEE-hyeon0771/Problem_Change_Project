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

    # LLM 호출 실패 시 재시도 횟수. 1이면 최초 1회 + 재시도 1회 = 최대 2번 호출합니다.
    # 재시도가 여러 겹(에이전트 x provider x 스키마리스 복구)으로 쌓이면 비용이 급증합니다.
    llm_max_retries: int = Field(default=1, ge=0, le=3, alias="LLM_MAX_RETRIES")

    # 요청 하나가 재시도로 폭주하는 것을 막는 상한.
    # 정상 성공은 보통 2~5회입니다. 초과하면 LLM 경로를 포기하고 로컬 폴백으로 갑니다.
    llm_max_calls_per_request: int = Field(default=12, alias="LLM_MAX_CALLS_PER_REQUEST")

    use_llm_generation: bool = Field(default=True, alias="USE_LLM_GENERATION")
    enable_self_check: bool = Field(default=False, alias="ENABLE_SELF_CHECK")

    enable_usage_log: bool = Field(default=True, alias="ENABLE_USAGE_LOG")
    usage_log_dir: str = Field(default="problem_log", alias="USAGE_LOG_DIR")
    # 0이면 표에 있는 모델 단가를 사용합니다. 단가가 바뀌면 여기서 덮어쓰세요.
    llm_input_price_per_mtok: float = Field(default=0.0, alias="LLM_INPUT_PRICE_PER_MTOK")
    llm_output_price_per_mtok: float = Field(default=0.0, alias="LLM_OUTPUT_PRICE_PER_MTOK")
    # 0이면 원화 환산을 남기지 않습니다. 환율은 사용자가 직접 지정해야 정확합니다.
    usd_krw_rate: float = Field(default=0.0, alias="USD_KRW_RATE")

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
