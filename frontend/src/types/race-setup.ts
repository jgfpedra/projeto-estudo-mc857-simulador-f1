import type { TireConfig } from "@/types/tires"
import type { WeatherConfig } from "@/types/weather"

/** Payload completo enviado ao backend ao iniciar a corrida. */
export type RaceSetupPayload = {
  season: string
  circuitId: string
  layoutId: string
  /** IDs dos pilotos na ordem do grid de largada (posição 1 primeiro). */
  grid: string[]
  weather: WeatherConfig
  tires: TireConfig
}