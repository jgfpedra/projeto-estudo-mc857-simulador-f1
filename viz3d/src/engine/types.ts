import type { CarIdentity } from '../cars/motion'

/**
 * An engine race recording, as `scripts/record_race.py` writes it: JSONL, one
 * static race block and then one line per engine tick, in the tick format the
 * group is converging on. Nothing outside `load.ts` should touch these raw
 * types: angles here are degrees, coordinates are the engine's plan `(x, y)`,
 * and the per-tick lists are in race order rather than per car.
 */

/** Line 1. Shaped like the group's `GET /races/{id}`. */
export interface RaceBlockJson {
  race_id: string
  num_laps: number
  track: {
    name: string
    /** `track_identity`'s `fonte`: `mirror` for `load_track_frozen`. */
    source: string
    /** `track_identity`'s hash of the float64 waypoint array, 16 hex chars. */
    geometry_sha256: string
    length_m: number
    width_m: number
    start_finish_waypoint: number
    /** Engine plan, metres, `[[x, y]]`, direction of travel, loop not closed. */
    waypoints: number[][]
  }
  drivers: { driver_id: string; name: string; grid_position: number }[]
  /** Recorder provenance: seed, profile, realtime factor. Not used to render. */
  recording?: Record<string, unknown>
}

export interface TickPositionJson {
  driver_id: string
  position: number
  lap: number
  /** Engine plan, metres. */
  position_xy: [number, number]
  /** Engine heading, degrees, anticlockwise from +x. */
  heading_deg: number
  velocity_mps: number
  /** `engine.race_progress_m`: unwrapped, from the start/finish waypoint. */
  progress_m: number
  /** Our refined projector: arc length within the lap from start/finish. */
  s_m: number
  /** Our refined projector: lateral, metres, POSITIVE TO THE RIGHT of travel. */
  d_m: number
  tyre_compound: string
  tyre_life_pct: number
  /**
   * The engine's `DriverState.pitting`. Nothing in the engine sets it true
   * (phase 3b): a stop happens inside `_complete_lap` and clears it at once.
   */
  pitting: boolean
  /** Phase 3b recorder only; absent from phase 3 recordings. */
  fuel_kg?: number
  /** `DriverState.pit_stop_done`: stops so far. Phase 3b recorder only. */
  pit_stops?: number
  /**
   * `DriverState.pit_penalty_pending_s`: the pit time set at the stop, added to
   * the *next* completed lap's time and then zeroed. Phase 3b recorder only.
   */
  pit_penalty_pending_s?: number
}

/** Lines 2..n. */
export interface TickJson {
  sim_ts: number
  /** The engine `TickEvent`'s own `lap`: the lowest lap in the field. */
  lap: number
  leader_lap: number
  positions: TickPositionJson[]
}

/** One car, in grid order. */
export interface EngineCar extends CarIdentity {
  driverId: string
  gridPosition: number
}

/**
 * Parsed recording. Channels are flat, `[tick * cars + car]`, with `car` the
 * grid index - so a car keeps its slot when the running order changes. Metres,
 * seconds, radians.
 */
export interface Recording {
  raceId: string
  numLaps: number
  track: {
    name: string
    source: string
    geometrySha256: string
    lengthM: number
    widthM: number
    startFinishWaypoint: number
    /** Engine plan, `[x0, y0, x1, y1, ...]`, in the file's order. */
    waypoints: Float64Array
  }
  cars: EngineCar[]
  ticks: number
  /** `sim_ts` of the first tick. Clock time 0 maps here. */
  t0S: number
  dtS: number
  durationS: number
  x: Float64Array
  y: Float64Array
  /** Engine heading, radians, anticlockwise from +x in the engine plan. */
  headingRad: Float64Array
  velocityMps: Float64Array
  progressM: Float64Array
  /** Rate `progress_m` advances, central difference. What the camera feeds forward. */
  paceMps: Float64Array
  sM: Float64Array
  dM: Float64Array
  position: Int16Array
  lap: Int16Array
  pitting: Uint8Array
  /** `fuel_kg`, NaN where the recording has none. */
  fuelKg: Float32Array
  /** `pit_stops`; 0 where the recording has none. */
  pitStops: Uint8Array
  /** `pit_penalty_pending_s`; 0 where the recording has none. */
  pitPenaltyS: Float32Array
  /** True when the ticks carry `pit_stops` / `pit_penalty_pending_s`. */
  hasPitFields: boolean
  /** Every stop inside the recorded window, in tick order. */
  pitEvents: PitEvent[]
  tyreLifePct: Float32Array
  /** Index into `compounds`. */
  tyreCompound: Uint8Array
  compounds: string[]
  /** Whatever the recorder wrote about itself. */
  meta: Record<string, unknown>
}

/**
 * One pit stop as the ticks show it: the first tick on which a car's
 * `pit_stops` went up (or, in a recording without that field, its tyre life
 * went up). The engine does the whole stop inside one `_complete_lap` call, so
 * this is a single tick: tyres and fuel change, the car does not stop.
 */
export interface PitEvent {
  car: number
  tick: number
  /** Clock time of `tick` (0 = first recorded tick). */
  tS: number
  /** Completed laps when it pitted: the stop is at the end of this lap. */
  lap: number
  compoundBefore: string
  /**
   * Tyre life on the tick before the stop, i.e. *before* the wear of the lap
   * that triggered it: the engine wears the tyre, asks `needs_pit` and swaps it
   * in one `_complete_lap` call, so the worn value below the threshold is never
   * in a tick.
   */
  lifeBefore: number
  compoundAfter: string
  lifeAfter: number
  fuelBeforeKg: number
  fuelAfterKg: number
  /** Pending penalty right after the stop, seconds. */
  penaltyS: number
}
