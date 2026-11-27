import React, { lazy, Suspense } from 'react'
import ReactDOM from 'react-dom/client'

const App = lazy(() => import('./App'))
const LiveRace = lazy(() => import('./live/LiveRace').then((module) => ({ default: module.LiveRace })))

const root = document.getElementById('root')
if (!root) throw new Error('#root not found in index.html')

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#15151e', color: '#d8d8e0' }}>Carregando visualização…</div>}>
      {new URLSearchParams(location.search).has('live') || new URLSearchParams(location.search).has('race') ? <LiveRace /> : <App />}
    </Suspense>
  </React.StrictMode>,
)
