"""gemini_client.py — one small wrapper around Google's Gemini API.

Used by the reasoning step (gemini_reasoning.py) and the proposal generator (agent.py).
Every function returns None on any problem (no key, no network, quota hit, bad output),
so callers can fall back to the rule-based / template versions and the app never crashes.

Setup:
    pip install -U google-genai
    put GEMINI_API_KEY=... in a .env file at the project root (see .env.example)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

try:  # load .env from the project root if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
_client = None


def api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def is_enabled() -> bool:
    """True when a key is set and Gemini hasn't been switched off with USE_GEMINI=false."""
    return bool(api_key()) and os.getenv("USE_GEMINI", "true").lower() not in ("0", "false", "no")


def _get_client():
    global _client
    if _client is None:
        from google import genai  # pip install google-genai

        _client = genai.Client(api_key=api_key())
    return _client


def _attempts(client, system: str, user: str, json_mode: bool):
    """Different ways to call the SDK, newest first — so it works across google-genai versions."""
    if hasattr(client, "interactions"):
        if json_mode:
            yield lambda: client.interactions.create(
                model=MODEL, system_instruction=system, input=user,
                response_format={"type": "text", "mime_type": "application/json"},
            ).output_text
        yield lambda: client.interactions.create(model=MODEL, system_instruction=system, input=user).output_text

    from google.genai import types

    if json_mode:
        yield lambda: client.models.generate_content(
            model=MODEL, contents=user,
            config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json"),
        ).text
    yield lambda: client.models.generate_content(
        model=MODEL, contents=user, config=types.GenerateContentConfig(system_instruction=system),
    ).text


def generate(system: str, user: str, json_mode: bool = False, retries: int = 2) -> str | None:
    """Send a prompt to Gemini and return the text reply, or None if anything goes wrong."""
    if not is_enabled():
        return None
    try:
        client = _get_client()
    except Exception as exc:
        logger.warning("Gemini unavailable (is google-genai installed?): %s", exc)
        return None

    for attempt in range(retries + 1):
        last_error = None
        for call in _attempts(client, system, user, json_mode):
            try:
                text = call()
                if text and text.strip():
                    return text
            except Exception as exc:
                last_error = exc
                if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    break  # rate limited — wait and retry instead of trying other call styles
        msg = str(last_error or "")
        if last_error and ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt < retries:
            time.sleep(5 * (attempt + 1))
            continue
        if last_error:
            logger.warning("Gemini call failed: %s", last_error)
        return None
    return None


def generate_json(system: str, user: str) -> dict | None:
    """Like generate(), but parses the reply as a JSON object."""
    text = generate(system, user, json_mode=True)
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)  # sometimes there's chatter around the JSON
        try:
            data = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        logger.warning("Gemini did not return a JSON object")
        return None
    return data


if __name__ == "__main__":
    # Quick check:  python gemini_client.py
    print("Model:", MODEL, "| key set:", bool(api_key()), "| enabled:", is_enabled())
    print(generate("You are terse.", "Reply with exactly: Gemini is working") or "No reply — check the key / package / model name.")
