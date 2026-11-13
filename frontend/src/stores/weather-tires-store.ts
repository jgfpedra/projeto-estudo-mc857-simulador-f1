import { create } from "zustand"
import { persist } from "zustand/middleware"

import { api } from "@/services/api"
import type {
  RaceSetupPayload,
  StrategyConfig,
  TireCompound,
  TireStint,
  WeatherCondition,
  WeatherTiresConfig,
} from "@/types/weather-tires"

export const MAX_STINTS = 5
export const DEFAULT_STINT_LAPS = 20

const createStint = (
  compound: TireCompound,
  laps: number = DEFAULT_STINT_LAPS,
): TireStint => ({
  id: crypto.randomUUID(),
  compound,
  laps,
})

export const DEFAULT_WEATHER_TIRES_CONFIG: WeatherTiresConfig = {
  weather: "dry",
  transition: {
    enabled: false,
    probability: 20,
    possibleConditions: ["cloudy"],
  },
  initialCompound: "MEDIUM",
  strategy: {
    enabled: false,
    stints: [createStint("MEDIUM")],
  },
}

/** Valida a configuração antes de permitir o início da corrida. */
export function isWeatherTiresConfigValid(config: WeatherTiresConfig): boolean {
  if (config.transition.enabled && config.transition.possibleConditions.length === 0) {
    return false
  }

  if (config.strategy.enabled) {
    const { stints } = config.strategy
    return (
      stints.length > 0 &&
      stints.every((stint) => Number.isInteger(stint.laps) && stint.laps >= 1)
    )
  }

  return true
}

type WeatherTiresStore = {
  config: WeatherTiresConfig
  isSubmitting: boolean
  submitError: string | null

  setWeather: (weather: WeatherCondition) => void
  setTransitionEnabled: (enabled: boolean) => void
  setTransitionProbability: (probability: number) => void
  toggleTransitionCondition: (condition: WeatherCondition) => void

  setInitialCompound: (compound: TireCompound) => void
  setStrategyEnabled: (enabled: boolean) => void
  addStint: () => void
  removeStint: (id: string) => void
  updateStintCompound: (id: string, compound: TireCompound) => void
  updateStintLaps: (id: string, laps: number) => void

  resetConfig: () => void
  startRace: (payload: RaceSetupPayload) => Promise<boolean>
}

export const useWeatherTiresStore = create<WeatherTiresStore>()(
  persist(
    (set, get) => ({
      config: DEFAULT_WEATHER_TIRES_CONFIG,
      isSubmitting: false,
      submitError: null,

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

      // O primeiro stint sempre acompanha o pneu inicial.
      setInitialCompound: (compound) =>
        set((state) => ({
          config: {
            ...state.config,
            initialCompound: compound,
            strategy: {
              ...state.config.strategy,
              stints: state.config.strategy.stints.map((stint, index) =>
                index === 0 ? { ...stint, compound } : stint,
              ),
            },
          },
        })),

      setStrategyEnabled: (enabled) =>
        set((state) => {
          const { strategy, initialCompound } = state.config
          const stints =
            strategy.stints.length > 0
              ? strategy.stints
              : [createStint(initialCompound)]

          return {
            config: {
              ...state.config,
              strategy: { enabled, stints },
            },
          }
        }),

      addStint: () =>
        set((state) => {
          const { stints } = state.config.strategy
          if (stints.length >= MAX_STINTS) return state

          const lastCompound = stints[stints.length - 1]?.compound ?? state.config.initialCompound
          const nextStrategy: StrategyConfig = {
            ...state.config.strategy,
            stints: [...stints, createStint(lastCompound)],
          }

          return { config: { ...state.config, strategy: nextStrategy } }
        }),

      removeStint: (id) =>
        set((state) => {
          const { stints } = state.config.strategy
          if (stints.length <= 1) return state

          return {
            config: {
              ...state.config,
              strategy: {
                ...state.config.strategy,
                stints: stints.filter((stint) => stint.id !== id),
              },
            },
          }
        }),

      updateStintCompound: (id, compound) =>
        set((state) => ({
          config: {
            ...state.config,
            strategy: {
              ...state.config.strategy,
              stints: state.config.strategy.stints.map((stint) =>
                stint.id === id ? { ...stint, compound } : stint,
              ),
            },
          },
        })),

      updateStintLaps: (id, laps) =>
        set((state) => ({
          config: {
            ...state.config,
            strategy: {
              ...state.config.strategy,
              stints: state.config.strategy.stints.map((stint) =>
                stint.id === id ? { ...stint, laps: Math.floor(laps) } : stint,
              ),
            },
          },
        })),

      resetConfig: () =>
        set({
          config: {
            ...DEFAULT_WEATHER_TIRES_CONFIG,
            strategy: {
              enabled: false,
              stints: [createStint(DEFAULT_WEATHER_TIRES_CONFIG.initialCompound)],
            },
          },
          submitError: null,
        }),

      startRace: async (payload) => {
        if (get().isSubmitting) return false

        set({ isSubmitting: true, submitError: null })

        try {
          await api.startRace(payload)
          set({ isSubmitting: false })
          return true
        } catch (error) {
          set({
            isSubmitting: false,
            submitError:
              error instanceof Error
                ? error.message
                : "Não foi possível iniciar a corrida.",
          })
          return false
        }
      },
    }),
    {
      name: "f1-simulator-weather-tires",
      partialize: (state) => ({ config: state.config }),
    },
  ),
)