import { Vector3 } from 'three'
import type { Track } from './types'

/** World-space up. Monza is flat; banking will make this per-sample later. */
const UP = new Vector3(0, 1, 0)

export interface TrackFrame {
  /** Cumulative arc length at each centreline sample, metres, s[0] = 0. */
  s: Float64Array
  /** Measured lap length: sum of segment lengths including the closing one. */
  lengthM: number
  points: Vector3[]
  /** Unit tangent, direction of travel. */
  tangent: Vector3[]
  /** Unit vector pointing to the RIGHT of the direction of travel. */
  right: Vector3[]
  /** Surface normal. `up = right x tangent`, so it is +y on a flat track. */
  up: Vector3[]
  /** Signed curvature, 1/m. Positive = turning right. */
  curvature: Float64Array
}

export interface Sample {
  position: Vector3
  tangent: Vector3
  right: Vector3
  up: Vector3
}

const wrapIndex = (i: number, n: number) => (i + n) % n

/**
 * Build the Frenet frame used by every `(s, d) -> world` conversion.
 *
 * Handedness convention, fixed here and nowhere else: with y up,
 *
 *     right = tangent x up        up = right x tangent
 *
 * Face along -z with y up and your right hand points to +x; `tangent x up`
 * reproduces that. Flipping this sign mirrors every lateral offset in the
 * simulation, so it is asserted in `verify.ts` rather than trusted.
 *
 * Despite the name, this is a *road* frame and deliberately not the textbook
 * Frenet frame. The Frenet normal is `dt/ds`: it points to the inside of the
 * turn, is undefined on a straight, and **flips sign wherever curvature
 * crosses zero** — which here is every straight and the midpoint of every
 * chicane. A frame built that way would invert anything placed on the ribbon,
 * twice per chicane. Deriving `up` from a fixed world up instead makes it
 * constant on a flat circuit, and it will vary only with banking when banking
 * arrives. `curvature` below is computed *from* this frame, never the reverse.
 *
 * The one degenerate case is a tangent parallel to world up — a vertical
 * track. No circuit does this, and a banked one will supply a per-sample `up`
 * before it could.
 */
export function buildFrame(track: Track): TrackFrame {
  const points = track.points
  const n = points.length

  const s = new Float64Array(n)
  let total = 0
  for (let i = 0; i < n; i++) {
    s[i] = total
    total += points[i].distanceTo(points[wrapIndex(i + 1, n)])
  }

  const tangent: Vector3[] = []
  const right: Vector3[] = []
  const up: Vector3[] = []
  for (let i = 0; i < n; i++) {
    // Central difference: less sensitive to sample noise than a forward one.
    const t = new Vector3()
      .subVectors(points[wrapIndex(i + 1, n)], points[wrapIndex(i - 1, n)])
      .normalize()
    const r = new Vector3().crossVectors(t, UP).normalize()
    tangent.push(t)
    right.push(r)
    up.push(new Vector3().crossVectors(r, t).normalize())
  }

  // Signed curvature: how fast the tangent rotates towards `right`.
  const curvature = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    const prev = wrapIndex(i - 1, n)
    const next = wrapIndex(i + 1, n)
    const ds = (s[next] - s[prev] + total) % total
    const dt = new Vector3().subVectors(tangent[next], tangent[prev])
    curvature[i] = ds > 0 ? dt.dot(right[i]) / ds : 0
  }

  return { s, lengthM: total, points, tangent, right, up, curvature }
}

/** Wrap an arc length into [0, lengthM). */
export function wrapS(frame: TrackFrame, s: number): number {
  const L = frame.lengthM
  return ((s % L) + L) % L
}

/**
 * Index of the sample at or before `s`, for `s` already wrapped.
 * Binary search rather than `s / spacingM`: spacing is near-uniform, not
 * exactly uniform, and this stays correct if that ever stops being true.
 */
function segmentIndex(frame: TrackFrame, s: number): number {
  const arr = frame.s
  let lo = 0
  let hi = arr.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (arr[mid] <= s) lo = mid
    else hi = mid - 1
  }
  return lo
}

/**
 * Evaluate the centreline at arc length `s`.
 *
 * Linear interpolation between samples, not a spline evaluation: at 5 m
 * spacing the chord error on Monza's tightest corner (19.54 m radius) is
 * 16.0 cm, which is far below anything visible at these camera distances. If a
 * later milestone needs C1 continuity for camera motion, swap the body of this
 * function — every caller goes through it.
 */
export function sampleAt(frame: TrackFrame, s: number, out?: Sample): Sample {
  const n = frame.points.length
  const sw = wrapS(frame, s)
  const i = segmentIndex(frame, sw)
  const j = wrapIndex(i + 1, n)
  const segLen = (frame.s[j] - frame.s[i] + frame.lengthM) % frame.lengthM
  const t = segLen > 0 ? (sw - frame.s[i]) / segLen : 0

  const target: Sample = out ?? {
    position: new Vector3(),
    tangent: new Vector3(),
    right: new Vector3(),
    up: new Vector3(),
  }
  target.position.lerpVectors(frame.points[i], frame.points[j], t)
  target.tangent.lerpVectors(frame.tangent[i], frame.tangent[j], t).normalize()
  target.right.crossVectors(target.tangent, UP).normalize()
  target.up.crossVectors(target.right, target.tangent).normalize()
  return target
}

/** Reused by `toWorld` so per-frame calls in later milestones don't allocate. */
const scratch: Sample = {
  position: new Vector3(),
  tangent: new Vector3(),
  right: new Vector3(),
  up: new Vector3(),
}

/**
 * The one conversion the whole project hangs off: `(s, d)` to world position.
 *
 * `d` is metres from the centreline, positive to the right of the direction of
 * travel. `h` lifts the result off the surface, for markers that would
 * otherwise z-fight with the ribbon.
 */
export function toWorld(
  frame: TrackFrame,
  s: number,
  d = 0,
  h = 0,
  out = new Vector3(),
): Vector3 {
  const sample = sampleAt(frame, s, scratch)
  return out
    .copy(sample.position)
    .addScaledVector(sample.right, d)
    .addScaledVector(sample.up, h)
}

/** Signed curvature at `s`. Positive = the track turns right here. */
export function curvatureAt(frame: TrackFrame, s: number): number {
  const sw = wrapS(frame, s)
  const i = segmentIndex(frame, sw)
  const j = wrapIndex(i + 1, frame.points.length)
  const segLen = (frame.s[j] - frame.s[i] + frame.lengthM) % frame.lengthM
  const t = segLen > 0 ? (sw - frame.s[i]) / segLen : 0
  return frame.curvature[i] * (1 - t) + frame.curvature[j] * t
}
