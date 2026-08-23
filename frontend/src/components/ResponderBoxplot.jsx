import Plot from 'react-plotly.js'
import FilterBar from './FilterBar'
import { ChartGridSkeleton } from './Skeleton'
import { useApiData } from '../hooks/useApiData'
import { useState } from 'react'

function median(sortedArr) {
  const mid = Math.floor(sortedArr.length / 2)
  return sortedArr.length % 2 !== 0
    ? sortedArr[mid]
    : (sortedArr[mid - 1] + sortedArr[mid]) / 2
}

function quartile(sortedArr, q) {
  const pos = (sortedArr.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (sortedArr[base + 1] !== undefined) {
    return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base])
  }
  return sortedArr[base]
}

function buildHoverOverlay(vals, label, xaxis, yaxis) {
  if (!vals.length) return null
  const sorted = [...vals].sort((a, b) => a - b)
  const min = sorted[0]
  const max = sorted[sorted.length - 1]
  const q1 = quartile(sorted, 0.25)
  const med = median(sorted)
  const q3 = quartile(sorted, 0.75)

  return {
    x: vals.map(() => label),
    y: [max - min],
    base: [min],
    type: 'bar',
    width: 0.6,
    marker: { color: 'rgba(0,0,0,0)' },
    xaxis,
    yaxis,
    customdata: [[max, q3, med, q1, min]],
    hovertemplate:
      'Max: %{customdata[0]:.1f}%<br>' +
      'Q3: %{customdata[1]:.1f}%<br>' +
      'Median: %{customdata[2]:.1f}%<br>' +
      'Q1: %{customdata[3]:.1f}%<br>' +
      'Min: %{customdata[4]:.1f}%' +
      '<extra></extra>',
    showlegend: false,
  }
}

function ResponderBoxplot() {
  const [filters, setFilters] = useState({
    condition: 'melanoma',
    treatment: 'miraclib',
    sample_type: 'PBMC',
  })

  const { data, loading, error } = useApiData('/api/comparison', filters)

  const dataPoints = data?.data_points ?? []
  const stats = data?.stats ?? []
  const populations = [...new Set(dataPoints.map((d) => d.population))].sort()

  return (
    <div className="space-y-4">
      <FilterBar filters={filters} onChange={setFilters} excludeTreatments={['none']} />

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">
            Response to Miraclib
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

              const allVals = [...nonResponderVals, ...responderVals]
              const yMin = allVals.length ? Math.min(...allVals) : 0
              const yMax = allVals.length ? Math.max(...allVals) : 1
              const pad = (yMax - yMin) * 0.1 || 1
              const yRange = [Math.max(0, yMin - pad), yMax + pad]

              const hoverlabelStyle = {
                bgcolor: '#1e293b',
                bordercolor: '#1e293b',
                font: { color: '#ffffff', size: 12 },
              }

              const noOverlay = buildHoverOverlay(nonResponderVals, 'no', 'x', 'y')
              const yesOverlay = buildHoverOverlay(responderVals, 'yes', 'x2', 'y2')

              const plotData = [
                {
                  x: nonResponderVals.map(() => 'no'),
                  y: nonResponderVals,
                  type: 'box',
                  name: 'no',
                  marker: { color: '#94a3b8' },
                  xaxis: 'x',
                  yaxis: 'y',
                  hoverinfo: 'skip',
                },
                {
                  x: responderVals.map(() => 'yes'),
                  y: responderVals,
                  type: 'box',
                  name: 'yes',
                  marker: { color: '#0ea5e9' },
                  xaxis: 'x2',
                  yaxis: 'y2',
                  hoverinfo: 'skip',
                },
              ]
              if (noOverlay) plotData.push(noOverlay)
              if (yesOverlay) plotData.push(yesOverlay)

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
                    data={plotData}
                    layout={{
                      height: 300,
                      margin: { t: 10, b: 30, l: 40, r: 10 },
                      autosize: true,
                      hovermode: 'closest',
                      showlegend: false,
                      barmode: 'overlay',
                      hoverlabel: hoverlabelStyle,
                      xaxis: { domain: [0, 0.46], anchor: 'y', fixedrange: true, title: 'response' },
                      xaxis2: { domain: [0.54, 1], anchor: 'y2', fixedrange: true, title: 'response' },
                      yaxis: { domain: [0, 1], range: yRange, title: '% of cells', anchor: 'x' },
                      yaxis2: { domain: [0, 1], range: yRange, showticklabels: false, anchor: 'x2' },
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