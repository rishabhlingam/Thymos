import { Search } from 'lucide-react'

function Header() {
  return (
    <div className="h-16 border-b border-slate-100 bg-white flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="flex items-center gap-2 text-sm text-slate-400 border border-slate-200 rounded-lg px-3 py-1.5">
        <Search size={14} />
        <span>Search</span>
        <kbd className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-400">
          Ctrl K
        </kbd>
      </div>
      <div className="w-8 h-8 rounded-full bg-accent text-white flex items-center justify-center text-xs font-semibold">
        BL
      </div>
    </div>
  )
}

export default Header