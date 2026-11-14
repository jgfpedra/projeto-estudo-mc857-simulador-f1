import { MAX_RACE_LAPS, MIN_RACE_LAPS } from "@/stores/race-laps-store"
import type { ApiRaceRequest, ApiTyre } from "@/types/api"
import type { TireCompound, TireConfig } from "@/types/tires"
import type { WeatherConfig } from "@/types/weather"

const GRID_SIZE = 20

const TYRE: Record<TireCompound, ApiTyre> = {
  SOFT: "soft",
  MEDIUM: "medium",
  HARD: "hard",
  INTERMEDIATE: "intermediate",
  WET: "wet",
}

/** Estado da tela de clima e pneus, já com o layout resolvido. */
export type RaceSetup = {
  circuitId: string
  season: number
  layoutId: string
  laps: number
  grid: string[]
  weather: WeatherConfig
  tires: TireConfig
}

/** Converte a probabilidade da UI (0–100) para o formato do backend. Ajustar após confirmar a unidade. */
function toPerLapProbability(percent: number): number {
  return percent / 100
}

/** Mensagem do primeiro problema encontrado, ou null se estiver válido. */
export function validateRaceSetup(setup: RaceSetup): string | null {
  if (setup.grid.length !== GRID_SIZE) {
    return `O grid precisa ter ${GRID_SIZE} pilotos.`
  }
  if (new Set(setup.grid).size !== setup.grid.length) {
    return "O grid contém pilotos repetidos."
  }
  if (!Number.isInteger(setup.laps) || setup.laps < MIN_RACE_LAPS || setup.laps > MAX_RACE_LAPS) {
    return `O número de voltas precisa estar entre ${MIN_RACE_LAPS} e ${MAX_RACE_LAPS}.`
  }
  if (setup.weather.transition.enabled && setup.weather.transition.possibleConditions.length === 0) {
    return "Selecione ao menos uma condição de mudança de clima."
  }
  if (setup.tires.strategy.enabled) {
    const planned = setup.tires.strategy.stints.reduce((sum, stint) => sum + stint.laps, 0)
    if (planned !== setup.laps) {
      return `Os stints precisam somar ${setup.laps} voltas (hoje somam ${planned}).`
    }
  }
  return null
}

export function buildRaceRequest(setup: RaceSetup): ApiRaceRequest {
  const request: ApiRaceRequest = {
    circuit: { id: setup.circuitId, layout_id: setup.layoutId },
    year: setup.season,
    laps: setup.laps,
    grid: setup.grid,
    weather: setup.weather.weather,
    // O 1º stint é o pneu inicial: o backend exige que os dois batam, e a UI já mantém isso.
    initial_tyre: TYRE[setup.tires.initialCompound],
  }

  const { transition } = setup.weather
  if (transition.enabled) {
    request.weather_change = {
      probability_per_lap: toPerLapProbability(transition.probability),
      possible: transition.possibleConditions,
    }
  }

  if (setup.tires.strategy.enabled) {
    request.stints = setup.tires.strategy.stints.map((stint) => ({
      compound: TYRE[stint.compound],
      laps: stint.laps,
    }))
  }

  return request
}