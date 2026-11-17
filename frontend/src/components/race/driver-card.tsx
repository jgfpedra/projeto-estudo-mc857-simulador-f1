import { X } from "lucide-react"

import { COMPOUND_BADGE, driverColor, gapLabel } from "@/helpers/race-live"
import type { CarFrame, FeedItem, FinalEntry, Frame, RaceInfo } from "@/types/race"

type Props = {
  race: RaceInfo
  frame: Frame | null
  prevFrame: Frame | null
  feed: FeedItem[]
  classification: FinalEntry[] | null
  driverId: string
  onClose: () => void
}

/** Cor da barra de vida do pneu: verde acima de 60%, amarela até 30%, vermelha abaixo. */
function tyreBar(pct: number | null): string {
  if (pct === null) return "bg-zinc-500"
  if (pct >= 60) return "bg-emerald-500"
  if (pct >= 30) return "bg-amber-400"
  return "bg-red-500"
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="font-black tabular-nums">{value}</dd>
    </div>
  )
}

/**
 * Informações de um piloto selecionado. Fica no canto do mapa, translúcido e pequeno,
 * para não cobrir a pista.
 */
export function DriverCard({
  race,
  frame,
  prevFrame,
  feed,
  classification,
  driverId,
  onClose,
}: Props) {
  const index = race.drivers.findIndex((d) => d.driverId === driverId)
  const info = race.drivers[index]
  if (!info) return null

  const color = driverColor(info, index)
  const car: CarFrame | null = frame?.cars.find((c) => c.driverId === driverId) ?? null
  const before = prevFrame?.cars.find((c) => c.driverId === driverId)
  const final = classification?.find((e) => e.driverId === driverId) ?? null
  const pitStops = feed.filter((i) => i.kind === "pit_stop" && i.driverIds.includes(driverId)).length
  const lastEvent = [...feed].reverse().find((i) => i.driverIds.includes(driverId))
  const delta = car && before ? before.position - car.position : 0
  const tyre = car ? COMPOUND_BADGE[car.tyre] : undefined

  return (
    <div className="pointer-events-auto absolute bottom-4 right-4 z-20 w-56 border border-border/60 bg-background/75 p-3 backdrop-blur-sm">
      <div className="mb-3 flex items-start gap-2">
        <span className="mt-0.5 h-8 w-1 shrink-0" style={{ backgroundColor: color }} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-black uppercase leading-tight">
            {info.abbreviation} <span className="text-muted-foreground">#{info.number ?? "—"}</span>
          </div>
          <div className="truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            {info.name}
            {info.team ? ` · ${info.team}` : ""}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar informações do piloto"
          className="flex h-6 w-6 shrink-0 items-center justify-center text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {car ? (
        <>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
            <Item
              label="Posição"
              value={`P${car.position}${delta > 0 ? ` ▲${delta}` : delta < 0 ? ` ▼${-delta}` : ""}`}
            />
            <Item label="Volta" value={`${car.lap}/${race.numLaps}`} />
            <Item label="Diferença" value={gapLabel(car)} />
            <Item label="Velocidade" value={`${Math.round(car.speedKmh)} km/h`} />
            <Item label="Paradas" value={String(pitStops)} />
            <Item label="Status" value={car.pitting ? "Nos boxes" : "Em pista"} />
          </dl>

          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <span className="flex items-center gap-2">
                Pneu
                {tyre && (
                  <span className={`flex h-4 w-4 items-center justify-center text-[9px] font-black ${tyre.className}`}>
                    {tyre.letter}
                  </span>
                )}
              </span>
              <span className="tabular-nums">
                {car.tyreLifePct !== null ? `${Math.round(car.tyreLifePct)}%` : "—"}
              </span>
            </div>
            <div className="h-1.5 w-full bg-muted">
              <div
                className={`h-full transition-all ${tyreBar(car.tyreLifePct)}`}
                style={{ width: `${Math.max(0, Math.min(100, car.tyreLifePct ?? 0))}%` }}
              />
            </div>
          </div>
        </>
      ) : final ? (
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          <Item label="Final" value={`P${final.position}`} />
          <Item label="Voltas" value={String(final.lapsCompleted)} />
          <Item label="Paradas" value={String(final.pitStops)} />
          <Item label="Status" value="Corrida encerrada" />
        </dl>
      ) : (
        <p className="text-xs text-muted-foreground">Sem dados ao vivo para este piloto.</p>
      )}

      {lastEvent && (
        <p className="mt-3 border-t border-border/60 pt-2 text-[11px] leading-snug">{lastEvent.message}</p>
      )}
    </div>
  )
}
