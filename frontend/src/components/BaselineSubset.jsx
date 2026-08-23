import { useState } from 'react'
import FilterBar from './FilterBar'
import { CardSkeleton } from './Skeleton'
import { useApiData } from '../hooks/useApiData'

function StatCard({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-xl font-semibold text-slate-800">{value}</p>
    </div>
  )
}

function BreakdownList({ title, breakdown }) {
  const entries = Object.entries(breakdown)
  return (
    <div>
      <p className="text-sm font-medium text-slate-600 mb-2">{title}</p>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-400">No data</p>
      ) : (
        <div className="space-y-1">
          {entries.map(([key, value]) => (
            <div
              key={key}
              className="flex justify-between text-sm bg-slate-50 rounded px-3 py-2 border border-slate-100"
            >
              <span className="text-slate-600">{key}</span>
              <span className="font-medium text-slate-800">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function BaselineSubset() {
  const [filters, setFilters] = useState({
    condition: 'melanoma',
    treatment: 'miraclib',
    sample_type: 'PBMC',
    time_from_treatment_start: 0,
  })

  const { data: subset, loading, error } = useApiData('/api/baseline-subset', filters)

  return (
    <div className="space-y-4">
      <FilterBar filters={filters} onChange={setFilters} excludeTreatments={['none']} />

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Subset Breakdown</h2>
          <p className="text-sm text-slate-500">
            {filters.condition}, {filters.sample_type} samples, {filters.treatment} treated,
            timepoint {filters.time_from_treatment_start}
          </p>
        </div>

        {error && <p className="text-red-600">Error, {error}</p>}

        {loading && !error && <CardSkeleton />}

        {!loading && !error && subset && subset.total_samples === 0 && (
          <p className="text-slate-500">No samples match this filter combination.</p>
        )}

        {!loading && !error && subset && subset.total_samples > 0 && (
          <>
            <StatCard label="Total samples" value={subset.total_samples} />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <BreakdownList title="Samples per project" breakdown={subset.samples_per_project} />
              <BreakdownList title="Subjects by response" breakdown={subset.subjects_by_response} />
              <BreakdownList title="Subjects by sex" breakdown={subset.subjects_by_sex} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default BaselineSubset