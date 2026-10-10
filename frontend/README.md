# Catering Hunter — UI

React + Vite frontend. Each priority (High-effort pitch, Standard proposal, Light outreach, Skip) gets its own window.

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

## Backend contract
The UI calls (proxied to `http://localhost:8000` in dev — change in `vite.config.js`):

- `GET  /api/verdicts` → array of announcements (or `{ announcements: [...] }`)
- `POST /api/analyze`  → same shape, after running the agents

Field shape is documented at the top of `src/mockData.js`. `verdict` must be one of `high | standard | light | skip`.
If the backend isn't running, the UI falls back to mock data and shows a "mock data" badge.
