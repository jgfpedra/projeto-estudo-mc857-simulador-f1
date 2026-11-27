import type {
  CarFrame,
  PitRequest,
  CarGeometry,
  FinalEntry,
  Frame,
  LiveMessage,
  RaceDriver,
  RaceInfo,
  RacePitLane,
  RaceSnapshot,
  RaceTrack,
  TrackStatus,
  Weather,
} from "@/types/race"

type Raw = Record<string, unknown>

const TRACK_STATUSES: readonly TrackStatus[] = ["GREEN", "YELLOW", "SAFETY_CAR", "VSC", "RED_FLAG"]

const isObj = (v: unknown): v is Raw => typeof v === "object" && v !== null && !Array.isArray(v)
const num = (v: unknown): number | undefined => (typeof v === "number" && Number.isFinite(v) ? v : undefined)
const str = (v: unknown): string => (typeof v === "string" ? v : "")
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

function parsePitRequest(raw: unknown): PitRequest | null {
  if (!isObj(raw)) return null
  const tyreCompound = str(raw.tyre_compound)
  if (!tyreCompound) return null
  return {
    tyreCompound,
    source: str(raw.source) ?? "automatic",
    status: str(raw.status) ?? "scheduled",
  }
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
    progressM: num(raw.progress_m) ?? null,
    sM: num(raw.s_m) ?? null,
    dM: num(raw.d_m) ?? null,
    pitRequest: parsePitRequest(raw.pit_request),
  }
}

/** Serve tanto para o `tick` do WebSocket quanto para `last_tick` do snapshot. */
export function parseFrame(raw: unknown): Frame | null {
  if (!isObj(raw)) return null
  const simTs = num(raw.sim_ts)
  // Snapshots antigos podem ter lap do último colocado; leader_lap é explícito.
  const lap = num(raw.leader_lap) ?? num(raw.lap)
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
    abbreviation: str(raw.abbreviation) || driverId.slice(0, 3).toUpperCase(),
    name: str(raw.name) || driverId,
    number: num(raw.number) ?? null,
    team: str(raw.team) || null,
    teamColor: str(raw.team_color) || null,
    teamColorSource: str(raw.team_color_source) || null,
    gridPosition: num(raw.grid_position) ?? 0,
  }
}

function parsePitLane(raw: unknown): RacePitLane | null {
  if (!isObj(raw) || !Array.isArray(raw.waypoints)) return null
  const points = raw.waypoints.map(parsePoint)
  const widthM = num(raw.width_m)
  if (points.length < 2 || !points.every(isPoint) || widthM === undefined || widthM <= 0) return null
  return { waypoints: points, widthM, source: str(raw.source) ?? null }
}

function parseCarGeometry(raw: unknown): CarGeometry | null {
  if (!isObj(raw)) return null
  const lengthM = num(raw.length_m)
  const widthM = num(raw.width_m)
  const heightM = num(raw.height_m)
  if (lengthM === undefined || widthM === undefined || heightM === undefined) return null
  if (lengthM <= 0 || widthM <= 0 || heightM <= 0) return null
  return { lengthM, widthM, heightM }
}

