/** Modelo de domínio da corrida. Os campos do backend (snake_case) são convertidos em services/race-parser.ts. */

export type Bounds = { minX: number; maxX: number; minY: number; maxY: number }

export type TrackStatus = "GREEN" | "YELLOW" | "SAFETY_CAR" | "VSC" | "RED_FLAG"

export type Tone = "info" | "success" | "warn" | "danger"

export type FeedKind =
  | "overtake"
  | "pit_stop"
  | "tyre_worn"
  | "weather"
  | "collision"
  | "race_control"
  | "finish"

export type FeedItem = {
  id: number
  simTs: number
  lap: number
  kind: FeedKind
  tone: Tone
  message: string
  driverIds: string[]
}

export type ViewMode = "2d" | "3d"

export type RaceDriver = {
  driverId: string
  abbreviation: string
  name: string
  number: number | null
  team: string | null
  /** Pode vir nulo enquanto o backend não envia a cor da temporada. */
  teamColor: string | null
  gridPosition: number
}

export type RaceTrack = {
  name: string
  lengthM: number
  startFinishWaypoint: number
  /** Metros, mesmo sistema de coordenadas dos carros. */
  waypoints: [number, number][]
}

/** GET /races/{race_id}: dados estáticos da corrida. */
export type RaceInfo = {
  raceId: string
  season: number | null
  circuitId: string
  layoutId: string | null
  numLaps: number
  track: RaceTrack
  drivers: RaceDriver[]
}

export type Weather = {
  kind: string
  trackTemp: number
  rainfall: number
}

export type CarFrame = {
  driverId: string
  position: number
  lap: number
  x: number
  y: number
  speedKmh: number
  tyre: string
  tyreLifePct: number | null
  pitting: boolean
  gapToLeaderS: number | null
  lapsBehind: number
  headingDeg: number | null
}

export type Frame = {
  simTs: number
  lap: number
  weather: Weather | null
  cars: CarFrame[]
}

export type FinalEntry = {
  position: number
  driverId: string
  lapsCompleted: number
  totalTimeS: number
  pitStops: number
}

/** Mensagens do WebSocket já validadas e convertidas. */
export type LiveMessage =
  | { kind: "tick"; frame: Frame }
  | { kind: "race_control"; simTs: number; lap: number; status: TrackStatus; message: string }
  | { kind: "pit_stop"; simTs: number; lap: number; driverId: string; newCompound: string; pitTimeS: number }
  | { kind: "tyre_worn"; simTs: number; driverId: string; compound: string; tyreLifePct: number }
  | { kind: "weather_changed"; simTs: number; lap: number; weather: Weather }
  | { kind: "collision"; simTs: number; lap: number; driverAId: string; driverBId: string; impactForceN: number }
  | { kind: "race_end"; simTs: number; classification: FinalEntry[] }

/** GET /races/{race_id}/snapshot. */
export type RaceSnapshot = {
  status: "running" | "finished"
  simTs: number
  lastFrame: Frame | null
  classification: FinalEntry[] | null
}
