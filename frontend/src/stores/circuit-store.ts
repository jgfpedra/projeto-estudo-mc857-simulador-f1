import { create } from "zustand"
import { persist } from "zustand/middleware"

import { api } from "@/services/api"
import { CURRENT_LAYOUT_ID, type Circuit } from "@/types/circuit"

type CircuitStore = {
  circuits: Circuit[]
  selectedCircuitId: string | null
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
      selectedLayoutId: CURRENT_LAYOUT_ID,
      isLoading: false,
      error: null,

      fetchCircuits: async () => {
        if (get().circuits.length > 0 || get().isLoading) return
        set({ isLoading: true, error: null })
        try {
          const circuits = await api.getCircuits()

          // Revalida a seleção persistida: se o circuito salvo não
          // existir mais na API (ou for de outra fonte), cai no primeiro.
          const persistedId = get().selectedCircuitId
          const persistedExists =
            persistedId != null &&
            circuits.some((circuit) => circuit.id === persistedId)
          const first = circuits[0]

          set({
            circuits,
            selectedCircuitId: persistedExists
              ? persistedId
              : (first?.id ?? null),
            selectedLayoutId: get().selectedLayoutId ?? CURRENT_LAYOUT_ID,
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
        const circuit = get().circuits.find((item) => item.id === circuitId)
        if (!circuit) return
        set({ selectedCircuitId: circuitId, selectedLayoutId: CURRENT_LAYOUT_ID })
      },

      selectLayout: (layoutId) => set({ selectedLayoutId: layoutId }),

      reset: () => set({ selectedCircuitId: null, selectedLayoutId: null }),
    }),
    {
      name: "f1-simulator-circuits",
      // A lista de circuitos vem da API e é revalidada a cada load;
      // só as seleções são persistidas.
      partialize: (state) => ({
        selectedCircuitId: state.selectedCircuitId,
        selectedLayoutId: state.selectedLayoutId,
      }),
    },
  ),
)