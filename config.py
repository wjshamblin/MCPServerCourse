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

    # Azure OAuth Settings
    azure_client_id: str = Field(default="", description="Azure AD Application (Client) ID")
    azure_client_secret: str = Field(default="", description="Azure AD Client Secret")
    azure_tenant_id: str = Field(default="", description="Azure AD Tenant ID")
    mcp_api_scope: str = Field(default="access_as_user", description="Custom API scope name")
    oauth_base_url: str = Field(default="http://localhost:8000", description="OAuth callback base URL")
    additional_auth_scopes: str = Field(
        default="email,openid,profile,offline_access",
        description="Comma-separated additional OAuth scopes",
    )

    # Access Control
    allowed_users: str = Field(
        default="",
        description="Comma-separated list of allowed user emails (empty = allow all authenticated)",
    )

    # Audit
    audit_log_dir: str = Field(default="logs", description="Directory for audit logs")

    # LLM Configuration (for NL-to-SQL)
    anthropic_api_key: str = Field(default="", description="Anthropic API key for NL-to-SQL")
    anthropic_model: str = Field(default="claude-sonnet-4-5", description="Anthropic model")
    openai_api_key: str = Field(default="", description="OpenAI API key for NL-to-SQL")
    openai_base_url: str = Field(default="", description="OpenAI base URL (for proxies)")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model")
    llm_provider: str = Field(default="anthropic", description="LLM provider: 'anthropic' or 'openai'")

    @property
    def database_path_resolved(self) -> Path:
        return Path(self.database_path)

    def get_log_level(self) -> int:
        levels = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
        return levels.get(self.log_level.upper(), logging.INFO)

    @property
    def full_mcp_scope(self) -> str:
        return f"api://{self.azure_client_id}/{self.mcp_api_scope}"

    @property
    def additional_auth_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.additional_auth_scopes.split(",") if s.strip()]

    @property
    def allowed_users_list(self) -> list[str]:
        if not self.allowed_users.strip():
            return []
        return [e.strip().lower() for e in self.allowed_users.split(",") if e.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.azure_client_id and self.azure_tenant_id)


def load_config() -> Settings:
    return Settings()
