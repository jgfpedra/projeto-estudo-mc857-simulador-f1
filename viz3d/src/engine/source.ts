import type { MotionSource, MotionState } from '../cars/motion'
import type { PitEvent, Recording } from './types'

/** Same floor, same reason, as `replay/source.ts`: the rig ignores speed <= 0. */
const MIN_REPORTED_MPS = 1e-3

/**
 * Engine heading to the car mesh's yaw about +y.
 *
 * The engine's heading is anticlockwise from +x in its own plan, so its
 * direction is `(cos h, sin h)`, which in Three.js is `(cos h, 0, -sin h)`. The
 * mesh faces local -Z, and a rotation `phi` about +y takes -Z to
 * `(-sin phi, 0, -cos phi)`. Matching the two gives `phi = h - pi/2`. A pure
 * rotation about one axis, so the matrix built from it has determinant +1 and
 * check J has nothing to catch - unless someone composes a mirror in later.
 */
export function engineYaw(headingRad: number): number {
  return headingRad - Math.PI / 2
}

/** Shortest-way interpolation between two angles, radians. */
function lerpAngle(a: number, b: number, f: number): number {
  const d = Math.atan2(Math.sin(b - a), Math.cos(b - a))
  return a + d * f
}

/**
 * Where the clock is in the recording: tick index `i` and the fraction `f`
 * towards `i + 1`. Clock time 0 is the first recorded tick. Direct index, no
 * search: `parseRecording` refuses a recording whose ticks are not uniform.
 */
export function tickAt(rec: Recording, tS: number): { i: number; f: number } {
  const x = tS / rec.dtS
  const i = Math.min(Math.max(Math.floor(x), 0), rec.ticks - 2)
  const f = Math.min(Math.max(x - i, 0), 1)
  return { i, f }
}

/** `progress_m` of one car at clock time `tS`, linear between ticks. */
export function progressAt(rec: Recording, tS: number, car: number): number {
  const { i, f } = tickAt(rec, tS)
  const n = rec.cars.length
  const a = rec.progressM[i * n + car]
  return a + (rec.progressM[(i + 1) * n + car] - a) * f
}

/**
 * Running position at clock time `tS`, from interpolated `progress_m`.
 *
 * Ties go to the lower grid slot, which is what the engine's `ranked_drivers`
 * does (a stable sort over the grid-ordered driver list). At every tick instant
 * the interpolation is exact, so this reproduces the recorded `position`
 * there; `engine.test.ts` asserts it over the whole fixture.
 */
export function positionAt(rec: Recording, tS: number, car: number): number {
  const mine = progressAt(rec, tS, car)
  let ahead = 0
  for (let k = 0; k < rec.cars.length; k++) {
    if (k === car) continue
    const p = progressAt(rec, tS, k)
    if (p > mine || (p === mine && k < car)) ahead++
  }
  return ahead + 1
}

/** The engine's own lap counter at the tick at or before `tS`. */
export function lapAtTime(rec: Recording, tS: number, car: number): number {
  const { i, f } = tickAt(rec, tS)
  const k = f >= 1 ? i + 1 : i
  return rec.lap[k * rec.cars.length + car]
}

/** What the panel and the timeline show about a car's pit state at one tick. */
export interface PitReadout {
  /** The engine's own `pitting` flag at that tick. */
  pitting: boolean
  compound: string
  tyreLifePct: number
  /** NaN when the recording has no `fuel_kg`. */
  fuelKg: number
  stops: number
  /** Pit time waiting to be added to the lap now being driven, seconds. */
  penaltyPendingS: number
  /**
   * The stop whose penalty is still pending: from the tick of the stop to the
   * next lap completion, the window in which this car is "pitting" in any
   * sense the engine has.
   */
  active: PitEvent | null
}

/**
 * Pit state of one car at the tick at or before `tS`, like `lapAtTime`.
 *
 * The engine never stops a car for a pit (phase 3b doc, section 4): the stop is
 * done inside the `_complete_lap` call that ends the lap, tyres and fuel change
 * on that tick, `pitting` is set false, and the pit time is held in
 * `pit_penalty_pending_s` until the next lap completes, when it is added to that
 * lap's time. So "pitting" here is that pending window, not a place.
 */
