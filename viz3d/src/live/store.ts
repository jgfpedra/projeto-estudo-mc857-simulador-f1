import type { PitReadout } from '../engine/source'
import type {
  AiCommand,
  AiSuggestion,
  LivePosition,
  LiveTick,
  RaceMeta,
} from './types'

export interface StoredTick {
  simTs: number
  lap: number
  /** One entry per car, in grid order. Gaps are cars missing from the tick. */
  rows: (LivePosition | undefined)[]
}

export type LiveStatus = 'connecting' | 'live' | 'ended' | 'error'

/**
 * Everything the live viewer knows: the race block, a growing tick buffer, and
 * the AI's text/commands.
 *
 * `Grid` and the panels read it every frame; the socket writes it on the
 * engine's own 10 Hz. Kept outside React state on purpose — the Canvas subtree
 * must not reconcile on every tick.
 */
export class LiveStore {
  readonly meta: RaceMeta
  private readonly byDriver = new Map<string, number>()
  private ticks: StoredTick[] = []
  private messagesList: AiSuggestion[] = []
  private commandsList: AiCommand[] = []
  private pitCounts = new Map<string, number>()
  private listeners = new Set<() => void>()

  status: LiveStatus = 'connecting'
  error: string | null = null
  version = 0

  constructor(meta: RaceMeta) {
    this.meta = meta
    const drivers = [...meta.drivers].sort((a, b) => a.grid_position - b.grid_position)
    drivers.forEach((driver, index) => this.byDriver.set(driver.driver_id, index))
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getVersion = (): number => this.version

  private emit(): void {
    this.version++
    for (const listener of this.listeners) listener()
  }

  get carCount(): number {
    return this.meta.drivers.length
  }

  get t0(): number {
    return this.ticks[0]?.simTs ?? 0
  }

  get lastSimTs(): number {
    return this.ticks[this.ticks.length - 1]?.simTs ?? 0
  }

  get ticksList(): readonly StoredTick[] {
    return this.ticks
  }

  get messages(): readonly AiSuggestion[] {
    return this.messagesList
  }

  get trackEvents(): readonly (AiCommand | AiSuggestion)[] {
    return this.commandsList
  }

  /** Index of a car in grid order, from the API's driver id. */
  indexOfDriver(driverId: string): number | undefined {
    return this.byDriver.get(driverId)
  }

  /** Latest row for a car, or `undefined` before the first tick. */
  latestRow(car: number): LivePosition | undefined {
    const last = this.ticks[this.ticks.length - 1]
    return last?.rows[car]
  }

  lapOf(car: number): number {
    return (this.latestRow(car)?.lap ?? 0) + 1
  }

  positionOf(car: number): number {
    return this.latestRow(car)?.position ?? 0
  }

  pitOf(car: number): PitReadout {
    const row = this.latestRow(car)
    return {
      pitting: Boolean(row?.pitting),
      compound: row?.tyre_compound ?? '—',
      tyreLifePct: row?.tyre_life_pct ?? 0,
      fuelKg: row?.fuel_kg ?? Number.NaN,
      stops: this.pitCounts.get(row?.driver_id ?? '') ?? 0,
      penaltyPendingS: 0,
      active: null,
    }
  }

  /** Most recent high-level command for a car, if any. */
  activeCommand(car: number): AiCommand | null {
    const driverId = this.meta.drivers[car]?.driver_id
    if (!driverId) return null
    for (let i = this.commandsList.length - 1; i >= 0; i--) {
      const cmd = this.commandsList[i]
      if (cmd.driver_id === driverId) return cmd
    }
    return null
  }

  activeCommandText(car: number): string | null {
    const cmd = this.activeCommand(car)
    if (!cmd || cmd.command === 'neutral') return null
    const reason = cmd.reason ? ` — ${cmd.reason}` : ''
    return `${cmd.command.toUpperCase()}${reason}`
  }

  /** Feed one WebSocket frame. Unknown event types are ignored. */
  ingest(event: unknown): void {
    if (!event || typeof event !== 'object') return
    const e = event as Record<string, unknown>
    const type = e.type

    if (type === 'tick') {
      this.ingestTick(e as unknown as LiveTick)
      this.status = 'live'
    } else if (type === 'position_update') {
      // Lap-boundary snapshots are *not* enrichment-complete (no `progress_m`,
      // `position`, `s_m`/`d_m`): feeding them to the motion buffer would make
      // `s` jump to zero at every boundary. Ticks already carry all of it.
      this.status = 'live'
    } else if (type === 'ai_suggestion') {
      const suggestion = e as unknown as AiSuggestion
      suggestion.sim_ts = Number(e.sim_ts ?? this.lastSimTs)
      // O replay do WebSocket e o evento ao vivo podem entregar a mesma
      // sugestão; evita duplicar no HUD.
      const duplicate = this.messagesList.some(
        (m) =>
          m.driver_id === suggestion.driver_id &&
          m.sim_ts === suggestion.sim_ts &&
          m.aviso === suggestion.aviso,
      )
      if (!duplicate) {
        this.messagesList.push(suggestion)
        if (this.messagesList.length > 60) this.messagesList.shift()
      }
    } else if (type === 'ai_command') {
      const command = e as unknown as AiCommand
      this.commandsList.push(command)
      if (this.commandsList.length > 120) this.commandsList.shift()
    } else if (type === 'pit_stop') {
      const driverId = String(e.driver_id ?? '')
      this.pitCounts.set(driverId, (this.pitCounts.get(driverId) ?? 0) + 1)
    } else if (type === 'race_end') {
      this.status = 'ended'
    } else if (type === 'race_start') {
      this.status = 'live'
    } else if (type === 'race_error') {
      this.status = 'error'
      this.error = String(e.message ?? 'race error')
    } else {
      return
    }

    this.emit()
  }

  private ingestTick(tick: LiveTick): void {
    const rows: (LivePosition | undefined)[] = new Array(this.carCount)
    for (const position of tick.positions ?? []) {
      const car = this.byDriver.get(position.driver_id)
      if (car !== undefined) rows[car] = position
    }
    this.ticks.push({
      simTs: Number(tick.sim_ts ?? this.lastSimTs),
      lap: Number(tick.lap ?? 0),
      rows,
    })
    // Keep a bounded history: enough to survive a tab hitch, not a whole race.
    if (this.ticks.length > 3000) this.ticks.shift()
  }
}
