import { useState } from "react"

import { Button } from "@/components/ui/button"
import { COMPOUND_BADGE } from "@/helpers/race-live"
import type { PitTyre } from "@/stores/live-race-store"
import type { Frame, RaceInfo } from "@/types/race"

const COMPOUNDS: { value: PitTyre; code: string; label: string }[] = [
  { value: "soft", code: "SOFT", label: "Macio" },
  { value: "medium", code: "MEDIUM", label: "Médio" },
  { value: "hard", code: "HARD", label: "Duro" },
  { value: "intermediate", code: "INTERMEDIATE", label: "Intermédio" },
  { value: "wet", code: "WET", label: "Chuva" },
]

const REQUEST_STATUS: Record<string, string> = {
  scheduled: "Pedido agendado para a próxima entrada",
  approaching: "Aproximando dos boxes",
  in_pit_lane: "Na via dos boxes",
}

type Props = {
  race: RaceInfo
  frame: Frame | null
  /** Só é possível pedir box com a corrida em andamento. */
  active: boolean
  busy: boolean
  error: string | null
  onRequest: (tyre: PitTyre) => void
  onCancel: () => void
}

/** Controle do piloto do usuário: pede ou cancela a troca de pneus nos boxes. */
export function UserPitPanel({ race, frame, active, busy, error, onRequest, onCancel }: Props) {
  const [tyre, setTyre] = useState<PitTyre>("hard")

  const info = race.drivers.find((d) => d.driverId === race.userDriverId)
  const car = frame?.cars.find((c) => c.driverId === race.userDriverId) ?? null
  if (!info) return null

  const request = car?.pitRequest ?? null
  const inPitLane = request?.status === "in_pit_lane"
  const canRequest = active && car !== null && request === null && !car.pitting && !busy
  const canCancel = active && request !== null && !inPitLane && !busy
  const currentBadge = car ? COMPOUND_BADGE[car.tyre] : undefined

  return (
    <section className="shrink-0 border border-border bg-card/40 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Meu piloto</div>
          <div className="truncate text-sm font-black uppercase">{info.abbreviation} · {info.name}</div>
        </div>
        {car && (
          <div className="shrink-0 text-right text-xs font-bold tabular-nums">
            <div>P{car.position}</div>
            <div className="flex items-center justify-end gap-1 text-muted-foreground">
              {currentBadge && (
                <span className={`flex h-4 w-4 items-center justify-center text-[9px] font-black ${currentBadge.className}`}>
                  {currentBadge.letter}
                </span>
              )}
              {car.tyreLifePct !== null ? `${Math.round(car.tyreLifePct)}%` : "—"}
            </div>
          </div>
        )}
      </div>

      {!car ? (
        <p className="text-xs text-muted-foreground">O seu piloto não está mais na corrida.</p>
      ) : request ? (
        <div className="mb-2 border border-amber-400/60 bg-amber-400/10 px-3 py-2 text-xs">
          <div className="font-black uppercase text-amber-400">
            {REQUEST_STATUS[request.status] ?? "Pedido de box"}
          </div>
          <div className="text-muted-foreground">Composto pedido: {request.tyreCompound.toLowerCase()}</div>
        </div>
      ) : (
        <>
          <div className="mb-2 grid grid-cols-5 gap-1">
            {COMPOUNDS.map((option) => {
              const badge = COMPOUND_BADGE[option.code]
              const selected = tyre === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={selected}
                  aria-label={option.label}
                  title={option.label}
                  onClick={() => setTyre(option.value)}
                  className={`flex h-7 items-center justify-center text-xs font-black transition-colors ${
                    selected ? "ring-2 ring-primary ring-offset-1 ring-offset-background" : "opacity-70 hover:opacity-100"
                  } ${badge?.className ?? "bg-zinc-700 text-white"}`}
                >
                  {badge?.letter ?? "?"}
                </button>
              )
            })}
          </div>
          <Button
            onClick={() => onRequest(tyre)}
            disabled={!canRequest}
            className="h-8 w-full rounded-none text-xs font-black uppercase tracking-wider"
          >
            {car.pitting ? "Já está nos boxes" : "Chamar para o box"}
          </Button>
        </>
      )}

      {request && (
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={!canCancel}
          className="mt-2 h-8 w-full rounded-none border-border bg-transparent text-xs font-black uppercase tracking-wider"
        >
          {inPitLane ? "Já entrou na via dos boxes" : "Cancelar pedido"}
        </Button>
      )}

      {error && <p className="mt-2 text-xs text-primary">{error}</p>}
      {!active && <p className="mt-2 text-xs text-muted-foreground">Pedidos de box só valem com a corrida em andamento.</p>}
    </section>
  )
}
