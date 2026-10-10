const s = { width: 20, height: 20, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const ForkKnifeIcon = () => (
  <svg viewBox="0 0 24 24" {...s} width={24} height={24}>
    <path d="M5 3v7a2 2 0 0 0 2 2v9M9 3v7a2 2 0 0 1-2 2M7 3v6" />
    <path d="M17 21V3c-2 1-3 3-3 6v4h3" />
  </svg>
)
export const PlayIcon = () => (<svg viewBox="0 0 24 24" {...s} width={16} height={16}><path d="M7 4l12 8-12 8z" /></svg>)
export const CopyIcon = () => (<svg viewBox="0 0 24 24" {...s} width={16} height={16}><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></svg>)
export const ExpandIcon = () => (<svg viewBox="0 0 24 24" {...s} width={16} height={16}><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></svg>)
export const CollapseIcon = () => (<svg viewBox="0 0 24 24" {...s} width={16} height={16}><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" /></svg>)
export const CloseIcon = () => (<svg viewBox="0 0 24 24" {...s}><path d="M6 6l12 12M18 6L6 18" /></svg>)
