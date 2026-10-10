import { MOCK_ANNOUNCEMENTS } from './mockData.js'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

// GET /api/verdicts  -> { announcements: [...] }   (or a plain array)
export async function fetchVerdicts() {
  if (USE_MOCK) return { data: MOCK_ANNOUNCEMENTS, mock: true }
  try {
    const res = await fetch('/api/verdicts')
    if (!res.ok) throw new Error(res.status)
    const json = await res.json()
    return { data: Array.isArray(json) ? json : json.announcements, mock: false }
  } catch {
    return { data: MOCK_ANNOUNCEMENTS, mock: true }
  }
}

// POST /api/analyze  -> runs the agent pipeline, returns the same shape as /api/verdicts
export async function analyzeAll() {
  if (USE_MOCK) { await sleep(1200); return { data: MOCK_ANNOUNCEMENTS, mock: true } }
  try {
    const res = await fetch('/api/analyze', { method: 'POST' })
    if (!res.ok) throw new Error(res.status)
    const json = await res.json()
    return { data: Array.isArray(json) ? json : json.announcements, mock: false }
  } catch {
    await sleep(1200)
    return { data: MOCK_ANNOUNCEMENTS, mock: true }
  }
}
