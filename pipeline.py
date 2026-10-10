"""pipeline.py — glue that runs the whole Catering Hunter flow end to end.

    data/*.csv  ->  agents/analysis_agent        (pasted announcements only)
                ->  agents/decision_agents        qualify -> reason -> choose tier
                ->  agents/proposal_generator     draft (template)
                ->  plain dicts for the UI (app/)

Gemini (agents/gemini_batch.py) is on-demand: the UI asks for a section, a company folder or a
single lead, and analyze_leads() sends just those leads. Gemini then writes the reasoning,
scores and a tailored draft. The hard rules (service area, capacity, notice) always stay
rule-based, and Member 1's strategy agent still turns the scores into the tier.
Results are cached in data/ai_cache.json.

Sanity check:   python3 pipeline.py
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "agents"))   # agent modules import each other by plain name

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
import gemini_batch
import gemini_client
from config import HUMAN_REVIEW_DISCLAIMER
from proposal_generator import validate_generated_content

DATA = ROOT / "data"
DATASET = DATA / "corporate_catering_hunter_synthetic_dataset_500.csv"
NEW_LEADS = DATA / "new_leads.csv"   # announcements pasted into the UI are saved here
AI_CACHE = DATA / "ai_cache.json"    # Gemini results, so they survive restarts
AI_CACHE_VERSION = 2

# One shared business profile. Service areas include all confirmed hubs present in the dataset.
SERVICE_AREAS = [
    "Kochi", "Ernakulam", "Trivandrum", "Thiruvananthapuram",
    "Bangalore", "Bengaluru", "Chennai", "Mumbai", "Pune",
    "Delhi", "New Delhi", "Noida", "Gurugram", "Gurgaon",
    "Hyderabad", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
    "Indore", "Bhubaneswar", "Coimbatore", "Goa", "Mysuru", "Visakhapatnam"
]
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
    "needs_research": "light",
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
def _clean_name(name) -> str:
    # dataset names carry an ID suffix ("Orbit Retail 038") — drop it
    return re.sub(r"\s+\d+$", "", str(name or "Unknown company"))


def _prepare(row: dict) -> dict:
    """Facts + rule-based qualification and reasoning for one lead (fast, no AI)."""
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

    # ---- Member 1: qualify + rule-based reasoning
    a1 = m1.LeadAnalysis(
        company_name=_clean_name(_clean(row.get("company_name"))),
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
    return dict(row=row, people=people, days=days, location=location, event_date=event_date,
                text=text, deal=deal, missing=missing, a1=a1, q1=q1, r1=r1)


def _ai_payload(ctx: dict) -> dict:
    """What Gemini sees for one lead."""
    q1, a1 = ctx["q1"], ctx["a1"]
    return {
        "id": str(ctx["row"].get("lead_id")),
        "company": a1.company_name, "event_type": a1.event_type, "date": ctx["event_date"],
        "location": ctx["location"], "attendees": ctx["people"], "duration_days": ctx["days"],
        "catering_signal": _clean(ctx["row"].get("catering_signal")),
        "estimated_deal_value_inr": ctx["deal"],
        "announcement": ctx["text"],
        "qualification_status": q1.status.value,
        "missing_info": q1.missing_critical_info,
        "catering_evidence_found": q1.has_catering_demand_evidence,
    }


def _score(v, fallback):
    try:
        return round(max(0.0, min(10.0, float(v))), 1)
    except (TypeError, ValueError):
        return fallback


def _list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:6]
    return [str(v)] if v else []


def _finish(ctx: dict, ai: dict | None = None) -> dict:
    """Tier + proposal + UI shape. `ai` is Gemini's result for this lead (or None for rule-based)."""
    a1, q1, r1 = ctx["a1"], ctx["q1"], ctx["r1"]
    people, days, location, event_date, text, deal = (ctx[k] for k in
                                                     ("people", "days", "location", "event_date", "text", "deal"))
    row = ctx["row"]
    ai_used = []

    if ai and q1.status != m1.QualificationStatus.DISQUALIFIED:
        r1 = m1.ReasoningResult(
            reasoning_summary=str(ai.get("summary", "")).strip() or r1.reasoning_summary,
            positives=_list(ai.get("positives")),
            risks=_list(ai.get("risks")),
            uncertainties=_list(ai.get("uncertainties")),
            commercial_potential_score=_score(ai.get("commercial_potential_score"), r1.commercial_potential_score),
            operational_feasibility_score=_score(ai.get("operational_feasibility_score"), r1.operational_feasibility_score),
            recommended_next_action=str(ai.get("next_action") or r1.recommended_next_action),
        )
        ai_used.append("reasoning")
    else:
        ai = None

    # ---- Member 1: strategy (tier) from the scores
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
        unknown_fields=ctx["missing"],
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

    # ---- proposal: Gemini's draft (sanitised by Member 3's checks) or Member 3's template
    draft = str((ai or {}).get("draft") or "").strip()
    if ai and draft and ai.get("tier") == tier:
        draft, val_warnings = validate_generated_content(draft_text=draft, business_profile=PROFILE_M3, analysis=a3)
        if tier == "needs_research":
            proposal = "**Internal research checklist (not for the client)**\n\n" + draft
        else:
            proposal = draft if HUMAN_REVIEW_DISCLAIMER in draft else f"{HUMAN_REVIEW_DISCLAIMER}\n\n{draft}"
        warnings = val_warnings
        ai_used.append("proposal")
    else:
        content = generate_content(a3, q3, r3, st3, PROFILE_M3)
        proposal = content.draft_text
        if not proposal and content.research_questions:
            proposal = "Research checklist:\n" + "\n".join(f"• {q}" for q in content.research_questions)
        warnings = content.warnings

    # ---- shape for the UI
    verdict = TIER_TO_VERDICT.get(tier, "skip")
    if q1.status == m1.QualificationStatus.DISQUALIFIED:
        if location and not q1.is_service_area_matched:
            why = f"Outside service area ({location.split(',')[0]})"
        else:
            why = q1.disqualification_reasons[0] if q1.disqualification_reasons else "Disqualified"
    elif ai and ai.get("headline"):
        why = str(ai["headline"]).strip()
    elif tier == "needs_research":
        why = "Needs research — missing " + ", ".join(q1.missing_critical_info).lower()
    else:
        bits = [f"{days}-day {(a1.event_type or 'event').lower()}"]
        if deal:
            bits.append(f"~{_money(deal)} deal")
        bits.append(f"score {r1.commercial_potential_score}/10")
        why = ", ".join(bits)

    next_steps = [r1.recommended_next_action] if ai else s1.action_items
    return {
        "id": str(row.get("lead_id")),
        "company": a1.company_name or "Unknown company",
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
            + [f"Next: {x}" for x in next_steps]
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
        "warnings": warnings,
        "ai": ai_used,   # which parts Gemini wrote: "reasoning", "proposal"
    }


