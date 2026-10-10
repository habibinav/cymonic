# Corporate Catering Hunter AI Agent

An autonomous multi-agent intelligence pipeline that identifies corporate event announcements, qualifies catering opportunities against operational constraints, computes commercial deal economics, decides on pursuit strategies, enforces deterministic proposal gates, and generates tailored prospect-facing drafts with human-review safeguards.

---

## 1. Architecture & Pipeline Sequence

The pipeline executes in a strict deterministic sequence across specialized agent modules:

```text
Corporate Event Announcement (Raw Text / URL)
                      ↓
1. Announcement Analysis Agent (analysis_agent.py)
   - Extracts company, event type, date, location, attendee count, catering signals
                      ↓
2. Opportunity Qualification Agent (qualification_agent.py)
   - Evaluates service areas, guest capacity, and hard constraints
                      ↓
3. Reasoning Agent (reasoning_agent.py)
   - Computes deal valuation (₹), assesses delivery risks, and articulates rationale
                      ↓
4. Pursuit Strategy Agent (strategy_agent.py)
   - Selects pursuit tier: light_outreach | standard_proposal | high_effort_pitch | needs_research | none
                      ↓
5. Deterministic Proposal Gate (orchestrator.py)
   - Python gate blocking external communication if disqualified or hard constraints failed
                      ↓
6. Proposal & Outreach Generator (proposal_generator.py + prompts.py)
   - Generates structured draft or internal checklist; sanitizes unverified prices & capabilities
                      ↓
7. Persistence & Analytics (processed_leads.csv)
   - Appends structured run result for auditability and dataset export
                      ↓
8. Streamlit Web Interface (app.py)
   - Interactive UI with form inputs, multi-stage inspection, dataset browsing, and CSV download
```

---

## 2. Shared Data Contracts (`schemas.py`)

All modules adhere strictly to shared Pydantic models defined in `schemas.py`:

- **`LeadInput`**: Ingests raw announcement text, optional source URL, and company override.
- **`EvidenceFact`**: Individual extracted fact tagged with evidence status (`explicit`, `inferred`, `unknown`).
- **`LeadAnalysis`**: Extracted corporate event facts and recorded unknowns.
- **`BusinessProfile`**: Configured caterer service areas, confirmed capabilities, and capacity boundaries.
- **`QualificationResult`**: Qualification status (`qualified`, `needs_research`, `disqualified`) and hard failures.
- **`ReasoningResult`**: Financial deal valuation in INR, operational risks, and synthesis summary.
- **`StrategyResult`**: Selected pursuit tier and pursuit necessity.
- **`GeneratedContent`**: Structured draft content, review flags, assumptions, warnings, and research questions.
- **`LeadRunResult`**: Consolidated end-to-end execution record with `.to_flat_dict()` for CSV persistence.

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.10, 3.11, 3.12, 3.13)
- Git

### Quickstart

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repo-url>
   cd cymonic
   ```

2. **Create and activate a virtual environment (Recommended):**
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. Running the Streamlit Application

Launch the interactive web application with:

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

### Application Features:
1. **Interactive Input Form:** Input raw announcements, pick pre-loaded sample leads, or load from the 500-lead synthetic dataset.
2. **Analysis Stage:** Inspect extracted facts, attendee headcount, event dates, and catering signal badges.
3. **Qualification & Reasoning:** View constraint checks, deal valuations, risk assessments, and selected pursuit tiers.
4. **Pursuit Content & Proposal Gate:** View proposal gate status, formatted drafts, review disclaimers, assumptions, and validation warnings.
5. **Dataset Explorer & History:** Search and filter historical processed leads alongside the baseline 500-lead synthetic dataset.
6. **One-Click CSV Export:** Download filtered processed opportunities anytime.

---

## 5. Running the Pipeline via Python API

You can programmatically execute the pipeline from any script or notebook:

```python
from orchestrator import process_lead
from schemas import BusinessProfile, LeadInput

# 1. Define caterer profile
profile = BusinessProfile(
    company_name="Royal Corporate Catering",
    service_area=["Bengaluru", "Mumbai", "Pune"],
    confirmed_capabilities=["corporate_lunch", "buffet_service", "high_tea"],
)

# 2. Process an announcement
result = process_lead(
    payload="Acme Corp announced a 200-person summit in Bengaluru for 2027-03-15. Requests lunch quotations.",
    business_profile=profile,
    save_to_csv=True,
)

# 3. Access structured results
print("Company:", result.analysis.company_name)
print("Status:", result.qualification.status)
print("Deal Value: ₹", result.reasoning.estimated_deal_value)
print("Pursuit Tier:", result.strategy.tier)
print("Proposal Gate Passed:", result.proposal_gate_passed)
print("Draft Text:\n", result.generated_content.draft_text)
```

---

## 6. Running the Automated Test Suite

Run the complete test suite (25 tests covering all unit and integration specifications):

```bash
python -m pytest -v
```

### Running Specific Test Modules:
- **Integration Tests (Member 4):**
  ```bash
  python -m pytest tests/test_integration.py -v
  ```
- **Proposal Generator & Policy Safeguards (Member 3):**
  ```bash
  python -m pytest tests/test_proposal_generator.py -v
  ```

---

## 7. Optional LLM Configuration

The application is completely functional **offline** using deterministic template generation and Python safety validators. 

To optionally enable external LLM generation:
- Set environment variable: `CATERING_HUNTER_USE_LLM=true`
- Provide your API key (e.g. `OPENAI_API_KEY` or `GEMINI_API_KEY`)
- If the LLM is offline, times out, or fails, the orchestrator automatically degrades to deterministic templates without raising unhandled errors.

---

## 8. Cross-Platform Compatibility Evidence

- **Operating Systems Supported:** Windows 10/11, macOS, Ubuntu / Debian Linux.
- **CSV Encoding:** All file readers and writers use explicit `utf-8` encoding.
- **Paths:** Path resolution uses Python's standard `pathlib.Path` ensuring full cross-platform compatibility without hardcoded path separators.
