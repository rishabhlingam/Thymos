import { useEffect, useState } from 'react'

function StatCard({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-xl font-semibold text-slate-800">{value}</p>
    </div>
  )
}

function BreakdownList({ title, breakdown }) {
  return (
    <div>
      <p className="text-sm font-medium text-slate-600 mb-2">{title}</p>
      <div className="space-y-1">
        {Object.entries(breakdown).map(([key, value]) => (
          <div
            key={key}
            className="flex justify-between text-sm bg-slate-50 rounded px-3 py-2 border border-slate-100"
          >
            <span className="text-slate-600">{key}</span>
            <span className="font-medium text-slate-800">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function BaselineSubset() {
  const [subset, setSubset] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/baseline-subset')
      .then((res) => res.json())
      .then((json) => {
        setSubset(json)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <p className="text-slate-500">Loading baseline subset...</p>
  if (error) return <p className="text-red-600">Error, {error}</p>

  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-800">
          Baseline Subset, Melanoma PBMC, Miraclib
        </h2>
        <p className="text-sm text-slate-500">
          Samples at time from treatment start equal to 0
        </p>
      </div>

      <StatCard label="Total baseline samples" value={subset.total_samples} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <BreakdownList title="Samples per project" breakdown={subset.samples_per_project} />
        <BreakdownList title="Subjects by response" breakdown={subset.subjects_by_response} />
        <BreakdownList title="Subjects by sex" breakdown={subset.subjects_by_sex} />
      </div>
    </div>
  )
}

export default BaselineSubset