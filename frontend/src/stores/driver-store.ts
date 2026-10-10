import { create } from "zustand"

import type { Driver, DriverMode } from "@/types/driver"

type DriverStore = {
  season: string
  mode: DriverMode
  /** Lista de drivers disponíveis na temporada, recebida da API. */
  availableDrivers: Driver[]
  /** A ordem do array representa a ordem do grid; null representa uma vaga vazia. */
  drivers: (Driver | null)[]
  setSeason: (season: string) => void
  setMode: (mode: DriverMode) => void
  setAvailableDrivers: (drivers: Driver[]) => void
  setDrivers: (drivers: (Driver | null)[]) => void
  updateDriverAtPosition: (index: number, driver: Driver | null) => void
  clearGrid: () => void
  resetDriverSelection: () => void
}

const GRID_SIZE = 20
const DEFAULT_SEASON = "2025"

const createEmptyGrid = (): (Driver | null)[] =>
  Array.from({ length: GRID_SIZE }, () => null)

export const useDriverStore = create<DriverStore>((set, get) => ({
  season: DEFAULT_SEASON,
  mode: "custom",
  availableDrivers: [],
  drivers: createEmptyGrid(),

  setSeason: (season) => {
    if (season === get().season) return

    // Ao trocar de temporada, limpa o grid e os dados da temporada anterior.
    set({
      season,
      availableDrivers: [],
      drivers: createEmptyGrid(),
      mode: "custom",
    })
  },

  // A flag indica o modo selecionado; não gera nem altera o grid.
  setMode: (mode) => set({ mode }),

  // Atualiza a lista completa de drivers disponíveis na temporada.
  setAvailableDrivers: (availableDrivers) => set({ availableDrivers: [...availableDrivers] }),

  // A ordem do array recebido passa a ser a ordem do grid.
  setDrivers: (drivers) => set({ drivers: [...drivers] }),

  updateDriverAtPosition: (index, driver) => {
    set((state) => {
      if (index < 0 || index >= state.drivers.length) return state

      const nextDrivers = [...state.drivers]
      const currentDriver = nextDrivers[index]

      if (currentDriver?.id === driver?.id) return state

      // null limpa apenas a posição selecionada.
      if (driver === null) {
        nextDrivers[index] = null
        return { drivers: nextDrivers }
      }

      // Se o driver já estiver no grid, troca de posição com o atual.
      const existingIndex = nextDrivers.findIndex(
        (item, itemIndex) => item?.id === driver.id && itemIndex !== index,
      )

      nextDrivers[index] = driver

      if (existingIndex !== -1) {
        nextDrivers[existingIndex] = currentDriver ?? null
      }

      return { drivers: nextDrivers }
    })
  },

  clearGrid: () => set({ drivers: createEmptyGrid() }),

  resetDriverSelection: () =>
    set({
      season: DEFAULT_SEASON,
      mode: "custom",
      availableDrivers: [],
      drivers: createEmptyGrid(),
    }),
}))