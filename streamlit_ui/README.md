# Catering Hunter — Streamlit UI (Netflix-style)

```bash
cd streamlit_ui
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8501
```

- **Home:** hero banner with the #1 lead + four verdict cards (High-effort, Standard, Light, Skip).
- **Click a verdict card:** it zooms into that category's page (cards for each lead, pill tabs to hop between categories).
- **Click a lead:** detail modal with reasoning, dossier and proposal (Copy button). `Esc` closes / goes back.

Files: `app.py` (loads data, Analyze all button) · `ui.html` (all the visuals + transitions) ·
`data.py` (backend hookup) · `mock_data.py` (sample data + field shape).

## Plugging in the backend
Edit `data.py`: point `CATERING_API_URL` at the API (`GET /api/verdicts`, `POST /api/analyze`) or call the
pipeline functions directly. `verdict` must be `high | standard | light | skip`.
