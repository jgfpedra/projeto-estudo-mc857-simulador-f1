import { create } from "zustand"
import { persist } from "zustand/middleware"

import { DEFAULT_SETTINGS } from "@/data/settings"
import type { GameSettings } from "@/types/settings"

type SettingsStore = {
  settings: GameSettings
  updateSetting: <K extends keyof GameSettings>(
    key: K,
    value: GameSettings[K],
  ) => void
  resetSettings: () => void
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,

      updateSetting: (key, value) =>
        set((state) => ({
          settings: {
            ...state.settings,
            [key]: value,
          },
        })),

      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    {
      name: "f1-simulator-settings",
      // Só as configurações do jogo são persistidas; ações não fazem parte do estado salvo.
      partialize: (state) => ({ settings: state.settings }),
    },
  ),
)
