import { create } from "zustand"

import { api } from "@/services/api"
import type { RaceSetupPayload } from "@/types/race-setup"

type RaceLaunchStore = {
  isSubmitting: boolean
  submitError: string | null
  startRace: (payload: RaceSetupPayload) => Promise<boolean>
  clearSubmitError: () => void
}

export const useRaceLaunchStore = create<RaceLaunchStore>()((set, get) => ({
  isSubmitting: false,
  submitError: null,

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

  clearSubmitError: () => set({ submitError: null }),
}))