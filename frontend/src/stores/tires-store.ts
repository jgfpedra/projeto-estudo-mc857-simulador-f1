import { create } from "zustand"
import { persist } from "zustand/middleware"

import { useRaceLapsStore } from "@/stores/race-laps-store"
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

/** Voltas do total da corrida ainda não atribuídas, ignorando opcionalmente um stint. */
export function getRemainingStintLaps(
  stints: TireStint[],
  totalLaps: number,
  excludeId?: string,
): number {
  const used = stints.reduce(
    (sum, stint) => (stint.id === excludeId ? sum : sum + stint.laps),
    0,
  )
  return totalLaps - used
}

/** Ajusta os stints para que a soma nunca passe do total de voltas. */
function fitStints(stints: TireStint[], totalLaps: number): TireStint[] {
  let remaining = totalLaps
  const fitted: TireStint[] = []

  for (const stint of stints) {
    if (remaining < 1) break

    const laps = Math.min(Math.max(1, Math.floor(stint.laps)), remaining)
    fitted.push(laps === stint.laps ? stint : { ...stint, laps })
    remaining -= laps
  }

  return fitted
}

function normalizeStints(
  stints: TireStint[],
  fallbackCompound: TireCompound,
  totalLaps: number,
): TireStint[] {
  const fitted = fitStints(stints, totalLaps)

  return fitted.length > 0
    ? fitted
    : [createStint(fallbackCompound, Math.min(DEFAULT_STINT_LAPS, totalLaps))]
}

export function isTireConfigValid(config: TireConfig, totalLaps: number): boolean {
  if (!config.strategy.enabled) return true

  const { stints } = config.strategy
  if (stints.length === 0) return false

  const everyStintValid = stints.every(
    (stint) => Number.isInteger(stint.laps) && stint.laps >= 1,
  )

  return everyStintValid && getRemainingStintLaps(stints, totalLaps) >= 0
}

type TiresStore = {
  config: TireConfig
  setInitialCompound: (compound: TireCompound) => void
  setStrategyEnabled: (enabled: boolean) => void
  addStint: () => void
  removeStint: (id: string) => void
  updateStintCompound: (id: string, compound: TireCompound) => void
  updateStintLaps: (id: string, laps: number) => void
  syncWithRaceLaps: () => void
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
          const totalLaps = useRaceLapsStore.getState().totalLaps

          return {
            config: {
              ...state.config,
              strategy: {
                enabled,
                stints: normalizeStints(strategy.stints, initialCompound, totalLaps),
              },
            },
          }
        }),

      addStint: () =>
        set((state) => {
          const { stints } = state.config.strategy
          const totalLaps = useRaceLapsStore.getState().totalLaps

          if (stints.length >= MAX_STINTS) return state

          const remaining = getRemainingStintLaps(stints, totalLaps)
          if (remaining < 1) return state

          const lastCompound =
            stints[stints.length - 1]?.compound ?? state.config.initialCompound

          return {
            config: {
              ...state.config,
              strategy: {
                ...state.config.strategy,
                stints: [
                  ...stints,
                  createStint(lastCompound, Math.min(DEFAULT_STINT_LAPS, remaining)),
                ],
              },
            },
          }
        }),

      removeStint: (id) =>
        set((state) => {
          const { stints } = state.config.strategy
          const index = stints.findIndex((stint) => stint.id === id)

          // O primeiro stint é o pneu escolhido na largada: não pode ser removido.
          if (index <= 0 || stints.length <= 1) return state

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
        set((state) => {
          const { stints } = state.config.strategy
          const totalLaps = useRaceLapsStore.getState().totalLaps
          const stint = stints.find((item) => item.id === id)
          if (!stint) return state

          const max = getRemainingStintLaps(stints, totalLaps, id)
          const safeLaps = Number.isFinite(laps) ? Math.floor(laps) : 1
          const nextLaps = Math.max(1, Math.min(safeLaps, max))

          return {
            config: {
              ...state.config,
              strategy: {
                ...state.config.strategy,
                stints: stints.map((item) =>
                  item.id === id ? { ...item, laps: nextLaps } : item,
                ),
              },
            },
          }
        }),

      // Chamada quando o total de voltas muda, para os stints acompanharem o novo limite.
      syncWithRaceLaps: () =>
        set((state) => {
          const { stints } = state.config.strategy
          const totalLaps = useRaceLapsStore.getState().totalLaps
          const next = normalizeStints(stints, state.config.initialCompound, totalLaps)

          const unchanged =
            next.length === stints.length && next.every((stint, i) => stint === stints[i])
          if (unchanged) return state

          return {
            config: {
              ...state.config,
              strategy: { ...state.config.strategy, stints: next },
            },
          }
        }),

      resetTires: () => set({ config: createDefaultTireConfig() }),
    }),
    {
      name: "f1-simulator-tires",
      partialize: (state) => ({ config: state.config }),
    },
  ),
)