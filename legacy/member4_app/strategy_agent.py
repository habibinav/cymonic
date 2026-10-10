"""Pursuit Strategy Agent (Member 2 module).

Selects the pursuit tier and decides whether a formal proposal is required.
"""

from __future__ import annotations

from schemas import LeadAnalysis, PursuitTier, QualificationResult, ReasoningResult, StrategyResult


def determine_strategy(
    analysis: LeadAnalysis,
    qualification: QualificationResult,
    reasoning: ReasoningResult,
) -> StrategyResult:
    """Select the optimal pursuit tier based on qualification status, deal value, and risks."""
    status = qualification.status

    if status == "disqualified":
        return StrategyResult(
            tier=PursuitTier.NONE.value,
            rationale="Opportunity is disqualified; no pursuit or proposal justified.",
            proposal_required=False,
        )

    if status == "needs_research":
        return StrategyResult(
            tier=PursuitTier.NEEDS_RESEARCH.value,
            rationale="Information incomplete; internal research checklist required before active pursuit.",
            proposal_required=False,
        )

    # Qualified Lead Strategy Selection
    deal_value = reasoning.estimated_deal_value or 0.0

    if deal_value >= 200000.0 or (analysis.attendee_count and analysis.attendee_count >= 250):
        return StrategyResult(
            tier=PursuitTier.HIGH_EFFORT_PITCH.value,
            rationale="High estimated order value and large headcount warrant a tailored executive pitch.",
            proposal_required=True,
        )
    elif deal_value >= 100000.0 or (analysis.attendee_count and analysis.attendee_count >= 100):
        return StrategyResult(
            tier=PursuitTier.STANDARD_PROPOSAL.value,
            rationale="Verified attendance and solid deal economics justify a standard proposal outline.",
            proposal_required=True,
        )
    else:
        return StrategyResult(
            tier=PursuitTier.LIGHT_OUTREACH.value,
            rationale="Qualified lead with moderate or unverified size; initiate with exploratory light outreach.",
            proposal_required=False,
        )
