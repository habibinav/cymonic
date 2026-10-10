"""Comprehensive unit test suite for Member 3 — Proposal & Outreach Generation Module.

Tests cover:
- Test 1: Light outreach generation
- Test 2: Standard proposal outline generation
- Test 3: High-effort pitch generation
- Test 4: Needs research checklist generation
- Test 5: Tier 'none' generation
- Test 6: Disqualified lead cannot receive draft (Mandatory security policy)
- Test 7: Unsupported price claim detection (Independent validator & generation)
- Test 8: Unsupported service capability claim detection (Independent validator & generation)
- Test 9: Unknown event details (placeholders instead of invented facts)
- Test 10: Hard-constraint failure blocking
- Test 11: Conflicting upstream decisions (needs_research vs standard_proposal)
- Test 12: Invalid LLM response handling & graceful fallback
- Test 13: Missing API key deterministic fallback
- Test 14: Human-review wording and disclaimer enforcement
- Test 15: Tier coverage across all 5 tiers
"""

import json
from unittest.mock import patch
import pytest

from config import HUMAN_REVIEW_DISCLAIMER
from proposal_generator import (
    evaluate_content_policy,
    generate_content,
    is_prospect_content_allowed,
    validate_generated_content,
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


# ============================================================================
# Reusable Test Fixtures
# ============================================================================

@pytest.fixture
def sample_business_profile() -> BusinessProfile:
    """Standard business profile with verified capabilities and no confirmed pricing."""
    return BusinessProfile(
        company_name="Apex Gourmet Catering",
        contact_name="Aarav Sharma",
        service_area=["Bengaluru", "Mumbai", "Pune"],
        confirmed_capabilities=[
            "corporate_lunch",
            "buffet_service",
            "high_tea",
            "refreshments",
        ],
        pricing_available=False,
        pricing_details=None,
        dietary_options=["vegetarian", "non_vegetarian", "vegan", "jain"],
    )


@pytest.fixture
def sample_analysis() -> LeadAnalysis:
    """Validated corporate event lead analysis."""
    return LeadAnalysis(
        lead_id="LEAD-TEST-001",
        company_name="Innovate Tech Solutions",
        event_type="Annual Engineering Conference",
        event_date="2027-02-15",
        event_location="Bengaluru, Karnataka, India",
        attendee_count=200,
        event_duration_days=1,
        catering_signal="explicit",
        source_url="https://example.com/announcements/tech-conf-2027",
        announcement_text="Innovate Tech Solutions announced their 200-person tech summit in Bengaluru.",
    )


@pytest.fixture
def sample_reasoning() -> ReasoningResult:
    """Standard reasoning evaluation."""
    return ReasoningResult(
        summary="High-profile full-day tech summit with 200 attendees in primary service area.",
        risks=["Tight lunch turnaround window during keynote interval."],
        uncertainties=["Final breakdown of dietary requirements."],
        estimated_deal_value=150000.0,
    )


# ============================================================================
# Test Cases
# ============================================================================

def test_1_light_outreach(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 1: Light outreach generates concise exploratory email draft with required review flags."""
    qualification = QualificationResult(
        status=QualificationStatus.QUALIFIED.value,
        hard_constraint_failures=[],
    )
    strategy = StrategyResult(
        tier=PursuitTier.LIGHT_OUTREACH.value,
        rationale="Opportunity is qualified; exploratory contact recommended.",
        proposal_required=False,
    )

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert isinstance(result, GeneratedContent)
    assert result.content_type == ContentType.LIGHT_OUTREACH.value
    assert result.prospect_facing is True
    assert result.human_review_required is True
    assert "Subject:" in result.draft_text
    assert sample_analysis.company_name in result.draft_text
    assert HUMAN_REVIEW_DISCLAIMER in result.draft_text
    # Ensure no unverified capability is claimed
    assert "wedding" not in result.draft_text.lower()
    assert "live counter" not in result.draft_text.lower()


def test_2_standard_proposal(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 2: Standard proposal produces structured outline with commercial placeholders."""
    qualification = QualificationResult(
        status=QualificationStatus.QUALIFIED.value,
        hard_constraint_failures=[],
    )
    strategy = StrategyResult(
        tier=PursuitTier.STANDARD_PROPOSAL.value,
        rationale="Clear catering signal and verified guest count justify standard proposal outline.",
        proposal_required=True,
    )

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == ContentType.STANDARD_PROPOSAL.value
    assert result.prospect_facing is True
    assert result.human_review_required is True
    assert "Catering Proposal Outline" in result.draft_text
    assert "Commercial Details" in result.draft_text
    # Pricing must remain an explicit placeholder
    assert "[to be confirmed after requirements are validated]" in result.draft_text
    assert "₹" not in result.draft_text


def test_3_high_effort_pitch(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 3: High-effort pitch generates tailored pitch grounded in verified facts."""
    qualification = QualificationResult(
        status=QualificationStatus.QUALIFIED.value,
        hard_constraint_failures=[],
    )
    strategy = StrategyResult(
        tier=PursuitTier.HIGH_EFFORT_PITCH.value,
        rationale="High deal value and strategic tier account.",
        proposal_required=True,
    )

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == ContentType.HIGH_EFFORT_PITCH.value
    assert result.prospect_facing is True
    assert result.human_review_required is True
    assert "Executive Catering Pitch" in result.draft_text
    assert sample_analysis.company_name in result.draft_text
    # Grounded in confirmed capabilities
    assert "Corporate Lunch" in result.draft_text or "corporate_lunch" in result.draft_text.lower()
    # Must not invent testimonials or awards
    assert "award-winning" not in result.draft_text.lower()
    assert "guaranteed" not in result.draft_text.lower()


def test_4_needs_research(sample_business_profile, sample_reasoning):
    """Test 4: Needs research produces internal research checklist, not external outreach."""
    analysis = LeadAnalysis(
        lead_id="LEAD-TEST-004",
        company_name="CloudPeak Technologies",
        event_type="Seminar",
        event_date=None,  # Missing date
        event_location=None,  # Missing location
        attendee_count=None,  # Missing headcount
        catering_signal="unknown",
    )
    qualification = QualificationResult(
        status=QualificationStatus.NEEDS_RESEARCH.value,
        hard_constraint_failures=[],
    )
    strategy = StrategyResult(
        tier=PursuitTier.NEEDS_RESEARCH.value,
        rationale="Critical event details are unknown.",
        proposal_required=False,
    )

    result = generate_content(
        analysis=analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == ContentType.RESEARCH_CHECKLIST.value
    assert result.prospect_facing is False
    assert result.human_review_required is True
    assert len(result.research_questions) > 0
    assert any("attendee" in q.lower() for q in result.research_questions)
    assert any("date" in q.lower() for q in result.research_questions)
    assert "Internal Research Checklist" in result.draft_text


def test_5_none(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 5: Tier 'none' produces empty draft with internal explanation."""
    qualification = QualificationResult(
        status=QualificationStatus.QUALIFIED.value,
        hard_constraint_failures=[],
    )
    strategy = StrategyResult(
        tier=PursuitTier.NONE.value,
        rationale="Opportunity postponed by organizer.",
        proposal_required=False,
    )

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == ContentType.NONE.value
    assert result.draft_text == ""
    assert result.prospect_facing is False
    assert result.human_review_required is True
    assert result.internal_explanation is not None


def test_6_disqualified_lead_cannot_receive_draft(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 6: Disqualified lead NEVER receives prospect-facing content (Mandatory Test)."""
    qualification = QualificationResult(
        status=QualificationStatus.DISQUALIFIED.value,
        hard_constraint_failures=["outside_service_area"],
        reason="Event in Srinagar; no operational logistics support.",
    )
    # Intentionally conflicting upstream strategy
    strategy = StrategyResult(
        tier=PursuitTier.HIGH_EFFORT_PITCH.value,
        rationale="Erroneous high-effort pitch selection.",
        proposal_required=True,
    )

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=sample_reasoning,
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    # Assertions
    assert result.content_type == ContentType.NONE.value
    assert result.draft_text == ""
    assert result.prospect_facing is False
    assert len(result.warnings) > 0
    assert any("disqualified" in w.lower() for w in result.warnings)
    # Upstream strategy object must remain completely unmodified
    assert strategy.tier == PursuitTier.HIGH_EFFORT_PITCH.value


def test_7_unsupported_price(sample_business_profile, sample_analysis):
    """Test 7: Unsupported price claims are detected and blocked/sanitized."""
    # Test independent validator
    unsafe_draft = (
        "We are pleased to offer our premium lunch buffet at ₹450 per person, "
        "total package cost is Rs. 90,000."
    )
    sanitized, warnings = validate_generated_content(
        draft_text=unsafe_draft,
        business_profile=sample_business_profile,
        analysis=sample_analysis,
    )

    assert "₹450" not in sanitized
    assert "Rs. 90,000" not in sanitized
    assert len(warnings) > 0
    assert any("price" in w.lower() for w in warnings)

    # Test generation pipeline does not emit unconfirmed pricing
    qualification = QualificationResult(status="qualified")
    strategy = StrategyResult(tier="standard_proposal")
    res = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=ReasoningResult(),
        strategy=strategy,
        business_profile=sample_business_profile,
    )
    assert "₹" not in res.draft_text
    assert "[to be confirmed after requirements are validated]" in res.draft_text


def test_8_unsupported_service_capability(sample_business_profile, sample_analysis):
    """Test 8: Unsupported service capabilities are detected and sanitized/blocked."""
    # Profile has corporate_lunch, buffet_service, high_tea, refreshments
    # It does NOT have live cooking stations, wedding catering, or dedicated waitstaff
    unsafe_draft = (
        "We will provide on-site chef services with a live cooking station "
        "and dedicated waitstaff for your wedding reception."
    )

    sanitized, warnings = validate_generated_content(
        draft_text=unsafe_draft,
        business_profile=sample_business_profile,
        analysis=sample_analysis,
    )

    assert "live cooking station" not in sanitized.lower()
    assert "dedicated waitstaff" not in sanitized.lower()
    assert len(warnings) >= 2
    assert any("unsupported service capability" in w.lower() for w in warnings)


def test_9_unknown_event_details(sample_business_profile):
    """Test 9: Unknown event details produce placeholders rather than invented facts."""
    analysis_sparse = LeadAnalysis(
        lead_id="LEAD-SPARSE",
        company_name="Vanguard Systems",
        event_type="Corporate Meet",
        event_date=None,
        event_location=None,
        attendee_count=None,
    )
    qualification = QualificationResult(status="qualified")
    strategy = StrategyResult(tier="standard_proposal")

    result = generate_content(
        analysis=analysis_sparse,
        qualification=qualification,
        reasoning=ReasoningResult(),
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert "[confirm guest count]" in result.draft_text
    assert "[confirm event date]" in result.draft_text
    assert "[confirm venue address and facilities]" in result.draft_text
    assert any("unverified" in w.lower() for w in result.warnings)


def test_10_hard_constraint_failure(sample_analysis, sample_business_profile):
    """Test 10: Hard-constraint failure blocks proposal generation even if qualified."""
    qualification = QualificationResult(
        status=QualificationStatus.QUALIFIED.value,
        hard_constraint_failures=["kitchen_capacity_exceeded", "blackout_date"],
    )
    strategy = StrategyResult(tier=PursuitTier.STANDARD_PROPOSAL.value)

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=ReasoningResult(),
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == ContentType.NONE.value
    assert result.draft_text == ""
    assert result.prospect_facing is False
    assert any("hard-constraint" in w.lower() for w in result.warnings)


def test_11_conflicting_upstream_decisions(sample_analysis, sample_business_profile):
    """Test 11: Conflicting decisions (needs_research vs standard_proposal) fail safely to research checklist."""
    qualification = QualificationResult(status=QualificationStatus.NEEDS_RESEARCH.value)
    strategy = StrategyResult(tier=PursuitTier.STANDARD_PROPOSAL.value)

    result = generate_content(
        analysis=sample_analysis,
        qualification=qualification,
        reasoning=ReasoningResult(),
        strategy=strategy,
        business_profile=sample_business_profile,
    )

    # Proposal blocked, re-routed to internal checklist
    assert result.content_type == ContentType.RESEARCH_CHECKLIST.value
    assert result.prospect_facing is False
    assert any("mismatch" in w.lower() for w in result.warnings)
    # Inputs not modified
    assert qualification.status == QualificationStatus.NEEDS_RESEARCH.value
    assert strategy.tier == PursuitTier.STANDARD_PROPOSAL.value


def test_12_invalid_llm_response(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 12: Invalid or malformed LLM response fails safely to deterministic fallback."""
    qualification = QualificationResult(status="qualified")
    strategy = StrategyResult(tier="light_outreach")

    with patch("agent.is_llm_available", return_value=True), \
         patch("agent.call_llm", return_value="Malformed JSON {{invalid-string"):

        result = generate_content(
            analysis=sample_analysis,
            qualification=qualification,
            reasoning=sample_reasoning,
            strategy=strategy,
            business_profile=sample_business_profile,
        )

        assert result.content_type == ContentType.LIGHT_OUTREACH.value
        assert result.prospect_facing is True
        assert any("fallback" in w.lower() for w in result.warnings)
        assert HUMAN_REVIEW_DISCLAIMER in result.draft_text


def test_13_missing_api_key(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 13: Missing API key triggers deterministic fallback without crashing."""
    qualification = QualificationResult(status="qualified")
    strategy = StrategyResult(tier="standard_proposal")

    with patch("agent.is_llm_available", return_value=False):
        result = generate_content(
            analysis=sample_analysis,
            qualification=qualification,
            reasoning=sample_reasoning,
            strategy=strategy,
            business_profile=sample_business_profile,
        )

        assert result.content_type == ContentType.STANDARD_PROPOSAL.value
        assert "## Catering Proposal Outline" in result.draft_text
        assert result.prospect_facing is True


def test_14_human_review_wording(sample_analysis, sample_business_profile):
    """Test 14: All prospect-facing drafts include mandatory review disclaimer."""
    tiers = [
        PursuitTier.LIGHT_OUTREACH.value,
        PursuitTier.STANDARD_PROPOSAL.value,
        PursuitTier.HIGH_EFFORT_PITCH.value,
    ]

    for tier in tiers:
        qualification = QualificationResult(status="qualified")
        strategy = StrategyResult(tier=tier)

        result = generate_content(
            analysis=sample_analysis,
            qualification=qualification,
            reasoning=ReasoningResult(),
            strategy=strategy,
            business_profile=sample_business_profile,
        )

        assert result.human_review_required is True
        assert result.prospect_facing is True
        assert HUMAN_REVIEW_DISCLAIMER in result.draft_text


def test_15_tier_coverage(sample_analysis, sample_business_profile, sample_reasoning):
    """Test 15: Verify all five tiers map to the correct content types."""
    cases = [
        ("qualified", "light_outreach", ContentType.LIGHT_OUTREACH.value, True),
        ("qualified", "standard_proposal", ContentType.STANDARD_PROPOSAL.value, True),
        ("qualified", "high_effort_pitch", ContentType.HIGH_EFFORT_PITCH.value, True),
        ("needs_research", "needs_research", ContentType.RESEARCH_CHECKLIST.value, False),
        ("qualified", "none", ContentType.NONE.value, False),
    ]

    for status, tier, expected_type, expected_prospect_facing in cases:
        qualification = QualificationResult(status=status)
        strategy = StrategyResult(tier=tier)

        result = generate_content(
            analysis=sample_analysis,
            qualification=qualification,
            reasoning=sample_reasoning,
            strategy=strategy,
            business_profile=sample_business_profile,
        )

        assert result.content_type == expected_type
        assert result.prospect_facing is expected_prospect_facing
        assert result.human_review_required is True


# ============================================================================
# Additional Edge Case & Policy Tests
# ============================================================================

def test_policy_helper_directly():
    """Verify is_prospect_content_allowed and evaluate_content_policy directly."""
    # Disqualified always False
    assert is_prospect_content_allowed("disqualified", "light_outreach", []) is False
    assert is_prospect_content_allowed("disqualified", "high_effort_pitch", []) is False

    # Hard constraints always False
    assert is_prospect_content_allowed("qualified", "light_outreach", ["out_of_area"]) is False

    # Needs research always False for prospect-facing
    assert is_prospect_content_allowed("needs_research", "standard_proposal", []) is False

    # Qualified is True only for outreach and proposals
    assert is_prospect_content_allowed("qualified", "light_outreach", []) is True
    assert is_prospect_content_allowed("qualified", "standard_proposal", []) is True
    assert is_prospect_content_allowed("qualified", "high_effort_pitch", []) is True
    assert is_prospect_content_allowed("qualified", "none", []) is False
    assert is_prospect_content_allowed("qualified", "needs_research", []) is False


def test_dict_input_tolerance(sample_business_profile):
    """Ensure generate_content handles plain dictionaries from upstream agents."""
    raw_analysis = {
        "lead_id": "DICT-001",
        "company_name": "Dict Corp",
        "event_type": "Dict Summit",
        "attendee_count": 50,
        "catering_signal": "explicit",
    }
    raw_qualification = {
        "status": "qualified",
        "hard_constraint_failures": [],
    }
    raw_strategy = {
        "tier": "light_outreach",
    }
    raw_reasoning = {
        "summary": "Valid dict test lead",
    }

    result = generate_content(
        analysis=raw_analysis,
        qualification=raw_qualification,
        reasoning=raw_reasoning,
        strategy=raw_strategy,
        business_profile=sample_business_profile,
    )

    assert result.content_type == "light_outreach"
    assert "Dict Corp" in result.draft_text
    assert result.prospect_facing is True
