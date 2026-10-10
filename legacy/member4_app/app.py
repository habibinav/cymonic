"""Streamlit Application for the Corporate Catering Hunter AI Agent (Member 4 module).

Interface components:
1. Input form (single announcement or pre-filled samples from dataset)
2. Analysis results (facts, unknowns, catering signal)
3. Qualification and reasoning (constraints, deal value, risks, pursuit tier)
4. Generated content (draft text, assumptions, warnings, proposal gate status)
5. Dataset display (processed leads history & baseline 500 synthetic leads)
6. CSV download (export processed opportunities anytime)
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from orchestrator import (
    process_lead,
    load_processed_leads,
    load_synthetic_dataset,
    export_leads_to_csv_bytes,
    DEFAULT_PROCESSED_CSV_PATH,
)
from schemas import BusinessProfile, LeadInput

# Streamlit Page Configuration
st.set_page_config(
    page_title="Corporate Catering Hunter AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.5rem; }
    .metric-card { background-color: #F3F4F6; padding: 1rem; border-radius: 8px; border-left: 4px solid #3B82F6; }
    .review-banner { background-color: #FEF3C7; border: 1px solid #F59E0B; color: #92400E; padding: 0.8rem; border-radius: 6px; font-weight: 600; margin-bottom: 1rem; }
    .gate-passed { background-color: #D1FAE5; color: #065F46; padding: 0.4rem 0.8rem; border-radius: 4px; font-weight: 600; display: inline-block; }
    .gate-blocked { background-color: #FEE2E2; color: #991B1B; padding: 0.4rem 0.8rem; border-radius: 4px; font-weight: 600; display: inline-block; }
    </style>
    """,
    unsafe_allow_html=True,
)


# Sidebar Configuration: Caterer Business Profile
st.sidebar.title("⚙️ Business Profile")
caterer_company = st.sidebar.text_input("Catering Company Name", value="Gourmet Corporate Catering")
caterer_contact = st.sidebar.text_input("Contact / Relations Team", value="Corporate Events Team")
service_areas_raw = st.sidebar.text_input("Approved Service Areas (comma-separated)", value="Bengaluru, Mumbai, Pune, Goa")
service_areas = [s.strip() for s in service_areas_raw.split(",") if s.strip()]

confirmed_caps_raw = st.sidebar.text_area(
    "Confirmed Capabilities (one per line)",
    value="corporate_lunch\nbuffet_service\nhigh_tea\nrefreshments\nexecutive_dining",
)
confirmed_capabilities = [c.strip() for c in confirmed_caps_raw.split("\n") if c.strip()]

min_guests = st.sidebar.number_input("Minimum Guest Headcount", value=20, min_value=1)
max_guests = st.sidebar.number_input("Maximum Guest Headcount", value=1000, min_value=10)

profile = BusinessProfile(
    company_name=caterer_company,
    contact_name=caterer_contact,
    service_area=service_areas,
    confirmed_capabilities=confirmed_capabilities,
    min_guests=min_guests,
    max_guests=max_guests,
)

# Application Header
st.markdown('<div class="main-title">🍽️ Corporate Catering Hunter AI Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Autonomous pipeline: Announcement Analysis ➔ Opportunity Qualification ➔ '
    'Reasoning & Deal Valuation ➔ Pursuit Strategy ➔ Proposal Gate ➔ Content Generation</div>',
    unsafe_allow_html=True,
)

# Tabs
tab_run, tab_dataset, tab_about = st.tabs(["🚀 Process New Lead", "📊 Dataset & History", "ℹ️ Workflow Details"])

