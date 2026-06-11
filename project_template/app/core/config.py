from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = Field(default="chatbot_rag", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="bge-m3", alias="OLLAMA_EMBED_MODEL")
    ollama_request_timeout: float = Field(default=120.0, alias="OLLAMA_REQUEST_TIMEOUT")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_num_predict: int = Field(default=256, alias="LLM_NUM_PREDICT")
    llm_think: bool = Field(default=False, alias="LLM_THINK")
    ollama_keep_alive: str = Field(default="10m", alias="OLLAMA_KEEP_ALIVE")

    chroma_path: Path = Field(default=PROJECT_ROOT / "data" / "vector_store" / "chroma", alias="CHROMA_PATH")
    chroma_collection: str = Field(default="manual_documents", alias="CHROMA_COLLECTION")

    database_url: str = Field(default="sqlite:///./data/app.sqlite3", alias="DATABASE_URL")

    raw_data_path: Path = Field(default=PROJECT_ROOT / "data" / "raw", alias="RAW_DATA_PATH")
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, alias="CHUNK_OVERLAP")
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")

    top_k: int = Field(default=40, alias="TOP_K")

    tour_api_service_key: str | None = Field(default=None, alias="TOUR_API_SERVICE_KEY")
    tour_api_accessible_service_key: str | None = Field(default=None, alias="TOUR_API_ACCESSIBLE_SERVICE_KEY")
    tour_api_base_url: str = Field(default="https://apis.data.go.kr/B551011/KorService2", alias="TOUR_API_BASE_URL")
    tour_api_accessible_base_url: str = Field(
        default="https://apis.data.go.kr/B551011/KorWithService2",
        alias="TOUR_API_ACCESSIBLE_BASE_URL",
    )
    tour_api_hub_base_url: str = Field(
        default="https://apis.data.go.kr/B551011/LocgoHubTarService1",
        alias="TOUR_API_HUB_BASE_URL",
    )
    tour_api_related_base_url: str = Field(
        default="https://apis.data.go.kr/B551011/TarRlteTarService1",
        alias="TOUR_API_RELATED_BASE_URL",
    )
    tour_api_wellness_base_url: str = Field(
        default="https://apis.data.go.kr/B551011/WellnessTursmService",
        alias="TOUR_API_WELLNESS_BASE_URL",
    )
    tour_api_mobile_os: str = Field(default="ETC", alias="TOUR_API_MOBILE_OS")
    tour_api_mobile_app: str = Field(default="chatbot_rag", alias="TOUR_API_MOBILE_APP")
    tour_api_timeout: float = Field(default=20.0, alias="TOUR_API_TIMEOUT")
    tour_api_daily_endpoint_limit: int = Field(default=1000, alias="TOUR_API_DAILY_ENDPOINT_LIMIT")
    tour_api_usage_log_path: Path = Field(
        default=PROJECT_ROOT / "data" / "generated" / "tour_api" / "usage" / "daily_usage.json",
        alias="TOUR_API_USAGE_LOG_PATH",
    )
    tour_api_response_cache_enabled: bool = Field(default=True, alias="TOUR_API_RESPONSE_CACHE_ENABLED")
    tour_api_response_cache_path: Path = Field(
        default=PROJECT_ROOT / "data" / "generated" / "tour_api" / "live_response_cache.sqlite3",
        alias="TOUR_API_RESPONSE_CACHE_PATH",
    )
    tourism_live_lookup_enabled: bool = Field(default=True, alias="TOURISM_LIVE_LOOKUP_ENABLED")
    tourism_lookup_strategy: str = Field(default="cache_first", alias="TOURISM_LOOKUP_STRATEGY")
    tourism_live_first_wait_seconds: float = Field(default=5.0, alias="TOURISM_LIVE_FIRST_WAIT_SECONDS")
    tourism_live_background_timeout_seconds: float = Field(default=15.0, alias="TOURISM_LIVE_BACKGROUND_TIMEOUT_SECONDS")
    tourism_live_rows: int = Field(default=10, alias="TOURISM_LIVE_ROWS")
    tourism_live_max_detail_calls: int = Field(default=10, alias="TOURISM_LIVE_MAX_DETAIL_CALLS")
    tourism_live_cache_path: Path = Field(
        default=PROJECT_ROOT / "data" / "generated" / "tour_api" / "live_markdown",
        alias="TOURISM_LIVE_CACHE_PATH",
    )
    tourism_query_event_log_enabled: bool = Field(default=True, alias="TOURISM_QUERY_EVENT_LOG_ENABLED")
    tourism_query_event_log_include_message: bool = Field(
        default=False,
        alias="TOURISM_QUERY_EVENT_LOG_INCLUDE_MESSAGE",
    )
    tourism_query_event_log_path: Path = Field(
        default=PROJECT_ROOT / "data" / "generated" / "tour_api" / "query_card_events.jsonl",
        alias="TOURISM_QUERY_EVENT_LOG_PATH",
    )
    tourism_sample_path: Path = Field(default=PROJECT_ROOT / "data" / "raw" / "tourism_accessible", alias="TOURISM_SAMPLE_PATH")
    tourism_reasoning_assist_enabled: bool = Field(default=False, alias="TOURISM_REASONING_ASSIST_ENABLED")
    tourism_reasoning_assist_max_cards: int = Field(default=5, alias="TOURISM_REASONING_ASSIST_MAX_CARDS")
    tourism_korean_correction_enabled: bool = Field(default=True, alias="TOURISM_KOREAN_CORRECTION_ENABLED")
    tourism_korean_correction_provider: str = Field(default="hf_seq2seq", alias="TOURISM_KOREAN_CORRECTION_PROVIDER")
    tourism_korean_correction_model: str = Field(
        default=str(PROJECT_ROOT / "data" / "models" / "tourism_korean_corrector"),
        alias="TOURISM_KOREAN_CORRECTION_MODEL",
    )
    tourism_korean_correction_base_model: str = Field(
        default="j5ng/et5-typos-corrector",
        alias="TOURISM_KOREAN_CORRECTION_BASE_MODEL",
    )
    tourism_korean_correction_device: str = Field(default="auto", alias="TOURISM_KOREAN_CORRECTION_DEVICE")
    tourism_korean_correction_risky_only: bool = Field(default=True, alias="TOURISM_KOREAN_CORRECTION_RISKY_ONLY")
    tourism_korean_correction_allow_download: bool = Field(default=False, alias="TOURISM_KOREAN_CORRECTION_ALLOW_DOWNLOAD")
    tourism_korean_correction_max_chars: int = Field(default=80, alias="TOURISM_KOREAN_CORRECTION_MAX_CHARS")
    tourism_korean_correction_max_length: int = Field(default=128, alias="TOURISM_KOREAN_CORRECTION_MAX_LENGTH")
    tourism_korean_correction_num_beams: int = Field(default=1, alias="TOURISM_KOREAN_CORRECTION_NUM_BEAMS")
    tourism_condition_transformer_enabled: bool = Field(default=False, alias="TOURISM_CONDITION_TRANSFORMER_ENABLED")
    tourism_condition_transformer_model: str = Field(
        default=str(PROJECT_ROOT / "data" / "generated" / "tour_api" / "condition_transformer_residual_aug_e2_fast" / "model"),
        alias="TOURISM_CONDITION_TRANSFORMER_MODEL",
    )
    tourism_condition_transformer_metrics_path: Path = Field(
        default=PROJECT_ROOT / "data" / "generated" / "tour_api" / "condition_transformer_residual_aug_e2_fast" / "metrics.json",
        alias="TOURISM_CONDITION_TRANSFORMER_METRICS_PATH",
    )
    tourism_condition_transformer_device: str = Field(default="auto", alias="TOURISM_CONDITION_TRANSFORMER_DEVICE")
    tourism_condition_transformer_max_length: int = Field(default=96, alias="TOURISM_CONDITION_TRANSFORMER_MAX_LENGTH")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_chroma_path(self) -> Path:
        return self._resolve_project_path(self.chroma_path)

    @property
    def resolved_raw_data_path(self) -> Path:
        return self._resolve_project_path(self.raw_data_path)

    @property
    def resolved_tourism_sample_path(self) -> Path:
        return self._resolve_project_path(self.tourism_sample_path)

    @property
    def resolved_tourism_live_cache_path(self) -> Path:
        return self._resolve_project_path(self.tourism_live_cache_path)

    @property
    def resolved_tourism_query_event_log_path(self) -> Path:
        return self._resolve_project_path(self.tourism_query_event_log_path)

    @property
    def resolved_tour_api_usage_log_path(self) -> Path:
        return self._resolve_project_path(self.tour_api_usage_log_path)

    @property
    def resolved_tour_api_response_cache_path(self) -> Path:
        return self._resolve_project_path(self.tour_api_response_cache_path)

    @staticmethod
    def _resolve_project_path(path: Path) -> Path:
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def prompt_path(self) -> Path:
        return PROJECT_ROOT / "prompts" / "rag_answer_prompt.txt"

    @property
    def no_context_prompt_path(self) -> Path:
        return PROJECT_ROOT / "prompts" / "no_context_prompt.txt"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
