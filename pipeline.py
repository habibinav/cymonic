"""pipeline.py — glue that runs the whole Catering Hunter flow end to end.

    dataset CSV  ->  decision_agents (qualify -> evaluate -> choose_strategy)
                 ->  proposal_generator.generate_content
                 ->  plain dicts the Streamlit UI understands

With Gemini on (use_ai=True), the reasoning step is done by gemini_reasoning.py and the
proposal is written by Gemini through Member 3's prompts. The hard business rules
(service area, capacity, notice period) always stay rule-based.

Run it directly to sanity-check:   python pipeline.py
The UI calls run_pipeline() via streamlit_ui/data.py.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

# Member 1 — decision-making agents (their own schema models)
from decision_agents import schemas as m1
from decision_agents.qualification_agent import qualify
from decision_agents.reasoning_agent import evaluate
from decision_agents.strategy_agent import choose_strategy

# Member 3 — proposal generator (root-level schema models)
import schemas as m3
from proposal_generator import generate_content

# Member 4 — reads raw announcement text and extracts the event facts
from analysis_agent import analyze_announcement

# Gemini (optional) — reasoning + proposal writing
import agent as llm_agent
import gemini_client
from gemini_reasoning import reason_with_gemini

ROOT = Path(__file__).parent
DATASET = ROOT / "corporate_catering_hunter_synthetic_dataset_500.csv"
NEW_LEADS = ROOT / "new_leads.csv"   # announcements pasted into the UI are saved here
AI_CACHE = ROOT / "ai_cache.json"    # Gemini results, so they survive restarts
AI_MAX_LEADS = int(__import__("os").getenv("GEMINI_MAX_LEADS", "25"))  # leads per "Analyze all" run
_AI_LOCK = threading.Lock()

# One shared business profile. Service areas include both spellings the dataset uses.
SERVICE_AREAS = ["Kochi", "Ernakulam", "Trivandrum", "Thiruvananthapuram", "Bangalore", "Bengaluru", "Chennai"]
PROFILE_M1 = m1.BusinessProfile(service_areas=SERVICE_AREAS)
PROFILE_M3 = m3.BusinessProfile(
    company_name="Apex Corporate Catering Co.",
    service_area=SERVICE_AREAS,
    min_guests=PROFILE_M1.min_capacity,
    max_guests=PROFILE_M1.max_capacity,
)

# Pursuit tier -> UI verdict bucket
TIER_TO_VERDICT = {
    "high_effort_pitch": "high",
    "standard_proposal": "standard",
    "light_outreach": "light",
    "needs_research": "skip",
    "none": "skip",
}


# ---------------------------------------------------------------- helpers
def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def _int(v):
    v = _clean(v)
    try:
        return int(float(v)) if v is not None else None
    except (TypeError, ValueError):
        return None


def _pretty_date(iso):
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%-d %b %Y")
    except (TypeError, ValueError):
        return None


def _money(x):
    if not x:
        return None
    return f"₹{x / 1e5:.1f}L" if x >= 1e5 else f"₹{x / 1e3:.0f}K"


# ---------------------------------------------------------------- one lead
def _set_proposal_llm(enabled: bool) -> None:
    """Switch Member 3's proposal generator between Gemini and its templates."""
    llm_agent.USE_LLM = enabled
    llm_agent.LLM_PROVIDER = "gemini"