# -----------------------------------------------------------------------------
# TAB 1: Process New Lead
# -----------------------------------------------------------------------------
with tab_run:
    st.subheader("1. Opportunity Input Form")

    # Sample Lead Loaders
    sample_col1, sample_col2, sample_col3 = st.columns(3)
    sample_text = ""

    if "announcement_text_input" not in st.session_state:
        st.session_state.announcement_text_input = ""

    if sample_col1.button("📌 Sample A: High-Value Conference (Bengaluru)"):
        st.session_state.announcement_text_input = (
            "Fictional company update: Apex Cloud Services is planning a technology summit in "
            "Bengaluru, Karnataka, India for 2027-02-15. Expected attendance is 240 delegates. "
            "The organizer requests quotations for lunch and afternoon refreshments."
        )
    if sample_col2.button("🔍 Sample B: Needs Research (Missing Headcount)"):
        st.session_state.announcement_text_input = (
            "Fictional notice: SilverOak Pharma announced a dealer convention scheduled for 2027-03-10 "
            "in Mumbai, Maharashtra, India. Full-day agenda; catering requirements are not specified."
        )
    if sample_col3.button("⛔ Sample C: Disqualified (Outside Service Area)"):
        st.session_state.announcement_text_input = (
            "Fictional press release: NorthStar Logistics is planning a 150-person seminar in "
            "Srinagar, Jammu and Kashmir, India for 2027-01-20. Refreshments requested."
        )

    with st.form("lead_input_form"):
        announcement_text = st.text_area(
            "Event Announcement Text *",
            value=st.session_state.announcement_text_input,
            placeholder="Paste raw corporate event announcement, press release, or social post...",
            height=130,
        )
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            source_url = st.text_input("Source URL (optional)", placeholder="https://news.example.com/event-101")
        with col_meta2:
            company_name_override = st.text_input("Company Name Override (optional)", placeholder="Leave blank for auto-extraction")

        submit_btn = st.form_submit_button("⚡ Run Multi-Agent Catering Pipeline", use_container_width=True)

    if submit_btn:
        if not announcement_text or not announcement_text.strip():
            st.error("Please provide non-empty corporate event announcement text.")
        else:
            with st.spinner("Executing multi-agent evaluation pipeline..."):
                input_payload = LeadInput(
                    announcement_text=announcement_text.strip(),
                    source_url=source_url.strip() if source_url else None,
                    company_name=company_name_override.strip() if company_name_override else None,
                )
                run_result = process_lead(
                    payload=input_payload,
                    business_profile=profile,
                    save_to_csv=True,
                )

            st.success("✅ Multi-agent analysis complete and saved to dataset!")

            # -------------------------------------------------------------
            # 2. Analysis Results
            # -------------------------------------------------------------
            st.markdown("---")
            st.subheader("2. Announcement Analysis Agent Results")
            analysis = run_result.analysis

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Lead ID", analysis.lead_id)
            c2.metric("Company Name", analysis.company_name)
            c3.metric("Event Date", analysis.event_date or "Unverified")
            c4.metric("Location", analysis.event_location or "Unverified")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Event Type", analysis.event_type or "General Event")
            c6.metric("Attendee Count", f"{int(analysis.attendee_count)}" if analysis.attendee_count else "Unknown")
            c7.metric("Duration", f"{analysis.event_duration_days} day(s)")
            signal_color = "🟢" if analysis.catering_signal == "explicit" else ("🟡" if analysis.catering_signal == "inferred" else "⚪")
            c8.metric("Catering Signal", f"{signal_color} {analysis.catering_signal.title()}")

            if analysis.unknown_fields:
                st.info(f"**Identified Information Gaps:** {', '.join(analysis.unknown_fields)}")

            # -------------------------------------------------------------
            # 3. Qualification and Reasoning
            # -------------------------------------------------------------
            st.markdown("---")
            st.subheader("3. Opportunity Qualification & Reasoning")
            qual = run_result.qualification
            reasoning = run_result.reasoning
            strategy = run_result.strategy

            q_col1, q_col2, q_col3 = st.columns(3)
            with q_col1:
                st.markdown("**Qualification Decision:**")
                if qual.status == "qualified":
                    st.success(f"STATUS: QUALIFIED")
                elif qual.status == "needs_research":
                    st.warning(f"STATUS: NEEDS RESEARCH")
                else:
                    st.error(f"STATUS: DISQUALIFIED")
                st.caption(f"Reason: {qual.reason}")

            with q_col2:
                st.markdown("**Deal Economics:**")
                deal_val = reasoning.estimated_deal_value
                st.metric("Estimated Deal Value", f"₹{deal_val:,.2f}" if deal_val else "Not estimated")
                if qual.hard_constraint_failures:
                    st.error(f"Hard Failures: {', '.join(qual.hard_constraint_failures)}")
                else:
                    st.success(f"Constraints Passed: {', '.join(qual.passed_constraints) if qual.passed_constraints else 'Standard'}")

            with q_col3:
                st.markdown("**Pursuit Strategy Tier:**")
                st.info(f"Selected Tier: **{strategy.tier.replace('_', ' ').title()}**")
                st.caption(f"Rationale: {strategy.rationale}")

            with st.expander("View Detailed Reasoning & Risk Assessment"):
                st.markdown(f"**Synthesis:** {reasoning.summary}")
                if reasoning.risks:
                    st.markdown("**Identified Risks:**")
                    for r in reasoning.risks:
                        st.markdown(f"- {r}")
                if reasoning.uncertainties:
                    st.markdown("**Uncertainties:**")
                    for u in reasoning.uncertainties:
                        st.markdown(f"- {u}")

            # -------------------------------------------------------------
            # 4. Generated Content
            # -------------------------------------------------------------
            st.markdown("---")
            st.subheader("4. Pursuit Content Generation & Proposal Gate")
            content = run_result.generated_content

            gate_col, type_col, rev_col = st.columns([2, 2, 2])
            with gate_col:
                if run_result.proposal_gate_passed:
                    st.markdown('<div class="gate-passed">🛡️ Proposal Gate: PASSED</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="gate-blocked">🛡️ Proposal Gate: BLOCKED (Internal Only)</div>', unsafe_allow_html=True)

            with type_col:
                st.markdown(f"**Content Type:** `{content.content_type}`")
            with rev_col:
                st.markdown(f"**Prospect-Facing:** `{content.prospect_facing}`")

            # Mandatory Human Review Header
            st.markdown(
                """
                <div class="review-banner">
                ⚠️ Draft for human review — not sent. Verify event details, recipient information,
                business capabilities, pricing, and availability before external use.
                </div>
                """,
                unsafe_allow_html=True,
            )

            if content.draft_text:
                st.markdown("**Generated Draft Content:**")
                st.code(content.draft_text, language="markdown")
            elif content.internal_explanation:
                st.info(f"**Internal Explanation:** {content.internal_explanation}")

            if content.research_questions:
                st.markdown("**Internal Research Questions Required:**")
                for q in content.research_questions:
                    st.markdown(f"- ❓ {q}")

            if content.warnings:
                st.markdown("**Safety & Validation Warnings:**")
                for w in content.warnings:
                    st.warning(f"⚠️ {w}")

            if content.assumptions:
                st.markdown("**Operational Assumptions:**")
                for a in content.assumptions:
                    st.caption(f"• {a}")


