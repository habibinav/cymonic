"""pipeline.py — glue that runs the whole Catering Hunter flow end to end.

    dataset CSV  ->  decision_agents (qualify -> evaluate -> choose_strategy)
                 ->  proposal_generator.generate_content
                 ->  plain dicts the Streamlit UI understands

Run it directly to sanity-check:   python pipeline.py
The UI calls run_pipeline() via streamlit_ui/data.py.
"""
from __future__ import annotations

import math
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

ROOT = Path(__file__).parent
DATASET = ROOT / "corporate_catering_hunter_synthetic_dataset_500.csv"

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
def process_row(row: dict) -> dict:
    people = _int(row.get("attendee_count"))
    days = _int(row.get("event_duration_days")) or 1
    location = _clean(row.get("event_location"))
    event_date = _clean(row.get("event_date"))
    text = _clean(row.get("announcement_text")) or ""
    deal = _clean(row.get("estimated_deal_value"))

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
    }


# ---------------------------------------------------------------- all leads
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
