import { COMPOUND_BADGE, currentLap, driverColor, formatClock, gapLabel } from "@/helpers/race-live"
import type { FinalEntry, Frame, RaceInfo } from "@/types/race"

type Props = {
  race: RaceInfo
  frame: Frame | null
  prevFrame: Frame | null
  classification: FinalEntry[] | null
  selectedDriverId: string | null
  followedDriverId: string | null
  onSelect: (driverId: string | null) => void
  onFollow: (driverId: string) => void
  onUnfollow: () => void
  /** Piloto controlado pelo usuário: fica destacado no ranking. */
  controlledDriverId?: string | null
}

const rowClass = (selected: boolean, controlled: boolean) =>
  `grid w-full grid-cols-[minmax(0,1fr)_2rem] items-center gap-2 border-b border-border px-3 py-2.5 transition-colors ${
    selected
      ? "bg-primary/20 ring-2 ring-inset ring-primary"
      : controlled
        ? "bg-primary/10 ring-1 ring-inset ring-primary/70"
        : "hover:bg-accent/60"
  }`

const selectButtonClass =
  "grid min-w-0 grid-cols-[2rem_4px_minmax(0,1fr)_auto] items-center gap-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary"

export function TimingPanel({
  race,
  frame,
  prevFrame,
  classification,
  selectedDriverId,
  followedDriverId,
  onSelect,
  onFollow,
  onUnfollow,
  controlledDriverId = null,
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
          const followed = followedDriverId === e.driverId
          const lapsDiff = leader ? leader.lapsCompleted - e.lapsCompleted : 0
          const timeLabel =
            e.position === 1
              ? formatClock(e.totalTimeS)
              : lapsDiff > 0
                ? `+${lapsDiff} V`
                : `+${(e.totalTimeS - (leader?.totalTimeS ?? 0)).toFixed(1)}`

          return (
            <li key={e.driverId}>
              <div className={rowClass(selected, controlledDriverId === e.driverId)}>
                <button
                  type="button"
                  aria-label={`Selecionar ${codeOf(e.driverId)}`}
                  aria-pressed={selected}
                  onClick={() => onSelect(selected ? null : e.driverId)}
                  className={selectButtonClass}
                >
                  <span className="text-sm font-black italic tabular-nums">
                    {String(e.position).padStart(2, "0")}
                  </span>
                  <span className="h-8 w-1" style={{ backgroundColor: colorOf(e.driverId) }} />
                  <div className="min-w-0">
                    <div className="text-sm font-black uppercase">
                      {codeOf(e.driverId)}
                      {controlledDriverId === e.driverId && (
                        <span className="ml-2 bg-primary px-1 text-[9px] font-black text-primary-foreground">CTRL</span>
                      )}
                    </div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {e.lapsCompleted} voltas · {e.pitStops} parada(s)
                    </div>
                  </div>
                  <span className="text-right text-xs font-bold tabular-nums">{timeLabel}</span>
                </button>
                {!followed && (
                  <button
                    type="button"
                    onClick={() => onFollow(e.driverId)}
                    className="flex h-6 w-6 items-center justify-center rounded border border-border/60 bg-background/75 text-muted-foreground transition-colors hover:border-primary/70 hover:text-foreground"
                    aria-label={`Acompanhar ${codeOf(e.driverId)}`}
                    title="Acompanhar piloto"
                  >
                    <span className="text-[10px] font-bold">👁</span>
                  </button>
                )}
                {followed && (
                  <button
                    type="button"
                    onClick={onUnfollow}
                    className="flex h-6 w-6 items-center justify-center rounded border border-border/60 bg-background/75 text-muted-foreground transition-colors hover:border-red-500/70 hover:text-red-400"
                    aria-label={`Parar de acompanhar ${codeOf(e.driverId)}`}
                    title="Parar de acompanhar"
                  >
                    <span className="text-[10px] font-bold">✕</span>
                  </button>
                )}
              </div>
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
        const followed = followedDriverId === car.driverId
        const before = prevPosition.get(car.driverId)
        const delta = before === undefined ? 0 : before - car.position
        const tyre = COMPOUND_BADGE[car.tyre]

        return (
          <li key={car.driverId}>
            <div className={rowClass(selected, controlledDriverId === car.driverId)}>
              <button
                type="button"
                aria-label={`Selecionar ${codeOf(car.driverId)}`}
                aria-pressed={selected}
                onClick={() => onSelect(selected ? null : car.driverId)}
                className={selectButtonClass}
              >
                <span className="text-sm font-black italic tabular-nums">
                  {String(car.position).padStart(2, "0")}
                </span>
                <span className="h-8 w-1" style={{ backgroundColor: colorOf(car.driverId) }} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-black uppercase">{codeOf(car.driverId)}</span>
                    {controlledDriverId === car.driverId && (
                      <span className="bg-primary px-1 text-[9px] font-black text-primary-foreground">CTRL</span>
                    )}
                    {tyre && (
                      <span
                        className={`flex h-4 w-4 items-center justify-center text-[9px] font-black ${tyre.className}`}
                        title={`Pneu ${car.tyre.toLowerCase()}${car.tyreLifePct !== null ? ` · ${Math.round(car.tyreLifePct)}%` : ""}`}
                      >
                        {tyre.letter}
                      </span>
                    )}
                    {car.pitting && <span className="bg-amber-400 px-1 text-[9px] font-black text-black">BOX</span>}
                  </div>
                  <div className="truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    V{currentLap(car.lap, race.numLaps)} · {Math.round(car.speedKmh)} km/h
                  </div>
                </div>
                <span className="flex items-center justify-end gap-1 text-right text-xs font-bold tabular-nums">
                  {delta > 0 && <span className="text-emerald-400">▲{delta}</span>}
                  {delta < 0 && <span className="text-red-500">▼{-delta}</span>}
                  <span>{gapLabel(car)}</span>
                </span>
              </button>
              {!followed && (
                <button
                  type="button"
                  onClick={() => onFollow(car.driverId)}
                  className="flex h-6 w-6 items-center justify-center rounded border border-border/60 bg-background/75 text-muted-foreground transition-colors hover:border-primary/70 hover:text-foreground"
                  aria-label={`Acompanhar ${codeOf(car.driverId)}`}
                  title="Acompanhar piloto"
                >
                  <span className="text-[10px] font-bold">👁</span>
                </button>
              )}
              {followed && (
                <button
                  type="button"
                  onClick={onUnfollow}
                  className="flex h-6 w-6 items-center justify-center rounded border border-border/60 bg-background/75 text-muted-foreground transition-colors hover:border-red-500/70 hover:text-red-400"
                  aria-label={`Parar de acompanhar ${codeOf(car.driverId)}`}
                  title="Parar de acompanhar"
                >
                  <span className="text-[10px] font-bold">✕</span>
                </button>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
