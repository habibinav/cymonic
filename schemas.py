"""Shared Pydantic schemas for the Corporate Catering Hunter AI Agent.

Defines the data models exchanged across multi-agent modules:
- LeadAnalysis (Announcement Analysis Agent)
- QualificationResult (Opportunity Qualification Agent)
- ReasoningResult (Reasoning Agent)
- StrategyResult (Pursuit Strategy Agent)
- BusinessProfile (Configured caterer profile)
- GeneratedContent (Proposal & Outreach Generation Module)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class QualificationStatus(str, Enum):
    """Permitted qualification statuses from upstream qualification agent."""
    QUALIFIED = "qualified"
    NEEDS_RESEARCH = "needs_research"
    DISQUALIFIED = "disqualified"


class PursuitTier(str, Enum):
    """Permitted pursuit tiers selected by upstream strategy agent."""
    LIGHT_OUTREACH = "light_outreach"
    STANDARD_PROPOSAL = "standard_proposal"
    HIGH_EFFORT_PITCH = "high_effort_pitch"
    NEEDS_RESEARCH = "needs_research"
    NONE = "none"


class CateringSignal(str, Enum):
    """Signal strength for catering requirements."""
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """Output content types produced by the proposal generator."""
    LIGHT_OUTREACH = "light_outreach"
    STANDARD_PROPOSAL = "standard_proposal"
    HIGH_EFFORT_PITCH = "high_effort_pitch"
    RESEARCH_CHECKLIST = "research_checklist"
    NONE = "none"


class LeadAnalysis(BaseModel):
    """Validated event analysis, extracted facts, evidence, and unknowns."""
    lead_id: str
    company_name: str
    event_type: str | None = None
    event_date: str | None = None
    event_location: str | None = None
    attendee_count: float | int | None = None
    event_duration_days: int | None = 1
    catering_signal: str = CateringSignal.UNKNOWN.value
    source_url: str | None = None
    announcement_text: str = ""
    extracted_facts: dict[str, Any] = Field(default_factory=dict)
    unknown_fields: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)


class QualificationResult(BaseModel):
    """Opportunity qualification status and recorded constraint checks."""
    status: str = QualificationStatus.NEEDS_RESEARCH.value
    hard_constraint_failures: list[str] = Field(default_factory=list)
    passed_constraints: list[str] = Field(default_factory=list)
    reason: str | None = None


class ReasoningResult(BaseModel):
    """Reasoning summary, risks, uncertainties, and estimated deal value."""
    summary: str = ""
    risks: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    estimated_deal_value: float | None = None


class StrategyResult(BaseModel):
    """Pursuit strategy decision and rationale."""
    tier: str = PursuitTier.NONE.value
    rationale: str = ""
    proposal_required: bool = False


class BusinessProfile(BaseModel):
    """Approved business details, service area, and confirmed capabilities."""
    company_name: str = "Gourmet Corporate Catering"
    contact_name: str | None = "Corporate Events Team"
    service_area: list[str] = Field(default_factory=lambda: ["Bengaluru", "Mumbai", "Pune", "Goa"])
    confirmed_capabilities: list[str] = Field(default_factory=lambda: [
        "corporate_lunch",
        "buffet_service",
        "high_tea",
        "refreshments",
        "executive_dining",
    ])
    pricing_available: bool = False
    pricing_details: dict[str, Any] | str | None = None
    dietary_options: list[str] = Field(default_factory=lambda: ["vegetarian", "non_vegetarian", "vegan", "jain"])
    min_guests: int | None = 20
    max_guests: int | None = 1000
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class GeneratedContent(BaseModel):
    """Agreed structured output returned by Member 3's proposal generator."""
    content_type: Literal[
        "light_outreach",
        "standard_proposal",
        "high_effort_pitch",
        "research_checklist",
        "none",
    ]
    draft_text: str = ""
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    prospect_facing: bool = False
    research_questions: list[str] = Field(default_factory=list)
    internal_explanation: str | None = None
