"""Application settings + config path resolution.

Values flow from env vars (loaded via pydantic-settings) but every field has a sensible
default so the static, offline path works without any configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RESUME_",
        extra="ignore",
    )

    llm_provider: str = "anthropic"
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gh_user: str | None = None
    config_dir: Path = DEFAULT_CONFIG_DIR

    @property
    def roles_path(self) -> Path:
        return self.config_dir / "roles.json"

    @property
    def regex_patterns_path(self) -> Path:
        return self.config_dir / "regex_patterns.json"

    @property
    def templates_dir(self) -> Path:
        return self.config_dir / "templates"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
