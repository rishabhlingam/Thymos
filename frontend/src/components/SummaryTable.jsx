import { useEffect, useState } from 'react'

function SummaryTable() {
  const [search, setSearch] = useState('')
  const [population, setPopulation] = useState('')
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [totalPages, setTotalPages] = useState(1)
  const [totalSamples, setTotalSamples] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const pageSize = 50

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({
      sample_search: search,
      population,
      page,
      page_size: pageSize,
    })
    fetch(`/api/summary?${params}`)
      .then((res) => res.json())
      .then((json) => {
        setRows(json.rows)
        setTotalPages(json.total_pages)
        setTotalSamples(json.total_samples)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [search, population, page])

  // reset to page 1 whenever the search or population filter changes
  useEffect(() => {
    setPage(1)
  }, [search, population])

  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 space-y-3">
                <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Cell Population Frequencies
            </h2>
            <p className="text-sm text-slate-500">
              {totalSamples.toLocaleString()} samples total
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>Page {page} of {totalPages.toLocaleString()}</span>
            <button
              className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <button
              className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </button>
          </div>
        </div>
       
               <div className="flex flex-wrap gap-3 items-start">
          <div>
            <input
              type="text"
              placeholder="e.g. sample00001, sample00005:sample00010"
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-80"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <p className="text-xs text-slate-400 mt-1">
              Comma for multiple IDs, colon for a range, or combine both
            </p>
          </div>
          <select
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            value={population}
            onChange={(e) => setPopulation(e.target.value)}
          >
            <option value="">All populations</option>
            <option value="b_cell">b_cell</option>
            <option value="cd4_t_cell">cd4_t_cell</option>
            <option value="cd8_t_cell">cd8_t_cell</option>
            <option value="monocyte">monocyte</option>
            <option value="nk_cell">nk_cell</option>
          </select>
        </div>
      </div>

      {error && <p className="text-red-600 px-6 py-4">Error, {error}</p>}

      {!error && (
        <>
          <div className="overflow-x-auto overflow-y-auto max-h-[500px]">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 sticky top-0 z-10">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">Sample</th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">Population</th>
                  <th className="text-right px-4 py-2 font-medium text-slate-600">Count</th>
                  <th className="text-right px-4 py-2 font-medium text-slate-600">Total Count</th>
                  <th className="text-right px-4 py-2 font-medium text-slate-600">Percentage</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                      Loading...
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                      No matching samples
                    </td>
                  </tr>
                ) : (
                  rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-4 py-2 text-slate-700">{row.sample}</td>
                      <td className="px-4 py-2 text-slate-700">{row.population}</td>
                      <td className="px-4 py-2 text-right text-slate-700">{row.count}</td>
                      <td className="px-4 py-2 text-right text-slate-700">{row.total_count}</td>
                      <td className="px-4 py-2 text-right text-slate-700">
                        {row.percentage.toFixed(2)}%
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between px-6 py-3 border-t border-slate-200 text-sm text-slate-600">
            <span>Page {page} of {totalPages.toLocaleString()}</span>
            <div className="flex gap-2">
              <button
                className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <button
                className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default SummaryTable