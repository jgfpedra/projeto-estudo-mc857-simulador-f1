import { create } from "zustand"
import { persist } from "zustand/middleware"

export const MIN_RACE_LAPS = 1
export const MAX_RACE_LAPS = 200
export const DEFAULT_RACE_LAPS = 50

/** Garante um inteiro dentro do intervalo permitido. Valores inválidos viram o padrão. */
export function clampRaceLaps(laps: number): number {
  if (!Number.isFinite(laps)) return DEFAULT_RACE_LAPS
  return Math.min(MAX_RACE_LAPS, Math.max(MIN_RACE_LAPS, Math.floor(laps)))
}

type RaceLapsStore = {
  totalLaps: number
  setTotalLaps: (laps: number) => void
  resetTotalLaps: () => void
}

export const useRaceLapsStore = create<RaceLapsStore>()(
  persist(
    (set) => ({
      totalLaps: DEFAULT_RACE_LAPS,
      setTotalLaps: (laps) => set({ totalLaps: clampRaceLaps(laps) }),
      resetTotalLaps: () => set({ totalLaps: DEFAULT_RACE_LAPS }),
    }),
    {
      name: "f1-simulator-race-laps",
      partialize: (state) => ({ totalLaps: state.totalLaps }),
    },
  ),
)