import { NavLink, Outlet } from 'react-router-dom'

const tabs = [
  { to: '/', label: 'Overview', end: true },
  { to: '/populations', label: 'Population Frequencies' },
  { to: '/responders', label: 'Responder Analysis' },
  { to: '/baseline', label: 'Baseline Subset' },
]

function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-8 pt-6">
          <h1 className="text-2xl font-bold text-slate-800 mb-4">
            Immune Cell Population Dashboard
          </h1>
          <nav className="flex gap-1">
            {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                className={({ isActive }) =>
                  `px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 ${
                    isActive
                      ? 'border-sky-500 text-sky-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
      <div className="max-w-6xl mx-auto p-8">
        <Outlet />
      </div>
    </div>
  )
}

export default Layout