import { useEffect, useState, useCallback } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import RiskScoreBadge from '../components/RiskScoreBadge.jsx'
import SessionTimeline from '../components/SessionTimeline.jsx'
import client from '../api/client.js'

function FlaggedCard({ session }) {
  const score = session.proxy_risk_score ?? 0
  const dlMB = session.bytes_downloaded_mb ?? 0
  const ulMB = session.bytes_uploaded_mb ?? 0

  // Build a tiny data series for the area chart
  const chartData = [
    { t: 'Start',  dl: 0,        ul: 0 },
    { t: 'Mid',    dl: dlMB / 2, ul: ulMB / 2 },
    { t: 'End',    dl: dlMB,     ul: ulMB },
  ]

  return (
    <div className="card-hover p-5 border-red-500/20 animate-fade-in">
      {/* Header row */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-xs text-slate-500 font-mono mb-1">{session.student_id}</p>
          <h3 className="font-semibold text-slate-100">{session.student_name ?? session.student_id}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="badge bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px]">{session.course_code}</span>
            <span className="text-xs text-slate-600">{session.date}</span>
          </div>
        </div>
        <RiskScoreBadge score={score} />
      </div>

      {/* Bandwidth area chart */}
      <div className="h-24 mb-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
            <XAxis dataKey="t" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(v, name) => [`${v.toFixed(1)} MB`, name === 'dl' ? 'Download' : 'Upload']}
              contentStyle={{ background: '#131929', border: '1px solid #1e2d45', borderRadius: 8, fontSize: 11 }}
            />
            <Area type="monotone" dataKey="dl" stroke="#ef4444" fill="#ef444415" strokeWidth={1.5} name="dl" />
            <Area type="monotone" dataKey="ul" stroke="#3b82f6" fill="#3b82f615" strokeWidth={1.5} name="ul" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          { label: 'Downloaded', value: `${dlMB.toFixed(1)} MB`, color: 'text-red-400' },
          { label: 'Uploaded',   value: `${ulMB.toFixed(1)} MB`, color: 'text-blue-400' },
          { label: 'Duration',   value: `${session.minutes_present ?? '?'} min`, color: 'text-slate-300' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-slate-900/50 rounded-lg p-2">
            <p className={`text-sm font-bold ${color}`}>{value}</p>
            <p className="text-[10px] text-slate-600 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* AP info */}
      <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-600">
        <span className="font-mono">{session.ap_name}</span>
        <span className="badge bg-red-500/15 text-red-400 border border-red-500/20">⚠ Anomalous Bandwidth</span>
      </div>
    </div>
  )
}

export default function Flagged() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [threshold, setThreshold] = useState(0.75)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await client.get(`/sessions/flagged?threshold=${threshold}`)
      setSessions(res.data.flagged || [])
      setError(null)
    } catch {
      setError('Failed to load flagged sessions')
    } finally {
      setLoading(false)
    }
  }, [threshold])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Flagged Sessions</h1>
          <p className="text-sm text-slate-500 mt-1">
            Sessions with anomalous bandwidth — potential distraction or proxy attendance
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-500">Threshold</label>
          <input
            id="threshold-input"
            type="number"
            min="0" max="1" step="0.05"
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
            className="w-20 bg-[#131929] border border-[#1e2d45] rounded-lg px-3 py-1.5 text-sm text-slate-200 text-center focus:outline-none focus:border-blue-500/50"
          />
          <button onClick={load} className="btn-ghost">↺</button>
        </div>
      </div>

      {/* Info card */}
      <div className="card border-yellow-500/20 bg-yellow-500/5 p-4">
        <p className="text-xs text-yellow-400">
          <strong>Focus Score</strong> is computed by an Isolation Forest model trained on session bandwidth + duration.
          Scores ≥ {threshold} indicate statistically anomalous bandwidth consumption for the session duration —
          consistent with video streaming, large downloads, or other non-lecture activities.
          This does <em>not</em> mark the student absent — it surfaces a signal for faculty review.
        </p>
      </div>

      {error && <div className="card border-red-500/30 bg-red-500/5 p-4 text-sm text-red-400">⚠️ {error}</div>}

      {loading ? (
        <div className="text-center py-20 text-slate-600">Loading …</div>
      ) : sessions.length === 0 ? (
        <div className="card p-16 text-center">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-slate-400">No flagged sessions at threshold {threshold}.</p>
          <p className="text-xs text-slate-600 mt-1">Run the bandwidth_fraud scenario to generate flagged data.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {sessions.map(s => <FlaggedCard key={s.id} session={s} />)}
        </div>
      )}
    </div>
  )
}
