import Plot from 'react-plotly.js'
import FilterBar from './FilterBar'
import Breadcrumb from './Breadcrumb'
import ExplainerBox from './ExplainerBox'
import FindingsTable from './FindingsTable'
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

const BOX_COLOR = '#b3aede'
const BOX_LINE_COLOR = '#8983c7'

function ResponderBoxplot() {
  const [filters, setFilters] = useState({
    condition: 'melanoma',
    treatment: 'miraclib',
    sample_type: 'PBMC',
  })
  const [sortBy, setSortBy] = useState('alphabetical')
  const [sameYAxis, setSameYAxis] = useState(false)

  const { data, loading, error } = useApiData('/api/comparison', filters)

  const dataPoints = data?.data_points ?? []
  const stats = data?.stats ?? []

  const populations = [...new Set(dataPoints.map((d) => d.population))]
  const sortedPopulations =
    sortBy === 'significance'
      ? [...populations].sort((a, b) => {
          const statA = stats.find((s) => s.population === a)
          const statB = stats.find((s) => s.population === b)
          const pA = statA?.p_value ?? 1
          const pB = statB?.p_value ?? 1
          return pA - pB
        })
      : [...populations].sort()

  const allPercentages = dataPoints.map((d) => d.percentage)
  const globalMin = allPercentages.length ? Math.min(...allPercentages) : 0
  const globalMax = allPercentages.length ? Math.max(...allPercentages) : 1
  const globalPad = (globalMax - globalMin) * 0.1 || 1
  const globalRange = [Math.max(0, globalMin - globalPad), globalMax + globalPad]

  const hoverlabelStyle = {
    bgcolor: '#1e293b',
    bordercolor: '#1e293b',
    font: { color: '#ffffff', size: 12 },
  }

  const handleJumpTo = (population) => {
    document.getElementById(`chart-${population}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { label: 'Endpoint', value: 'Response' },
          { label: 'Treatment', value: filters.treatment },
          { label: 'Sort By', value: sortBy === 'significance' ? 'Significance' : 'Alphabetical' },
        ]}
      />

      <FilterBar filters={filters} onChange={setFilters} excludeTreatments={['none']} />

      <ExplainerBox title="What does FDR mean here?">
        <p>
          The P-value column tests one population at a time. Testing all five
          populations together increases the chance that at least one looks
          significant purely by chance, even if nothing real is going on. The
          FDR column corrects for this by accounting for how many populations
          were tested together. A population is only robustly significant
          here if its FDR value is below 0.05, shown in bold in the table below.
        </p>
        <p>
          Watch for populations where the raw P-value looks significant but
          the FDR value does not, that gap means the difference is suggestive
          rather than confirmed, worth stating plainly rather than overclaiming
          a single population as a reliable predictor.
        </p>
      </ExplainerBox>

      {!loading && !error && stats.length > 0 && (
        <FindingsTable stats={stats} onJumpTo={handleJumpTo} />
      )}

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Population Frequencies
            </h2>
            <p className="text-sm text-slate-500">
              {filters.condition}, {filters.sample_type} samples, {filters.treatment} treated patients
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div>
              <label className="block text-[10px] font-semibold tracking-wider text-slate-400 uppercase mb-1">
                Sort by
              </label>
              <select
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="alphabetical">Alphabetical</option>
                <option value="significance">Significance</option>
              </select>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
              <span>Same Y-axis across all plots</span>
              <button
                type="button"
                onClick={() => setSameYAxis((v) => !v)}
                className={`relative w-9 h-5 rounded-full transition-colors ${
                  sameYAxis ? 'bg-accent' : 'bg-slate-200'
                }`}
                aria-pressed={sameYAxis}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                    sameYAxis ? 'translate-x-4' : ''
                  }`}
                />
              </button>
            </label>
          </div>
        </div>

        {error && <p className="text-red-600">Error, {error}</p>}

        {loading && !error && <ChartGridSkeleton count={4} />}

        {!loading && !error && sortedPopulations.length === 0 && (
          <p className="text-slate-500">No data available for this filter combination.</p>
        )}

        {!loading && !error && sortedPopulations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {sortedPopulations.map((population) => {
              const popStats = stats.find((s) => s.population === population)
              const responderVals = dataPoints
                .filter((d) => d.population === population && d.response === 'yes')
                .map((d) => d.percentage)
              const nonResponderVals = dataPoints
                .filter((d) => d.population === population && d.response === 'no')
                .map((d) => d.percentage)

              const localAllVals = [...nonResponderVals, ...responderVals]
              const localMin = localAllVals.length ? Math.min(...localAllVals) : 0
              const localMax = localAllVals.length ? Math.max(...localAllVals) : 1
              const localPad = (localMax - localMin) * 0.1 || 1
              const localRange = [Math.max(0, localMin - localPad), localMax + localPad]

              const yRange = sameYAxis ? globalRange : localRange

              const nonResponderLabel = `Nonresponder (n=${nonResponderVals.length})`
              const responderLabel = `Responder (n=${responderVals.length})`

              const noOverlay = buildHoverOverlay(nonResponderVals, nonResponderLabel, 'x', 'y')
              const yesOverlay = buildHoverOverlay(responderVals, responderLabel, 'x2', 'y2')

              const plotData = [
                {
                  x: nonResponderVals.map(() => nonResponderLabel),
                  y: nonResponderVals,
                  type: 'box',
                  name: 'Nonresponder',
                  marker: { color: BOX_COLOR },
                  line: { color: BOX_LINE_COLOR },
                  xaxis: 'x',
                  yaxis: 'y',
                  hoverinfo: 'skip',
                },
                {
                  x: responderVals.map(() => responderLabel),
                  y: responderVals,
                  type: 'box',
                  name: 'Responder',
                  marker: { color: BOX_COLOR },
                  line: { color: BOX_LINE_COLOR },
                  xaxis: 'x2',
                  yaxis: 'y2',
                  hoverinfo: 'skip',
                },
              ]
              if (noOverlay) plotData.push(noOverlay)
              if (yesOverlay) plotData.push(yesOverlay)

              return (
                <div key={population} id={`chart-${population}`} className="border border-slate-100 rounded-lg p-3">
                  <div className="mb-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium text-slate-700">{population}</h3>
                      <span className="text-xs text-slate-500">
                        P-Value: {popStats?.p_value != null ? popStats.p_value.toFixed(3) : 'N/A'}
                      </span>
                    </div>
                    {popStats && popStats.auc != null && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        AUC {popStats.auc.toFixed(2)}, effect size {popStats.effect_size >= 0 ? '+' : ''}
                        {popStats.effect_size.toFixed(3)}, FDR {popStats.fdr != null ? popStats.fdr.toFixed(3) : 'N/A'}
                      </p>
                    )}
                  </div>

                  <Plot
                    data={plotData}
                    layout={{
                      height: 300,
                      margin: { t: 10, b: 40, l: 40, r: 10 },
                      autosize: true,
                      hovermode: 'closest',
                      showlegend: false,
                      barmode: 'overlay',
                      hoverlabel: hoverlabelStyle,
                      xaxis: { domain: [0, 0.46], anchor: 'y', fixedrange: true },
                      xaxis2: { domain: [0.54, 1], anchor: 'y2', fixedrange: true },
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