"""Integration Test Suite for Member 4 — Integration, Interface and Testing.

Tests cover:
1. Complete End-to-End Workflow (all agents + proposal gate + generator + CSV)
2. Invalid & Malformed Input Handling
3. Proposal Gate Compliance (Disqualified, Out-of-Area, and Needs-Research leads)
4. API / LLM Failure Handling & Graceful Recovery
5. CSV Persistence & Row Appending
6. CSV Download & Data Export
7. Missing / Incomplete Event Information Handling
8. Clean Startup & Module Imports
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest

from config import HUMAN_REVIEW_DISCLAIMER
from orchestrator import (
    export_leads_to_csv_bytes,
    load_processed_leads,
    load_synthetic_dataset,
    process_lead,
    proposal_gate,
    save_result_to_csv,
)
from schemas import (
    BusinessProfile,
    ContentType,
    LeadAnalysis,
    LeadInput,
    LeadRunResult,
    QualificationResult,
    QualificationStatus,
    ReasoningResult,
    StrategyResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_business_profile() -> BusinessProfile:
    """Configured test caterer business profile."""
    return BusinessProfile(
        company_name="Royal Catering Services",
        contact_name="Rohan Verma",
        service_area=["Bengaluru", "Mumbai", "Pune", "Goa"],
        confirmed_capabilities=[
            "corporate_lunch",
            "buffet_service",
            "high_tea",
            "refreshments",
            "executive_dining",
        ],
        min_guests=20,
        max_guests=1000,
        pricing_available=False,
    )


# ============================================================================
# 1. Complete Workflow
# ============================================================================

def test_1_complete_workflow(tmp_path, test_business_profile):
    """Test 1: Verify the complete sequence from raw announcement to saved CSV and draft."""
    test_csv = tmp_path / "complete_leads.csv"
    payload = LeadInput(
        announcement_text=(
            "Fictional announcement: TechNova Innovations announced a 250-person technology conference "
            "scheduled for 2027-04-12 in Bengaluru, Karnataka, India. Full-day agenda; requests quotations "
            "for lunch and afternoon refreshments."
        ),
        source_url="https://example.com/events/technova-2027",
        company_name="TechNova Innovations",
    )

    result = process_lead(
        payload=payload,
        business_profile=test_business_profile,
        save_to_csv=True,
        csv_path=str(test_csv),
    )

    # Validate consolidated output
    assert isinstance(result, LeadRunResult)
    assert result.error is None
    assert result.analysis.company_name == "TechNova Innovations"
    assert result.analysis.attendee_count == 250.0
    assert result.analysis.event_location == "Bengaluru, Karnataka, India"
    assert result.analysis.catering_signal == "explicit"

    # Qualification & Reasoning
    assert result.qualification.status == "qualified"
    assert "service_area_compatible" in result.qualification.passed_constraints
    assert result.reasoning.estimated_deal_value == 250 * 750.0
    assert result.strategy.tier in {"standard_proposal", "high_effort_pitch"}

    # Proposal Gate & Content
    assert result.proposal_gate_passed is True
    assert result.generated_content.prospect_facing is True
    assert result.generated_content.human_review_required is True
    assert HUMAN_REVIEW_DISCLAIMER in result.generated_content.draft_text

    # CSV Persistence
    assert test_csv.exists()
    saved_df = pd.read_csv(test_csv)
    assert len(saved_df) == 1
    assert saved_df.iloc[0]["company_name"] == "TechNova Innovations"
    assert saved_df.iloc[0]["proposal_gate_passed"] == True


# ============================================================================
# 2. Invalid Input Handling
# ============================================================================

def test_2_invalid_input(tmp_path):
    """Test 2: Ensure invalid or empty input payloads are safely intercepted without crashing."""
    test_csv = tmp_path / "invalid_leads.csv"

    # Case A: Empty string
    res_empty = process_lead(payload="", save_to_csv=False, csv_path=str(test_csv))
    assert isinstance(res_empty, LeadRunResult)
    assert res_empty.error is not None
    assert res_empty.proposal_gate_passed is False
    assert res_empty.generated_content.content_type == ContentType.NONE.value

    # Case B: Whitespace only
    res_ws = process_lead(payload="   \n   ", save_to_csv=False, csv_path=str(test_csv))
    assert res_ws.error is not None
    assert res_ws.proposal_gate_passed is False

    # Case C: Malformed dict
    res_malformed = process_lead(payload={"unrecognized_field": 123}, save_to_csv=False)
    assert res_malformed.error is not None
    assert res_malformed.proposal_gate_passed is False


# ============================================================================
# 3. Proposal Gate Compliance
# ============================================================================

def test_3_proposal_gate_compliance(tmp_path, test_business_profile):
    """Test 3: Verify proposal gate blocks out-of-area, disqualified, and research leads."""
    test_csv = tmp_path / "gate_leads.csv"

    # Case A: Out of service area lead (Srinagar)
    payload_disq = (
        "Fictional notice: NorthStar Enterprises scheduled an executive training in "
        "Srinagar, Jammu & Kashmir, India for 2027-05-15. 100 attendees; catering requested."
    )
    res_disq = process_lead(payload=payload_disq, business_profile=test_business_profile, csv_path=str(test_csv))

    assert res_disq.qualification.status == QualificationStatus.DISQUALIFIED.value
    assert "outside_service_area" in res_disq.qualification.hard_constraint_failures
    assert res_disq.proposal_gate_passed is False
    assert res_disq.generated_content.prospect_facing is False
    assert res_disq.generated_content.content_type == ContentType.NONE.value
    assert res_disq.generated_content.draft_text == ""

    # Direct unit test of proposal_gate helper
    qual_ok = QualificationResult(status="qualified", hard_constraint_failures=[])
    qual_bad = QualificationResult(status="qualified", hard_constraint_failures=["blackout_date"])
    qual_research = QualificationResult(status="needs_research", hard_constraint_failures=[])

    strat_proposal = StrategyResult(tier="standard_proposal")
    strat_none = StrategyResult(tier="none")

    assert proposal_gate(qual_ok, strat_proposal) is True
    assert proposal_gate(qual_bad, strat_proposal) is False
    assert proposal_gate(qual_research, strat_proposal) is False
    assert proposal_gate(qual_ok, strat_none) is False


# ============================================================================
# 4. API / LLM Failure Handling
# ============================================================================

def test_4_api_failure_handling(tmp_path, test_business_profile):
    """Test 4: Ensure mocked LLM failures/exceptions degrade gracefully to deterministic templates."""
    payload = (
        "Fictional notice: Horizon Financial announced a 150-person seminar in Mumbai, India for 2027-03-20. "
        "Lunch and tea requested."
    )

    with patch("agent.is_llm_available", return_value=True), \
         patch("agent.call_llm", side_effect=RuntimeError("Simulated LLM Gateway Timeout 504")):

        result = process_lead(
            payload=payload,
            business_profile=test_business_profile,
            save_to_csv=False,
        )

        assert result.error is None
        assert result.proposal_gate_passed is True
        assert result.generated_content.prospect_facing is True
        assert HUMAN_REVIEW_DISCLAIMER in result.generated_content.draft_text
        assert any("fallback" in w.lower() for w in result.generated_content.warnings)


# ============================================================================
# 5. CSV Persistence
# ============================================================================

def test_5_csv_persistence(tmp_path, test_business_profile):
    """Test 5: Verify multiple leads append correctly to CSV and load_processed_leads reads them."""
    test_csv = tmp_path / "persistence_test.csv"

    # Process Lead 1
    res1 = process_lead(
        payload="Company Alpha announced an annual meet for 2027-01-10 in Bengaluru. 100 guests.",
        business_profile=test_business_profile,
        csv_path=str(test_csv),
    )
    # Process Lead 2
    res2 = process_lead(
        payload="Company Beta announced a workshop for 2027-02-10 in Mumbai. 50 guests.",
        business_profile=test_business_profile,
        csv_path=str(test_csv),
    )

    assert test_csv.exists()
    df = load_processed_leads(str(test_csv))
    assert len(df) == 2
    assert "lead_id" in df.columns
    assert "qualification_status" in df.columns
    assert "draft_text" in df.columns
    assert "proposal_gate_passed" in df.columns


# ============================================================================
# 6. CSV Download & Export
# ============================================================================

def test_6_csv_download():
    """Test 6: Verify export_leads_to_csv_bytes produces valid, downloadable CSV bytes."""
    # Case A: Non-empty DataFrame
    sample_df = pd.DataFrame([
        {"lead_id": "L1", "company_name": "Acme Corp", "status": "qualified"},
        {"lead_id": "L2", "company_name": "Globex Corp", "status": "needs_research"},
    ])
    csv_bytes = export_leads_to_csv_bytes(sample_df)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0

    # Parse back to verify validity
    recovered_df = pd.read_csv(io.BytesIO(csv_bytes))
    assert len(recovered_df) == 2
    assert list(recovered_df["company_name"]) == ["Acme Corp", "Globex Corp"]

    # Case B: Empty DataFrame
    empty_bytes = export_leads_to_csv_bytes(pd.DataFrame())
    assert empty_bytes == b""


# ============================================================================
# 7. Missing Information Handling
# ============================================================================

def test_7_missing_information(test_business_profile):
    """Test 7: Ensure leads with missing date, location, or headcount trigger needs_research safely."""
    sparse_payload = "Fictional update: Quantum Analytics is planning an event. No date or headcount stated."

    result = process_lead(
        payload=sparse_payload,
        business_profile=test_business_profile,
        save_to_csv=False,
    )

    assert result.error is None
    assert result.analysis.attendee_count is None
    assert result.analysis.event_date is None
    assert result.qualification.status == QualificationStatus.NEEDS_RESEARCH.value
    assert result.strategy.tier == "needs_research"
    assert result.proposal_gate_passed is False

    # Must produce research checklist, NOT prospect-facing draft
    assert result.generated_content.content_type == ContentType.RESEARCH_CHECKLIST.value
    assert result.generated_content.prospect_facing is False
    assert len(result.generated_content.research_questions) > 0


# ============================================================================
# 8. Clean Startup & Module Imports
# ============================================================================

def test_8_clean_startup_and_imports():
    """Test 8: Verify all required project modules import cleanly without circular dependencies."""
    import schemas
    import analysis_agent
    import qualification_agent
    import reasoning_agent
    import strategy_agent
    import proposal_generator
    import orchestrator
    import app
    import config

    # Check key symbols exist
    assert hasattr(schemas, "LeadRunResult")
    assert hasattr(schemas, "LeadInput")
    assert hasattr(schemas, "GeneratedContent")
    assert hasattr(orchestrator, "process_lead")
    assert hasattr(orchestrator, "proposal_gate")
    assert hasattr(proposal_generator, "generate_content")
