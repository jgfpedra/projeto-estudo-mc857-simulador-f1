import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { TireCompound, TireConfig, TireStint } from "@/types/tires"

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

// Função em vez de constante: cada reset gera IDs de stint novos.
export const createDefaultTireConfig = (): TireConfig => ({
  initialCompound: "MEDIUM",
  strategy: {
    enabled: false,
    stints: [createStint("MEDIUM")],
  },
})

export function isTireConfigValid(config: TireConfig): boolean {
  if (!config.strategy.enabled) return true

  const { stints } = config.strategy
  return (
    stints.length > 0 &&
    stints.every((stint) => Number.isInteger(stint.laps) && stint.laps >= 1)
  )
}

type TiresStore = {
  config: TireConfig
  setInitialCompound: (compound: TireCompound) => void
  setStrategyEnabled: (enabled: boolean) => void
  addStint: () => void
  removeStint: (id: string) => void
  updateStintCompound: (id: string, compound: TireCompound) => void
  updateStintLaps: (id: string, laps: number) => void
  resetTires: () => void
}

export const useTiresStore = create<TiresStore>()(
  persist(
    (set) => ({
      config: createDefaultTireConfig(),

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

          const lastCompound =
            stints[stints.length - 1]?.compound ?? state.config.initialCompound

          return {
            config: {
              ...state.config,
              strategy: {
                ...state.config.strategy,
                stints: [...stints, createStint(lastCompound)],
              },
            },
          }
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

      resetTires: () => set({ config: createDefaultTireConfig() }),
    }),
    {
      name: "f1-simulator-tires",
      partialize: (state) => ({ config: state.config }),
    },
  ),
)