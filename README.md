# Corporate Catering Hunter

```
corporate_catering_hunter_synthetic_dataset_500.csv   # dataset
decision_agents/        # Member 1 – qualify → reason → choose strategy
proposal_generator.py   # Member 3 – writes pitch / proposal / outreach / research checklist
prompts.py, agent.py, config.py, schemas.py            # Member 3 support files
pipeline.py             # glue: CSV → decision agents → proposal generator → UI data
streamlit_ui/           # UI (Netflix-style)
```

## Run
```bash
pip install -r requirements.txt
python pipeline.py                 # sanity check: prints verdict counts + a sample pitch
cd streamlit_ui && streamlit run app.py
```

## Tests
```bash
python -m unittest decision_agents.test_decision_agents
python -m pytest tests
```

## Optional LLM drafting (Member 3)
`CATERING_HUNTER_USE_LLM=true CATERING_HUNTER_LLM_PROVIDER=gemini GEMINI_API_KEY=...`
(otherwise deterministic templates are used).
