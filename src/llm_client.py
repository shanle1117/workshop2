"""
LLM client for calling open-source Llama models via Ollama.

This module provides a small, testable wrapper around the Ollama HTTP API
using an OpenAI-style chat message format:

    messages = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ]
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from urllib import request, error as urlerror

from .settings_llm import get_llm_settings


class LLMError(Exception):
    """Raised when the LLM provider returns an error or cannot be reached."""


@dataclass
class LLMResponse:
    """Simple container for LLM responses."""

    content: str
    raw: Dict[str, Any]


class LLMClient:
    """
    Client for interacting with an LLM provider.

    Currently supports:
        - Ollama chat API (non-streaming)
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        settings = get_llm_settings()
        self.base_url = base_url or settings.base_url
        self.model = model or settings.model
        self.timeout = settings.request_timeout
        self.enabled = settings.enabled

    def _build_ollama_payload(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Build request payload for Ollama /api/chat endpoint."""
        # Ollama expects messages in OpenAI format; we pass through directly.
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 200,  # Reduced for shorter, more concise responses
    ) -> LLMResponse:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate (mapped to num_predict)

        Returns:
            LLMResponse with `content` and raw provider response.
        """
        if not self.enabled:
            raise LLMError(
                "LLM is disabled. Set LLM_ENABLED=1 (or remove it) to enable the LLM."
            )

        if not messages:
            raise ValueError("messages must be a non-empty list")

        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = self._build_ollama_payload(messages, temperature, max_tokens)
        data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read().decode("utf-8")
        except urlerror.HTTPError as e:
            # HTTP error from Ollama
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = ""
            raise LLMError(f"LLM HTTP error {e.code}: {err_body or e.reason}") from e
        except urlerror.URLError as e:
            raise LLMError(f"Could not reach LLM provider: {e.reason}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error while calling LLM: {e}") from e

        try:
            resp_json = json.loads(resp_body)
        except json.JSONDecodeError as e:
            raise LLMError(f"Invalid JSON from LLM provider: {e}") from e

        # Ollama chat format: { "message": {"role": "...", "content": "..."}, ... }
        message = resp_json.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned an empty response")

        return LLMResponse(content=content, raw=resp_json)


_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get a process-wide default LLM client instance.

    This avoids re-reading env vars and re-creating clients on each request.
    """
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


