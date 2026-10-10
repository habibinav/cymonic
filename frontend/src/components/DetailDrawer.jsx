import { useEffect, useState } from 'react'
import { VERDICT_BY_KEY } from '../verdicts.js'
import { CloseIcon } from './Icons.jsx'

export default function DetailDrawer({ item, byId, onClose, onOpen }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const onKey = e => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  useEffect(() => setCopied(false), [item])

  const open = Boolean(item)
  const v = item ? VERDICT_BY_KEY[item.verdict] : null
  const original = item?.duplicateOf ? byId[item.duplicateOf] : null

  const copy = async () => {
    try { await navigator.clipboard.writeText(item.proposal); setCopied(true) } catch {}
  }

  return (
    <>
      <div className={`scrim ${open ? 'show' : ''}`} onClick={onClose} />
      <aside className={`drawer ${open ? 'show' : ''}`} aria-hidden={!open}>
        {item && (
          <>
            <div className="drawer-head">
              <div>
                <h2>{item.company}</h2>
                <div className="sub">{[item.title, item.location, item.date].filter(Boolean).join(' · ')}</div>
              </div>
              <button className="icon-btn" onClick={onClose}><CloseIcon /></button>
            </div>

            <div className="drawer-meta">
              <span className={`pill tone-${v.tone}`}>{v.label}</span>
              <span className="meta">{item.people ?? '–'} people</span>
              {item.source && <a className="meta link" href={item.source} target="_blank" rel="noreferrer">Source ↗</a>}
            </div>

            <Section title="Why">
              <p>{item.why}</p>
              {original && (
                <button className="link" onClick={() => onOpen(original)}>Open original: {original.company} · {original.title}</button>
              )}
            </Section>

            <Section title="Reasoning">
              {item.reasoning?.length
                ? <ul>{item.reasoning.map((r, i) => <li key={i}>{r}</li>)}</ul>
                : <p className="muted">No detailed reasoning yet.</p>}
            </Section>

            <Section title="Dossier">
              {item.dossier ? (
                <dl className="dossier">
                  {Object.entries(item.dossier).map(([k, val]) => (
                    <div key={k}><dt>{k}</dt><dd>{val}</dd></div>
                  ))}
                </dl>
              ) : <p className="muted">No dossier yet.</p>}
            </Section>

            <Section title="Proposal" action={item.proposal && <button className="btn sm" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>}>
              {item.proposal
                ? <pre className="proposal">{item.proposal}</pre>
                : <p className="muted">{item.verdict === 'skip' ? 'Skipped — no proposal needed.' : 'No proposal drafted yet.'}</p>}
            </Section>
          </>
        )}
      </aside>
    </>
  )
}

function Section({ title, action, children }) {
  return (
    <section className="drawer-section">
      <div className="section-head"><h3>{title}</h3>{action}</div>
      {children}
    </section>
  )
}
