import { COMPOUND_BADGE, driverColor, formatClock, gapLabel } from "@/helpers/race-live"
import type { FinalEntry, Frame, RaceInfo } from "@/types/race"

type Props = {
  race: RaceInfo
  frame: Frame | null
  prevFrame: Frame | null
  classification: FinalEntry[] | null
  selectedDriverId: string | null
  onSelect: (driverId: string | null) => void
}

const rowClass = (selected: boolean) =>
  `grid w-full grid-cols-[2rem_4px_1fr_auto] items-center gap-3 border-b border-border px-4 py-2.5 text-left transition-colors ${
    selected ? "bg-accent" : "hover:bg-accent/60"
  }`

export function TimingPanel({
  race,
  frame,
  prevFrame,
  classification,
  selectedDriverId,
  onSelect,
}: Props) {
  const drivers = new Map(race.drivers.map((d, i) => [d.driverId, { d, i }]))
  const colorOf = (id: string) => {
    const meta = drivers.get(id)
    return driverColor(meta?.d, meta?.i ?? 0)
  }
  const codeOf = (id: string) => drivers.get(id)?.d.abbreviation ?? id.slice(0, 3).toUpperCase()

  if (classification) {
    const leader = classification[0]
    return (
      <ol className="min-h-0 flex-1 overflow-y-auto">
        {classification.map((e) => {
          const selected = selectedDriverId === e.driverId
          const lapsDiff = leader ? leader.lapsCompleted - e.lapsCompleted : 0
          const timeLabel =
            e.position === 1
              ? formatClock(e.totalTimeS)
              : lapsDiff > 0
                ? `+${lapsDiff} V`
                : `+${(e.totalTimeS - (leader?.totalTimeS ?? 0)).toFixed(1)}`

          return (
            <li key={e.driverId}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(selected ? null : e.driverId)}
                className={rowClass(selected)}
              >
                <span className="text-sm font-black italic tabular-nums">
                  {String(e.position).padStart(2, "0")}
                </span>
                <span className="h-8 w-1" style={{ backgroundColor: colorOf(e.driverId) }} />
                <div className="min-w-0">
                  <div className="text-sm font-black uppercase">{codeOf(e.driverId)}</div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {e.lapsCompleted} voltas · {e.pitStops} parada(s)
                  </div>
                </div>
                <span className="text-right text-xs font-bold tabular-nums">{timeLabel}</span>
              </button>
            </li>
          )
        })}
      </ol>
    )
  }

  const cars = [...(frame?.cars ?? [])].sort((a, b) => a.position - b.position)

  if (cars.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-xs uppercase tracking-wider text-muted-foreground">
        Aguardando dados...
      </div>
    )
  }

  const prevPosition = new Map((prevFrame?.cars ?? []).map((c) => [c.driverId, c.position]))

  return (
    <ol className="min-h-0 flex-1 overflow-y-auto">
      {cars.map((car) => {
        const selected = selectedDriverId === car.driverId
        const before = prevPosition.get(car.driverId)
        const delta = before === undefined ? 0 : before - car.position
        const tyre = COMPOUND_BADGE[car.tyre]

        return (
          <li key={car.driverId}>
            <button
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(selected ? null : car.driverId)}
              className={rowClass(selected)}
            >
              <span className="text-sm font-black italic tabular-nums">
                {String(car.position).padStart(2, "0")}
              </span>
              <span className="h-8 w-1" style={{ backgroundColor: colorOf(car.driverId) }} />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-black uppercase">{codeOf(car.driverId)}</span>
                  {tyre && (
                    <span
                      className={`flex h-4 w-4 items-center justify-center text-[9px] font-black ${tyre.className}`}
                      title={`Pneu ${car.tyre.toLowerCase()}${car.tyreLifePct !== null ? ` · ${Math.round(car.tyreLifePct)}%` : ""}`}
                    >
                      {tyre.letter}
                    </span>
                  )}
                  {car.pitting && (
                    <span className="bg-amber-400 px-1 text-[9px] font-black text-black">BOX</span>
                  )}
                </div>
                <div className="truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  V{car.lap} · {Math.round(car.speedKmh)} km/h
                </div>
              </div>
              <span className="flex items-center justify-end gap-1 text-right text-xs font-bold tabular-nums">
                {delta > 0 && <span className="text-emerald-400">▲{delta}</span>}
                {delta < 0 && <span className="text-red-500">▼{-delta}</span>}
                <span>{gapLabel(car)}</span>
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
