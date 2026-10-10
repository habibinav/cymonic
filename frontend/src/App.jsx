import { useEffect, useMemo, useState } from 'react'
import { VERDICTS } from './verdicts.js'
import { fetchVerdicts, analyzeAll } from './api.js'
import SummaryTiles from './components/SummaryTiles.jsx'
import PriorityWindow from './components/PriorityWindow.jsx'
import DetailDrawer from './components/DetailDrawer.jsx'
import { ForkKnifeIcon, PlayIcon } from './components/Icons.jsx'

export default function App() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [usingMock, setUsingMock] = useState(false)
  const [focus, setFocus] = useState(null)      // verdict key or null = show all windows
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetchVerdicts().then(({ data, mock }) => { setItems(data); setUsingMock(mock); setLoading(false) })
  }, [])

  const onAnalyze = async () => {
    setAnalyzing(true)
    const { data, mock } = await analyzeAll()
    setItems(data); setUsingMock(mock); setAnalyzing(false)
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter(a =>
      [a.company, a.title, a.why, a.location].some(f => f?.toLowerCase().includes(q)))
  }, [items, query])

  const grouped = useMemo(() => {
    const g = Object.fromEntries(VERDICTS.map(v => [v.key, []]))
    filtered.forEach(a => (g[a.verdict] ??= []).push(a))
    return g
  }, [filtered])

  const counts = useMemo(() => {
    const c = Object.fromEntries(VERDICTS.map(v => [v.key, 0]))
    items.forEach(a => { c[a.verdict] = (c[a.verdict] || 0) + 1 })
    return c
  }, [items])

  const visible = focus ? VERDICTS.filter(v => v.key === focus) : VERDICTS
  const byId = useMemo(() => Object.fromEntries(items.map(a => [a.id, a])), [items])

  return (
    <div className="page">
      <header className="topbar">
        <div className="title">
          <ForkKnifeIcon />
          <h1>Verdicts <span className="dot">·</span> {items.length} announcements</h1>
          {usingMock && <span className="badge-mock" title="Backend not reachable — showing sample data">mock data</span>}
        </div>
        <div className="actions">
          <input
            className="search" placeholder="Search company, event…"
            value={query} onChange={e => setQuery(e.target.value)}
          />
          <button className="btn" onClick={onAnalyze} disabled={analyzing}>
            {analyzing ? <span className="spinner" /> : <PlayIcon />}
            {analyzing ? 'Analyzing…' : 'Analyze all'}
          </button>
        </div>
      </header>

      <SummaryTiles counts={counts} focus={focus} onFocus={k => setFocus(f => (f === k ? null : k))} />

      <div className="view-bar">
        <span className="muted">
          {focus ? 'Showing one priority' : 'Showing all priorities'} · click a row for reasoning, dossier and proposal
        </span>
        {focus && <button className="link" onClick={() => setFocus(null)}>Show all windows</button>}
      </div>

      {loading ? (
        <div className="empty">Loading…</div>
      ) : (
        <main className={`windows ${focus ? 'single' : ''}`}>
          {visible.map(v => (
            <PriorityWindow
              key={v.key}
              verdict={v}
              rows={grouped[v.key] || []}
              expanded={focus === v.key}
              onExpand={() => setFocus(f => (f === v.key ? null : v.key))}
              onRowClick={setSelected}
              byId={byId}
            />
          ))}
        </main>
      )}

      <DetailDrawer item={selected} byId={byId} onClose={() => setSelected(null)} onOpen={setSelected} />
    </div>
  )
}
