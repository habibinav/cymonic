"""Opportunity Qualification Agent (Member 2 module).

Evaluates whether an opportunity is qualified, needs research, or is disqualified
based on business profile constraints and evidence completeness.
"""

from __future__ import annotations

from schemas import BusinessProfile, LeadAnalysis, QualificationResult, QualificationStatus


def qualify_lead(analysis: LeadAnalysis, business_profile: BusinessProfile | None = None) -> QualificationResult:
    """Evaluate opportunity qualification status and hard constraint checks."""
    profile = business_profile or BusinessProfile()

    hard_failures: list[str] = []
    passed_constraints: list[str] = []

    # 1. Service Area Check
    if analysis.event_location:
        in_area = any(area.lower() in analysis.event_location.lower() for area in profile.service_area)
        if not in_area:
            hard_failures.append("outside_service_area")
        else:
            passed_constraints.append("service_area_compatible")
    else:
        # Location unknown - not an automatic disqualification, but triggers research
        pass

    # 2. Capacity Check
    if analysis.attendee_count is not None:
        if profile.max_guests and analysis.attendee_count > profile.max_guests:
            hard_failures.append("exceeds_max_capacity")
        elif profile.min_guests and analysis.attendee_count < profile.min_guests:
            hard_failures.append("below_min_capacity")
        else:
            passed_constraints.append("capacity_within_range")

    # 3. Decision Logic
    if hard_failures:
        status = QualificationStatus.DISQUALIFIED.value
        reason = f"Opportunity disqualified due to constraint failure(s): {', '.join(hard_failures)}."
    elif (
        analysis.attendee_count is None
        or not analysis.event_date
        or not analysis.event_location
        or analysis.catering_signal == "unknown"
    ):
        status = QualificationStatus.NEEDS_RESEARCH.value
        missing = []
        if analysis.attendee_count is None:
            missing.append("attendee count")
        if not analysis.event_date:
            missing.append("event date")
        if not analysis.event_location:
            missing.append("event location")
        if analysis.catering_signal == "unknown":
            missing.append("catering signal")
        reason = f"Critical information missing ({', '.join(missing)}); research required before commitment."
    else:
        status = QualificationStatus.QUALIFIED.value
        passed_constraints.append("catering_demand_credible")
        reason = "Opportunity satisfies service area, capacity limits, and verified catering signals."

    return QualificationResult(
        status=status,
        hard_constraint_failures=hard_failures,
        passed_constraints=passed_constraints,
        reason=reason,
    )
