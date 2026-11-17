import type {
  CarFrame,
  FinalEntry,
  Frame,
  LiveMessage,
  RaceDriver,
  RaceInfo,
  RaceSnapshot,
  RaceTrack,
  TrackStatus,
  Weather,
} from "@/types/race"

type Raw = Record<string, unknown>

const TRACK_STATUSES: readonly TrackStatus[] = ["GREEN", "YELLOW", "SAFETY_CAR", "VSC", "RED_FLAG"]

const isObj = (v: unknown): v is Raw => typeof v === "object" && v !== null && !Array.isArray(v)
const num = (v: unknown): number | undefined => (typeof v === "number" && Number.isFinite(v) ? v : undefined)
const str = (v: unknown): string | undefined => (typeof v === "string" ? v : undefined)
const isTrackStatus = (v: unknown): v is TrackStatus =>
  typeof v === "string" && (TRACK_STATUSES as readonly string[]).includes(v)

const parsePoint = (v: unknown): [number, number] | null => {
  if (!Array.isArray(v)) return null
  const x = num(v[0])
  const y = num(v[1])
  return x === undefined || y === undefined ? null : [x, y]
}

const isPoint = (p: [number, number] | null): p is [number, number] => p !== null
const isCar = (c: CarFrame | null): c is CarFrame => c !== null
const isDriver = (d: RaceDriver | null): d is RaceDriver => d !== null
const isFinal = (e: FinalEntry | null): e is FinalEntry => e !== null

function parseWeather(raw: unknown): Weather | null {
  if (!isObj(raw)) return null
  const kind = str(raw.kind)
  const trackTemp = num(raw.track_temp)
  if (!kind || trackTemp === undefined) return null
  return { kind, trackTemp, rainfall: num(raw.rainfall) ?? 0 }
}

function parseCar(raw: unknown): CarFrame | null {
  if (!isObj(raw)) return null
  const driverId = str(raw.driver_id)
  const position = num(raw.position)
  const lap = num(raw.lap)
  const xy = parsePoint(raw.position_xy)
  if (!driverId || position === undefined || lap === undefined || !xy) return null

  return {
    driverId,
    position,
    lap,
    x: xy[0],
    y: xy[1],
    speedKmh: num(raw.speed_kmh) ?? (num(raw.velocity_mps) ?? 0) * 3.6,
    tyre: str(raw.tyre_compound) ?? "UNKNOWN",
    tyreLifePct: num(raw.tyre_life_pct) ?? null,
    pitting: raw.pitting === true,
    gapToLeaderS: num(raw.gap_to_leader_s) ?? null,
    lapsBehind: num(raw.laps_behind) ?? 0,
    headingDeg: num(raw.heading_deg) ?? null,
  }
}

/** Serve tanto para o `tick` do WebSocket quanto para `last_tick` do snapshot. */
export function parseFrame(raw: unknown): Frame | null {
  if (!isObj(raw)) return null
  const simTs = num(raw.sim_ts)
  const lap = num(raw.lap)
  if (simTs === undefined || lap === undefined || !Array.isArray(raw.positions)) return null

  return {
    simTs,
    lap,
    weather: parseWeather(raw.weather),
    cars: raw.positions.map(parseCar).filter(isCar),
  }
}

function parseDriver(raw: unknown): RaceDriver | null {
  if (!isObj(raw)) return null
  const driverId = str(raw.driver_id)
  if (!driverId) return null

  return {
    driverId,
    abbreviation: str(raw.abbreviation) ?? driverId.slice(0, 3).toUpperCase(),
    name: str(raw.name) ?? driverId,
    number: num(raw.number) ?? null,
    team: str(raw.team) ?? null,
    teamColor: str(raw.team_color) ?? null,
    gridPosition: num(raw.grid_position) ?? 0,
  }
}

