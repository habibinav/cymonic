"""Proposal & Outreach Generation Module for the Corporate Catering Hunter AI Agent.

Primary Objective:
Produces safe, structured pursuit content matching the pursuit tier selected by upstream agents:
- Tier 1: light_outreach (short exploratory outreach draft)
- Tier 2: standard_proposal (standard proposal outline)
- Tier 3: high_effort_pitch (tailored executive pitch)
- Tier 4: needs_research (internal research checklist)
- Tier 5: none (no prospect-facing content)

Enforces strict deterministic policy safeguards:
- Disqualified leads NEVER receive prospect-facing content.
- Hard-constraint failures block prospect-facing drafts.
- Needs-research leads cannot receive outreach or proposals; routed to research checklist.
- Unsupported prices, unconfirmed capabilities, guarantees, or testimonials are blocked/sanitized.
- All prospect-facing drafts are explicitly marked for human review.
- Never sends external communications or calls external communication tools.

ILLUSTRATIVE EXAMPLES (Fictional — for reference only):
-------------------------------------------------------
Example 1 (light_outreach):
    **Draft for human review — not sent. Verify event details, recipient information, business capabilities, pricing, and availability before use.**

    Subject: Catering support for TechCorp - Annual Summit
    Hello [contact name],
    I came across the announcement for TechCorp's Annual Summit in Bengaluru and wanted to inquire whether catering arrangements have already been finalized.
    If catering support is still under consideration, Apex Catering would welcome the opportunity to discuss your requirements.
    Best regards,
    Aarav Sharma
    Apex Catering

Example 2 (standard_proposal):
    **Draft for human review — not sent. Verify event details, recipient information, business capabilities, pricing, and availability before use.**

    ## Catering Proposal Outline
    **Catering Provider:** Apex Catering
    **Target Company:** TechCorp
    **Event Title:** Annual Summit
    **Date:** 2027-02-15
    **Location:** Bengaluru, Karnataka
    ### 1. Understanding of Requirements
    - Scope: Catering support for Annual Summit hosting 200 estimated attendees.
    ### 2. Proposed Approach
    - Core Services: Corporate Lunch, Buffet Service.
    ### 3. Details to Confirm
    - Final attendee headcount: 200 estimated attendees
    - Venue access: [confirm venue address and facilities]
    ### 4. Commercial Details
    Pricing and package details: [to be confirmed after requirements are validated]
    ### 5. Next Steps
    Confirm outstanding requirements before preparing final quotation.

Example 3 (high_effort_pitch):
    **Draft for human review — not sent. Verify event details, recipient information, business capabilities, pricing, and availability before use.**

    ## Executive Catering Pitch: Leadership Summit
    **Prepared for:** TechCorp
    ### 1. Executive Summary
    Tailored culinary solution for high-priority leadership gathering.
    ### 2. Tailored Culinary Solution
    Executive Dining, Buffet Service adhering to verified venue protocols.
    ### 3. Commercial Framework
    Pricing status: [to be confirmed after requirements are validated]

Example 4 (needs_research):
    ## Internal Research Checklist
    **Opportunity:** Alpha Inc - Seminar
    **Status:** Incomplete information — internal research required.
    ### Outstanding Questions
    - What is the confirmed attendee headcount?
    - What is the confirmed event date?
    ### Recommended Research Tasks
    - Verify primary announcement source.
    - Confirm event location is within approved service area.

Example 5 (none):
    content_type: "none"
    draft_text: ""
    prospect_facing: False
    internal_explanation: "No prospect-facing content generated: opportunity is disqualified."
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Tuple

from config import (
    HUMAN_REVIEW_DISCLAIMER,
    PLACEHOLDER_CONFIRM_DATE,
    PLACEHOLDER_CONFIRM_GUESTS,
    PLACEHOLDER_CONFIRM_PRICING,
    PLACEHOLDER_CONFIRM_VENUE,
    PLACEHOLDER_CONTACT_NAME,
    PLACEHOLDER_YOUR_NAME,
)
from prompts import (
    build_system_prompt,
    build_user_prompt,
)
from schemas import (
    BusinessProfile,
    ContentType,
    GeneratedContent,
    LeadAnalysis,
    PursuitTier,
    QualificationResult,
    QualificationStatus,
    ReasoningResult,
    StrategyResult,
)

logger = logging.getLogger(__name__)

# High-risk service keywords that must be explicitly confirmed in BusinessProfile
HIGH_RISK_SERVICES: dict[str, list[str]] = {
    "staffing": [
        "dedicated waitstaff",
        "event staffing",
        "waitstaff",
        "table service",
        "bartender",
        "bar service",
        "waiter service",
    ],
    "on_site_chef": [
        "on-site chef",
        "live cooking station",
        "live counter",
        "live cooking",
    ],
    "delivery": [
        "same-day delivery",
        "guaranteed delivery time",
        "express delivery",
    ],
    "wedding": [
        "wedding catering",
        "wedding reception",
    ],
    "international": [
        "international cuisine",
        "exotic cuisine",
    ],
    "equipment": [
        "equipment rental",
        "tableware rental",
        "furniture setup",
    ],
}

# Prohibited promotional, guarantee, or past-relationship claims
PROHIBITED_MARKETING_CLAIMS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bguaranteed (?:satisfaction|success|perfection|attendance)\b", re.I), "guaranteed outcome"),
    (re.compile(r"\b100%\s*guarantee\b", re.I), "100% guarantee"),
    (re.compile(r"\baward-winning\b", re.I), "award-winning claim"),
    (re.compile(r"\brated\s*(?:#1|number\s*one)\b", re.I), "market ranking claim"),
    (re.compile(r"\bmarket leader\b", re.I), "market leader claim"),
    (re.compile(r"\bour past partnership\b", re.I), "unverified prior relationship"),
    (re.compile(r"\bas discussed previously\b", re.I), "unverified prior conversation"),
    (re.compile(r"\bin our previous conversation\b", re.I), "unverified prior conversation"),
]

# Patterns for currency and price claims
PRICE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:₹|Rs\.?|INR|\$|€|£)\s*\d+(?:,\d+)*(?:\.\d+)?", re.I),
    re.compile(r"\b\d+\s*(?:INR|rupees|dollars|per plate|per person|per head|\/person|\/plate|\/head)\b", re.I),
    re.compile(r"\b(?:rate of|priced at|cost is|package at)\s*(?:₹|Rs\.?|INR|\$)?\s*\d+", re.I),
]


# ============================================================================
# Helpers for input normalization and extraction
# ============================================================================

def _get_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """Safely extract field from a Pydantic model, dataclass, or dictionary."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _to_clean_dict(obj: Any) -> dict[str, Any]:
    """Convert input object into a dictionary for prompts or processing without mutation."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


# ============================================================================
# Policy Enforcement (Task B)
# ============================================================================

def evaluate_content_policy(
    qualification_status: str,
    pursuit_tier: str,
    hard_constraint_failures: list[str],
) -> Tuple[bool, str, list[str]]:
    """Evaluate whether prospect-facing content is permitted based on strict policy rules.

    Args:
        qualification_status: Status string ('qualified', 'needs_research', 'disqualified').
        pursuit_tier: Pursuit tier ('light_outreach', 'standard_proposal',
                      'high_effort_pitch', 'needs_research', 'none').
        hard_constraint_failures: List of recorded hard-constraint failures.

    Returns:
        Tuple of:
            - is_prospect_allowed: bool
            - effective_content_type: str ("light_outreach", "standard_proposal",
                                          "high_effort_pitch", "research_checklist", "none")
            - warnings: list of warnings generated during evaluation
    """
    warnings: list[str] = []
    norm_status = str(qualification_status).strip().lower() if qualification_status else "unknown"
    norm_tier = str(pursuit_tier).strip().lower() if pursuit_tier else "unknown"

    # Rule 1 & 2: Disqualified lead or hard constraint failures ALWAYS block prospect-facing drafts
    is_disqualified = (norm_status == QualificationStatus.DISQUALIFIED.value)
    if is_disqualified:
        if norm_tier != PursuitTier.NONE.value:
            warnings.append(
                f"Policy enforcement: Lead is disqualified. Upstream strategy requested '{norm_tier}', "
                f"but prospect-facing content is strictly blocked."
            )
        else:
            warnings.append("Lead is disqualified. No prospect-facing content permitted.")

    if hard_constraint_failures:
        warnings.append(
            f"Prospect-facing content blocked due to hard-constraint failure(s): "
            f"{', '.join(hard_constraint_failures)}."
        )

    if is_disqualified or hard_constraint_failures:
        return False, ContentType.NONE.value, warnings

    # Rule 3: Any status with tier 'none'
    if norm_tier == PursuitTier.NONE.value:
        return False, ContentType.NONE.value, warnings

    # Rule 4: Status 'needs_research'
    if norm_status == QualificationStatus.NEEDS_RESEARCH.value:
        if norm_tier in {
            PursuitTier.LIGHT_OUTREACH.value,
            PursuitTier.STANDARD_PROPOSAL.value,
            PursuitTier.HIGH_EFFORT_PITCH.value,
        }:
            warnings.append(
                f"Policy mismatch: Lead status is 'needs_research', but strategy requested '{norm_tier}'. "
                f"External draft blocked; generating internal research checklist."
            )
        return False, ContentType.RESEARCH_CHECKLIST.value, warnings

    # Rule 5: Status 'qualified'
    if norm_status == QualificationStatus.QUALIFIED.value:
        if norm_tier == PursuitTier.LIGHT_OUTREACH.value:
            return True, ContentType.LIGHT_OUTREACH.value, warnings
        elif norm_tier == PursuitTier.STANDARD_PROPOSAL.value:
            return True, ContentType.STANDARD_PROPOSAL.value, warnings
        elif norm_tier == PursuitTier.HIGH_EFFORT_PITCH.value:
            return True, ContentType.HIGH_EFFORT_PITCH.value, warnings
        elif norm_tier == PursuitTier.NEEDS_RESEARCH.value:
            warnings.append("Qualified lead assigned 'needs_research' tier; generating internal checklist.")
            return False, ContentType.RESEARCH_CHECKLIST.value, warnings
        else:
            warnings.append(f"Unrecognized pursuit tier '{norm_tier}' for qualified lead. Failing closed.")
            return False, ContentType.NONE.value, warnings

    # Rule 6: Unknown or invalid status - fail closed
    warnings.append(f"Unrecognized qualification status '{norm_status}'. Failing closed.")
    return False, ContentType.NONE.value, warnings


def is_prospect_content_allowed(
    qualification_status: str,
    pursuit_tier: str,
    hard_constraint_failures: list[str],
) -> bool:
    """Convenience helper checking if external prospect-facing content is allowed."""
    allowed, _, _ = evaluate_content_policy(
        qualification_status=qualification_status,
        pursuit_tier=pursuit_tier,
        hard_constraint_failures=hard_constraint_failures,
    )
    return allowed


# ============================================================================
# Fact and Claim Validation (Task C)
# ============================================================================

def validate_generated_content(
    draft_text: str,
    business_profile: Any,
    analysis: Any = None,
) -> Tuple[str, list[str]]:
    """Validate and sanitize draft text to prevent unsupported commercial and capability claims.

    Args:
        draft_text: The generated draft text to inspect.
        business_profile: Approved BusinessProfile or dict.
        analysis: Validated LeadAnalysis or dict.

    Returns:
        Tuple of (sanitized_draft_text, validation_warnings).
    """
    warnings: list[str] = []
    if not draft_text:
        return draft_text, warnings

    sanitized = draft_text

    # 1. Price Claim Validation
    pricing_available = _get_field(business_profile, "pricing_available", False)
    pricing_details = _get_field(business_profile, "pricing_details", None)

    for pattern in PRICE_PATTERNS:
        matches = pattern.findall(sanitized)
        for match in matches:
            # If pricing is not explicitly confirmed or match not in pricing details
            is_confirmed = False
            if pricing_available and pricing_details:
                if isinstance(pricing_details, str) and match in pricing_details:
                    is_confirmed = True
                elif isinstance(pricing_details, dict) and any(match in str(v) for v in pricing_details.values()):
                    is_confirmed = True

            if not is_confirmed:
                warnings.append(f"Unsupported price claim detected: '{match}'. Replaced with placeholder.")
                sanitized = pattern.sub(PLACEHOLDER_CONFIRM_PRICING, sanitized)

    # 2. Service Capability Validation
    confirmed_caps = _get_field(business_profile, "confirmed_capabilities", []) or []
    norm_confirmed = [str(c).lower().replace(" ", "_").replace("-", "_") for c in confirmed_caps]

    for category, keywords in HIGH_RISK_SERVICES.items():
        # Check if category is confirmed
        category_confirmed = any(category in c for c in norm_confirmed)
        if not category_confirmed:
            for kw in keywords:
                kw_regex = re.compile(rf"\b{re.escape(kw)}\b", re.I)
                if kw_regex.search(sanitized):
                    warnings.append(
                        f"Unsupported service capability claim detected: '{kw}'. "
                        f"Capability is not confirmed in business profile."
                    )
                    replacement = f"[confirm service capabilities: {kw}]"
                    sanitized = kw_regex.sub(replacement, sanitized)

    # 3. Prohibited Marketing / Guarantee Claims
    for pattern, claim_type in PROHIBITED_MARKETING_CLAIMS:
        if pattern.search(sanitized):
            warnings.append(f"Prohibited promotional or guarantee claim detected: '{claim_type}'. Sanitized.")
            sanitized = pattern.sub("[claim removed - pending verification]", sanitized)

    # 4. Human Review Disclaimer Check
    if sanitized.strip() and HUMAN_REVIEW_DISCLAIMER not in sanitized:
        sanitized = f"{HUMAN_REVIEW_DISCLAIMER}\n\n{sanitized}"

    return sanitized, warnings


# ============================================================================
# Deterministic Python Templates (Task A & Task E Fallback)
# ============================================================================

def _generate_light_outreach_template(
    analysis: Any,
    business_profile: Any,
) -> GeneratedContent:
    """Generate Tier 1: light_outreach draft."""
    company_name = _get_field(analysis, "company_name", "your organization")
    event_type = _get_field(analysis, "event_type", "upcoming corporate event")
    event_location = _get_field(analysis, "event_location")
    caterer_name = _get_field(business_profile, "company_name", "Corporate Catering Services")
    contact_name = _get_field(business_profile, "contact_name", "Events Team")

    location_str = f" in {event_location}" if event_location else ""

    draft = (
        f"{HUMAN_REVIEW_DISCLAIMER}\n\n"
        f"Subject: Catering support for {company_name} - {event_type}\n\n"
        f"Hello {PLACEHOLDER_CONTACT_NAME},\n\n"
        f"I came across the announcement for {company_name}'s {event_type}{location_str} and "
        f"wanted to inquire whether catering arrangements have already been finalized.\n\n"
        f"If catering support is still under consideration, {caterer_name} would welcome the "
        f"opportunity to discuss your food and beverage requirements.\n\n"
        f"Best regards,\n"
        f"{contact_name}\n"
        f"{caterer_name}"
    )

    assumptions = [
        "Recipient is responsible for event logistics and vendor selection.",
        "Catering arrangements have not yet been contracted with another vendor.",
    ]
    warnings = []
    if not event_location:
        warnings.append("Event location is unverified; ensure venue falls within approved service area.")

    return GeneratedContent(
        content_type=ContentType.LIGHT_OUTREACH.value,
        draft_text=draft,
        assumptions=assumptions,
        warnings=warnings,
        human_review_required=True,
        prospect_facing=True,
        research_questions=[],
        internal_explanation=None,
    )


def _generate_standard_proposal_template(
    analysis: Any,
    business_profile: Any,
) -> GeneratedContent:
    """Generate Tier 2: standard_proposal outline."""
    company_name = _get_field(analysis, "company_name", "Client Organization")
    event_type = _get_field(analysis, "event_type", "Corporate Event")
    event_date = _get_field(analysis, "event_date") or PLACEHOLDER_CONFIRM_DATE
    event_location = _get_field(analysis, "event_location") or PLACEHOLDER_CONFIRM_VENUE
    attendee_count = _get_field(analysis, "attendee_count")
    catering_signal = _get_field(analysis, "catering_signal", "unknown")

    caterer_name = _get_field(business_profile, "company_name", "Corporate Catering Services")
    confirmed_caps = _get_field(business_profile, "confirmed_capabilities", [])
    dietary_options = _get_field(business_profile, "dietary_options", [])

    guest_str = f"{int(attendee_count)} estimated attendees" if attendee_count else PLACEHOLDER_CONFIRM_GUESTS
    caps_str = ", ".join(c.replace("_", " ").title() for c in confirmed_caps) if confirmed_caps else "Corporate catering services"
    dietary_str = ", ".join(d.replace("_", " ").title() for d in dietary_options) if dietary_options else "Standard dietary accommodations"

    draft = (
        f"{HUMAN_REVIEW_DISCLAIMER}\n\n"
        f"## Catering Proposal Outline\n\n"
        f"**Catering Provider:** {caterer_name}\n"
        f"**Target Company:** {company_name}\n"
        f"**Event Title:** {event_type}\n"
        f"**Date:** {event_date}\n"
        f"**Location:** {event_location}\n\n"
        f"### 1. Understanding of Requirements\n"
        f"- Scope: Catering support for {event_type} hosting {guest_str}.\n"
        f"- Evidence Status: Catering demand signal is recorded as '{catering_signal}'.\n\n"
        f"### 2. Proposed Approach\n"
        f"- Core Services: {caps_str}.\n"
        f"- Dietary Capabilities: Accommodations available for {dietary_str}.\n"
        f"- Service Standards: Professional setup adhering strictly to verified venue protocols.\n\n"
        f"### 3. Details to Confirm\n"
        f"- Final attendee headcount and schedule: {guest_str}\n"
        f"- Dietary preferences and allergen restrictions: [confirm dietary breakdown]\n"
        f"- Venue access, staging area, and power/water availability: {PLACEHOLDER_CONFIRM_VENUE}\n"
        f"- Service timeline and refreshment break windows: [confirm service timeline]\n\n"
        f"### 4. Commercial Details\n"
        f"Pricing and package details: {PLACEHOLDER_CONFIRM_PRICING}\n\n"
        f"### 5. Next Steps\n"
        f"1. Confirm outstanding requirements and final guest count.\n"
        f"2. Issue final tailored commercial proposal and menu selection."
    )

    assumptions = [
        "Event date and venue will permit appropriate loading and staging windows.",
        "Final headcount will be locked within standard booking lead times.",
    ]
    warnings = []
    if attendee_count is None:
        warnings.append("Attendee count unverified; accurate pricing requires finalized headcount.")
    if event_date == PLACEHOLDER_CONFIRM_DATE:
        warnings.append("Event date unverified; date availability must be checked before quotation.")

    return GeneratedContent(
        content_type=ContentType.STANDARD_PROPOSAL.value,
        draft_text=draft,
        assumptions=assumptions,
        warnings=warnings,
        human_review_required=True,
        prospect_facing=True,
        research_questions=[],
        internal_explanation=None,
    )


def _generate_high_effort_pitch_template(
    analysis: Any,
    business_profile: Any,
    reasoning: Any,
) -> GeneratedContent:
    """Generate Tier 3: high_effort_pitch draft."""
    company_name = _get_field(analysis, "company_name", "Client Organization")
    event_type = _get_field(analysis, "event_type", "Executive Event")
    event_date = _get_field(analysis, "event_date") or PLACEHOLDER_CONFIRM_DATE
    event_location = _get_field(analysis, "event_location") or PLACEHOLDER_CONFIRM_VENUE
    attendee_count = _get_field(analysis, "attendee_count")

    caterer_name = _get_field(business_profile, "company_name", "Corporate Catering Services")
    confirmed_caps = _get_field(business_profile, "confirmed_capabilities", [])
    dietary_options = _get_field(business_profile, "dietary_options", [])

    guest_str = f"{int(attendee_count)} confirmed attendees" if attendee_count else PLACEHOLDER_CONFIRM_GUESTS
    caps_str = ", ".join(c.replace("_", " ").title() for c in confirmed_caps) if confirmed_caps else "Premium catering operations"
    dietary_str = ", ".join(d.replace("_", " ").title() for d in dietary_options) if dietary_options else "Comprehensive dietary options"

    reasoning_summary = _get_field(reasoning, "summary", "High-value corporate engagement opportunity.")

    draft = (
        f"{HUMAN_REVIEW_DISCLAIMER}\n\n"
        f"## Executive Catering Pitch: {event_type}\n\n"
        f"**Prepared by:** {caterer_name}\n"
        f"**Prepared for:** {company_name}\n"
        f"**Event Overview:** {event_type} | {event_date} | {event_location}\n\n"
        f"### 1. Executive Summary\n"
        f"{company_name}'s upcoming {event_type} represents an important gathering requiring reliable, "
        f"seamless culinary execution. {reasoning_summary}\n\n"
        f"### 2. Tailored Culinary Solution\n"
        f"Our team proposes an integrated catering approach focusing strictly on our confirmed competencies: "
        f"{caps_str}. We deliver punctuality, refined presentation, and dietary inclusivity ({dietary_str}).\n\n"
        f"### 3. Key Planning Considerations\n"
        f"- Flow & Timing: Designing the service window to align smoothly with the {guest_str} agenda.\n"
        f"- Venue Logistics: Verifying staging access, loading times, and safety standards at {event_location}.\n"
        f"- Quality Control: Fresh preparation schedule synchronized with event meal breaks.\n\n"
        f"### 4. Commercial Framework\n"
        f"- Structure: Customized package quotation.\n"
        f"- Pricing status: {PLACEHOLDER_CONFIRM_PRICING}\n\n"
        f"### 5. Information Required for Final Proposal\n"
        f"- Final confirmed attendee count: {guest_str}\n"
        f"- Detailed service schedule and meal break times: [confirm service timeline]\n"
        f"- Venue layout and staging facility access: {PLACEHOLDER_CONFIRM_VENUE}\n\n"
        f"### 6. Recommended Next Steps\n"
        f"Schedule a brief operational alignment call with our corporate relations manager to review "
        f"sample menus and finalize logistics."
    )

    assumptions = [
        "The event requires external food and beverage service.",
        "Venue permits approved outside catering and staging operations.",
    ]
    warnings = []
    if attendee_count is None:
        warnings.append("Attendee count unverified; must be confirmed before locking operational commitments.")

    return GeneratedContent(
        content_type=ContentType.HIGH_EFFORT_PITCH.value,
        draft_text=draft,
        assumptions=assumptions,
        warnings=warnings,
        human_review_required=True,
        prospect_facing=True,
        research_questions=[],
        internal_explanation=None,
    )


def _generate_research_checklist_template(
    analysis: Any,
    business_profile: Any,
    reasoning: Any = None,
    extra_warnings: list[str] | None = None,
) -> GeneratedContent:
    """Generate Tier 4: needs_research checklist (Internal only)."""
    company_name = _get_field(analysis, "company_name", "Unverified Lead")
    event_type = _get_field(analysis, "event_type", "Corporate Event")
    event_date = _get_field(analysis, "event_date")
    event_location = _get_field(analysis, "event_location")
    attendee_count = _get_field(analysis, "attendee_count")
    catering_signal = _get_field(analysis, "catering_signal", "unknown")
    source_url = _get_field(analysis, "source_url", "No source URL provided")

    service_areas = _get_field(business_profile, "service_area", [])
    service_area_str = ", ".join(service_areas) if service_areas else "Approved service zones"

    questions: list[str] = []
    if catering_signal != "explicit":
        questions.append("Is catering explicitly required, or is this only a general event announcement?")
    if attendee_count is None:
        questions.append("What is the confirmed or estimated attendee headcount?")
    if not event_date:
        questions.append("What is the confirmed event date and service schedule?")
    if not event_location:
        questions.append("What is the confirmed venue location, and is it inside our approved service area?")
    else:
        # Check if location matches service area
        if service_areas and not any(area.lower() in event_location.lower() for area in service_areas):
            questions.append(
                f"Event location '{event_location}' appears outside standard service area ({service_area_str}); "
                f"can operations support this zone?"
            )
    questions.append("Is there an allocated budget and designated decision-maker for catering services?")
    questions.append("What are the venue's staging, kitchen, and vendor loading policies?")

    questions_markdown = "\n".join(f"- {q}" for q in questions)

    draft = (
        f"## Internal Research Checklist\n\n"
        f"**Opportunity:** {company_name} - {event_type}\n"
        f"**Internal Status:** Requires information verification before external outreach.\n\n"
        f"### Outstanding Questions\n"
        f"{questions_markdown}\n\n"
        f"### Recommended Research Tasks\n"
        f"- Verify primary announcement source ({source_url}).\n"
        f"- Confirm event location compatibility with service areas: {service_area_str}.\n"
        f"- Cross-reference attendee capacity with venue specifications.\n"
        f"- Identify specific catering decision-maker or event procurement contact.\n\n"
        f"### Next Decision\n"
        f"Reassess opportunity qualification and pursuit tier once outstanding items are verified."
    )

    warnings = list(extra_warnings or [])
    warnings.append("Internal research checklist — NOT for prospect communication.")

    return GeneratedContent(
        content_type=ContentType.RESEARCH_CHECKLIST.value,
        draft_text=draft,
        assumptions=["Data collected from public announcements remains subject to verification."],
        warnings=warnings,
        human_review_required=True,
        prospect_facing=False,
        research_questions=questions,
        internal_explanation="Opportunity has unconfirmed parameters. Internal checklist generated for verification.",
    )


def _generate_none_template(
    reason: str,
    extra_warnings: list[str] | None = None,
) -> GeneratedContent:
    """Generate Tier 5: none (No prospect-facing content)."""
    warnings = list(extra_warnings or [])
    return GeneratedContent(
        content_type=ContentType.NONE.value,
        draft_text="",
        assumptions=[],
        warnings=warnings,
        human_review_required=True,
        prospect_facing=False,
        research_questions=[],
        internal_explanation=reason,
    )


# ============================================================================
# LLM Integration and Parsing (Task E)
# ============================================================================

def _generate_with_llm(
    effective_content_type: str,
    analysis: Any,
    qualification: Any,
    reasoning: Any,
    strategy: Any,
    business_profile: Any,
) -> GeneratedContent | None:
    """Attempt content generation via configured LLM with strict validation and error handling."""
    from agent import call_llm

    system_prompt = build_system_prompt(effective_content_type)
    user_prompt = build_user_prompt(
        analysis_data=_to_clean_dict(analysis),
        qualification_data=_to_clean_dict(qualification),
        reasoning_data=_to_clean_dict(reasoning),
        strategy_data=_to_clean_dict(strategy),
        business_profile_data=_to_clean_dict(business_profile),
    )

    raw_response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    if not raw_response:
        return None

    try:
        # Strip code fences if present
        clean_text = raw_response.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

        data = json.loads(clean_text)

        # Validate with GeneratedContent schema
        content_type = data.get("content_type", effective_content_type)
        draft_text = data.get("draft_text", "")
        assumptions = data.get("assumptions", [])
        warnings = data.get("warnings", [])
        prospect_facing = data.get("prospect_facing", False)
        research_questions = data.get("research_questions", [])
        internal_explanation = data.get("internal_explanation")

        # Sanitize draft text against unsupported claims
        sanitized_draft, val_warnings = validate_generated_content(
            draft_text=draft_text,
            business_profile=business_profile,
            analysis=analysis,
        )
        warnings.extend(val_warnings)

        return GeneratedContent(
            content_type=content_type,
            draft_text=sanitized_draft,
            assumptions=assumptions if isinstance(assumptions, list) else [str(assumptions)],
            warnings=warnings if isinstance(warnings, list) else [str(warnings)],
            human_review_required=True,
            prospect_facing=prospect_facing,
            research_questions=research_questions if isinstance(research_questions, list) else [str(research_questions)],
            internal_explanation=internal_explanation,
        )

    except Exception as exc:
        logger.warning("Failed to parse or validate LLM response: %s", exc)
        return None


# ============================================================================
# Main Public Function Contract (Section 4 & 14)
# ============================================================================

def generate_content(
    analysis: Any,
    qualification: Any,
    reasoning: Any,
    strategy: Any,
    business_profile: Any,
) -> GeneratedContent:
    """Generate structured proposal, outreach, research, or null content based on upstream decisions.

    Args:
        analysis: Validated event analysis, extracted facts, evidence, and unknowns.
        qualification: Qualification status and any hard-constraint failures.
        reasoning: Reasoning summary, risks, and uncertainty.
        strategy: Selected pursuit tier and its rationale.
        business_profile: Approved business details, service area, and confirmed capabilities.

    Returns:
        GeneratedContent: Agreed Pydantic model containing draft text, warnings, assumptions,
                         and review requirements.
    """
    # 1. Extract status and parameters defensively without modifying upstream objects
    status = _get_field(qualification, "status", QualificationStatus.NEEDS_RESEARCH.value)
    hard_failures = _get_field(qualification, "hard_constraint_failures", []) or []
    tier = _get_field(strategy, "tier", PursuitTier.NONE.value)

    # 2. Evaluate Policy
    is_allowed, effective_type, policy_warnings = evaluate_content_policy(
        qualification_status=status,
        pursuit_tier=tier,
        hard_constraint_failures=hard_failures,
    )

    # 3. Handle Tier 5 (none) or blocked leads immediately
    if effective_type == ContentType.NONE.value:
        explanation = (
            f"No prospect-facing content was generated because the opportunity is "
            f"classified as '{status}' with pursuit tier '{tier}'."
        )
        return _generate_none_template(reason=explanation, extra_warnings=policy_warnings)

    # 4. Handle Tier 4 (needs_research / research_checklist)
    if effective_type == ContentType.RESEARCH_CHECKLIST.value:
        return _generate_research_checklist_template(
            analysis=analysis,
            business_profile=business_profile,
            reasoning=reasoning,
            extra_warnings=policy_warnings,
        )

    # 5. Handle Prospect-Facing Content (Tiers 1, 2, 3)
    from agent import is_llm_available
    if is_llm_available():
        llm_result = _generate_with_llm(
            effective_content_type=effective_type,
            analysis=analysis,
            qualification=qualification,
            reasoning=reasoning,
            strategy=strategy,
            business_profile=business_profile,
        )
        if llm_result is not None:
            llm_result.warnings.extend(policy_warnings)
            return llm_result
        else:
            policy_warnings.append("LLM generation unavailable or failed; deterministic template fallback applied.")

    # 6. Deterministic Template Fallback for Tiers 1, 2, 3
    if effective_type == ContentType.LIGHT_OUTREACH.value:
        result = _generate_light_outreach_template(analysis=analysis, business_profile=business_profile)
    elif effective_type == ContentType.STANDARD_PROPOSAL.value:
        result = _generate_standard_proposal_template(analysis=analysis, business_profile=business_profile)
    elif effective_type == ContentType.HIGH_EFFORT_PITCH.value:
        result = _generate_high_effort_pitch_template(
            analysis=analysis,
            business_profile=business_profile,
            reasoning=reasoning,
        )
    else:
        # Fallback safety guard
        return _generate_none_template(
            reason=f"Unsupported effective content type: {effective_type}",
            extra_warnings=policy_warnings,
        )

    # Run post-template claim validation & append policy warnings
    sanitized_text, val_warnings = validate_generated_content(
        draft_text=result.draft_text,
        business_profile=business_profile,
        analysis=analysis,
    )
    result.draft_text = sanitized_text
    result.warnings.extend(policy_warnings)
    result.warnings.extend(val_warnings)

    return result
