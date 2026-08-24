import { useEffect, useState } from 'react'
import Breadcrumb from './Breadcrumb'
import ExplainerBox from './ExplainerBox'

function KpiCard({ label, value }) {
  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 p-6">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold text-accent mt-1">{value}</p>
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
      <Breadcrumb items={[{ label: 'View', value: 'Overview' }]} />

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Miraclib Immune Monitoring</h1>
          <p className="text-sm text-slate-600 mt-2">
            <span className="font-semibold text-slate-700">Goal: </span>
            Investigate how immune cell population frequencies relate to treatment
            response in melanoma patients receiving miraclib, to identify patterns
            that might help predict which patients are likely to respond.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-700 mb-2">Key Questions</p>
          <ul className="text-sm text-slate-600 space-y-1.5 list-disc list-inside">
            <li>What is the relative frequency of each immune cell population per sample?</li>
            <li>Do responders and non-responders differ in their immune population frequencies?</li>
            <li>Which populations show a statistically significant, and practically meaningful, difference?</li>
            <li>How well can immune population frequencies predict individual response?</li>
          </ul>
        </div>
      </div>

      <ExplainerBox title="What am I looking at?" defaultOpen>
        <p>
          This dashboard summarizes immune cell population data from a miraclib
          clinical trial in melanoma patients. Each sample was measured for five
          immune cell populations, b cell, cd4 t cell, cd8 t cell, monocyte, and
          nk cell, reported as relative percentages of the total cell count.
        </p>
        <p>
          Use the sidebar to explore population frequencies for every sample,
          compare responders against non-responders with statistical support,
          and break down the baseline patient cohort by project, response, and sex.
        </p>
      </ExplainerBox>

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