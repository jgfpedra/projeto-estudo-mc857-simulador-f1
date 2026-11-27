import type { RaceBlockJson } from '../engine/types'

/** `GET /races/{race_id}` — the race block the API stores before the first tick. */
export interface RaceMeta {
  race_id: string
  num_laps: number
  num_drivers?: number
  /** Driver the AI race engineer follows (the car selected in the panel). */
  followed_driver_id?: string
  /** Logic step, seconds. The live buffer interpolates between ticks. */
  dt_s?: number
  track: RaceBlockJson['track']
  drivers: { driver_id: string; name: string; grid_position: number }[]
}

/** One car in one `tick` event, as the API's `LivePublisher` writes it. */
export interface LivePosition {
  driver_id: string
  driver_name?: string
  lap: number
  /** Rank in the tick, 1-based. Added by `LivePublisher`. */
  position?: number
  position_xy: [number, number]
  heading_deg: number
  velocity_mps: number
  /** Unwrapped engine race progress, metres. */
  progress_m?: number
  /** Refined projector, metres within the lap. */
  s_m?: number
  /** Refined projector, metres, positive to the right of travel. */
  d_m?: number
  tyre_compound?: string
  tyre_life_pct?: number
  fuel_kg?: number
  pitting?: boolean
}

export interface LiveTick {
  type: 'tick'
  sim_ts: number
  lap: number
  tick_in_lap?: number
  positions: LivePosition[]
  weather?: Record<string, unknown>
}

/** The text half of the AI: what the race engineer says. */
export interface AiSuggestion {
  type: 'ai_suggestion'
  aviso: string
  urgencia: 'baixa' | 'media' | 'alta'
  previsao?: {
    pit_stop_recomendado?: boolean | null
    volta_estimada?: number | null
    composto_sugerido?: string | null
  }
  comando?: {
    tipo: string
    valor: number
    motivo: string
  } | null
  volta?: number
  driver_id?: string
  fallback?: boolean
  /** Sim time of the latest tick when this message arrived. Added client-side. */
  sim_ts: number
}

/** The car half of the AI: the command the coach applied. */
export interface AiCommand {
  type: 'ai_command'
  sim_ts: number
  ts?: number
  driver_id: string
  driver_name?: string
  lap: number
  command: string
  value: number
  reason: string
  issued_by: string
}

export interface OffTrack {
  type: 'off_track'
  sim_ts: number
  driver_id: string
  driver_name: string
  lap: number
  side: string
  distance_m: number
  speed_mps: number
  severity: string
}

export interface OnTrack {
  type: 'on_track'
  sim_ts: number
  driver_id: string
  driver_name: string
  lap: number
  duration_s: number
}

export interface RaceEnd {
  type: 'race_end'
  sim_ts: number
  final_classification: unknown[]
  total_time_s: number
}

export type LiveEvent =
  | LiveTick
  | AiSuggestion
  | AiCommand
  | OffTrack
  | OnTrack
  | RaceEnd
  | { type: string; sim_ts?: number; [key: string]: unknown }

export interface LiveCommandRecord {
  sim_ts: number
  command: string
  value: number
  reason: string
  issued_by: string
}

export type DebriefImpact = 'alto' | 'medio' | 'baixo'

export interface DebriefMoment {
  volta: number
  evento: string
  impacto: DebriefImpact
}

export interface Debrief {
  resumo_geral: string
  largada: string
  estrategia_pneus: string
  combustivel: string
  momentos_chave: DebriefMoment[]
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