export function pitStateAt(rec: Recording, tS: number, car: number): PitReadout {
  const { i, f } = tickAt(rec, tS)
  const k = f >= 1 ? i + 1 : i
  const j = k * rec.cars.length + car
  const pending = rec.pitPenaltyS[j]
  let active: PitEvent | null = null
  for (const e of rec.pitEvents) {
    if (e.car !== car || e.tick > k) continue
    if (rec.hasPitFields ? pending > 0 : rec.lap[j] === e.lap) active = e
  }
  return {
    pitting: rec.pitting[j] === 1,
    compound: rec.compounds[rec.tyreCompound[j]],
    tyreLifePct: rec.tyreLifePct[j],
    fuelKg: rec.fuelKg[j],
    stops: rec.pitStops[j],
    penaltyPendingS: pending,
    active,
  }
}

/** The panel's tyre line: compound, life, stops. */
export function tyreText(p: PitReadout): string {
  const stops = `${p.stops} stop${p.stops === 1 ? '' : 's'}`
  return `${p.compound} ${p.tyreLifePct.toFixed(1)}% · ${stops}`
}

/** The panel's pit line, empty when the car has nothing pending. */
export function pitText(p: PitReadout): string {
  if (p.active) {
    const e = p.active
    return (
      `PIT end of lap ${e.lap}: ${e.compoundBefore} (${e.lifeBefore.toFixed(1)}% before that lap) → ` +
      `${e.compoundAfter} ${e.lifeAfter.toFixed(1)}%, +${p.penaltyPendingS.toFixed(1)} s ` +
      `on lap ${e.lap + 1}'s time (car not stopped)`
    )
  }
  return p.pitting ? 'PITTING (engine flag)' : ''
}

/**
 * An engine recording as a `MotionSource`.
 *
 * **Placement is by the engine's own pose**, `position_xy` and `heading_deg`,
 * not by `(s, d)`: the engine is the authority on where its cars are, and that
 * includes a car off the edge where the refined projector's identity is no
 * longer guaranteed (phase 0 report section 5). The pose is interpolated
 * linearly between ticks, heading the short way round. At 10 Hz that cuts a
 * corner by 7 mm at the median and 73 mm at worst over the seed-42 race
 * (`check_recording.py`, chord sag), so a spline would buy nothing visible.
 *
 * **`sUnwrapped` is `progress_m`**, interpolated linearly. The frame
 * `trackFromRecording` builds starts at the start/finish waypoint, so
 * `progress_m` is an unwrapped `s` on it and needs no offset. It drives
 * everything that wants a distance along the track: the chase camera's damped
 * trail, lookahead and the T-cam's roll, the wheel odometer and the running
 * order. Where the cameras sit relative to the car comes from the pose, not
 * from here (`rig.ts`, `chasePose` / `onboardPose`). `d` is `d_m`, for the
 * panel and the chase camera's lateral.
 *
 * `speedMps` is the rate `progress_m` advances, not `velocity_mps`: the rig feeds
 * it forward into a trail that follows `progress_m`, and the two must agree.
 */
export function engineSource(rec: Recording): MotionSource {
  const n = rec.cars.length
  return {
    kind: 'engine',
    cars: rec.cars,
    durationS: rec.durationS,
    sampleInto(tSeconds: number, car: number, out: MotionState): MotionState {
      if (car < 0 || car >= n) {
        out.sUnwrapped = 0
        out.d = 0
        out.speedMps = 0
        out.posed = false
        return out
      }
      const { i, f } = tickAt(rec, tSeconds)
      const a = i * n + car
      const b = a + n
      const lerp = (ch: Float64Array) => ch[a] + (ch[b] - ch[a]) * f
      out.sUnwrapped = lerp(rec.progressM)
      out.d = lerp(rec.dM)
      out.speedMps = Math.max(lerp(rec.paceMps), MIN_REPORTED_MPS)
      out.posed = true
      // CLAUDE.md: three.x = x, three.z = -y.
      out.x = lerp(rec.x)
      out.z = -lerp(rec.y)
      out.yawRad = engineYaw(lerpAngle(rec.headingRad[a], rec.headingRad[b], f))
      return out
    },
    originM(car: number): number {
      return rec.progressM[car] ?? 0
    },
  }
}
