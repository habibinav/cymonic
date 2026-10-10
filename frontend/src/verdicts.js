// The four priority buckets. `key` must match the `verdict` field the backend returns.
export const VERDICTS = [
  { key: 'high',     label: 'High-effort pitch',  tone: 'red',   blurb: 'Big deals worth a custom pitch' },
  { key: 'standard', label: 'Standard proposal',  tone: 'blue',  blurb: 'Send a templated proposal' },
  { key: 'light',    label: 'Light outreach',     tone: 'green', blurb: 'Quick email / call' },
  { key: 'skip',     label: 'Skip',               tone: 'gray',  blurb: 'Not worth chasing' },
]

export const VERDICT_BY_KEY = Object.fromEntries(VERDICTS.map(v => [v.key, v]))
