"""Base abstractions for LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    content: str
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    raw_response: Optional[Dict[str, Any]] = None


class BaseLLM(ABC):
    """Abstract LLM interface for conversational generation and evaluation judges."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronously generate completion for messages."""
        pass