# -----------------------------------------------------------------------------
# TAB 2: Dataset Display and CSV Download
# -----------------------------------------------------------------------------
with tab_dataset:
    st.subheader("5. Processed Opportunities Dataset & Historical Archive")

    processed_df = load_processed_leads()
    synthetic_df = load_synthetic_dataset()

    view_option = st.radio(
        "Select dataset view:",
        ["Processed Opportunities History (Live CSV)", "Baseline Synthetic Dataset (500 Leads)"],
        horizontal=True,
    )

    if view_option.startswith("Processed"):
        if processed_df.empty:
            st.info("No leads processed yet in this session. Process a lead in Tab 1 to see records here.")
        else:
            st.markdown(f"**Total Processed Opportunities:** {len(processed_df)}")

            # Filter controls
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                status_filter = st.multiselect(
                    "Filter by Qualification Status:",
                    options=list(processed_df["qualification_status"].unique()),
                    default=list(processed_df["qualification_status"].unique()),
                )
            with f_col2:
                tier_filter = st.multiselect(
                    "Filter by Pursuit Tier:",
                    options=list(processed_df["pursuit_tier"].unique()),
                    default=list(processed_df["pursuit_tier"].unique()),
                )

            filtered_df = processed_df[
                processed_df["qualification_status"].isin(status_filter)
                & processed_df["pursuit_tier"].isin(tier_filter)
            ]

            st.dataframe(filtered_df, use_container_width=True)

            # 6. CSV Download
            st.markdown("### 6. Export Processed Dataset")
            csv_bytes = export_leads_to_csv_bytes(filtered_df)
            st.download_button(
                label="📥 Download Filtered Processed Leads as CSV",
                data=csv_bytes,
                file_name="processed_catering_leads.csv",
                mime="text/csv",
                use_container_width=True,
            )

    else:
        if synthetic_df.empty:
            st.warning("Baseline synthetic dataset file not found.")
        else:
            st.markdown(f"**Baseline Synthetic Leads Archive:** {len(synthetic_df)} records")
            st.dataframe(synthetic_df, use_container_width=True)

            csv_synthetic_bytes = export_leads_to_csv_bytes(synthetic_df)
            st.download_button(
                label="📥 Download Baseline Synthetic Dataset CSV",
                data=csv_synthetic_bytes,
                file_name="corporate_catering_hunter_synthetic_dataset_500.csv",
                mime="text/csv",
                use_container_width=True,
            )


# -----------------------------------------------------------------------------
# TAB 3: Workflow Details
# -----------------------------------------------------------------------------
with tab_about:
    st.markdown(
        """
        ### Multi-Agent Pipeline Architecture
        
        1. **Announcement Analysis Agent (Member 1):**  
           Ingests corporate announcements, extracts facts (Company, Event, Date, Location, Guest Count, Catering Signal), and highlights unverified unknowns.
        
        2. **Opportunity Qualification Agent (Member 2):**  
           Compares event facts against the approved caterer business profile (service area, min/max guests) and tags leads as `qualified`, `needs_research`, or `disqualified`.
        
        3. **Reasoning Agent (Member 2):**  
           Assesses commercial order potential (deal value in ₹), articulates delivery risks, and compiles a comprehensive decision reason.
        
        4. **Pursuit Strategy Agent (Member 2):**  
           Selects the pursuit tier (`standard_proposal`, `high_effort_pitch`, `light_outreach`, `needs_research`, `none`).
        
        5. **Deterministic Proposal Gate (Member 4):**  
           Strict Python gate blocking prospect-facing drafts if hard constraints failed or lead is disqualified.
        
        6. **Proposal & Outreach Generator (Member 3):**  
           Produces safe, tailored content matching the approved tier. Scrubbing unsupported prices and unconfirmed capabilities.
        
        7. **Persistence & Export (Member 4):**  
           Appends leads to CSV archive and exposes Streamlit UI with download capability.
        """
    )
