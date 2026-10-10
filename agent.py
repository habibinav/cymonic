"""LLM client interface for the Corporate Catering Hunter AI Agent.

Provides a unified interface for calling external LLM providers when configured,
handling missing keys, timeouts, and errors safely with fallback support.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from config import USE_LLM, LLM_PROVIDER, LLM_MODEL

logger = logging.getLogger(__name__)


def is_llm_available() -> bool:
    """Check if LLM execution is enabled and an API key is available."""
    if not USE_LLM:
        return False

    if LLM_PROVIDER == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    elif LLM_PROVIDER == "gemini":
        return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    elif LLM_PROVIDER == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    elif LLM_PROVIDER == "mock":
        return True
    return False


def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """Call the configured LLM provider and return the response string.

    Returns None if the LLM is not enabled, no key is found, or an error occurs.
    """
    if not is_llm_available():
        logger.info("LLM is disabled or API key is not configured; using deterministic fallback.")
        return None

    try:
        if LLM_PROVIDER == "mock":
            # For testing LLM integration directly
            mock_handler = os.getenv("CATERING_HUNTER_MOCK_RESPONSE")
            return mock_handler if mock_handler else "{}"

        elif LLM_PROVIDER == "openai":
            import openai  # type: ignore
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content

        elif LLM_PROVIDER == "gemini":
            import google.generativeai as genai  # type: ignore
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=LLM_MODEL or "gemini-1.5-flash",
                system_instruction=system_prompt,
            )
            resp = model.generate_content(user_prompt)
            return resp.text

        elif LLM_PROVIDER == "anthropic":
            import anthropic  # type: ignore
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=LLM_MODEL or "claude-3-5-sonnet-20241022",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=2048,
            )
            return response.content[0].text

    except Exception as exc:
        logger.warning("LLM call failed with error: %s. Falling back to deterministic templates.", exc)
        return None

    return None
