"""
strategy_agent.py - Member 1: Decision-making AI (Strategy Selection Module)

Selects the exact pursuit strategy tier based on qualification status and reasoning analytics.
Pursuit Tiers:
- light_outreach: Low-effort exploratory outreach
- standard_proposal: Standard proposal outline for qualified leads
- high_effort_pitch: High-value pitch with custom presentation & menus
- needs_research: Information gathering checklist before proposal
- none: Do not pursue (Disqualified)
"""

from typing import List
from .schemas import (
    QualificationResult,
    QualificationStatus,
    ReasoningResult,
    PursuitTier,
    StrategyResult,
)


def choose_strategy(qualification: QualificationResult, reasoning: ReasoningResult) -> StrategyResult:
    """
    Selects exactly one pursuit tier and provides justification and action items.
    
    Function contract:
    def choose_strategy(qualification, reasoning) -> StrategyResult
    """
    action_items: List[str] = []
    
    # 1. Hard Disqualification -> Pursuit Tier NONE
    if qualification.status == QualificationStatus.DISQUALIFIED:
        tier = PursuitTier.NONE
        justification = (
            f"Opportunity disqualified due to hard constraints: "
            f"{'; '.join(qualification.disqualification_reasons)}"
        )
        action_items.append("Log lead as disqualified in CRM / dataset.")
        action_items.append("Do not send prospect-facing communications.")
        
    # 2. Missing Data -> Pursuit Tier NEEDS_RESEARCH
    elif qualification.status == QualificationStatus.NEEDS_RESEARCH:
        tier = PursuitTier.NEEDS_RESEARCH
        justification = (
            f"Lead requires research due to unconfirmed fields: "
            f"{', '.join(qualification.missing_critical_info)}."
        )
        action_items.append(f"Execute research checklist to clarify: {', '.join(qualification.missing_critical_info)}.")
        action_items.append("Re-evaluate opportunity after gathering facts.")

    # 3. Qualified Leads -> Choose Tier based on Commercial & Operational Scores
    else:
        comm_score = reasoning.commercial_potential_score
        feas_score = reasoning.operational_feasibility_score
        
        if comm_score >= 7.5 and feas_score >= 6.0:
            tier = PursuitTier.HIGH_EFFORT_PITCH
            justification = (
                f"High-value target (Commercial Score: {comm_score}/10, Feasibility Score: {feas_score}/10). "
                f"Justifies customized pitch deck, tailored menu concepts, and senior management outreach."
            )
            action_items.append("Prepare customized corporate menu proposal with chef notes.")
            action_items.append("Schedule discovery call with event manager.")
            
        elif comm_score >= 5.0:
            tier = PursuitTier.STANDARD_PROPOSAL
            justification = (
                f"Solid qualified lead (Commercial Score: {comm_score}/10). "
                f"Warrants standard corporate proposal outline and standard pricing menu."
            )
            action_items.append("Generate standard catering proposal outline.")
            action_items.append("Send preliminary information deck to host contact.")
            
        else:
            tier = PursuitTier.LIGHT_OUTREACH
            justification = (
                f"Qualified but lower commercial return or high operational effort (Commercial Score: {comm_score}/10). "
                f"Appropriate for lightweight introductory email outreach."
            )
            action_items.append("Send standard introductory brochure and catering flyer.")
            action_items.append("Follow up in 5 business days.")

    return StrategyResult(
        pursuit_tier=tier,
        justification=justification,
        action_items=action_items,
    )