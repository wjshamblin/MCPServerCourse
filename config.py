"""Configuration settings for the Financial MCP Server."""

import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)
    database_path: str = Field(default="data/university_gl.db", description="Path to the SQLite database")
    max_rows: int = Field(default=2000, description="Max rows returned per query")
    warning_rows: int = Field(default=100, description="Row count that triggers a warning")
    log_level: str = Field(default="INFO")

    # LLM Configuration (for NL-to-SQL)
    anthropic_api_key: str = Field(default="", description="Anthropic API key for NL-to-SQL")
    anthropic_model: str = Field(default="claude-opus-4-6", description="Anthropic model")
    openai_api_key: str = Field(default="", description="OpenAI API key for NL-to-SQL")
    openai_base_url: str = Field(default="", description="OpenAI base URL (for proxies)")
    openai_model: str = Field(default="gpt-5.4", description="OpenAI model")
    llm_provider: str = Field(default="openai", description="LLM provider: 'openai' or 'anthropic'")

    @property
    def database_path_resolved(self) -> Path:
        return Path(self.database_path)

    def get_log_level(self) -> int:
        levels = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
        return levels.get(self.log_level.upper(), logging.INFO)


def load_config() -> Settings:
    return Settings()
