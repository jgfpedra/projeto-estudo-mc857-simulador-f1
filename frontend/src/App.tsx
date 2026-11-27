import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

const MainMenu = lazy(() => import("@/pages/main-menu").then((module) => ({ default: module.MainMenu })))
const CircuitSelection = lazy(() => import("@/pages/circuit-selection").then((module) => ({ default: module.CircuitSelection })))
const DriverTeamSelection = lazy(() => import("@/pages/driver-team-selection").then((module) => ({ default: module.DriverTeamSelection })))
const WeatherTiresSelection = lazy(() => import("@/pages/weather-tires-selection").then((module) => ({ default: module.WeatherTiresSelection })))
const RaceSimulation = lazy(() => import("@/pages/race-simulation").then((module) => ({ default: module.RaceSimulation })))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="flex min-h-svh items-center justify-center bg-background text-sm text-muted-foreground">Carregando...</div>}>
        <Routes>
          <Route path="/" element={<MainMenu />} />
          <Route path="/circuit-selection" element={<CircuitSelection />} />
          <Route path="/driver-team-selection" element={<DriverTeamSelection />} />
          <Route path="/weather-tires-selection" element={<WeatherTiresSelection />} />
          <Route path="/race-simulation/:raceId" element={<RaceSimulation />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
