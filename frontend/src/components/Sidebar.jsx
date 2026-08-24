import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Table2, Activity, Users, ChevronLeft } from 'lucide-react'
import { useState } from 'react'

const sections = [
  {
    label: 'Overview',
    items: [
      { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
    ],
  },
  {
    label: 'Sample Analysis',
    items: [
      { to: '/populations', label: 'Population Frequencies', icon: Table2 },
      { to: '/baseline', label: 'Baseline Subset', icon: Users },
    ],
  },
  {
    label: 'Statistical Analysis',
    items: [
      { to: '/responders', label: 'Responder Analysis', icon: Activity },
    ],
  },
]

function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div
      className={`h-screen sticky top-0 flex flex-col border-r border-slate-200 bg-white transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      <div className="flex items-center justify-between px-4 h-16 border-b border-slate-100">
        {!collapsed && (
          <span className="font-bold text-lg tracking-tight text-slate-900">Thymos</span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="text-slate-400 hover:text-slate-600 p-1 rounded transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft size={16} className={collapsed ? 'rotate-180 transition-transform' : 'transition-transform'} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {sections.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="px-2.5 mb-2 text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                {section.label}
              </p>
            )}
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-accent-soft text-accent'
                          : 'text-slate-600 hover:bg-slate-50'
                      }`
                    }
                  >
                    <Icon size={16} />
                    {!collapsed && <span>{item.label}</span>}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  )
}

export default Sidebar