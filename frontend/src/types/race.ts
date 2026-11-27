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
  | "pit_request"

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
  /** Origem da cor no backend; "unknown" indica o cinza de emergência. */
  teamColorSource: string | null
  gridPosition: number
}

export type RacePitLane = {
  /** Via aberta, em metros no mesmo sistema de coordenadas da pista. */
  waypoints: [number, number][]
  widthM: number
  source: string | null
}

/** Caixa de colisão do chassi no backend, em metros. */
export type CarGeometry = {
  lengthM: number
  widthM: number
  heightM: number
}

export type RaceTrack = {
  name: string
  lengthM: number
  startFinishWaypoint: number
  widthM: number | null
  pitLane: RacePitLane | null
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
  /** Nulo em corridas antigas que não enviam `car_geometry`. */
  carGeometry: CarGeometry | null
  /** Piloto controlado pelo usuário: recebe pit stop manual. */
  userDriverId: string | null
  drivers: RaceDriver[]
}

export type Weather = {
  kind: string
  trackTemp: number
  rainfall: number
}

/** Pedido de box pendente de um carro (vem no tick). */
export type PitRequest = {
  tyreCompound: string
  source: string
  /** scheduled | approaching | in_pit_lane */
  status: string
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
  /** Progresso acumulado na corrida, em metros (`progress_m`). */
  progressM: number | null
  /** Distância desde a linha de chegada na volta atual, em metros (`s_m`). */
  sM: number | null
  /** Deslocamento lateral assinado, positivo à direita (`d_m`). */
  dM: number | null
  pitRequest: PitRequest | null
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
  | { kind: "race_recovered"; simTs: number; raceId: string }
  | { kind: "pit_requested"; simTs: number; lap: number; driverId: string; tyreCompound: string }
  | { kind: "pit_cancelled"; simTs: number; lap: number; driverId: string }
  | { kind: "pit_cancel_rejected"; simTs: number; lap: number; driverId: string; reason: string }
  | { kind: "ai_suggestion"; simTs: number; lap: number; driverId: string; raceId: string; message: string; urgency: "baixa" | "media" | "alta"; command?: { type: string; value: number; reason: string; confianca?: number } | null }
  | { kind: "ai_command"; simTs: number; lap: number; driverId: string; command: string; value: number; reason: string; issuedBy: string }
  | { kind: "ai_started"; simTs: number; raceId: string; totalLaps: number; userDriverId: string | null; numDrivers: number; decisionIntervalS: number }
  | { kind: "ai_monitoring"; simTs: number; raceId: string; status: "waiting_for_race_start" | "running" | "paused"; stats: Record<string, unknown> }
  | { kind: "ai_stopped"; simTs: number; raceId: string; reason: "race_ended" | "error" | "cancelled"; stats: Record<string, unknown> }
  | { kind: "ai_error"; simTs: number; raceId: string; error: string; errorType: string; cycle: number; driverId?: string }
  | { kind: "driver_radio"; simTs: number; lap: number; driverId: string; driverName: string; message: string; trigger: string; confidence: number }

/** Sugestão do engenheiro de IA para o HUD 2D. */
export type AiSuggestion = {
  simTs: number
  lap: number
  driverId: string
  raceId: string
  message: string
  urgency: "baixa" | "media" | "alta"
  command?: { type: string; value: number; reason: string; confianca?: number } | null
  id?: string
}

/** Comando ativo do engenheiro de IA. */
export type AiCommand = {
  simTs: number
  lap: number
  driverId: string
  command: string
  value: number
  reason: string
  issuedBy: string
}

/** Evento: AiEngineer iniciado. */
export type AiStarted = {
  simTs: number
  raceId: string
  totalLaps: number
  userDriverId: string | null
  numDrivers: number
  decisionIntervalS: number
}

/** Evento: AiEngineer monitorando (heartbeat). */
export type AiMonitoring = {
  simTs: number
  raceId: string
  status: "waiting_for_race_start" | "running" | "paused"
  stats: Record<string, unknown>
}

/** Evento: AiEngineer parado. */
export type AiStopped = {
  simTs: number
  raceId: string
  reason: "race_ended" | "error" | "cancelled"
  stats: Record<string, unknown>
}

/** Evento: Erro no AiEngineer (não fatal). */
export type AiError = {
  simTs: number
  raceId: string
  error: string
  errorType: string
  cycle: number
  driverId?: string
}

/** Resposta/rádio do piloto (fallback) quando IA fala bobagem. */
export type DriverRadio = {
  simTs: number
  lap: number
  driverId: string
  driverName: string
  message: string
  trigger: string
  confidence: number
}

/** GET /races/{race_id}/snapshot. */
export type RaceSnapshot = {
  status: "running" | "finished" | "cancelled"
  simTs: number
  lastFrame: Frame | null
  classification: FinalEntry[] | null
}

/** Debrief pós-corrida gerado pelo LLM. */
export type Debrief = {
  resumo_geral: string
  largada: string
  estrategia_pneus: string
  combustivel: string
  momentos_chave: Array<{ volta: number; evento: string; impacto: "alta" | "media" | "baixa" }>
  contatos_incidentes: string
  performance_pilotos: {
    vencedor?: string
    surpresa_positiva?: string
    decepcao?: string
    melhor_ultrapassagem?: string
  }
  decisoes_engenheiro: string
  licoes_aprendidas: string
  fallback?: boolean
  fallback_motivo?: string
  race_id: string
  gerado_em: number
}
