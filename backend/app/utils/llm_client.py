"""
LLM Client — Provider-aware router for all OASIS pipeline calls.

╔══════════════════════════════════════════════════════════════════╗
║                       ARCHITECTURE                               ║
╠══════════════════════════════════════════════════════════════════╣
║  LITE MODE  (DEFAULT_LLM_PROVIDER=groq)                         ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  OASIS + Graph backbone (always)                        │    ║
║  │    ├─ Ontology generation    → Llama 3.3 70B (Groq)    │    ║
║  │    ├─ Profile generation     → Llama 3.3 70B (Groq)    │    ║
║  │    ├─ Simulation config      → Llama 3.3 70B (Groq)    │    ║
║  │    └─ Agent behaviour        → Llama 3.3 70B (Groq)    │    ║
║  │  Report (always Gemini)      → Gemini 2.5 Flash        │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  FULL MODE  (DEFAULT_LLM_PROVIDER=gemini)                       ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  OASIS + Graph backbone (always)                        │    ║
║  │    ├─ Ontology generation    → Gemini 2.5 Flash         │    ║
║  │    ├─ Profile generation     → Gemini 2.5 Flash         │    ║
║  │    ├─ Simulation config      → Gemini 2.5 Flash         │    ║
║  │    └─ Agent behaviour        → Gemini 2.5 Flash         │    ║
║  │  Report (always Gemini)      → Gemini 2.5 Flash         │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  HOW TO SWITCH:                                                  ║
║    Lite → DEFAULT_LLM_PROVIDER=groq   in .env                   ║
║    Full → DEFAULT_LLM_PROVIDER=gemini in .env                   ║
║                                                                  ║
║  Report agent ALWAYS uses Gemini (use LLMClient(report=True))   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import re
from typing import Any, Dict, List, Optional

from ..config import Config
from .gemini_service import GeminiService
from .groq_service import GroqService


def _messages_to_prompt(messages: List[Dict[str, str]]) -> tuple:
    """Convert OpenAI-style message list → (system_prompt, user_prompt)."""
    system_parts, user_parts = [], []
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            user_parts.append(f"[Assistant]: {content}")
        else:
            user_parts.append(content)
    return "\n\n".join(system_parts), "\n\n".join(user_parts)


class LLMClient:
    """
    Universal LLM client used by the OASIS pipeline.

    Instantiation:
        LLMClient()              → uses DEFAULT_LLM_PROVIDER from .env
        LLMClient(report=True)   → always Gemini (report agent)
        LLMClient(provider='groq')   → force Groq/Llama
        LLMClient(provider='gemini') → force Gemini

    Public interface: chat() and chat_json()
    All existing service callers work without modification.
    """

    def __init__(
        self,
        api_key:   Optional[str] = None,
        base_url:  Optional[str] = None,   # kept for signature compat
        model:     Optional[str] = None,   # kept for signature compat
        provider:  Optional[str] = None,
        report:    bool = False,            # True → always Gemini (report agent)
    ):
        # Report agent ALWAYS uses Gemini regardless of global provider
        if report:
            effective_provider = "gemini"
        else:
            effective_provider = (provider or Config.DEFAULT_LLM_PROVIDER).lower()

        self.provider = effective_provider

        if effective_provider == "gemini":
            self._llm = GeminiService.get_instance()
        else:
            # groq → Llama 3.3 70B
            self._llm = GroqService.get_instance()

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        messages:        List[Dict[str, str]],
        temperature:     float = 0.7,
        max_tokens:      int = 4096,        # kept for signature compat
        response_format: Optional[Dict] = None,
        simulation_id:   Optional[str] = None,
    ) -> str:
        """Send a chat request and return the response text."""
        system_prompt, user_prompt = _messages_to_prompt(messages)
        json_mode = (
            response_format is not None
            and response_format.get("type") == "json_object"
        )
        return self._llm.generate(
            prompt        = user_prompt,
            system_prompt = system_prompt,
            json_mode     = json_mode,
            temperature   = temperature,
            simulation_id = simulation_id,
        )

    def chat_json(
        self,
        messages:      List[Dict[str, str]],
        temperature:   float = 0.3,
        max_tokens:    int = 4096,          # kept for signature compat
        simulation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat request and return parsed JSON."""
        system_prompt, user_prompt = _messages_to_prompt(messages)
        return self._llm.generate_json(
            prompt        = user_prompt,
            system_prompt = system_prompt,
            temperature   = temperature,
            simulation_id = simulation_id,
        )
