"""
schemas.py - Shared Pydantic Data Models and Enums

This module defines the shared schema models for the Corporate Catering Hunter AI Agent.
All team members (Member 1, 2, 3, 4) import from this file to ensure contract compatibility.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class QualificationStatus(str, Enum):
    QUALIFIED = "qualified"
    NEEDS_RESEARCH = "needs_research"
    DISQUALIFIED = "disqualified"


class PursuitTier(str, Enum):
    LIGHT_OUTREACH = "light_outreach"
    STANDARD_PROPOSAL = "standard_proposal"
    HIGH_EFFORT_PITCH = "high_effort_pitch"
    NEEDS_RESEARCH = "needs_research"
    NONE = "none"


class EvidenceClassification(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class EvidenceFact(BaseModel):
    fact: str
    classification: EvidenceClassification = EvidenceClassification.EXPLICIT


class LeadAnalysis(BaseModel):
    company_name: Optional[str] = None
    event_name: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[str] = None  # ISO format YYYY-MM-DD or descriptive string
    location: Optional[str] = None
    attendance_estimate: Optional[int] = None
    event_duration: Optional[str] = None
    catering_evidence: Optional[str] = None
    evidence_facts: List[EvidenceFact] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None


class BusinessProfile(BaseModel):
    company_name: str = "Apex Corporate Catering Co."
    service_areas: List[str] = Field(
        default_factory=lambda: ["Kochi", "Ernakulam", "Trivandrum", "Bangalore", "Chennai"]
    )
    min_capacity: int = 25
    max_capacity: int = 1000
    min_order_value: float = 5000.0  # Currency units
    min_notice_days: int = 3
    supported_event_types: List[str] = Field(
        default_factory=lambda: [
            "conference", "staff conference", "seminar", "workshop", 
            "gala", "corporate party", "launch event", "meeting", "town hall"
        ]
    )


class QualificationResult(BaseModel):
    status: QualificationStatus
    is_service_area_matched: bool
    is_capacity_matched: bool
    has_catering_demand_evidence: bool
    is_sufficient_prep_time: bool
    is_min_order_satisfied: bool
    missing_critical_info: List[str] = Field(default_factory=list)
    disqualification_reasons: List[str] = Field(default_factory=list)
    qualification_notes: List[str] = Field(default_factory=list)


class ReasoningResult(BaseModel):
    reasoning_summary: str
    positives: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    commercial_potential_score: float = Field(default=0.0, ge=0.0, le=10.0)
    operational_feasibility_score: float = Field(default=0.0, ge=0.0, le=10.0)
    recommended_next_action: str


class StrategyResult(BaseModel):
    pursuit_tier: PursuitTier
    justification: str
    action_items: List[str] = Field(default_factory=list)