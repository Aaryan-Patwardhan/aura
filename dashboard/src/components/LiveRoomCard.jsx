/**
 * LiveRoomCard — shows real-time occupancy for a single room.
 * Groups active sessions by room_id.
 */
export default function LiveRoomCard({ roomId, apName, sessions, capacity = 60 }) {
  const count = sessions.length
  const pct = Math.min(100, Math.round((count / capacity) * 100))

  const barColor =
    pct >= 90 ? 'bg-red-500' :
    pct >= 60 ? 'bg-yellow-500' :
    pct > 0   ? 'bg-green-500' :
    'bg-slate-700'

  return (
    <div className="card-hover p-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Room</p>
          <h3 className="text-lg font-bold text-slate-100">{roomId ?? '—'}</h3>
          <p className="text-xs text-slate-600 font-mono mt-0.5">{apName}</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-blue-400 tabular-nums">{count}</span>
          <p className="text-xs text-slate-600">/ {capacity}</p>
        </div>
      </div>

      {/* Occupancy bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-4">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Active students list */}
      {sessions.length > 0 ? (
        <ul className="space-y-1 max-h-36 overflow-y-auto">
          {sessions.map(s => (
            <li key={s.username} className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-mono">{s.username}</span>
              <span className="text-slate-600">{s.bytes_downloaded_mb?.toFixed(1)} MB</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-600 italic">No active sessions</p>
      )}

      {/* Live indicator */}
      {count > 0 && (
        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-800">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse-slow" />
          <span className="text-xs text-green-400">LIVE</span>
        </div>
      )}
    </div>
  )
}
