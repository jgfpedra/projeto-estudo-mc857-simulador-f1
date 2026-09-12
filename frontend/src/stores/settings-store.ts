import { create } from "zustand"
import { persist } from "zustand/middleware"

export type GameSettings = {
  masterVolume: number
  sfxVolume: number
  musicVolume: number
  resolution: string
  graphicsQuality: string
}

type SettingsStore = {
  settings: GameSettings
  updateSetting: <K extends keyof GameSettings>(
    key: K,
    value: GameSettings[K],
  ) => void
  resetSettings: () => void
}

const defaultSettings: GameSettings = {
  masterVolume: 80,
  sfxVolume: 80,
  musicVolume: 60,
  resolution: "1920x1080",
  graphicsQuality: "high",
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: defaultSettings,

      updateSetting: (key, value) =>
        set((state) => ({
          settings: {
            ...state.settings,
            [key]: value,
          },
        })),

      resetSettings: () =>
        set({
          settings: defaultSettings,
        }),
    }),
    {
      name: "f1-simulator-settings",
    },
  ),
)
