import { useEffect, useState, useCallback } from 'react'
import LiveRoomCard from '../components/LiveRoomCard.jsx'
import client from '../api/client.js'



function groupByRoom(sessions) {
  const map = {}
  for (const s of sessions) {
    const key = s.room_id ?? 'unknown'
    if (!map[key]) map[key] = { roomId: key, apName: s.ap_name, sessions: [] }
    map[key].sessions.push(s)
  }
  return Object.values(map)
}

function StatCard({ label, value, sub, color = 'text-slate-100', icon }) {
  return (
    <div className="card p-6 animate-slide-up">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label mb-2">{label}</p>
          <p className={`stat-number ${color}`}>{value}</p>
          {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
        </div>
        <span className="text-2xl opacity-60">{icon}</span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [liveSessions, setLiveSessions] = useState([])
  const [summary, setSummary] = useState({ total: 0, present: 0, flagged: 0 })
  const [lastUpdate, setLastUpdate] = useState(null)
  const [error, setError] = useState(null)
  const [roomMeta, setRoomMeta] = useState({})

  const loadData = useCallback(async () => {
    try {
      const [liveRes, finalRes, flaggedRes, roomsRes] = await Promise.all([
        client.get('/sessions/live'),
        client.get('/sessions/finalized?limit=500'),
        client.get('/sessions/flagged?threshold=0.75'),
        client.get('/metadata/rooms').catch(() => ({ data: { rooms: [] } }))
      ])
      setLiveSessions(liveRes.data.sessions || [])
      const finalized = finalRes.data.sessions || []
      const present = finalized.filter(s => s.status === 'PRESENT').length
      setSummary({
        total: finalized.length,
        present,
        flagged: (flaggedRes.data.flagged || []).length,
        liveCount: liveRes.data.active_count || 0,
      })
      
      const rMeta = {}
      for (const r of (roomsRes.data.rooms || [])) {
        rMeta[r.id] = r
      }
      setRoomMeta(rMeta)

      setLastUpdate(new Date())
      setError(null)
    } catch (e) {
      console.error(e)
      setError(`Cannot reach Aura API — is the ingestion server running? ${e.response?.status ? '(Error ' + e.response.status + ')' : ''}`)
    }
  }, [])

  useEffect(() => {
    loadData()
    const id = setInterval(loadData, 5000)
    return () => clearInterval(id)
  }, [loadData])

  const rooms = groupByRoom(liveSessions)

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Live Campus View</h1>
          <p className="text-sm text-slate-500 mt-1">RADIUS-passive attendance · 5-second refresh</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse-slow" />
          {lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : 'Connecting …'}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="card border-red-500/30 bg-red-500/5 p-4 text-sm text-red-400">
          ⚠️ {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Live Sessions"   value={summary.liveCount ?? 0}  icon="📡" color="text-blue-400"   sub="Currently on campus Wi-Fi" />
        <StatCard label="Finalized Today" value={summary.total}            icon="📋" sub="Attendance records" />
        <StatCard label="Present"         value={summary.present}          icon="✅" color="text-green-400"  sub="≥75% threshold met" />
        <StatCard label="Flagged"         value={summary.flagged}          icon="🚨" color="text-red-400"    sub="Focus score > 0.75" />
      </div>

      {/* Live room occupancy */}
      <div>
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Live Room Occupancy</h2>
        {rooms.length === 0 ? (
          <div className="card p-12 text-center text-slate-600">
            <p className="text-4xl mb-3">📡</p>
            <p className="text-sm">No active RADIUS sessions.</p>
            <p className="text-xs mt-1">Run a simulator scenario to see live data.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {rooms.map(room => (
              <LiveRoomCard
                key={room.roomId}
                roomId={roomMeta[room.roomId]?.name || room.roomId}
                apName={room.apName}
                sessions={room.sessions}
                capacity={roomMeta[room.roomId]?.capacity || 60}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
