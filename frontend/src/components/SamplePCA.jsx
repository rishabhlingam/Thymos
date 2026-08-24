import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import FilterBar from './FilterBar'
import Breadcrumb from './Breadcrumb'
import ExplainerBox from './ExplainerBox'
import { useApiData } from '../hooks/useApiData'

const COLOR_OPTIONS = [
  { key: 'response', label: 'Response' },
  { key: 'sex', label: 'Sex' },
  { key: 'project_id', label: 'Project' },
]

const PALETTE = ['#0ea5e9', '#e8574a', '#8983c7', '#22c55e', '#f59e0b', '#64748b']

function SamplePCA() {
  const [filters, setFilters] = useState({
    condition: 'melanoma',
    treatment: 'miraclib',
    sample_type: 'PBMC',
  })
  const [colorBy, setColorBy] = useState('response')

  const { data, loading, error } = useApiData('/api/pca', filters)

  const points = data?.points ?? []
  const varianceExplained = data?.variance_explained ?? [0, 0]
  const loadings = data?.loadings ?? []

  const maxLoading = loadings.length
    ? Math.max(0.1, ...loadings.flatMap((l) => [Math.abs(l.pc1_loading), Math.abs(l.pc2_loading)]))
    : 0.1
  const loadingRange = [-maxLoading * 1.3, maxLoading * 1.3]

  const loadingTraces = loadings.map((l, i) => ({
    x: [0, l.pc1_loading],
    y: [0, l.pc2_loading],
    mode: 'lines+markers+text',
    type: 'scatter',
    text: ['', l.population],
    textposition: 'top center',
    textfont: { size: 11, color: '#1e293b' },
    line: { color: PALETTE[i % PALETTE.length], width: 2 },
    marker: { size: [0, 6], color: PALETTE[i % PALETTE.length] },
    hovertemplate:
      `${l.population}<br>PC1 loading: ${l.pc1_loading.toFixed(3)}<br>PC2 loading: ${l.pc2_loading.toFixed(3)}<extra></extra>`,
    showlegend: false,
  }))

  const groups = useMemo(() => {
    const map = new Map()
    points.forEach((p) => {
      const key = p[colorBy] ?? 'Unknown'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(p)
    })
    return map
  }, [points, colorBy])

  const traces = [...groups.entries()].map(([key, groupPoints], i) => ({
    x: groupPoints.map((p) => p.pc1),
    y: groupPoints.map((p) => p.pc2),
    text: groupPoints.map((p) => p.sample),
    mode: 'markers',
    type: 'scatter',
    name: String(key),
    marker: { color: PALETTE[i % PALETTE.length], size: 6, opacity: 0.7 },
    hovertemplate: '%{text}<extra>' + key + '</extra>',
  }))

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { label: 'View', value: 'Sample Similarity' },
          { label: 'Color By', value: COLOR_OPTIONS.find((o) => o.key === colorBy)?.label },
        ]}
      />

      <FilterBar filters={filters} onChange={setFilters} excludeTreatments={['none']} />

      <ExplainerBox title="What am I looking at?">
        <p>
          Each point is one sample, projected from its five population percentages
          down to two dimensions using PCA. Samples with similar immune profiles sit
          closer together. Since the five percentages always sum to 100, only four
          are truly independent, so PC1 and PC2 here capture the two strongest
          patterns of variation without needing all five dimensions to plot.
        </p>
        <p>
          If responders and non-responders formed distinct clusters here, that would
          suggest immune profile alone could reliably separate the two groups. In
          this dataset they overlap heavily, consistent with the weak individual
          predictive power already found in the Responder Analysis tab.
        </p>
      </ExplainerBox>

      <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Sample Similarity Map</h2>
            <p className="text-sm text-slate-500">
              {filters.condition}, {filters.sample_type} samples, {filters.treatment} treated patients
            </p>
          </div>
          <div>
            <label className="block text-[10px] font-semibold tracking-wider text-slate-400 uppercase mb-1">
              Color by
            </label>
            <select
              className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700"
              value={colorBy}
              onChange={(e) => setColorBy(e.target.value)}
            >
              {COLOR_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-red-600">Error, {error}</p>}
        {loading && !error && <div className="h-96 bg-slate-100 rounded-lg animate-pulse" />}

        {!loading && !error && points.length === 0 && (
          <p className="text-slate-500">No data available for this filter combination.</p>
        )}

        {!loading && !error && points.length > 0 && (
          <Plot
            data={traces}
            layout={{
              height: 500,
              margin: { t: 10, b: 50, l: 60, r: 20 },
              hovermode: 'closest',
              xaxis: { title: `PC1 (${(varianceExplained[0] * 100).toFixed(1)}% variance)`, zeroline: true },
              yaxis: { title: `PC2 (${(varianceExplained[1] * 100).toFixed(1)}% variance)`, zeroline: true },
              legend: { orientation: 'h', y: -0.2 },
            }}
            useResizeHandler
            style={{ width: '100%', height: '500px' }}
            config={{ displayModeBar: 'hover', scrollZoom: true }}
          />
        )}
      </div>

      {!loading && !error && loadings.length > 0 && (
        <div className="bg-white shadow rounded-xl border border-slate-200 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Key Drivers</h2>
            <p className="text-sm text-slate-500">
              How much and in which direction each population contributes to PC1 and PC2
            </p>
          </div>
          <Plot
            data={loadingTraces}
            layout={{
              height: 450,
              margin: { t: 20, b: 50, l: 60, r: 20 },
              hovermode: 'closest',
              xaxis: {
                title: `PC1 (${(varianceExplained[0] * 100).toFixed(1)}% variance)`,
                range: loadingRange,
                zeroline: true,
              },
              yaxis: {
                title: `PC2 (${(varianceExplained[1] * 100).toFixed(1)}% variance)`,
                range: loadingRange,
                zeroline: true,
              },
            }}
            useResizeHandler
            style={{ width: '100%', height: '450px' }}
            config={{ displayModeBar: 'hover', scrollZoom: true }}
          />
        </div>
      )}
    </div>
  )
}

export default SamplePCA