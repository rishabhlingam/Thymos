import { useEffect, useState } from 'react'

function KpiCard({ label, value }) {
  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 p-6">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold text-slate-800 mt-1">{value}</p>
    </div>
  )
}

function Overview() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetch('/api/baseline-subset')
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  return (
    <div className="space-y-6">
      <p className="text-slate-600">
        This dashboard summarizes immune cell population data from the miraclib
        clinical trial. Use the tabs above to explore population frequencies,
        responder comparisons, and baseline subset breakdowns.
      </p>
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <KpiCard label="Baseline melanoma PBMC samples" value={stats.total_samples} />
          <KpiCard
            label="Responders"
            value={stats.subjects_by_response?.yes ?? '—'}
          />
          <KpiCard
            label="Non responders"
            value={stats.subjects_by_response?.no ?? '—'}
          />
        </div>
      )}
    </div>
  )
}

export default Overview