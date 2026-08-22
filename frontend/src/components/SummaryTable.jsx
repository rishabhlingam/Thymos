import { useEffect, useState } from 'react'

function SummaryTable() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/summary')
      .then((res) => res.json())
      .then((json) => {
        setData(json)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <p className="text-slate-500">Loading summary table...</p>
  if (error) return <p className="text-red-600">Error, {error}</p>

  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200">
        <h2 className="text-lg font-semibold text-slate-800">
          Cell Population Frequencies
        </h2>
        <p className="text-sm text-slate-500">
          Relative frequency of each immune cell population per sample
        </p>
      </div>
      <div className="max-h-96 overflow-y-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 sticky top-0">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-slate-600">Sample</th>
              <th className="text-left px-4 py-2 font-medium text-slate-600">Population</th>
              <th className="text-right px-4 py-2 font-medium text-slate-600">Count</th>
              <th className="text-right px-4 py-2 font-medium text-slate-600">Total Count</th>
              <th className="text-right px-4 py-2 font-medium text-slate-600">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-700">{row.sample}</td>
                <td className="px-4 py-2 text-slate-700">{row.population}</td>
                <td className="px-4 py-2 text-right text-slate-700">{row.count}</td>
                <td className="px-4 py-2 text-right text-slate-700">{row.total_count}</td>
                <td className="px-4 py-2 text-right text-slate-700">
                  {row.percentage.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default SummaryTable