def process_row(row: dict, ai: dict | None = None) -> dict:
    return _finish(_prepare(row), ai)


# ---------------------------------------------------------------- all leads
def _row_key(row: dict) -> str:
    """Changes if the lead's data changes, so stale Gemini results aren't reused."""
    raw = json.dumps({k: _clean(v) for k, v in row.items()}, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _load_cache() -> dict:
    try:
        cache = json.loads(AI_CACHE.read_text(encoding="utf-8"))
        return cache if cache.get("_version") == AI_CACHE_VERSION else {"_version": AI_CACHE_VERSION}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return {"_version": AI_CACHE_VERSION}


def _save_cache(cache: dict) -> None:
    AI_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


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
    ctx = _prepare(row)
    ai = None
    if gemini_client.is_enabled() and ctx["q1"].status != m1.QualificationStatus.DISQUALIFIED:
        ai = gemini_batch.analyze([_ai_payload(ctx)], PROFILE_M3).get(str(row["lead_id"]))
        if ai:
            cache = _load_cache()
            cache[str(row["lead_id"])] = {"key": _row_key(row), "ai": ai}
            _save_cache(cache)
    lead = _finish(ctx, ai)
    lead["is_new"] = True
    return lead


def _all_rows() -> list[dict]:
    rows = pd.read_csv(DATASET).to_dict(orient="records")
    if NEW_LEADS.exists():
        rows = [dict(r, _new=True) for r in pd.read_csv(NEW_LEADS).to_dict(orient="records")][::-1] + rows
    return rows


def run_all() -> list[dict]:
    """Every lead (pasted announcements first, then the dataset), plus any saved Gemini results."""
    rows = _all_rows()
    cache = _load_cache()
    leads = []
    for row in rows:
        clean = {k: v for k, v in row.items() if k != "_new"}
        hit = cache.get(str(clean.get("lead_id")))
        ai = hit["ai"] if isinstance(hit, dict) and hit.get("key") == _row_key(clean) else None
        try:
            lead = _finish(_prepare(clean), ai)
        except Exception as e:  # one bad row shouldn't kill the whole run
            lead = {"id": str(clean.get("lead_id")), "company": str(clean.get("company_name")),
                    "title": "Error", "date": None, "location": None, "people": None, "verdict": "skip",
                    "why": f"Pipeline error: {e}", "duplicate_of": None, "source": None,
                    "reasoning": [], "dossier": None, "proposal": "", "ai": []}
        if row.get("_new"):
            lead["is_new"] = True
        leads.append(lead)
    return leads


def analyze_leads(ids, progress=None) -> int:
    """Send the given lead ids to Gemini (skipping out-of-policy ones) and cache the results.
    Returns how many leads Gemini analysed. progress: optional callback(done, total)."""
    if not gemini_client.is_enabled():
        return 0
    wanted = {str(i) for i in ids}
    ctxs = [_prepare({k: v for k, v in r.items() if k != "_new"}) for r in _all_rows()
            if str(r.get("lead_id")) in wanted]
    ctxs = [c for c in ctxs if c["q1"].status != m1.QualificationStatus.DISQUALIFIED]
    results = gemini_batch.analyze([_ai_payload(c) for c in ctxs], PROFILE_M3, progress=progress)
    cache = _load_cache()
    for c in ctxs:
        lead_id = str(c["row"].get("lead_id"))
        if lead_id in results:
            cache[lead_id] = {"key": _row_key(c["row"]), "ai": results[lead_id]}
    _save_cache(cache)
    return sum(1 for c in ctxs if str(c["row"].get("lead_id")) in results)


if __name__ == "__main__":
    from collections import Counter

    leads = run_all()
    print(f"{len(leads)} leads | Gemini {'ON' if gemini_client.is_enabled() else 'off'} "
          f"| {sum(1 for l in leads if l.get('ai'))} analysed by Gemini so far")
    print(Counter(l["verdict"] for l in leads))
    print(Counter(l.get("tier") for l in leads))
    errors = [l for l in leads if l["title"] == "Error"]
    print(f"{len(errors)} errors", errors[:2])
    top = next((l for l in leads if l["verdict"] == "high"), None)
    if top:
        safe_why = str(top["why"]).encode("ascii", "replace").decode("ascii")
        print("\nSample high-effort lead:", top["company"], "|", safe_why)
        safe_prop = str(top["proposal"][:400]).encode("ascii", "replace").decode("ascii")
        print(safe_prop)
