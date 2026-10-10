import { VERDICTS } from '../verdicts.js'

export default function SummaryTiles({ counts, focus, onFocus }) {
  return (
    <section className="tiles">
      {VERDICTS.map(v => (
        <button
          key={v.key}
          className={`tile tone-${v.tone} ${focus === v.key ? 'active' : ''} ${focus && focus !== v.key ? 'dim' : ''}`}
          onClick={() => onFocus(v.key)}
        >
          <span className="tile-label">{v.label}</span>
          <span className="tile-count">{counts[v.key] ?? 0}</span>
        </button>
      ))}
    </section>
  )
}
