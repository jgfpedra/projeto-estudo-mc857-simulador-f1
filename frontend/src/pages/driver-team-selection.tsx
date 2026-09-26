import { useMemo, useState } from "react"
import { ArrowLeft, Check, Dices, Users } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { GridSlot, type GridSlotValue } from "@/components/grid-slot"
import { NULL_DRIVER_ID, pilots } from "@/data/pilots"

type Mode = "custom" | "random"

const createEmptyGrid = (): GridSlotValue[] =>
  Array.from({ length: 20 }, (_, index) => ({
    position: index + 1,
    driverId: NULL_DRIVER_ID,
  }))

function shuffle<T>(items: T[]) {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export function DriverTeamSelection() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>("custom")
  const [grid, setGrid] = useState<GridSlotValue[]>(createEmptyGrid)

  const selectedDriverIds = useMemo(
    () =>
      new Set(
        grid
          .map((slot) => slot.driverId)
          .filter((driverId) => driverId !== NULL_DRIVER_ID),
      ),
    [grid],
  )

  const selectedCount = selectedDriverIds.size
  const isComplete = selectedCount === 20

  const updateSlot = (position: number, driverId: string) => {
    setGrid((current) =>
      current.map((slot) =>
        slot.position === position ? { ...slot, driverId } : slot,
      ),
    )
  }

  const generateRandomGrid = () => {
    setGrid(
      shuffle(pilots).map((pilot, index) => ({
        position: index + 1,
        driverId: pilot.id,
      })),
    )
  }

  const handleModeChange = (nextMode: Mode) => {
    setMode(nextMode)
    if (nextMode === "random") {
      generateRandomGrid()
    } else {
      setGrid(createEmptyGrid())
    }
  }

  const handleConfirm = () => {
    if (!isComplete) return
    navigate("/weather-tires")
  }

  return (
    <main className="relative min-h-svh bg-background text-foreground lg:h-svh lg:overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_42%,rgba(220,38,38,0.12),transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(0,0,0,0.28)_100%)]" />
      </div>
      <div className="absolute left-0 top-0 h-1 w-full bg-primary" />

      <div className="relative z-10 flex min-h-svh flex-col lg:h-svh">
        <header className="shrink-0 border-b border-border">
          <div className="container mx-auto px-6 py-6 lg:px-12 lg:py-7">
            <div className="flex items-center gap-5">
              <Button
                variant="outline"
                onClick={() => navigate("/circuit-selection")}
                aria-label="Voltar para seleção de circuito"
                className="h-11 w-11 shrink-0 rounded-none border-border bg-transparent p-0 hover:bg-accent sm:w-auto sm:px-4"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>

              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-3">
                  <div className="h-1 w-10 bg-primary" />
                  <span className="text-xs font-bold uppercase tracking-[0.3em] text-primary">
                    F1 SIMULATOR
                  </span>
                </div>
                <h1 className="text-3xl font-black uppercase italic tracking-tighter sm:text-5xl">
                  Pilotos & Equipes
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Defina os 20 pilotos e a ordem do grid de largada.
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="container mx-auto flex min-h-0 flex-1 px-6 py-5 lg:px-12 lg:py-7">
          <section className="flex min-h-0 flex-1 flex-col overflow-hidden border border-border bg-card/40">
            <div className="flex shrink-0 flex-col gap-4 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between lg:p-5">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
                  Configuração do grid
                </span>
                <h2 className="mt-1 text-xl font-black uppercase italic">
                  {mode === "custom" ? "Modo personalizado" : "Grid aleatório"}
                </h2>
              </div>

              <div className="grid grid-cols-2 border border-border bg-background">
                <button
                  type="button"
                  onClick={() => handleModeChange("custom")}
                  className={[
                    "flex h-11 items-center justify-center gap-2 px-4 text-xs font-black uppercase tracking-wider transition-colors",
                    mode === "custom"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  ].join(" ")}
                >
                  <Users className="h-4 w-4" />
                  Personalizado
                </button>
                <button
                  type="button"
                  onClick={() => handleModeChange("random")}
                  className={[
                    "flex h-11 items-center justify-center gap-2 border-l border-border px-4 text-xs font-black uppercase tracking-wider transition-colors",
                    mode === "random"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  ].join(" ")}
                >
                  <Dices className="h-4 w-4" />
                  Aleatório
                </button>
              </div>
            </div>

            {mode === "random" && (
              <div className="flex shrink-0 items-center justify-between border-b border-border bg-primary/5 px-5 py-3">
                <p className="text-xs text-muted-foreground">
                  Os 20 pilotos são embaralhados automaticamente. Cada piloto permanece vinculado à sua equipe original.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={generateRandomGrid}
                  className="ml-4 shrink-0 rounded-none border-border bg-transparent uppercase"
                >
                  <Dices className="mr-2 h-4 w-4" />
                  Sortear novamente
                </Button>
              </div>
            )}

            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 xl:grid-cols-3">
                {grid.map((slot) => (
                  <GridSlot
                    key={slot.position}
                    slot={slot}
                    drivers={pilots}
                    selectedDriverIds={selectedDriverIds}
                    disabled={mode === "random"}
                    onSelect={updateSlot}
                  />
                ))}
              </div>
            </div>

            <div className="flex shrink-0 flex-col gap-3 border-t border-border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={[
                    "flex h-8 w-8 items-center justify-center",
                    isComplete ? "bg-primary text-primary-foreground" : "bg-secondary",
                  ].join(" ")}
                >
                  {isComplete ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="text-xs font-black">{selectedCount}/20</span>
                  )}
                </div>
                <div>
                  <div className="text-xs font-black uppercase">
                    {isComplete ? "Grid completo" : "Grid incompleto"}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {selectedCount} pilotos selecionados · 20 necessários
                  </div>
                </div>
              </div>

              <Button
                onClick={handleConfirm}
                disabled={!isComplete}
                size="lg"
                className="h-12 w-full rounded-none px-8 font-black uppercase tracking-wider sm:w-auto"
              >
                Clima / Pneus
                <span className="ml-3 text-lg">→</span>
              </Button>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
