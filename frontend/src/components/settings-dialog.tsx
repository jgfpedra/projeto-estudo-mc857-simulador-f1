import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { Separator } from "@/components/ui/separator"

import { useSettingsStore } from "@/stores/settings-store"

type SettingsDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SettingsDialog({
  open,
  onOpenChange,
}: SettingsDialogProps) {
  const settings = useSettingsStore((state) => state.settings)
  const updateSetting = useSettingsStore(
    (state) => state.updateSetting,
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-zinc-800 bg-zinc-950 text-white sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-2xl font-black uppercase tracking-wider">
            Configurações
          </DialogTitle>

          <DialogDescription className="text-zinc-400">
            Ajuste sua experiência antes de entrar na pista.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-8 py-4">
          <section className="space-y-5">
            <div>
              <h2 className="text-lg font-bold uppercase tracking-wide">
                Áudio
              </h2>

              <p className="text-sm text-zinc-500">
                Controle o volume da experiência.
              </p>
            </div>

            <div className="space-y-6">
              <VolumeControl
                label="Volume geral"
                value={settings.masterVolume}
                onChange={(value) =>
                  updateSetting("masterVolume", value)
                }
              />

              <VolumeControl
                label="Efeitos sonoros"
                value={settings.sfxVolume}
                onChange={(value) =>
                  updateSetting("sfxVolume", value)
                }
              />

              <VolumeControl
                label="Música"
                value={settings.musicVolume}
                onChange={(value) =>
                  updateSetting("musicVolume", value)
                }
              />
            </div>
          </section>

          <Separator className="bg-zinc-800" />

          <section className="space-y-5">
            <div>
              <h2 className="text-lg font-bold uppercase tracking-wide">
                Vídeo
              </h2>

              <p className="text-sm text-zinc-500">
                Configure a qualidade visual da simulação.
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Resolução</Label>

                <Select
                  value={settings.resolution}
                  onValueChange={(value) =>
                    updateSetting("resolution", value)
                  }
                >
                  <SelectTrigger className="border-zinc-700 bg-zinc-900">
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="1280x720">
                      1280 × 720
                    </SelectItem>

                    <SelectItem value="1600x900">
                      1600 × 900
                    </SelectItem>

                    <SelectItem value="1920x1080">
                      1920 × 1080
                    </SelectItem>

                    <SelectItem value="2560x1440">
                      2560 × 1440
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Qualidade gráfica</Label>

                <Select
                  value={settings.graphicsQuality}
                  onValueChange={(value) =>
                    updateSetting("graphicsQuality", value)
                  }
                >
                  <SelectTrigger className="border-zinc-700 bg-zinc-900">
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="low">Baixa</SelectItem>
                    <SelectItem value="medium">Média</SelectItem>
                    <SelectItem value="high">Alta</SelectItem>
                    <SelectItem value="ultra">Ultra</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}

type VolumeControlProps = {
  label: string
  value: number
  onChange: (value: number) => void
}

function VolumeControl({
  label,
  value,
  onChange,
}: VolumeControlProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>

        <span className="font-mono text-sm text-zinc-400">
          {value}%
        </span>
      </div>

      <Slider
        value={[value]}
        max={100}
        step={1}
        onValueChange={([newValue]) => onChange(newValue)}
      />
    </div>
  )
}
