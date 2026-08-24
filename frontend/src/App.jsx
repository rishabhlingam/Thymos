import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './components/Overview'
import SummaryTable from './components/SummaryTable'
import ResponderBoxplot from './components/ResponderBoxplot'
import BaselineSubset from './components/BaselineSubset'
import SamplePCA from './components/SamplePCA'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="populations" element={<SummaryTable />} />
          <Route path="responders" element={<ResponderBoxplot />} />
          <Route path="baseline" element={<BaselineSubset />} />
          <Route path="similarity" element={<SamplePCA />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App