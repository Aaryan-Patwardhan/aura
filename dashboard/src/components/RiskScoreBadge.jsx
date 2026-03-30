/**
 * RiskScoreBadge — color-coded pill showing Focus Score value.
 * green  < 0.30   (normal)
 * yellow 0.30–0.75 (moderate)
 * red    > 0.75   (flagged)
 */
export default function RiskScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return <span className="badge bg-slate-800 text-slate-500">—</span>
  }

  const pct = Math.round(score * 100)

  let colorClass, dotColor, label
  if (score >= 0.75) {
    colorClass = 'bg-red-500/15 text-red-400 border border-red-500/30'
    dotColor   = 'bg-red-400'
    label      = 'FLAGGED'
  } else if (score >= 0.3) {
    colorClass = 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30'
    dotColor   = 'bg-yellow-400'
    label      = 'MODERATE'
  } else {
    colorClass = 'bg-green-500/15 text-green-400 border border-green-500/30'
    dotColor   = 'bg-green-400'
    label      = 'NORMAL'
  }

  return (
    <span className={`badge ${colorClass} font-mono`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} ${score >= 0.75 ? 'animate-pulse' : ''}`} />
      {pct}%&nbsp;<span className="opacity-60 text-[10px]">{label}</span>
    </span>
  )
}
