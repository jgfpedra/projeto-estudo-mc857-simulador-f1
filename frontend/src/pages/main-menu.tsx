import { useState } from "react"
import { Play, Settings, Trophy } from "lucide-react"

import { Button } from "@/components/ui/button"
import { SettingsDialog } from "@/components/settings-dialog"

export function MainMenu() {
  const [settingsOpen, setSettingsOpen] = useState(false)

  function handleStart() {
    // navigate("/circuit-selection")
  }

  return (
    <main className="relative min-h-svh overflow-hidden bg-zinc-950 text-white">
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,rgba(220,38,38,0.18),transparent_45%)]" />

        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0.2),rgba(0,0,0,0.9))]" />
      </div>

      <div className="absolute left-0 top-0 h-1 w-full bg-red-600" />

      <div className="relative z-10 flex min-h-svh items-center">
        <div className="container mx-auto px-6 py-12 lg:px-12">
          <div className="max-w-2xl">
            <div className="mb-12">
              <div className="mb-3 flex items-center gap-3">
                <div className="h-1 w-12 bg-red-600" />

                <span className="text-sm font-bold uppercase tracking-[0.35em] text-red-500">
                  Racing Simulator
                </span>
              </div>

              <h1 className="text-6xl font-black uppercase italic leading-none tracking-tighter sm:text-7xl md:text-8xl">
                F1
                <span className="block text-zinc-400">
                  Simulator
                </span>
              </h1>
            </div>

            <div className="flex w-full max-w-md flex-col gap-3">
              <Button
                onClick={handleStart}
                size="lg"
                className="group h-16 justify-between rounded-none bg-red-600 px-6 text-lg font-black uppercase tracking-wider text-white hover:bg-red-700"
              >
                <span className="flex items-center gap-3">
                  <Play className="h-5 w-5 fill-current" />
                  Iniciar
                </span>

                <span className="text-xl transition-transform group-hover:translate-x-1">
                  →
                </span>
              </Button>

              <Button
                onClick={() => setSettingsOpen(true)}
                variant="outline"
                size="lg"
                className="h-16 justify-start gap-3 rounded-none border-zinc-700 bg-zinc-950/70 px-6 text-lg font-bold uppercase tracking-wider text-zinc-200 hover:bg-zinc-900 hover:text-white"
              >
                <Settings className="h-5 w-5" />
                Configurações
              </Button>
            </div>

            <div className="mt-12 flex items-center gap-3 text-sm text-zinc-600">
              <Trophy className="h-4 w-4" />

              <span>Prepare-se para a corrida</span>
            </div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-0 right-0 hidden select-none lg:block">
        <span className="text-[18rem] font-black italic leading-none text-white/2">
          01
        </span>
      </div>

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </main>
  )
}
