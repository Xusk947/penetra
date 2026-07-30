"""Application configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and ``.env`` files."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # OpenRouter LLM configuration (default model: tencent/hy3:free)
    openrouter_api_key: str | None = None
    openrouter_model: str = "tencent/hy3:free"
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    log_level: str = "INFO"

    # Authorized target configuration (loaded from .env, never committed).
    target_host: str | None = None
    target_url: str | None = None
    target_username: str | None = None
    target_password: str | None = None
    target_admin_username: str | None = None
    target_admin_password: str | None = None

    nmap_mock: bool = True
    nmap_policy: str = "safe"
    nmap_allowed_targets: list[str] = Field(default_factory=list)
    nmap_use_docker: bool = False
    nmap_docker_image: str = "instrumentisto/nmap"
    nmap_docker_network: str = "host"

    # Docker sandbox for untrusted Python code execution.
    python_use_docker: bool = False
    python_docker_image: str = "python:3.12-slim"

    # Exploitation simulation safety switches
    exploit_execute: bool = False
    exploit_sandbox: bool = True
    exploit_allowed_targets: list[str] = Field(default_factory=list)

    # Centralized scope policy
    allowed_targets: list[str] = Field(default_factory=list)
    denied_targets: list[str] = Field(default_factory=list)
    research_allowed_targets: list[str] = Field(default_factory=list)
    block_private_ips: bool = True

    # Research browser
    research_mock: bool = True

    # OSINT tool configuration
    osint_mock: bool = True
    censys_api_id: str | None = None
    censys_api_secret: str | None = None
    chaos_api_key: str | None = None
    virustotal_api_key: str | None = None
    securitytrails_api_key: str | None = None
    ipinfo_token: str | None = None

    # Report output/delivery
    reports_dir: str = "reports"
    report_remote_endpoint: str | None = None