function parseTrack(raw: unknown): RaceTrack | null {
  if (!isObj(raw)) return null
  const widthM = num(raw.width_m)
  return {
    name: str(raw.name) ?? "Circuito",
    lengthM: num(raw.length_m) ?? 0,
    startFinishWaypoint: num(raw.start_finish_waypoint) ?? 0,
    widthM: widthM !== undefined && widthM > 0 ? widthM : null,
    pitLane: parsePitLane(raw.pit_lane),
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
    carGeometry: parseCarGeometry(raw.car_geometry),
    userDriverId: str(raw.user_driver_id) ?? null,
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
    status: raw.status === "finished" || raw.status === "cancelled" ? raw.status : "running",
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

    case "pit_requested": {
      const driverId = str(raw.driver_id)
      if (!driverId) return null
      return { kind: "pit_requested", simTs, lap, driverId, tyreCompound: str(raw.tyre_compound) ?? "UNKNOWN" }
    }

    case "pit_cancelled": {
      const driverId = str(raw.driver_id)
      if (!driverId) return null
      return { kind: "pit_cancelled", simTs, lap, driverId }
    }

    case "pit_cancel_rejected": {
      const driverId = str(raw.driver_id)
      if (!driverId) return null
      return { kind: "pit_cancel_rejected", simTs, lap, driverId, reason: str(raw.reason) ?? "" }
    }

    case "ai_suggestion": {
      const driverId = str(raw.driver_id)
      const message = str(raw.aviso)
      const urgency = str(raw.urgencia)
      const lap = num(raw.lap) ?? 0
      const raceId = str(raw.race_id)
      if (!driverId || !message || !urgency || !["baixa", "media", "alta"].includes(urgency)) return null
      let command: { type: string; value: number; reason: string } | null = null
      if (raw.comando && isObj(raw.comando)) {
        const tipo = str(raw.comando.tipo)
        const valor = num(raw.comando.valor)
        const motivo = str(raw.comando.motivo)
        if (tipo && valor !== undefined && motivo) {
          command = { type: tipo, value: valor, reason: motivo }
        }
      }
      return { kind: "ai_suggestion", simTs, lap, driverId, raceId, message, urgency: urgency as "baixa" | "media" | "alta", command }
    }

    case "ai_command": {
      const driverId = str(raw.driver_id)
      const command = str(raw.command)
      const value = num(raw.value)
      const reason = str(raw.reason)
      const issuedBy = str(raw.issued_by)
      const lap = num(raw.lap) ?? 0
      if (!driverId || !command || value === undefined || !reason || !issuedBy) return null
      return { kind: "ai_command", simTs, lap, driverId, command, value, reason, issuedBy }
    }

    case "driver_radio": {
      const driverId = str(raw.driver_id)
      const driverName = str(raw.driver_name)
      const message = str(raw.message)
      const trigger = str(raw.trigger)
      const confidence = num(raw.confidence) ?? 0
      const lap = num(raw.lap) ?? 0
      if (!driverId || !driverName || !message || !trigger) return null
      return { kind: "driver_radio", simTs, lap, driverId, driverName, message, trigger, confidence }
    }

    case "ai_started": {
      const raceId = str(raw.race_id)
      const totalLaps = num(raw.total_laps) ?? 0
      const userDriverId = str(raw.user_driver_id) ?? null
      const numDrivers = num(raw.num_drivers) ?? 0
      const decisionIntervalS = num(raw.decision_interval_s) ?? 5.0
      if (!raceId) return null
      return { kind: "ai_started", simTs, raceId, totalLaps, userDriverId, numDrivers, decisionIntervalS }
    }

    case "ai_monitoring": {
      const raceId = str(raw.race_id)
      const status = str(raw.status)
      const stats = isObj(raw.stats) ? raw.stats : {}
      if (!raceId || !status || !["waiting_for_race_start", "running", "paused"].includes(status)) return null
      return { kind: "ai_monitoring", simTs, raceId, status: status as "waiting_for_race_start" | "running" | "paused", stats }
    }

    case "ai_stopped": {
      const raceId = str(raw.race_id)
      const reason = str(raw.reason)
      const stats = isObj(raw.stats) ? raw.stats : {}
      if (!raceId || !reason || !["race_ended", "error", "cancelled"].includes(reason)) return null
      return { kind: "ai_stopped", simTs, raceId, reason: reason as "race_ended" | "error" | "cancelled", stats }
    }

    case "ai_error": {
      const raceId = str(raw.race_id)
      const error = str(raw.error)
      const errorType = str(raw.error_type)
      const cycle = num(raw.cycle) ?? 0
      const driverId = str(raw.driver_id)
      if (!raceId || !error || !errorType) return null
      return { kind: "ai_error", simTs, raceId, error, errorType, cycle, driverId }
    }

    case "race_recovered": {
      const raceId = str(raw.race_id)
      if (!raceId) return null
      return { kind: "race_recovered", simTs, raceId }
    }

    default:
      return null
  }
}
