import { create } from "zustand"

import { api, type RaceStartResponse } from "@/services/api"
import { buildRaceRequest, validateRaceSetup, type RaceSetup } from "@/helpers/race-request"

type RaceLaunchStore = {
  isSubmitting: boolean
  submitError: string | null
  /** Última corrida criada. A tela de simulação lê daqui (ou do state da navegação). */
  lastRace: RaceStartResponse | null
  startRace: (setup: RaceSetup) => Promise<RaceStartResponse | null>
  clearSubmitError: () => void
}

export const useRaceLaunchStore = create<RaceLaunchStore>()((set, get) => ({
  isSubmitting: false,
  submitError: null,
  lastRace: null,

  startRace: async (setup) => {
    if (get().isSubmitting) return null

    const validationError = validateRaceSetup(setup)
    if (validationError) {
      set({ submitError: validationError })
      return null
    }

    set({ isSubmitting: true, submitError: null })

    try {
      const race = await api.startRace(buildRaceRequest(setup))
      set({ isSubmitting: false, lastRace: race })
      return race
    } catch (error) {
      set({
        isSubmitting: false,
        submitError:
          error instanceof Error ? error.message : "Não foi possível iniciar a corrida.",
      })
      return null
    }
  },

  clearSubmitError: () => set({ submitError: null }),
}))