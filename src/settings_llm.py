"""
LLM configuration helpers.

Reads environment variables to configure the LLM provider (Ollama by default)
and exposes a small settings object for use across the backend.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMSettings:
    """Configuration for the LLM provider."""

    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    request_timeout: int = 60  # seconds
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "LLMSettings":
        """
        Load settings from environment variables.

        Environment variables:
            LLM_PROVIDER:     e.g. 'ollama'
            OLLAMA_BASE_URL:  e.g. 'http://localhost:11434'
            OLLAMA_MODEL:     e.g. 'llama3.2:3b'
            LLM_ENABLED:      '0' or 'false' to disable
            LLM_REQUEST_TIMEOUT: request timeout in seconds
        """
        provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()

        enabled_raw = os.getenv("LLM_ENABLED", "1").strip().lower()
        enabled = enabled_raw not in ("0", "false", "no", "off")

        timeout_raw: Optional[str] = os.getenv("LLM_REQUEST_TIMEOUT")
        try:
            request_timeout = int(timeout_raw) if timeout_raw is not None else 60
        except ValueError:
            request_timeout = 60

        return cls(
            provider=provider,
            base_url=base_url,
            model=model,
            request_timeout=request_timeout,
            enabled=enabled,
        )


def get_llm_settings() -> LLMSettings:
    """
    Convenience accessor so other modules don't need to know about env keys.
    """
    return LLMSettings.from_env()


