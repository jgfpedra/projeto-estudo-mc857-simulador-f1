export type TrackStatus = "green" | "yellow" | "safety_car" | "vsc" | "red_flag"
export type Tyre = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET" | "UNKNOWN"

export type RaceEventType =
  | "overtake"
  | "pit_stop"
  | "safety_car"
  | "vsc"
  | "red_flag"
  | "yellow_flag"
  | "green_flag"
  | "finish"

export type DriverInfo = {
  id: string
  code: string
  name: string
  teamColor: string
}

/** Estado de um carro em um tick. Coordenadas na unidade da FastF1 (décimos de metro). */
export type TickCar = {
  id: string
  x: number
  y: number
  position: number
  lap: number
  lapTotal: number
  speedKmh: number
  tyre: Tyre
  inPit: boolean
  gapToLeaderS: number | null
}

/** Um instante da corrida. É o objeto que vai pelo websocket no futuro. */
export type Tick = {
  t: number
  trackStatus: TrackStatus
  cars: TickCar[]
}

export type RaceEvent = {
  t: number
  type: RaceEventType
  driverIds: string[]
  lap: number
  message: string
}

export type Bounds = { minX: number; maxX: number; minY: number; maxY: number }

export type RaceData = {
  meta: { totalLaps: number; tickHz: number; durationS: number }
  track: { points: [number, number][]; bounds: Bounds }
  drivers: DriverInfo[]
  ticks: Tick[]
  events: RaceEvent[]
}