def process_row(row: dict, use_ai: bool = False) -> dict:
    people = _int(row.get("attendee_count"))
    days = _int(row.get("event_duration_days")) or 1
    location = _clean(row.get("event_location"))
    event_date = _clean(row.get("event_date"))
    text = _clean(row.get("announcement_text")) or ""
    deal = _clean(row.get("estimated_deal_value"))
    if deal is None and people:
        deal = people * days * 750   # rough estimate (~₹750 per head per day, matches the dataset)

    missing = [name for name, val in (("Event Location", location), ("Attendance Estimate", people),
                                      ("Event Date", event_date)) if val is None]

    # ---- Member 1: decide
    a1 = m1.LeadAnalysis(
        company_name=_clean(row.get("company_name")),
        event_name=_clean(row.get("event_type")),
        event_type=_clean(row.get("event_type")),
        event_date=event_date,
        location=location,
        attendance_estimate=people,
        event_duration=f"{days} day(s)",
        catering_evidence=text,
        missing_info=missing,
        source_url=_clean(row.get("source_url")),
    )
    q1 = qualify(a1, PROFILE_M1)
    r1 = evaluate(a1, q1)
    ai_used = []
    if use_ai and q1.status != m1.QualificationStatus.DISQUALIFIED:
        facts = {
            "company": a1.company_name, "event_type": a1.event_type, "date": event_date,
            "location": location, "attendees": people, "duration_days": days,
            "catering_signal": _clean(row.get("catering_signal")), "estimated_deal_value_inr": deal,
            "announcement": text,
        }
        ai_reasoning = reason_with_gemini(facts, q1, r1)
        if ai_reasoning:
            r1 = ai_reasoning
            ai_used.append("reasoning")
    s1 = choose_strategy(q1, r1)
    tier = s1.pursuit_tier.value

    # ---- adapt Member 1 output -> Member 3 input contract
    a3 = m3.LeadAnalysis(
        lead_id=str(row.get("lead_id")),
        company_name=a1.company_name or "Unknown company",
        event_type=a1.event_type,
        event_date=event_date,
        event_location=location,
        attendee_count=people,
        event_duration_days=days,
        catering_signal=_clean(row.get("catering_signal")) or "unknown",
        source_url=a1.source_url,
        announcement_text=text,
        unknown_fields=missing,
    )
    q3 = m3.QualificationResult(
        status=q1.status.value,
        hard_constraint_failures=q1.disqualification_reasons,
        passed_constraints=q1.qualification_notes,
        reason="; ".join(q1.disqualification_reasons or q1.missing_critical_info) or None,
    )
    r3 = m3.ReasoningResult(
        summary=r1.reasoning_summary, risks=r1.risks, uncertainties=r1.uncertainties,
        estimated_deal_value=deal,
    )
    st3 = m3.StrategyResult(
        tier=tier, rationale=s1.justification,
        proposal_required=tier in ("light_outreach", "standard_proposal", "high_effort_pitch"),
    )

    # ---- Member 3: write the pitch / outreach / research checklist
    content = generate_content(a3, q3, r3, st3, PROFILE_M3)
    if (use_ai and content.content_type in ("light_outreach", "standard_proposal", "high_effort_pitch")
            and not any("template fallback" in w for w in content.warnings)):
        ai_used.append("proposal")

    # ---- shape for the UI
    verdict = TIER_TO_VERDICT.get(tier, "skip")
    if q1.status == m1.QualificationStatus.DISQUALIFIED:
        if location and not q1.is_service_area_matched:
            why = f"Outside service area ({location.split(',')[0]})"
        else:
            why = q1.disqualification_reasons[0] if q1.disqualification_reasons else "Disqualified"
    elif tier == "needs_research":
        why = "Needs research — missing " + ", ".join(q1.missing_critical_info).lower()
    else:
        bits = [f"{days}-day {(a1.event_type or 'event').lower()}"]
        if deal:
            bits.append(f"~{_money(deal)} deal")
        bits.append(f"score {r1.commercial_potential_score}/10")
        why = ", ".join(bits)

    proposal = content.draft_text
    if not proposal and content.research_questions:
        proposal = "Research checklist:\n" + "\n".join(f"• {q}" for q in content.research_questions)

    return {
        "id": str(row.get("lead_id")),
        # dataset names carry an ID suffix ("Orbit Retail 038") — drop it so events group by company
        "company": re.sub(r"\s+\d+$", "", a1.company_name or "Unknown company"),
        "title": a1.event_type or "Event",
        "date": _pretty_date(event_date),
        "location": location.split(",")[0] if location else None,
        "people": people,
        "verdict": verdict,
        "tier": tier,
        "why": why,
        "duplicate_of": None,
        "source": a1.source_url,
        "reasoning": (
            [r1.reasoning_summary] + r1.positives
            + [f"Risk: {x}" for x in r1.risks]
            + [f"Unclear: {x}" for x in r1.uncertainties]
            + [f"Next: {x}" for x in s1.action_items]
        ),
        "dossier": {
            "event": a1.event_type,
            "where": location,
            "when": event_date,
            "duration": f"{days} day(s)",
            "deal value": _money(deal),
            "commercial score": f"{r1.commercial_potential_score}/10",
            "feasibility": f"{r1.operational_feasibility_score}/10",
            "announcement": text,
        },
        "proposal": proposal,
        "warnings": content.warnings,
        "ai": ai_used,   # which parts Gemini wrote: "reasoning", "proposal"
    }


