import type { CarIdentity } from '../cars/motion'

/**
 * Raw replay JSON, as `scripts/extract_replay.py` writes it. Nothing outside
 * `load.ts` should touch this type.
 *
 * Columnar per car and integer-valued, which is what keeps five laps of twenty
 * cars at 5 Hz down to 379 KB. The channels:
 *
 * - `s0M` + `dsMm` — arc length. A float origin plus **millimetre deltas**, so a
 *   step is four digits instead of the seven or eight an absolute arc length
 *   needs after five laps. Millimetres rather than centimetres because the
 *   deltas accumulate: centimetres random-walk about 0.33 m of absolute `s` over
 *   this window, millimetres about 0.03 m, for one extra digit.
 * - `dCm` — lateral offset in centimetres. 1 cm is a quarter of the measured
 *   standard deviation of `d`, so the quantisation is well inside the signal.
 * - `lapStartS` / `lapStartT` — the **official** lap boundaries. Kept because
 *   they are not the same thing as the geometric `floor(s / L)`: `s = 0` is point
 *   0 of the median lap rather than the surveyed painted line, and the extractor
 *   measures the two disagreeing by up to 13 m.
 *
 * There is deliberately no speed channel and no colour. Speed is derived here
 * from `s` so the two cannot disagree, and colour comes from `PALETTE` so the
 * rule about liveries in CLAUDE.md lives in one place.
 */
export interface ReplayJson {
  name: string
  year: number
  session: string
  /** The frame length the projection used. Cross-checked at parse time. */
  trackLengthM: number
  hz: number
  /** Session time of sample 0. For cross-referencing FastF1, not for playback. */
  t0S: number
  /** Samples per car. Every car has the same count. */
  samples: number
  fromLap: number
  toLap: number
  /** The `|d|` above which the extractor called a sample "in the pit lane". */
  pitAbsDM: number
  cars: {
    code: string
    name: string
    s0M: number
    dsMm: number[]
    dCm: number[]
    lapNumber: number[]
    lapStartS: number[]
    lapStartT: number[]
  }[]
}

/** One car's replay channels. Metres and seconds throughout. */
export interface ReplayCar extends CarIdentity {
  /** Three-letter driver code, e.g. `VER`. Also used as the swatch label. */
  code: string
  /**
   * Arc length, metres, **unwrapped** — it grows past the lap length and is
   * never passed through `wrapS`. See `src/cars/motion.ts`.
   */
  sUnwrapped: Float64Array
  /** Lateral offset, metres, positive to the right of the direction of travel. */
  d: Float64Array
  /** Derived at load from `sUnwrapped`; never read from the file. */
  speedMps: Float64Array
  /** Official lap number starting at each `lapStartS` / `lapStartT`. */
  lapNumber: number[]
  lapStartS: Float64Array
  /** Seconds since the start of the replay. */
  lapStartT: Float64Array
}

/** Parsed replay. Metres, seconds, and `Float64Array` channels. */
export interface Replay {
  name: string
  year: number
  session: string
  trackLengthM: number
  hz: number
  /** `1 / hz`, precomputed because every sample lookup divides by it. */
  dtS: number
  samples: number
  durationS: number
  fromLap: number
  toLap: number
  pitAbsDM: number
  cars: ReplayCar[]
}
