"""
qualification_agent.py - Member 1: Decision-making AI (Qualification Module)

Determines whether a corporate catering opportunity is feasible based on business rules,
operational capacity, location constraints, and evidence of catering demand.
"""

from datetime import datetime, date
import re
from typing import List, Optional

from .schemas import (
    LeadAnalysis,
    BusinessProfile,
    QualificationResult,
    QualificationStatus,
)


def _check_service_area(location: Optional[str], service_areas: List[str]) -> bool:
    """Check if event location falls within any of the supported service areas."""
    if not location or location.strip().lower() in ["unknown", "n/a", "tbd", "unspecified"]:
        return False
    
    loc_clean = location.lower()
    for area in service_areas:
        if area.lower() in loc_clean:
            return True
    return False


def _check_capacity(
    attendance: Optional[int], min_cap: int, max_cap: int
) -> tuple[bool, Optional[str]]:
    """
    Check if estimated attendance is within business operational limits.
    Returns (is_valid, disqualification_reason_if_any).
    """
    if attendance is None:
        return False, None
    
    if attendance > max_cap:
        return False, f"Estimated attendance ({attendance}) exceeds maximum confirmed catering capacity ({max_cap})."
    
    if attendance < min_cap:
        return False, f"Estimated attendance ({attendance}) is below minimum order requirement ({min_cap} guests)."
    
    return True, None


def _check_catering_demand(catering_evidence: Optional[str], evidence_facts: list) -> bool:
    """Verify if there is explicit or strongly inferred evidence of food/catering demand."""
    keywords = [
        "catering", "lunch", "dinner", "food", "buffet", "meal", "refreshment",
        "coffee", "snack", "breakfast", "banquet", "cocktail", "tea break", "hospitality"
    ]
    
    if catering_evidence and any(kw in catering_evidence.lower() for kw in keywords):
        return True
        
    for fact_obj in evidence_facts:
        fact_text = getattr(fact_obj, "fact", str(fact_obj)).lower()
        if any(kw in fact_text for kw in keywords):
            return True
            
    return False


def _parse_days_until_event(event_date_str: Optional[str]) -> Optional[int]:
    """Parse notice days remaining before event date."""
    if not event_date_str:
        return None
    
    match = re.search(r"(\d{4}-\d{2}-\d{2})", event_date_str)
    if match:
        try:
            evt_dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            today = date.today()
            return (evt_dt - today).days
        except ValueError:
            pass
            
    return None


def qualify(analysis: LeadAnalysis, business_profile: BusinessProfile) -> QualificationResult:
    """
    Evaluates a LeadAnalysis against the BusinessProfile and returns a structured QualificationResult.
    
    Hard Disqualification Triggers:
    - Attendance > max_capacity or < min_capacity.
    - Location explicitly outside service area.
    - Preparation notice days less than min_notice_days.

    Needs Research Triggers:
    - Critical commercial fields missing (Location, Attendance, or Event Date unknown).

    Qualified Trigger:
    - All operational, geographic, and temporal constraints satisfied.
    """
    missing_critical_info: List[str] = []
    disqualification_reasons: List[str] = []
    notes: List[str] = []

    # 1. Service Area Check
    is_location_known = bool(
        analysis.location and analysis.location.strip().lower() not in ["unknown", "tbd", "n/a", "unspecified"]
    )
    is_service_area_matched = False
    
    if not is_location_known:
        missing_critical_info.append("Event Location")
        notes.append("Location is unconfirmed/missing.")
    else:
        is_service_area_matched = _check_service_area(analysis.location, business_profile.service_areas)
        if not is_service_area_matched:
            disqualification_reasons.append(
                f"Location '{analysis.location}' is outside confirmed service areas ({', '.join(business_profile.service_areas)})."
            )
        else:
            notes.append(f"Location '{analysis.location}' is within service area.")

    # 2. Capacity Check
    is_capacity_matched = False
    if analysis.attendance_estimate is None:
        missing_critical_info.append("Attendance Estimate")
        notes.append("Attendance count is missing.")
    else:
        cap_ok, disq_reason = _check_capacity(
            analysis.attendance_estimate, business_profile.min_capacity, business_profile.max_capacity
        )
        if not cap_ok and disq_reason:
            disqualification_reasons.append(disq_reason)
        else:
            is_capacity_matched = cap_ok
            notes.append(f"Attendance estimate ({analysis.attendance_estimate}) is within capacity range.")

    # 3. Minimum Order Requirement Check
    is_min_order_satisfied = True
    if analysis.attendance_estimate is not None and analysis.attendance_estimate < business_profile.min_capacity:
        is_min_order_satisfied = False

    # 4. Catering Demand Evidence Check
    has_catering_demand_evidence = _check_catering_demand(
        analysis.catering_evidence, analysis.evidence_facts
    )
    if not has_catering_demand_evidence:
        missing_critical_info.append("Catering Demand Confirmation")
        notes.append("No explicit mention of food or catering requirements found.")
    else:
        notes.append("Catering demand confirmed by announcement evidence.")

    # 5. Prep Time Check
    is_sufficient_prep_time = True
    days_notice = _parse_days_until_event(analysis.event_date)
    if days_notice is not None:
        if days_notice < business_profile.min_notice_days:
            is_sufficient_prep_time = False
            disqualification_reasons.append(
                f"Event date provides only {days_notice} day(s) notice, below required minimum notice of {business_profile.min_notice_days} days."
            )
        else:
            notes.append(f"Preparation window is sufficient ({days_notice} days notice).")
    elif not analysis.event_date or analysis.event_date.strip().lower() in ["unknown", "tbd", "n/a"]:
        missing_critical_info.append("Event Date")
        notes.append("Exact event date is unknown.")

    # 6. Synthesize Final Status
    if disqualification_reasons:
        status = QualificationStatus.DISQUALIFIED
    elif missing_critical_info:
        status = QualificationStatus.NEEDS_RESEARCH
    else:
        status = QualificationStatus.QUALIFIED

    return QualificationResult(
        status=status,
        is_service_area_matched=is_service_area_matched,
        is_capacity_matched=is_capacity_matched,
        has_catering_demand_evidence=has_catering_demand_evidence,
        is_sufficient_prep_time=is_sufficient_prep_time,
        is_min_order_satisfied=is_min_order_satisfied,
        missing_critical_info=missing_critical_info,
        disqualification_reasons=disqualification_reasons,
        qualification_notes=notes,
    )