function parseTrack(raw: unknown): RaceTrack | null {
  if (!isObj(raw)) return null
  return {
    name: str(raw.name) ?? "Circuito",
    lengthM: num(raw.length_m) ?? 0,
    startFinishWaypoint: num(raw.start_finish_waypoint) ?? 0,
    waypoints: Array.isArray(raw.waypoints) ? raw.waypoints.map(parsePoint).filter(isPoint) : [],
  }
}

export function parseRaceInfo(raw: unknown): RaceInfo | null {
  if (!isObj(raw)) return null
  const raceId = str(raw.race_id)
  const numLaps = num(raw.num_laps)
  const track = parseTrack(raw.track)
  if (!raceId || numLaps === undefined || !track) return null

  return {
    raceId,
    season: num(raw.season) ?? null,
    circuitId: str(raw.circuit_id) ?? "",
    layoutId: str(raw.layout_id) ?? null,
    numLaps,
    track,
    drivers: Array.isArray(raw.drivers) ? raw.drivers.map(parseDriver).filter(isDriver) : [],
  }
}

function parseFinal(raw: unknown): FinalEntry | null {
  if (!isObj(raw)) return null
  const driverId = str(raw.driver_id)
  const position = num(raw.position)
  if (!driverId || position === undefined) return null

  return {
    position,
    driverId,
    lapsCompleted: num(raw.laps_completed) ?? 0,
    totalTimeS: num(raw.total_time_s) ?? 0,
    pitStops: num(raw.pit_stops) ?? 0,
  }
}

export function parseSnapshot(raw: unknown): RaceSnapshot | null {
  if (!isObj(raw)) return null
  return {
    status: raw.status === "finished" ? "finished" : "running",
    simTs: num(raw.sim_ts) ?? 0,
    lastFrame: parseFrame(raw.last_tick),
    classification: Array.isArray(raw.classification)
      ? raw.classification.map(parseFinal).filter(isFinal)
      : null,
  }
}

/** Converte uma mensagem do WebSocket. Mensagens desconhecidas ou inválidas retornam null. */
export function parseLiveMessage(raw: unknown): LiveMessage | null {
  if (!isObj(raw)) return null
  const simTs = num(raw.sim_ts) ?? 0
  const lap = num(raw.lap) ?? 0

  switch (raw.type) {
    case "tick": {
      const frame = parseFrame(raw)
      return frame ? { kind: "tick", frame } : null
    }

    case "race_control": {
      if (!isTrackStatus(raw.status)) return null
      return { kind: "race_control", simTs, lap, status: raw.status, message: str(raw.message) ?? "" }
    }

    case "pit_stop": {
      const driverId = str(raw.driver_id)
      if (!driverId) return null
      return {
        kind: "pit_stop",
        simTs,
        lap,
        driverId,
        newCompound: str(raw.new_compound) ?? "UNKNOWN",
        pitTimeS: num(raw.pit_time_s) ?? 0,
      }
    }

    case "tyre_worn": {
      const driverId = str(raw.driver_id)
      if (!driverId) return null
      return {
        kind: "tyre_worn",
        simTs,
        driverId,
        compound: str(raw.compound) ?? "UNKNOWN",
        tyreLifePct: num(raw.tyre_life_pct) ?? 0,
      }
    }

    case "weather_changed": {
      const weather = parseWeather(raw.current)
      return weather ? { kind: "weather_changed", simTs, lap, weather } : null
    }

    case "collision": {
      const driverAId = str(raw.driver_a_id)
      const driverBId = str(raw.driver_b_id)
      if (!driverAId || !driverBId) return null
      return {
        kind: "collision",
        simTs,
        lap,
        driverAId,
        driverBId,
        impactForceN: num(raw.impact_force_n) ?? 0,
      }
    }

    case "race_end": {
      if (!Array.isArray(raw.final_classification)) return null
      return {
        kind: "race_end",
        simTs,
        classification: raw.final_classification.map(parseFinal).filter(isFinal),
      }
    }

    default:
      return null
  }
}
