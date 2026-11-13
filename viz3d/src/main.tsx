import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { LiveRace } from './live/LiveRace'

const root = document.getElementById('root')
if (!root) throw new Error('#root not found in index.html')

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    {new URLSearchParams(location.search).has('live') || new URLSearchParams(location.search).has('race') ? <LiveRace /> : <App />}
  </React.StrictMode>,
)
