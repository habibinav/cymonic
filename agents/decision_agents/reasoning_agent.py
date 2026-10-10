"""
reasoning_agent.py - Member 1: Decision-making AI (Reasoning Module)

Provides multi-dimensional reasoning on why an opportunity is or is not worth pursuing,
scoring commercial potential and operational feasibility while detailing pros, risks, and uncertainties.
"""

from typing import List
from .schemas import (
    LeadAnalysis,
    QualificationResult,
    QualificationStatus,
    ReasoningResult,
)


def evaluate(analysis: LeadAnalysis, qualification: QualificationResult) -> ReasoningResult:
    """
    Evaluates an analyzed lead alongside its qualification assessment to produce
    comprehensive business reasoning, risk profiles, scores, and recommended actions.
    """
    positives: List[str] = []
    risks: List[str] = []
    uncertainties: List[str] = []
    
    # --- 1. Identify Positives ---
    if qualification.is_service_area_matched and analysis.location:
        positives.append(f"Event is located within active service area ({analysis.location}).")
    
    if qualification.is_capacity_matched and analysis.attendance_estimate:
        positives.append(
            f"Strong attendance size ({analysis.attendance_estimate} guests) falls within optimal capacity limits."
        )
    
    if qualification.has_catering_demand_evidence:
        evidence_msg = analysis.catering_evidence or "Direct catering demand explicitly mentioned."
        positives.append(f"Confirmed catering interest: {evidence_msg}")
        
    if analysis.company_name:
        positives.append(f"Identified corporate host: '{analysis.company_name}'.")

    # --- 2. Identify Risks ---
    if qualification.status == QualificationStatus.DISQUALIFIED:
        for reason in qualification.disqualification_reasons:
            risks.append(f"CRITICAL DISQUALIFIER: {reason}")
    
    if not qualification.is_sufficient_prep_time and analysis.event_date:
        risks.append(f"Short turnaround window for event date: {analysis.event_date}.")
        
    if analysis.attendance_estimate and analysis.attendance_estimate > 800:
        risks.append("High-volume staffing and kitchen logistically intensive (attendance > 800).")

    # --- 3. Identify Uncertainties ---
    for item in qualification.missing_critical_info:
        uncertainties.append(f"Missing critical information: {item}.")
        
    for item in analysis.missing_info:
        if item not in qualification.missing_critical_info:
            uncertainties.append(f"Uncertain parameter: {item}.")

    # --- 4. Score Commercial Potential (0.0 to 10.0) ---
    commercial_score = 4.5  # Base neutral score
    
    if qualification.status == QualificationStatus.DISQUALIFIED:
        commercial_score = 0.0
    else:
        if analysis.attendance_estimate:
            if analysis.attendance_estimate >= 300:
                commercial_score += 3.0
            elif analysis.attendance_estimate >= 150:
                commercial_score += 2.0
            elif analysis.attendance_estimate >= 50:
                commercial_score += 1.0
            else:
                commercial_score += 0.5
        
        if qualification.has_catering_demand_evidence:
            commercial_score += 1.0
            
        commercial_score -= 0.5 * len(qualification.missing_critical_info)
        commercial_score = max(0.0, min(10.0, commercial_score))

    # --- 5. Score Operational Feasibility (0.0 to 10.0) ---
    feasibility_score = 7.0  # Base score
    
    if qualification.status == QualificationStatus.DISQUALIFIED:
        feasibility_score = 0.0
    else:
        if qualification.is_service_area_matched:
            feasibility_score += 1.5
        else:
            feasibility_score -= 3.0
            
        if qualification.is_capacity_matched:
            feasibility_score += 1.5
        else:
            feasibility_score -= 2.0
            
        if not qualification.is_sufficient_prep_time:
            feasibility_score -= 4.0

        feasibility_score = max(0.0, min(10.0, feasibility_score))

    # --- 6. Formulate Summary and Recommended Action ---
    if qualification.status == QualificationStatus.DISQUALIFIED:
        summary = (
            f"Opportunity disqualified due to strict operational or geographic constraints: "
            f"{'; '.join(qualification.disqualification_reasons)}"
        )
        action = "Do not pursue. Log lead as disqualified in database."
        
    elif qualification.status == QualificationStatus.NEEDS_RESEARCH:
        summary = (
            f"Opportunity shows potential but cannot be fully qualified. "
            f"Key missing data: {', '.join(qualification.missing_critical_info)}."
        )
        action = (
            f"Initiate preliminary research to verify missing details "
            f"({', '.join(qualification.missing_critical_info)}) before generating a proposal."
        )
        
    else:  # QUALIFIED
        summary = (
            f"Strong opportunity with verified capacity ({analysis.attendance_estimate or 'suitable'} guests) "
            f"and confirmed location ({analysis.location}). Commercial potential score: {commercial_score:.1f}/10."
        )
        if commercial_score >= 7.5:
            action = "Prioritize for high-effort tailored pitch and dedicated account outreach."
        else:
            action = "Proceed with standard commercial proposal outreach."

    return ReasoningResult(
        reasoning_summary=summary,
        positives=positives,
        risks=risks,
        uncertainties=uncertainties,
        commercial_potential_score=round(commercial_score, 1),
        operational_feasibility_score=round(feasibility_score, 1),
        recommended_next_action=action,
    )