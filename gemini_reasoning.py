"""gemini_reasoning.py — Gemini-powered reasoning agent.

The hard business rules stay in Member 1's qualification_agent (service area, capacity,
notice period) so nothing out-of-policy ever gets pursued. For leads that pass those checks,
Gemini reads the full announcement and the rule results, then writes the reasoning and scores
the opportunity. Member 1's strategy_agent then turns those scores into a pursuit tier.

Returns None if Gemini is off or fails — the caller keeps the rule-based reasoning instead.
"""
from __future__ import annotations

import json

from decision_agents import schemas as m1
from gemini_client import generate_json

SYSTEM_PROMPT = """You are the Reasoning Agent for a corporate catering company in India.
You receive one corporate event lead: the original announcement text, the extracted facts,
and the results of rule-based qualification checks (service area, capacity, notice period,
catering evidence). Decide how attractive this catering opportunity is and explain why.

Think about: likely order size (guests x days x meals), whether food is explicitly needed or
only implied, repeat-business potential (annual events, new offices, large employers),
brand value of the client, timing pressure, logistics (multi-day, very large crowds), and
anything missing that we would need to confirm.

Rules:
- Use ONLY the facts provided. Never invent numbers, names, prices or past relationships.
- Be specific to THIS event — no generic filler.
- If the qualification status is "needs_research", explain what is missing and why it matters.

Scoring guide (0-10, one decimal):
- commercial_potential_score: 8+ = big, high-value or strategic deal worth a custom pitch;
  5-7.9 = solid standard deal; below 5 = small or uncertain, worth only a light email.
- operational_feasibility_score: how comfortably we can deliver it (0 = impossible, 10 = easy).

Return ONLY a JSON object with exactly these keys:
{
  "summary": "2-3 sentence assessment of this specific opportunity",
  "positives": ["specific reasons to pursue"],
  "risks": ["specific delivery or commercial risks"],
  "uncertainties": ["facts we still need to confirm"],
  "commercial_potential_score": 0.0,
  "operational_feasibility_score": 0.0,
  "recommended_next_action": "one concrete next step"
}"""


def _score(value, fallback: float) -> float:
    try:
        return round(max(0.0, min(10.0, float(value))), 1)
    except (TypeError, ValueError):
        return fallback


def _str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:6]
    return [str(value)] if value else []


def reason_with_gemini(
    facts: dict,
    qualification: m1.QualificationResult,
    rule_reasoning: m1.ReasoningResult,
) -> m1.ReasoningResult | None:
    """Ask Gemini to reason about one lead. Returns a ReasoningResult or None."""
    payload = {
        "lead": facts,
        "qualification": {
            "status": qualification.status.value,
            "in_service_area": qualification.is_service_area_matched,
            "capacity_ok": qualification.is_capacity_matched,
            "catering_evidence_found": qualification.has_catering_demand_evidence,
            "enough_notice": qualification.is_sufficient_prep_time,
            "missing_info": qualification.missing_critical_info,
            "notes": qualification.qualification_notes,
        },
        "rule_based_scores_for_reference": {
            "commercial_potential_score": rule_reasoning.commercial_potential_score,
            "operational_feasibility_score": rule_reasoning.operational_feasibility_score,
        },
    }
    data = generate_json(SYSTEM_PROMPT, "Assess this lead:\n" + json.dumps(payload, indent=2, default=str))
    if not data or not data.get("summary"):
        return None

    return m1.ReasoningResult(
        reasoning_summary=str(data["summary"]).strip(),
        positives=_str_list(data.get("positives")),
        risks=_str_list(data.get("risks")),
        uncertainties=_str_list(data.get("uncertainties")),
        commercial_potential_score=_score(data.get("commercial_potential_score"), rule_reasoning.commercial_potential_score),
        operational_feasibility_score=_score(data.get("operational_feasibility_score"), rule_reasoning.operational_feasibility_score),
        recommended_next_action=str(data.get("recommended_next_action") or rule_reasoning.recommended_next_action),
    )
