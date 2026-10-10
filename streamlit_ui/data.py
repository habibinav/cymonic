"""Where the UI gets its data.

Default: runs the real pipeline (../pipeline.py) on the dataset CSV in-process.
Optional: set CATERING_API_URL to fetch from an HTTP backend instead.
If both fail, falls back to mock data (the UI shows a "mock data" badge).
"""
import os
import sys
import traceback
from pathlib import Path

from mock_data import MOCK_ANNOUNCEMENTS

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

API_URL = os.getenv("CATERING_API_URL", "").rstrip("/")


def _unwrap(payload):
    return payload if isinstance(payload, list) else payload.get("announcements", [])


def _from_pipeline(ai=False, progress=None):
    from pipeline import run_all
    return run_all(ai=ai, progress=progress)


def gemini_enabled():
    try:
        import gemini_client
        return gemini_client.is_enabled()
    except Exception:
        return False


def analyze_new(text, source_url=None):
    """Run a pasted announcement through the agents. Returns the lead dict."""
    from pipeline import process_announcement
    return process_announcement(text, source_url)


def _from_api(method="get"):
    import requests
    path = "/api/verdicts" if method == "get" else "/api/analyze"
    r = requests.request(method, f"{API_URL}{path}", timeout=300)
    r.raise_for_status()
    return _unwrap(r.json())


def load_verdicts():
    """Returns (announcements, using_mock)."""
    try:
        return (_from_api() if API_URL else _from_pipeline()), False
    except Exception:
        traceback.print_exc()
        return MOCK_ANNOUNCEMENTS, True


def run_analysis(progress=None):
    """Re-runs the agents (Gemini on every not-yet-analysed lead if a key is set). Returns (announcements, using_mock)."""
    try:
        return (_from_api("post") if API_URL else _from_pipeline(ai=True, progress=progress)), False
    except Exception:
        traceback.print_exc()
        return MOCK_ANNOUNCEMENTS, True
