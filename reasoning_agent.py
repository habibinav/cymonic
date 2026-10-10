"""Reasoning Agent (Member 2 module).

Synthesizes event facts, estimates deal value, assesses risks, and produces reasoning summaries.
"""

from __future__ import annotations

from schemas import BusinessProfile, LeadAnalysis, QualificationResult, ReasoningResult


def reason_about_lead(
    analysis: LeadAnalysis,
    qualification: QualificationResult,
    business_profile: BusinessProfile | None = None,
) -> ReasoningResult:
    """Evaluate financial potential, operational risks, and overall opportunity reasoning."""
    # Estimate deal value (Standard benchmark: 750 INR per plate * guests * days)
    deal_value = None
    if analysis.attendee_count is not None and analysis.attendee_count > 0:
        days = analysis.event_duration_days or 1
        deal_value = float(analysis.attendee_count * 750.0 * days)

    risks: list[str] = []
    uncertainties: list[str] = []

    if qualification.status == "disqualified":
        risks.append(f"Hard constraint barrier: {qualification.reason}")
    elif qualification.status == "needs_research":
        uncertainties.extend(analysis.unknown_fields)
        risks.append("Operational logistics cannot be locked without verified event parameters.")
    else:
        if analysis.attendee_count and analysis.attendee_count > 300:
            risks.append("High guest volume requires enhanced kitchen staging and server coordination.")
        uncertainties.append("Final dietary requirements and VIP guest count.")

    # Generate reasoning summary
    if qualification.status == "qualified":
        summary = (
            f"Known attendance ({int(analysis.attendee_count) if analysis.attendee_count else 'unconfirmed'}) "
            f"and credible catering demand indicate a plausible order; "
            f"proposal is justified subject to standard capacity and margin validation."
        )
    elif qualification.status == "needs_research":
        summary = (
            "Critical information about attendance, date, or catering demand is missing; "
            "use light outreach or research before estimating value or preparing a proposal."
        )
    else:
        summary = f"Opportunity blocked: {qualification.reason}"

    return ReasoningResult(
        summary=summary,
        risks=risks,
        uncertainties=uncertainties,
        estimated_deal_value=deal_value,
    )