# ---------------------------------------------------------------- all leads
def _row_key(row: dict) -> str:
    """Changes if the lead's data changes, so stale Gemini results aren't reused."""
    raw = json.dumps({k: _clean(v) for k, v in row.items()}, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _load_cache() -> dict:
    try:
        return json.loads(AI_CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    AI_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _process_ai(row: dict) -> dict:
    """Gemini version of process_row, cached by lead data."""
    lead = process_row(row, use_ai=True)
    if lead.get("ai"):
        with _AI_LOCK:
            cache = _load_cache()
            cache[str(row.get("lead_id"))] = {"key": _row_key(row), "lead": lead}
            _save_cache(cache)
    return lead


def run_pipeline(csv_path: str | Path = DATASET, limit: int | None = None) -> list[dict]:
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)
    out = []
    for row in df.to_dict(orient="records"):
        try:
            out.append(process_row(row))
        except Exception as e:  # one bad row shouldn't kill the whole run
            out.append({
                "id": str(row.get("lead_id")), "company": str(row.get("company_name")), "title": "Error",
                "date": None, "location": None, "people": None, "verdict": "skip",
                "why": f"Pipeline error: {e}", "duplicate_of": None, "source": None,
                "reasoning": [], "dossier": None, "proposal": "",
            })
    return out


# ---------------------------------------------------------------- new announcements
def _guess_headcount(text: str) -> int | None:
    m = re.search(r"\b(\d{2,5})\s*(?:employees|staff|members|visitors|participants|pax|people)\b", text, re.I)
    return int(m.group(1)) if m else None


EVENT_WORDS = ["summit", "conference", "convention", "workshop", "offsite", "seminar", "training", "town hall",
               "kickoff", "launch", "gala", "meetup", "hackathon", "celebration", "party", "forum", "expo", "meeting"]


def _guess_event_type(text: str) -> str | None:
    """Fallback when the analysis agent can't name the event: 'a 2-day tech summit in' -> 'Tech Summit'."""
    for word in EVENT_WORDS:
        m = re.search(rf"((?:[A-Za-z]+\s){{0,2}}{word})\b", text, re.I)
        if m:
            words = [w for w in m.group(1).split() if w.lower() not in ("a", "an", "the", "our", "its", "their", "day", "days")]
            return " ".join(words).title() or word.title()
    return None

def process_announcement(text: str, source_url: str | None = None, save: bool = True) -> dict:
    """Run one pasted announcement through the full flow:
    analysis_agent (Member 4) -> decision_agents (Member 1) -> proposal_generator (Member 3)."""
    analysis = analyze_announcement(m3.LeadInput(announcement_text=text, source_url=source_url or None))
    event_type = analysis.event_type or _guess_event_type(text)
    row = {
        "lead_id": analysis.lead_id,
        "announcement_text": text,
        "source_url": analysis.source_url,
        "company_name": analysis.company_name,
        "event_type": event_type,
        "event_date": analysis.event_date,
        "event_location": analysis.event_location,
        "attendee_count": analysis.attendee_count or _guess_headcount(text),
        "event_duration_days": analysis.event_duration_days,
        "catering_signal": analysis.catering_signal,
        "estimated_deal_value": None,
    }
    if save:
        pd.DataFrame([row]).to_csv(NEW_LEADS, mode="a", header=not NEW_LEADS.exists(), index=False)
    if gemini_client.is_enabled():
        _set_proposal_llm(True)
        try:
            lead = _process_ai(row)
        finally:
            _set_proposal_llm(False)
    else:
        lead = process_row(row)
    lead["is_new"] = True
    return lead


def _all_rows() -> list[dict]:
    rows = pd.read_csv(DATASET).to_dict(orient="records")
    if NEW_LEADS.exists():
        rows = [dict(r, _new=True) for r in pd.read_csv(NEW_LEADS).to_dict(orient="records")][::-1] + rows
    return rows


def run_all(ai: bool = False, progress=None) -> list[dict]:
    """Every lead (pasted announcements first, then the dataset).

    ai=False: rule-based for everything, plus any Gemini results saved from earlier runs.
    ai=True:  also sends the best AI_MAX_LEADS not-yet-analysed leads to Gemini.
    progress: optional callback(done, total) for a progress bar.
    """
    rows = _all_rows()
    _set_proposal_llm(False)
    leads = []
    for row in rows:
        clean = {k: v for k, v in row.items() if k != "_new"}
        try:
            lead = process_row(clean)
        except Exception as e:
            lead = {"id": str(row.get("lead_id")), "company": str(row.get("company_name")), "title": "Error",
                    "date": None, "location": None, "people": None, "verdict": "skip",
                    "why": f"Pipeline error: {e}", "duplicate_of": None, "source": None,
                    "reasoning": [], "dossier": None, "proposal": "", "ai": []}
        leads.append(lead)

    cache = _load_cache()
    by_index = {}
    for i, row in enumerate(rows):
        clean = {k: v for k, v in row.items() if k != "_new"}
        hit = cache.get(str(row.get("lead_id")))
        if hit and hit.get("key") == _row_key(clean):
            leads[i] = hit["lead"]
        by_index[i] = clean

    if ai and gemini_client.is_enabled():
        # Pick the most promising leads Gemini hasn't seen yet (skip out-of-policy ones).
        todo = [i for i, l in enumerate(leads)
                if not l.get("ai") and l.get("verdict") != "skip"]
        todo.sort(key=lambda i: ({"high": 0, "standard": 1, "light": 2}.get(leads[i]["verdict"], 3),
                                 -(leads[i].get("people") or 0)))
        todo = todo[:AI_MAX_LEADS]
        _set_proposal_llm(True)
        try:
            done = 0
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(_process_ai, by_index[i]): i for i in todo}
                for fut in futures:
                    i = futures[fut]
                    try:
                        leads[i] = fut.result()
                    except Exception:
                        pass
                    done += 1
                    if progress:
                        progress(done, len(todo))
        finally:
            _set_proposal_llm(False)

    for i, row in enumerate(rows):
        if row.get("_new"):
            leads[i]["is_new"] = True
    return leads


if __name__ == "__main__":
    from collections import Counter

    leads = run_pipeline()
    print(f"{len(leads)} leads")
    print(Counter(l["verdict"] for l in leads))
    print(Counter(l.get("tier") for l in leads))
    errors = [l for l in leads if l["title"] == "Error"]
    print(f"{len(errors)} errors", errors[:2])
    top = next((l for l in leads if l["verdict"] == "high"), None)
    if top:
        print("\nSample high-effort lead:", top["company"], "|", top["why"])
        print(top["proposal"][:400])
