"""Configuration module for the Corporate Catering Hunter AI Agent.

Handles environment variables, optional LLM settings, and global defaults.
No API keys are hard-coded in this or any other module.
"""

import os
from typing import Literal

# Optional LLM configuration
USE_LLM: bool = os.getenv("CATERING_HUNTER_USE_LLM", "false").lower() in ("true", "1", "yes")
LLM_PROVIDER: Literal["openai", "gemini", "anthropic", "mock"] = os.getenv(  # type: ignore[assignment]
    "CATERING_HUNTER_LLM_PROVIDER", "openai"
).lower()
LLM_MODEL: str = os.getenv("CATERING_HUNTER_LLM_MODEL", "gpt-4o-mini")

# Standard human-review disclaimer required on all prospect-facing drafts
HUMAN_REVIEW_DISCLAIMER: str = (
    "**Draft for human review — not sent. Verify event details, recipient information, "
    "business capabilities, pricing, and availability before use.**"
)

# Standard placeholders for missing/unverified details
PLACEHOLDER_CONFIRM_GUESTS: str = "[confirm guest count]"
PLACEHOLDER_CONFIRM_DATE: str = "[confirm event date]"
PLACEHOLDER_CONFIRM_VENUE: str = "[confirm venue address and facilities]"
PLACEHOLDER_CONFIRM_REQUIREMENTS: str = "[confirm catering requirements]"
PLACEHOLDER_CONFIRM_PRICING: str = "[to be confirmed after requirements are validated]"
PLACEHOLDER_CONFIRM_AVAILABILITY: str = "[confirm date availability]"
PLACEHOLDER_CONTACT_NAME: str = "[contact name]"
PLACEHOLDER_YOUR_NAME: str = "[Your name]"
