import { Download } from 'lucide-react'
import { exportToCsv } from '../utils/csv'

function ExportButton({ filename, rows, label = 'Export CSV', onClick }) {
  const disabled = !onClick && (!rows || rows.length === 0)

  const handleClick = async () => {
    if (onClick) {
      const data = await onClick()
      if (data && data.length) exportToCsv(filename, data)
      return
    }
    exportToCsv(filename, rows)
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={handleClick}
      className="flex items-center gap-1.5 text-sm border border-slate-200 rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
    >
      <Download size={14} />
      {label}
    </button>
  )
}

export default ExportButton