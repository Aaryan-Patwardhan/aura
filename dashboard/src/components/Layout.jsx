import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/',          label: 'Live view',  icon: '📡' },
  { to: '/sessions',  label: 'Sessions',   icon: '📋' },
  { to: '/flagged',   label: 'Flagged',    icon: '🚨' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav */}
      <header className="sticky top-0 z-30 bg-[#0c0f1a]/90 backdrop-blur-sm border-b border-[#1e2d45]">
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          {/* Wordmark */}
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-sm">📡</div>
            <div>
              <span className="font-bold text-slate-100 text-sm tracking-wide">Aura</span>
              <span className="hidden sm:inline text-slate-500 text-xs ml-2 border-l border-slate-700 pl-2">
                <span className="text-slate-200 animate-flicker inline-block">A</span>utomate yo<span className="text-slate-200 animate-flicker inline-block" style={{ animationDelay: '0.15s' }}>UR</span> <span className="text-slate-200 animate-flicker inline-block" style={{ animationDelay: '0.4s' }}>A</span>ttendance
              </span>
            </div>
          </div>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {NAV.map(n => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === '/'}
                id={`nav-${n.label.toLowerCase().replace(' ', '-')}`}
                className={({ isActive }) =>
                  `btn-ghost flex items-center gap-1.5 ${isActive ? 'text-blue-400 bg-blue-500/10' : ''}`
                }
              >
                <span>{n.icon}</span>
                <span className="hidden sm:inline">{n.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Status chip */}
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse-slow" />
            <span className="hidden md:inline">RADIUS ingestion active</span>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-screen-xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1e2d45] py-4 text-center text-xs text-slate-700">
        Aura · Built by{' '}
        <a href="https://aaryan.daemonlabs.systems" className="hover:text-slate-500 transition-colors" target="_blank" rel="noreferrer">
          Aaryan Patwardhan
        </a>{' '}
        · DaemonLabs
      </footer>
    </div>
  )
}
