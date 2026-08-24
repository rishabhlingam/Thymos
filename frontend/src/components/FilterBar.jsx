import { useEffect, useState } from 'react'

function FilterBar({ filters, onChange, excludeTreatments = [] }) {
  const [options, setOptions] = useState(null)

  useEffect(() => {
    fetch('/api/filter-options')
      .then((res) => res.json())
      .then(setOptions)
      .catch(() => {})
  }, [])

  if (!options) return null

  const handleChange = (key, value) => {
    onChange({ ...filters, [key]: value })
  }

  const treatmentOptions = options.treatments.filter((t) => !excludeTreatments.includes(t))

  const fieldClass =
    'border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent'
  const labelClass = 'block text-[10px] font-semibold tracking-wider text-slate-400 uppercase mb-1'

  return (
    <div className="bg-white shadow rounded-xl border border-slate-200 p-4 flex flex-wrap gap-4 items-end">
      <div>
        <label className={labelClass}>Condition</label>
        <select
          className={fieldClass}
          value={filters.condition}
          onChange={(e) => handleChange('condition', e.target.value)}
        >
          {options.conditions.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={labelClass}>Treatment</label>
        <select
          className={fieldClass}
          value={filters.treatment}
          onChange={(e) => handleChange('treatment', e.target.value)}
        >
          {treatmentOptions.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={labelClass}>Sample Type</label>
        <select
          className={fieldClass}
          value={filters.sample_type}
          onChange={(e) => handleChange('sample_type', e.target.value)}
        >
          {options.sample_types.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {filters.time_from_treatment_start !== undefined && (
        <div>
          <label className={labelClass}>Timepoint</label>
          <select
            className={fieldClass}
            value={filters.time_from_treatment_start}
            onChange={(e) => handleChange('time_from_treatment_start', Number(e.target.value))}
          >
            {options.timepoints.map((t) => (
              <option key={t} value={t}>{t === 0 ? 'Baseline (0)' : `Day ${t}`}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

export default FilterBar