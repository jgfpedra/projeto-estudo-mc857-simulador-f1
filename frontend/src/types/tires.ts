export const TIRE_COMPOUNDS = [
  "SOFT",
  "MEDIUM",
  "HARD",
  "INTERMEDIATE",
  "WET",
] as const

export type TireCompound = (typeof TIRE_COMPOUNDS)[number]

export const TIRE_LABELS: Record<TireCompound, string> = {
  SOFT: "Macio",
  MEDIUM: "Médio",
  HARD: "Duro",
  INTERMEDIATE: "Intermediário",
  WET: "Chuva",
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

export type TireConfig = {
  initialCompound: TireCompound
  strategy: StrategyConfig
}