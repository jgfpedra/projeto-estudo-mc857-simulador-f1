export const WEATHER_CONDITIONS = [
  "dry",
  "cloudy",
  "light_rain",
  "rain",
  "heavy_rain",
] as const

export type WeatherCondition = (typeof WEATHER_CONDITIONS)[number]

export const TIRE_COMPOUNDS = [
  "SOFT",
  "MEDIUM",
  "HARD",
  "INTERMEDIATE",
  "WET",
] as const

export type TireCompound = (typeof TIRE_COMPOUNDS)[number]

export const WEATHER_LABELS: Record<WeatherCondition, string> = {
  dry: "Seco",
  cloudy: "Nublado",
  light_rain: "Chuva fraca",
  rain: "Chuva",
  heavy_rain: "Chuva forte",
}

export const TIRE_LABELS: Record<TireCompound, string> = {
  SOFT: "Macio",
  MEDIUM: "Médio",
  HARD: "Duro",
  INTERMEDIATE: "Intermediário",
  WET: "Chuva",
}

export type WeatherTransitionConfig = {
  enabled: boolean
  /** Probabilidade (0–100) de o clima mudar durante a corrida. */
  probability: number
  /** Condições possíveis para as quais o clima pode transitar. */
  possibleConditions: WeatherCondition[]
}

export type TireStint = {
  id: string
  compound: TireCompound
  /** Número de voltas planejadas para o stint. */
  laps: number
}

export type StrategyConfig = {
  enabled: boolean
  stints: TireStint[]
}

export type WeatherTiresConfig = {
  weather: WeatherCondition
  transition: WeatherTransitionConfig
  initialCompound: TireCompound
  strategy: StrategyConfig
}

/** Payload completo enviado ao backend ao iniciar a corrida. */
export type RaceSetupPayload = {
  season: string
  circuitId: string
  layoutId: string
  /** IDs dos pilotos na ordem do grid de largada (posição 1 primeiro). */
  grid: string[]
  config: WeatherTiresConfig
}