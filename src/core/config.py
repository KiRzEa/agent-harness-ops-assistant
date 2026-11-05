from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

FailureMode = Literal["none", "transient", "permanent", "timeout", "invalid_output"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    mongodb_uri: str = "mongodb://localhost:27017/?directConnection=true"
    mongodb_db: str = "ops_assistant"

    max_steps: int = 8
    max_run_seconds: float = 60
    tool_timeout_seconds: float = 5
    tool_max_retries: int = 2
    max_repairs: int = 2

    failure_mode: FailureMode = "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()
