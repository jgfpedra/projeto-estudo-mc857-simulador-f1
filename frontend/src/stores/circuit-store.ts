import { create } from "zustand"
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

export const useCircuitStore = create<CircuitStore>((set, get) => ({
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
      const first = circuits[0]
      set({
        circuits,
        selectedCircuitId: get().selectedCircuitId ?? first?.id ?? null,
        selectedLayoutId: get().selectedLayoutId ?? CURRENT_LAYOUT_ID,
        isLoading: false,
      })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Não foi possível carregar os circuitos.", isLoading: false })
    }
  },

  selectCircuit: (circuitId) => {
    const circuit = get().circuits.find((item) => item.id === circuitId)
    if (!circuit) return
    set({ selectedCircuitId: circuitId, selectedLayoutId: CURRENT_LAYOUT_ID })
  },

  selectLayout: (layoutId) => set({ selectedLayoutId: layoutId }),
  reset: () => set({ selectedCircuitId: null, selectedLayoutId: null }),
}))
