export const WEATHER_CONDITIONS = [
  "dry",
  "cloudy",
  "light_rain",
  "rain",
  "heavy_rain",
] as const

export type WeatherCondition = (typeof WEATHER_CONDITIONS)[number]

export const WEATHER_LABELS: Record<WeatherCondition, string> = {
  dry: "Seco",
  cloudy: "Nublado",
  light_rain: "Chuva fraca",
  rain: "Chuva",
  heavy_rain: "Chuva forte",
}

export type WeatherTransitionConfig = {
  enabled: boolean
  /** Probabilidade (0–100) de o clima mudar durante a corrida. */
  probability: number
  /** Condições possíveis para as quais o clima pode transitar. */
  possibleConditions: WeatherCondition[]
}

export type WeatherConfig = {
  weather: WeatherCondition
  transition: WeatherTransitionConfig
}