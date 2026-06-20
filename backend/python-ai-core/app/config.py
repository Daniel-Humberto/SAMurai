from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SAMurAI FutBotMX API"
    app_version: str = "0.2.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # SAM 3 — Segment Anything with Concepts (arXiv:2511.16719)
    # sam_model_size: auto | tiny | small | base | large
    #   auto  → detecta VRAM disponible y elige el perfil mayor que quepa
    #   tiny  → CPU / GPU < 2 GB VRAM
    #   small → GPU >= 2 GB VRAM
    #   base  → GPU >= 4 GB VRAM
    #   large → GPU >= 8 GB VRAM
    sam_model_size: str = "auto"
    sam_profile: str = "tiny"          # legado, sobreescrito por sam_model_size si != "auto"
    yolo_model: str = "yolov8n.pt"
    sam_frame_skip: int = 4
    tts_voice: str = "es_MX-claude-medium"
    max_upload_size_mb: int = 512
    upload_chunk_size_kb: int = 1024

    postgres_user: str = "futbotmx"
    postgres_password: str = "futbotmx"
    postgres_db: str = "futbotmx_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_password: str = ""
    redis_host: str = "redis"
    redis_port: int = 6379

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    models_dir: Path = BASE_DIR / "models"
    data_dir: Path = BASE_DIR / "data"
    uploads_dir: Path = BASE_DIR / "data" / "uploads"
    reports_dir: Path = BASE_DIR / "data" / "reports"
    runtime_namespace: str = "samurai-futbot:sessions"

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_chunk_size_bytes(self) -> int:
        return self.upload_chunk_size_kb * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
