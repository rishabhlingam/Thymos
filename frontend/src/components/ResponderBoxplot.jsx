import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import FilterBar from './FilterBar'
import { ChartGridSkeleton } from './Skeleton'

function ResponderBoxplot() {
  const [filters, setFilters] = useState({
    condition: 'melanoma',
    treatment: 'miraclib',
    sample_type: 'PBMC',
  })
  const [dataPoints, setDataPoints] = useState([])
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams(filters)
    fetch(`/api/comparison?${params}`)
      .then((res) => res.json())
      .then((json) => {
        setDataPoints(json.data_points)
        setStats(json.stats)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [filters])

  const populations = [...new Set(dataPoints.map((d) => d.population))].sort()

  return (
    <div className="space-y-4">
      <FilterBar filters={filters} onChange={setFilters} excludeTreatments={['none']} />

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">
            Responders vs Non Responders
          </h2>
          <p className="text-sm text-slate-500">
            {filters.condition}, {filters.sample_type} samples, {filters.treatment} treated patients
          </p>
        </div>

        {error && <p className="text-red-600">Error, {error}</p>}

        {loading && !error && <ChartGridSkeleton count={4} />}

        {!loading && !error && populations.length === 0 && (
          <p className="text-slate-500">No data available for this filter combination.</p>
        )}

        {!loading && !error && populations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {populations.map((population) => {
              const popStats = stats.find((s) => s.population === population)
              const responderVals = dataPoints
                .filter((d) => d.population === population && d.response === 'yes')
                .map((d) => d.percentage)
              const nonResponderVals = dataPoints
                .filter((d) => d.population === population && d.response === 'no')
                .map((d) => d.percentage)

              return (
                <div key={population} className="border border-slate-100 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium text-slate-700">{population}</h3>
                    {popStats && (
                      <span
                        className={
                          popStats.significant
                            ? 'text-xs font-semibold px-2 py-1 rounded bg-green-100 text-green-700'
                            : 'text-xs font-semibold px-2 py-1 rounded bg-slate-100 text-slate-500'
                        }
                      >
                        p = {popStats.p_value !== null ? popStats.p_value.toFixed(4) : 'N/A'}
                        {popStats.significant ? ', significant' : ''}
                      </span>
                    )}
                  </div>
                  <Plot
                    data={[
                      { y: nonResponderVals, type: 'box', name: 'Non responder', marker: { color: '#94a3b8' } },
                      { y: responderVals, type: 'box', name: 'Responder', marker: { color: '#0ea5e9' } },
                    ]}
                    layout={{
                      height: 300,
                      margin: { t: 10, b: 30, l: 40, r: 10 },
                      yaxis: { title: '% of cells' },
                      autosize: true,
                    }}
                    useResizeHandler
                    style={{ width: '100%', height: '300px' }}
                    config={{ displayModeBar: false }}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResponderBoxplot