"""Orchestrator Module (Member 4 module).

Coordinates the multi-agent pipeline in the strict required sequence:
Input ➔ Analysis Agent ➔ Qualification Agent ➔ Reasoning Agent ➔ Strategy Agent
➔ Python Proposal Gate ➔ Proposal Generator (if permitted) ➔ CSV Persistence ➔ Streamlit/Caller.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from analysis_agent import analyze_announcement
from proposal_generator import generate_content
from qualification_agent import qualify_lead
from reasoning_agent import reason_about_lead
from schemas import (
    BusinessProfile,
    ContentType,
    GeneratedContent,
    LeadAnalysis,
    LeadInput,
    LeadRunResult,
    QualificationResult,
    ReasoningResult,
    StrategyResult,
)
from strategy_agent import determine_strategy

logger = logging.getLogger(__name__)

DEFAULT_PROCESSED_CSV_PATH = "processed_leads.csv"
SYNTHETIC_DATASET_PATH = "corporate_catering_hunter_synthetic_dataset_500.csv"


def proposal_gate(qualification: QualificationResult, strategy: StrategyResult) -> bool:
    """Evaluate whether prospect-facing proposal content is strictly permitted.

    Rules:
    1. Opportunity MUST be 'qualified'.
    2. Must have ZERO hard-constraint failures.
    3. Strategy tier MUST be one of the permitted prospect-facing tiers.
    """
    if qualification.hard_constraint_failures:
        return False
    if qualification.status != "qualified":
        return False
    return strategy.tier in {"light_outreach", "standard_proposal", "high_effort_pitch"}


def save_result_to_csv(run_result: LeadRunResult, csv_path: str = DEFAULT_PROCESSED_CSV_PATH) -> bool:
    """Persist a single processed lead result to a CSV file."""
    try:
        row_dict = run_result.to_flat_dict()
        file_path = Path(csv_path)
        file_exists = file_path.exists() and file_path.stat().st_size > 0

        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row_dict.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_dict)
        return True
    except Exception as exc:
        logger.error("Failed to save lead result to CSV (%s): %s", csv_path, exc)
        return False


def load_processed_leads(csv_path: str = DEFAULT_PROCESSED_CSV_PATH) -> pd.DataFrame:
    """Load historical processed leads from CSV file, returning empty DataFrame if not found."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        logger.warning("Error reading processed leads CSV: %s", exc)
        return pd.DataFrame()


def load_synthetic_dataset(csv_path: str = SYNTHETIC_DATASET_PATH) -> pd.DataFrame:
    """Load the project's baseline synthetic dataset."""
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        logger.warning("Error reading synthetic dataset CSV: %s", exc)
        return pd.DataFrame()


def export_leads_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame of leads into UTF-8 encoded CSV bytes for download."""
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def process_lead(
    payload: LeadInput | dict | str,
    business_profile: BusinessProfile | dict | None = None,
    save_to_csv: bool = True,
    csv_path: str = DEFAULT_PROCESSED_CSV_PATH,
) -> LeadRunResult:
    """Execute the complete multi-agent catering pipeline for a single corporate event announcement.

    Args:
        payload: Announcement text string, dictionary, or LeadInput model.
        business_profile: Optional BusinessProfile configuration.
        save_to_csv: Whether to automatically append the run result to disk.
        csv_path: Path to the target CSV file.

    Returns:
        LeadRunResult: Structured consolidated run object.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Input Normalization & Validation
    try:
        if isinstance(payload, str):
            clean_text = payload.strip()
            if not clean_text:
                raise ValueError("Announcement text payload cannot be empty.")
            lead_input = LeadInput(announcement_text=clean_text)
        elif isinstance(payload, dict):
            lead_input = LeadInput(**payload)
        elif isinstance(payload, LeadInput):
            lead_input = payload
        else:
            raise TypeError(f"Invalid payload type: {type(payload)}")

        if not lead_input.announcement_text or not lead_input.announcement_text.strip():
            raise ValueError("Announcement text must contain non-whitespace characters.")

    except Exception as err:
        logger.error("Payload validation failed: %s", err)
        error_msg = f"Payload validation error: {err}"
        empty_input = LeadInput(announcement_text=str(payload) if payload else "")
        empty_analysis = LeadAnalysis(lead_id="INVALID", company_name="Invalid Lead")
        empty_qual = QualificationResult(status="disqualified", reason=error_msg)
        empty_reasoning = ReasoningResult(summary=error_msg)
        empty_strategy = StrategyResult(tier="none", rationale=error_msg)
        empty_content = GeneratedContent(
            content_type=ContentType.NONE.value,
            draft_text="",
            warnings=[error_msg],
            internal_explanation=error_msg,
        )
        return LeadRunResult(
            lead_input=empty_input,
            analysis=empty_analysis,
            qualification=empty_qual,
            reasoning=empty_reasoning,
            strategy=empty_strategy,
            proposal_gate_passed=False,
            generated_content=empty_content,
            execution_timestamp=timestamp,
            error=error_msg,
        )

    # 2. Normalize Business Profile
    if business_profile is None:
        profile = BusinessProfile()
    elif isinstance(business_profile, dict):
        profile = BusinessProfile(**business_profile)
    else:
        profile = business_profile

    # 3. Agent Execution Pipeline
    try:
        # Step 1: Announcement Analysis Agent
        analysis: LeadAnalysis = analyze_announcement(lead_input)

        # Step 2: Opportunity Qualification Agent
        qualification: QualificationResult = qualify_lead(analysis, business_profile=profile)

        # Step 3: Reasoning Agent
        reasoning: ReasoningResult = reason_about_lead(analysis, qualification, business_profile=profile)

        # Step 4: Pursuit Strategy Agent
        strategy: StrategyResult = determine_strategy(analysis, qualification, reasoning)

        # Step 5: Proposal Gate
        gate_passed: bool = proposal_gate(qualification, strategy)

        # Step 6: Proposal & Outreach Generator (Member 3)
        generated_content: GeneratedContent = generate_content(
            analysis=analysis,
            qualification=qualification,
            reasoning=reasoning,
            strategy=strategy,
            business_profile=profile,
        )

        run_result = LeadRunResult(
            lead_input=lead_input,
            analysis=analysis,
            qualification=qualification,
            reasoning=reasoning,
            strategy=strategy,
            proposal_gate_passed=gate_passed,
            generated_content=generated_content,
            execution_timestamp=timestamp,
            error=None,
        )

        # Step 7: Persistence
        if save_to_csv:
            save_result_to_csv(run_result, csv_path=csv_path)

        return run_result

    except Exception as exc:
        logger.exception("Pipeline execution failed: %s", exc)
        error_msg = f"Orchestrator pipeline exception: {exc}"
        fallback_analysis = LeadAnalysis(lead_id="ERROR", company_name="Execution Failed")
        fallback_qual = QualificationResult(status="disqualified", reason=error_msg)
        fallback_reasoning = ReasoningResult(summary=error_msg)
        fallback_strategy = StrategyResult(tier="none", rationale=error_msg)
        fallback_content = GeneratedContent(
            content_type=ContentType.NONE.value,
            draft_text="",
            warnings=[error_msg],
            internal_explanation=error_msg,
        )
        return LeadRunResult(
            lead_input=lead_input,
            analysis=fallback_analysis,
            qualification=fallback_qual,
            reasoning=fallback_reasoning,
            strategy=fallback_strategy,
            proposal_gate_passed=False,
            generated_content=fallback_content,
            execution_timestamp=timestamp,
            error=error_msg,
        )
