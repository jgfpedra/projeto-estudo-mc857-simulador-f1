import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { MainMenu } from "@/pages/main-menu"
import { CircuitSelection } from "@/pages/circuit-selection"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainMenu />} />

        <Route
          path="/circuit-selection"
          element={<CircuitSelection />}
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}
