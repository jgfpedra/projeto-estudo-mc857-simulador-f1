/** Contrato HTTP do backend (snake_case). Só services/api.ts e lib/ usam estes tipos. */

export type ApiCountry = { name: string | null; code: string | null }

export type ApiLayout = {
  id: string
  years: string[]
  first_year: number | null
  last_year: number | null
  length_km: number | null
  turns: number | null
  svg: Record<string, string | null>
  is_current: boolean
  simulable: boolean
}

export type ApiCircuit = {
  id: string
  name: string | null
  full_name: string | null
  city: string | null
  country: ApiCountry
  svg: Record<string, string | null> | null
  current_layout_id: string | null
  simulable: boolean
  layouts: ApiLayout[]
}

export type ApiDriver = {
  id: string
  name: string | null
  abbreviation: string | null
  number: number | null
  team: string | null
  team_id: string | null
  country: ApiCountry
}

export type ApiWeather = "dry" | "cloudy" | "light_rain" | "rain" | "heavy_rain"
export type ApiTyre = "soft" | "medium" | "hard" | "intermediate" | "wet"

export type ApiRaceRequest = {
  circuit: { id: string; layout_id?: string }
  year: number
  laps: number
  grid: string[]
  weather: ApiWeather
  weather_change?: {
    probability_per_lap: number // CONFIRMAR unidade
    possible: ApiWeather[] // CONFIRMAR: 5 climas ou os 4 do motor
  }
  initial_tyre?: ApiTyre
  stints?: { compound: ApiTyre; laps: number }[]
}

export type ApiRaceResponse = {
  race_id: string
  ws_path: string
  grid: string[]
  initial_weather: ApiWeather
  warnings: string[]
}