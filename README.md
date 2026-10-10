# Corporate Catering Hunter

Finds corporate event announcements, decides which ones are worth chasing, and drafts the pitch.

## Run it
```bash
pip3 install -r requirements.txt
cp .env.example .env          # then paste your Gemini key into .env (optional)
streamlit run app/app.py      # run from this folder
```
Gemini check: `python3 agents/gemini_client.py` · Pipeline check: `python3 pipeline.py` · Tests: `python3 -m pytest tests`

## How it works
```
announcement ──► analysis_agent ──► decision_agents ──────────────► proposal
 (text / CSV)    extract facts      qualify → reason → pick tier     template, or Gemini on demand
```
- **Hard rules stay in code** (service area, 25–1000 guests, 3+ days notice) — out-of-policy leads never reach Gemini.
- **Gemini is on demand**: in the UI, open a section or a company folder and click **✨ Analyse … with Gemini**,
  or use the button inside a single lead. Gemini writes the reasoning, scores and a tailored draft;
  Member 1's strategy agent still turns the scores into the tier. Results are saved in `data/ai_cache.json`.
- **＋ New announcement** runs a pasted announcement through every agent (with Gemini if a key is set).

## Folder layout
```
cymonic/
├── README.md · requirements.txt · .env.example
├── pipeline.py              glue: data → agents → UI   (python3 pipeline.py to sanity-check)
├── app/                     Streamlit UI
│   ├── app.py               page + "New announcement" + Gemini requests from the UI
│   ├── data.py              UI ↔ pipeline
│   ├── mock_data.py         fallback sample data
│   └── frontend/index.html  the Netflix-style interface (two-way Streamlit component)
├── agents/
│   ├── analysis_agent.py    Member 4 – extracts event facts from announcement text
│   ├── decision_agents/     Member 1 – qualification, reasoning, strategy
│   ├── proposal_generator.py, prompts.py, agent.py, config.py   Member 3 – drafts + safety checks
│   ├── schemas.py           shared data models
│   ├── gemini_client.py     Gemini API wrapper (returns None on any failure → rule-based fallback)
│   └── gemini_batch.py      Gemini reasoning + drafts, several leads per request
├── data/
│   ├── corporate_catering_hunter_synthetic_dataset_500.csv
│   ├── ai_cache.json        saved Gemini results (commit it to share)
│   └── new_leads.csv        pasted announcements (local, git-ignored)
├── tests/                   Member 1 + Member 3 tests
└── legacy/member4_app/      Member 4's earlier standalone app (archived, not used)
```

## Team rules
Work on your own branch off `main`, open a pull request, and run `python3 pipeline.py` before pushing.
