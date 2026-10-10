import { CopyIcon, ExpandIcon, CollapseIcon } from './Icons.jsx'

export default function PriorityWindow({ verdict, rows, expanded, onExpand, onRowClick, byId }) {
  return (
    <section className={`window tone-${verdict.tone}`}>
      <div className="window-head">
        <div>
          <div className="window-title">
            <span className="window-dot" />
            {verdict.label}
            <span className="window-count">{rows.length}</span>
          </div>
          <div className="window-blurb">{verdict.blurb}</div>
        </div>
        <button className="icon-btn" onClick={onExpand} title={expanded ? 'Back to all' : 'Open this window'}>
          {expanded ? <CollapseIcon /> : <ExpandIcon />}
        </button>
      </div>

      <div className="table">
        <div className="thead">
          <span>Announcement</span>
          <span className="num">People</span>
          <span>Why</span>
        </div>
        <div className="tbody">
          {rows.length === 0 && <div className="empty small">Nothing here</div>}
          {rows.map(a => (
            <button key={a.id} className="row" onClick={() => onRowClick(a)}>
              <span className="cell-main">
                <span className="company">{a.company}</span>
                <span className="sub">{[a.title, a.location !== 'Kochi' ? a.location : null, a.date].filter(Boolean).join(' · ')}</span>
              </span>
              <span className="num">{a.people ?? '–'}</span>
              <span className="why">
                {a.duplicateOf && <CopyIcon />}
                {a.duplicateOf && byId[a.duplicateOf]
                  ? `Duplicate of ${byId[a.duplicateOf].company} · ${byId[a.duplicateOf].title}`
                  : a.why}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
