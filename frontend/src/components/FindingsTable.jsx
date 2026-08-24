import { useState } from 'react'

const HEADERS = [
  { key: 'population', label: 'Population' },
  { key: 'p_value', label: 'P-value' },
  { key: 'fdr', label: 'FDR' },
  { key: 'effect_size', label: 'Effect Size' },
  { key: 'auc', label: 'AUC' },
]

function formatValue(key, value) {
  if (value == null) return 'N/A'
  if (key === 'population') return value
  if (key === 'effect_size') return (value >= 0 ? '+' : '') + value.toFixed(3)
  if (key === 'auc') return value.toFixed(2)
  return value.toFixed(4)
}

function FindingsTable({ stats, onJumpTo }) {
  const [sortKey, setSortKey] = useState('p_value')
  const [sortDir, setSortDir] = useState('asc')

  const sorted = [...stats].sort((a, b) => {
    const aVal = a[sortKey] == null ? Infinity : a[sortKey]
    const bVal = b[sortKey] == null ? Infinity : b[sortKey]
    if (sortKey === 'population') {
      return sortDir === 'asc' ? a.population.localeCompare(b.population) : b.population.localeCompare(a.population)
    }
    return sortDir === 'asc' ? aVal - bVal : bVal - aVal
  })

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-700">Statistical Findings</h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Click a column to sort. FDR corrected significance shown in bold.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              {HEADERS.map((h) => (
                <th
                  key={h.key}
                  onClick={() => toggleSort(h.key)}
                  className="text-left px-4 py-2 font-medium text-slate-600 cursor-pointer select-none hover:text-accent"
                >
                  {h.label} {sortKey === h.key ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
              ))}
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.population} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium text-slate-700">{row.population}</td>
                <td className="px-4 py-2 text-slate-600">{formatValue('p_value', row.p_value)}</td>
                <td className="px-4 py-2">
                  <span className={row.significant_fdr ? 'text-accent font-semibold' : 'text-slate-500'}>
                    {formatValue('fdr', row.fdr)}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-600">{formatValue('effect_size', row.effect_size)}</td>
                <td className="px-4 py-2 text-slate-600">{formatValue('auc', row.auc)}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => onJumpTo(row.population)}
                    className="text-xs text-accent hover:underline"
                  >
                    View chart
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default FindingsTable