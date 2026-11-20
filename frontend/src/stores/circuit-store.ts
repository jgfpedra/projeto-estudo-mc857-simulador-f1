import { create } from "zustand"
import { persist } from "zustand/middleware"

import { api } from "@/services/api"
import type { Circuit } from "@/types/circuit"

type CircuitStore = {
  circuits: Circuit[]
  selectedCircuitId: string | null
  /** null = layout padrão (o atual simulável). Ver resolveLayout. */
  selectedLayoutId: string | null
  isLoading: boolean
  error: string | null
  fetchCircuits: () => Promise<void>
  selectCircuit: (circuitId: string) => void
  selectLayout: (layoutId: string) => void
  reset: () => void
}

export const useCircuitStore = create<CircuitStore>()(
  persist(
    (set, get) => ({
      circuits: [],
      selectedCircuitId: null,
      selectedLayoutId: null,
      isLoading: false,
      error: null,

      fetchCircuits: async () => {
        if (get().circuits.length > 0 || get().isLoading) return
        set({ isLoading: true, error: null })

        try {
          const circuits = await api.getCircuits()

          // Se o circuito salvo não existir mais na API, cai no primeiro.
          // O layout salvo é validado depois, por resolveLayout.
          const persistedId = get().selectedCircuitId
          const exists = circuits.some((circuit) => circuit.id === persistedId)

          set({
            circuits,
            selectedCircuitId: exists ? persistedId : (circuits[0]?.id ?? null),
            isLoading: false,
          })
        } catch (error) {
          set({
            error:
              error instanceof Error
                ? error.message
                : "Não foi possível carregar os circuitos.",
            isLoading: false,
          })
        }
      },

      selectCircuit: (circuitId) => {
        if (!get().circuits.some((circuit) => circuit.id === circuitId)) return
        set({ selectedCircuitId: circuitId, selectedLayoutId: null })
      },

      selectLayout: (layoutId) => set({ selectedLayoutId: layoutId }),

      reset: () => set({ selectedCircuitId: null, selectedLayoutId: null }),
    }),
    {
      name: "f1-simulator-circuits",
      partialize: (state) => ({
        selectedCircuitId: state.selectedCircuitId,
        selectedLayoutId: state.selectedLayoutId,
      }),
    },
  ),
)