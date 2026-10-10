"""Shared Pydantic schemas for the Corporate Catering Hunter AI Agent.

Defines the data models exchanged across all multi-agent modules:
- LeadInput (Raw input payload)
- LeadAnalysis (Announcement Analysis Agent)
- EvidenceFact (Extracted fact evidence unit)
- BusinessProfile (Configured caterer profile)
- QualificationResult (Opportunity Qualification Agent)
- ReasoningResult (Reasoning Agent)
- StrategyResult (Pursuit Strategy Agent)
- GeneratedContent (Proposal & Outreach Generation Module)
- LeadRunResult (Consolidated end-to-end pipeline execution result)
"""

from __future__ import annotations

from datetime import datetime, timezone
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


class LeadInput(BaseModel):
    """Raw event announcement input received by the pipeline."""
    announcement_text: str
    source_url: str | None = None
    company_name: str | None = None
    lead_id: str | None = None


class EvidenceFact(BaseModel):
    """Specific extracted event fact with confidence / evidence status."""
    field_name: str
    value: Any
    status: str = CateringSignal.EXPLICIT.value  # "explicit", "inferred", "unknown"
    snippet: str | None = None


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
    evidence_facts: list[EvidenceFact] = Field(default_factory=list)
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
    """Agreed structured output returned by the proposal generator."""
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


class LeadRunResult(BaseModel):
    """Complete consolidated result of a lead execution run through the multi-agent pipeline."""
    lead_input: LeadInput
    analysis: LeadAnalysis
    qualification: QualificationResult
    reasoning: ReasoningResult
    strategy: StrategyResult
    proposal_gate_passed: bool
    generated_content: GeneratedContent
    execution_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten the run result into a dictionary suitable for tabular and CSV persistence."""
        return {
            "lead_id": self.analysis.lead_id,
            "announcement_text": self.lead_input.announcement_text,
            "source_url": self.lead_input.source_url or "",
            "company_name": self.analysis.company_name,
            "event_type": self.analysis.event_type or "",
            "event_date": self.analysis.event_date or "",
            "event_location": self.analysis.event_location or "",
            "attendee_count": self.analysis.attendee_count if self.analysis.attendee_count is not None else "",
            "event_duration_days": self.analysis.event_duration_days or 1,
            "catering_signal": self.analysis.catering_signal,
            "estimated_deal_value": self.reasoning.estimated_deal_value if self.reasoning.estimated_deal_value is not None else "",
            "qualification_status": self.qualification.status,
            "pursuit_tier": self.strategy.tier,
            "proposal_required": self.strategy.proposal_required,
            "decision_reason": self.reasoning.summary,
            "proposal_gate_passed": self.proposal_gate_passed,
            "content_type": self.generated_content.content_type,
            "prospect_facing": self.generated_content.prospect_facing,
            "human_review_required": self.generated_content.human_review_required,
            "draft_text": self.generated_content.draft_text,
            "assumptions": "; ".join(self.generated_content.assumptions),
            "warnings": "; ".join(self.generated_content.warnings),
            "research_questions": "; ".join(self.generated_content.research_questions),
            "internal_explanation": self.generated_content.internal_explanation or "",
            "execution_timestamp": self.execution_timestamp,
            "error": self.error or "",
        }
