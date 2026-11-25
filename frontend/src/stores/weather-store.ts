import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { WeatherCondition, WeatherConfig } from "@/types/weather"

export const DEFAULT_WEATHER_CONFIG: WeatherConfig = {
  weather: "dry",
  transition: {
    enabled: false,
    probability: 20,
    possibleConditions: ["cloudy"],
  },
}

export function isWeatherConfigValid(config: WeatherConfig): boolean {
  return !config.transition.enabled || config.transition.possibleConditions.length > 0
}

type WeatherStore = {
  config: WeatherConfig
  setWeather: (weather: WeatherCondition) => void
  setTransitionEnabled: (enabled: boolean) => void
  setTransitionProbability: (probability: number) => void
  toggleTransitionCondition: (condition: WeatherCondition) => void
  resetWeather: () => void
}

export const useWeatherStore = create<WeatherStore>()(
  persist(
    (set) => ({
      config: DEFAULT_WEATHER_CONFIG,

      setWeather: (weather) =>
        set((state) => ({
          config: { ...state.config, weather },
        })),

      setTransitionEnabled: (enabled) =>
        set((state) => ({
          config: {
            ...state.config,
            transition: { ...state.config.transition, enabled },
          },
        })),

      setTransitionProbability: (probability) =>
        set((state) => ({
          config: {
            ...state.config,
            transition: {
              ...state.config.transition,
              probability: Math.min(100, Math.max(0, Math.round(probability))),
            },
          },
        })),

      toggleTransitionCondition: (condition) =>
        set((state) => {
          const current = state.config.transition.possibleConditions
          const possibleConditions = current.includes(condition)
            ? current.filter((item) => item !== condition)
            : [...current, condition]

          return {
            config: {
              ...state.config,
              transition: { ...state.config.transition, possibleConditions },
            },
          }
        }),

      resetWeather: () => set({ config: DEFAULT_WEATHER_CONFIG }),
    }),
    {
      name: "f1-simulator-weather",
      partialize: (state) => ({ config: state.config }),
    },
  ),
)