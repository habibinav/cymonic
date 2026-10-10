# Corporate Catering Hunter

```
corporate_catering_hunter_synthetic_dataset_500.csv   # dataset
analysis_agent.py       # Member 4 – extracts event facts from raw announcement text
decision_agents/        # Member 1 – qualify → reason → choose strategy
proposal_generator.py   # Member 3 – writes pitch / proposal / outreach / research checklist
prompts.py, agent.py, config.py, schemas.py            # Member 3 support files
pipeline.py             # glue: CSV / pasted text → analysis → decision agents → proposal generator → UI data
streamlit_ui/           # UI (Netflix-style)
```

## Run
```bash
pip install -r requirements.txt
python pipeline.py                 # sanity check: prints verdict counts + a sample pitch
cd streamlit_ui && streamlit run app.py
```

In the UI, **＋ New announcement** runs a pasted announcement through every agent and opens the result.
Pasted leads are saved to `new_leads.csv` (git-ignored) and show up with a NEW badge.

## Tests
```bash
python -m unittest decision_agents.test_decision_agents
python -m pytest tests
```

## Optional LLM drafting (Member 3)
`CATERING_HUNTER_USE_LLM=true CATERING_HUNTER_LLM_PROVIDER=gemini GEMINI_API_KEY=...`
(otherwise deterministic templates are used).
