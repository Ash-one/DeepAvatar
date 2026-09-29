"""Gemini LLM client adapter supporting OpenAI-compatible gateway endpoints."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

from deep_persona.llm.base import BaseLLM, LLMResponse

# Load .env file automatically
load_dotenv(Path(__file__).resolve().parents[3] / ".env")


class GeminiLLM(BaseLLM):
    """OpenAI-compatible client for Gemini models hosted on local or remote proxies."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        base_endpoint = endpoint or os.getenv("GEMINI_ENDPOINT", "http://127.0.0.1:8045")
        
        # Normalize endpoint URL
        base_endpoint = base_endpoint.rstrip("/")
        if not base_endpoint.endswith("/v1"):
            self.chat_url = f"{base_endpoint}/v1/chat/completions"
        else:
            self.chat_url = f"{base_endpoint}/chat/completions"

        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call chat completions API."""
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            # trust_env=False prevents local proxies like Surge from hijacking loopback 127.0.0.1 requests
            with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                response = client.post(self.chat_url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"LLM API error (status {response.status_code}): {response.text}"
                    )
                data = response.json()
        except httpx.RequestError as exc:
            raise RuntimeError(f"LLM network request failed: {exc}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"No completion choices returned by model: {data}")

        choice = choices[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content.strip(),
            usage=usage,
            model=data.get("model", self.model),
            raw_response=data,
        )


class MockLLM(BaseLLM):
    """Deterministic Mock LLM for offline tests and smoke runs."""

    def __init__(self, responses: Optional[List[str]] = None, default_response: str = "I understand."):
        self.responses = list(responses or [])
        self.default_response = default_response
        self.call_history: List[Dict[str, Any]] = []

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_history.append({
            "messages": messages,
            "system_prompt": system_prompt,
            "temperature": temperature,
        })
        if self.responses:
            reply = self.responses.pop(0)
        else:
            reply = self.default_response

        return LLMResponse(
            content=reply,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            model="mock-model",
        )
