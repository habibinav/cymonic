"""Where the UI gets its data.

Two ways to plug in the backend:
  1. HTTP: set CATERING_API_URL (e.g. http://localhost:8000). The UI calls
       GET  {url}/api/verdicts   -> list of announcements (or {"announcements": [...]})
       POST {url}/api/analyze    -> same shape, after running the agents
  2. Direct Python: replace the bodies of load_verdicts() / run_analysis()
     with calls to the pipeline functions.
If neither works, the UI falls back to mock data.
"""
import os

import requests

from mock_data import MOCK_ANNOUNCEMENTS

API_URL = os.getenv("CATERING_API_URL", "http://localhost:8000").rstrip("/")


def _unwrap(payload):
    return payload if isinstance(payload, list) else payload.get("announcements", [])


def load_verdicts():
    """Returns (announcements, using_mock)."""
    try:
        r = requests.get(f"{API_URL}/api/verdicts", timeout=3)
        r.raise_for_status()
        return _unwrap(r.json()), False
    except Exception:
        return MOCK_ANNOUNCEMENTS, True


def run_analysis():
    """Triggers the agent pipeline. Returns (announcements, using_mock)."""
    try:
        r = requests.post(f"{API_URL}/api/analyze", timeout=300)
        r.raise_for_status()
        return _unwrap(r.json()), False
    except Exception:
        return MOCK_ANNOUNCEMENTS, True
