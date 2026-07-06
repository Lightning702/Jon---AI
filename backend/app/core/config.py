from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Jon"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8756
    cors_origins: str = "*"

    database_url: str = f"sqlite:///{(DATA_DIR / 'jon.db').as_posix()}"

    default_provider: str = "nvidia"
    default_model: str = "openai/gpt-oss-120b"

    openai_api_key: str | None = None
    nvidia_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    mistral_api_key: str | None = None
    glm_api_key: str | None = None
    qwen_api_key: str | None = None

    openai_base_url: str = "https://api.openai.com/v1"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    mistral_base_url: str = "https://api.mistral.ai/v1"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ollama_base_url: str = "http://localhost:11434/v1"

    request_timeout: float = 180.0
    max_tokens: int = 32768
    default_temperature: float = 1.0
    default_top_p: float = 1.0

    def origins(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
