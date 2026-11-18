import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { MainMenu } from "@/pages/main-menu"
import { CircuitSelection } from "@/pages/circuit-selection"
import { DriverTeamSelection } from "./pages/driver-team-selection"
import { WeatherTiresSelection } from "./pages/weather-tires-selection"

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
          path="/driver-team-selection"
          element={<DriverTeamSelection />}
        />

        <Route
          path="/weather-tires-selection"
          element={<WeatherTiresSelection />}
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}
