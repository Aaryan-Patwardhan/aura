import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

/**
 * SessionTimeline — horizontal bar showing a student session with bandwidth profile.
 */
export default function SessionTimeline({ session }) {
  const data = [
    { name: 'Download', value: session.bytes_downloaded_mb ?? 0 },
    { name: 'Upload',   value: session.bytes_uploaded_mb ?? 0 },
  ]

  const connectTime = session.connect_time
    ? new Date(session.connect_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—'
  const disconnectTime = session.disconnect_time
    ? new Date(session.disconnect_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'active'

  return (
    <div className="space-y-1.5">
      {/* Time bar */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="font-mono">{connectTime}</span>
        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full"
            style={{ width: `${Math.min(100, (session.minutes_present ?? 45) * 2)}%` }}
          />
        </div>
        <span className="font-mono">{disconnectTime}</span>
        <span className="text-slate-600">{session.minutes_present ?? '—'} min</span>
      </div>

      {/* Bandwidth mini chart */}
      <div className="h-10">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 0, left: 48, bottom: 0 }}>
            <XAxis type="number" hide domain={[0, 'dataMax']} />
            <YAxis type="category" dataKey="name" width={48} tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={v => [`${v.toFixed(1)} MB`]}
              contentStyle={{ background: '#131929', border: '1px solid #1e2d45', borderRadius: 8, fontSize: 11 }}
            />
            <Bar dataKey="value" radius={[0, 2, 2, 0]}>
              <Cell fill="#3b82f6" />
              <Cell fill="#22c55e" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
