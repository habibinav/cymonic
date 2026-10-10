"""The UI's link to the pipeline. Falls back to mock data if the pipeline can't load."""
import sys
import traceback
from pathlib import Path

from mock_data import MOCK_ANNOUNCEMENTS

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "agents"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def load_leads():
    """Returns (leads, using_mock)."""
    try:
        from pipeline import run_all
        return run_all(), False
    except Exception:
        traceback.print_exc()
        return MOCK_ANNOUNCEMENTS, True


def gemini_enabled():
    try:
        import gemini_client
        return gemini_client.is_enabled()
    except Exception:
        return False


def analyze_with_gemini(ids, progress=None):
    """Gemini-analyse just these leads, then return the refreshed list."""
    from pipeline import analyze_leads
    analyze_leads(ids, progress=progress)
    return load_leads()


def analyze_new(text, source_url=None):
    """Run a pasted announcement through all agents (Gemini if a key is set)."""
    from pipeline import process_announcement
    return process_announcement(text, source_url)
