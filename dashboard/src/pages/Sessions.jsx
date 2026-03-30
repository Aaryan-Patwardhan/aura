import { useEffect, useState, useCallback } from 'react'
import RiskScoreBadge from '../components/RiskScoreBadge.jsx'
import client from '../api/client.js'

const STATUS_BADGE = {
  PRESENT:           'bg-green-500/15 text-green-400 border border-green-500/30',
  PARTIAL:           'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  ABSENT:            'bg-red-500/15 text-red-400 border border-red-500/30',
  INTEGRITY_SUSPECT: 'bg-purple-500/15 text-purple-400 border border-purple-500/30',
  UNSCHEDULED:       'bg-slate-700 text-slate-400',
}

function exportCSV(sessions) {
  const headers = ['Student ID','Name','Course','Date','Connect','Disconnect','Minutes','DL (MB)','UL (MB)','Status','Focus Score','AP']
  const rows = sessions.map(s => [
    s.student_id, s.student_name, s.course_code, s.date,
    s.connect_time ?? '', s.disconnect_time ?? '',
    s.minutes_present ?? '', s.bytes_downloaded_mb?.toFixed(2) ?? '',
    s.bytes_uploaded_mb?.toFixed(2) ?? '', s.status, s.proxy_risk_score?.toFixed(4) ?? '', s.ap_name,
  ])
  const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'aura_sessions.csv'; a.click()
  URL.revokeObjectURL(url)
}

export default function Sessions() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const res = await client.get('/sessions/finalized?limit=500')
      setSessions(res.data.sessions || [])
      setError(null)
    } catch {
      setError('Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = sessions.filter(s => {
    const matchSearch = !search ||
      s.student_id?.toLowerCase().includes(search.toLowerCase()) ||
      s.student_name?.toLowerCase().includes(search.toLowerCase()) ||
      s.course_code?.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'ALL' || s.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Attendance Sessions</h1>
          <p className="text-sm text-slate-500 mt-1">{filtered.length} finalized records</p>
        </div>
        <button id="export-csv-btn" onClick={() => exportCSV(filtered)} className="btn-primary">
          ↓ Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          id="session-search"
          type="text"
          placeholder="Search by student, name or course …"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-[#131929] border border-[#1e2d45] rounded-lg px-4 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
        />
        <select
          id="status-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-[#131929] border border-[#1e2d45] rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500/50"
        >
          {['ALL','PRESENT','PARTIAL','ABSENT','INTEGRITY_SUSPECT','UNSCHEDULED'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button onClick={load} className="btn-ghost">↺ Refresh</button>
      </div>

      {/* Error */}
      {error && <div className="card border-red-500/30 bg-red-500/5 p-4 text-sm text-red-400">⚠️ {error}</div>}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e2d45]">
                {['Student','Course','Date','Duration','Bandwidth','Status','Focus Score','AP'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2d45]">
              {loading ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-600">Loading …</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-600">No sessions found.</td></tr>
              ) : (
                filtered.map(s => (
                  <tr key={s.id} className="hover:bg-white/2 transition-colors duration-100">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-200">{s.student_name ?? s.student_id}</p>
                      <p className="text-xs text-slate-600 font-mono">{s.student_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="badge bg-blue-500/10 text-blue-400 border border-blue-500/20">{s.course_code}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">{s.date}</td>
                    <td className="px-4 py-3 text-slate-400">{s.minutes_present ?? '—'} min</td>
                    <td className="px-4 py-3">
                      <p className="text-slate-400 text-xs">↓ {(s.bytes_downloaded_mb ?? 0).toFixed(1)} MB</p>
                      <p className="text-slate-600 text-xs">↑ {(s.bytes_uploaded_mb ?? 0).toFixed(1)} MB</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${STATUS_BADGE[s.status] ?? 'bg-slate-700 text-slate-400'}`}>
                        {s.status ?? '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <RiskScoreBadge score={s.proxy_risk_score} />
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-xs">{s.ap_name}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
