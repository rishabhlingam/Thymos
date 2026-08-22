import SummaryTable from './components/SummaryTable'
import ResponderBoxplot from './components/ResponderBoxplot'
import BaselineSubset from './components/BaselineSubset'

function App() {
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold text-slate-800">
          Immune Cell Population Dashboard
        </h1>
        <SummaryTable />
        <ResponderBoxplot />
        <BaselineSubset />
      </div>
    </div>
  )
}

export default App