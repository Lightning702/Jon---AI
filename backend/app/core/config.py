from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".jon-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def _resolve_data_dir() -> Path:
    override = os.environ.get("JON_DATA_DIR")
    if override:
        return Path(override)
    if FROZEN:
        beside = Path(sys.executable).resolve().parent / "data"
        if _writable(beside):
            return beside
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "Jon" / "data"
    return Path.home() / ".jon" / "data"


DATA_DIR = _resolve_data_dir()
_OLD_DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

if _OLD_DATA_DIR.exists() and _OLD_DATA_DIR.resolve() != DATA_DIR.resolve():
    for _item in _OLD_DATA_DIR.iterdir():
        _target = DATA_DIR / _item.name
        if _target.exists():
            continue
        try:
            if _item.is_dir():
                shutil.copytree(_item, _target)
            else:
                shutil.copy2(_item, _target)
        except Exception:
            pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Jon"
    app_version: str = "3.17.0"
    host: str = "127.0.0.1"
    port: int = 8756
    cors_origins: str = "*"
    jon_lan: bool = False

    database_url: str = f"sqlite:///{(DATA_DIR / 'jon.db').as_posix()}"

    default_provider: str = "nvidia"
    default_model: str = ""
    default_jon_model: str = "openai/gpt-oss-120b"
    default_emil_model: str = "openai/gpt-oss-20b"

    openai_api_key: str | None = None
    nvidia_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    mistral_api_key: str | None = None
    glm_api_key: str | None = None
    qwen_api_key: str | None = None
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    together_api_key: str | None = None
    xai_api_key: str | None = None

    openai_base_url: str = "https://api.openai.com/v1"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    mistral_base_url: str = "https://api.mistral.ai/v1"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ollama_base_url: str = "http://localhost:11434/v1"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    together_base_url: str = "https://api.together.xyz/v1"
    xai_base_url: str = "https://api.x.ai/v1"

    request_timeout: float = 90.0
    first_token_timeout: float = 10.0
    models_timeout: float = 6.0
    max_tokens: int = 32768
    reasoning_effort: str = "low"
    default_temperature: float = 0.7
    default_top_p: float = 0.9

    @property
    def jon_model(self) -> str:
        return (
            self.default_jon_model.strip()
            or self.default_model.strip()
            or "openai/gpt-oss-120b"
        )

    @property
    def emil_model(self) -> str:
        return self.default_emil_model.strip() or self.jon_model

    def model_for(self, slot: str) -> str:
        return self.emil_model if slot == "emil" else self.jon_model

    def origins(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
