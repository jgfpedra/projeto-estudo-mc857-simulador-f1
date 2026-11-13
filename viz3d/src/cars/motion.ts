/**
 * What the car renderer needs from a motion source, and nothing else.
 *
 * `Grid` used to read a `CarSpec[]` and integrate `s` itself. Two motion
 * sources — the synthetic field and a telemetry replay — cannot share that:
 * one is generated, the other is sampled from a file, and a replay has a clock
 * that can be scrubbed. So the renderer asks a question instead of being handed
 * a state: *where is car `i` at replay time `t`*.
 *
 * **The invariant this interface exists to carry.** `sUnwrapped` is metres
 * since the replay began, growing without bound, and it is never passed through
 * `wrapS`. Only `toWorld` wraps, internally, at the moment it evaluates the
 * spline. That is the same discipline `src/cameras/rig.ts` documents at its
 * head, and the reason the start/finish seam is a non-event rather than a case
 * to handle: nothing subtracts two wrapped values, so no quantity can jump by a
 * lap length when a car crosses the line.
 *
 * It also removes an integration rather than adding one. `sampleInto` is a pure
 * function of `t`, so the wheel odometer becomes `sUnwrapped - originM(car)`
 * instead of an accumulator — which makes wheel phase a function of position,
 * so scrubbing a replay backwards rewinds the wheels instead of leaving them
 * wherever the accumulator had got to. After this the car path integrates
 * nothing at all; the only remaining integration in the project is the camera
 * rig's damped anchor, and that is a filter rather than kinematics.
 */

/**
 * Who a car is, independent of where its motion comes from.
 *
 * The panels need this and nothing else, which is what lets one `CarPanel`
 * serve a synthetic field and a real grid. `CarSpec` in `field.ts` extends it,
 * so `buildField`'s output satisfies it unchanged.
 */
export interface CarIdentity {
  index: number
  /** Short label for the swatch: `#7` for the synthetic field, `VER` for a replay. */
  label: string
  colourName: string
  hex: string
  /** Full name, where there is a real one to show. */
  name?: string
}

/** One car's motion at one instant. Caller-owned and mutated, never allocated. */
export interface MotionState {
  /** Metres since the replay began. Never wrapped — see the module comment. */
  sUnwrapped: number
  /** Lateral offset, metres, positive to the right of the direction of travel. */
  d: number
  /**
   * Along-track ground speed, m/s. The car's *physical* speed, not the rate the
   * playback clock is advancing: `CameraRig` applies the replay rate to its own
   * `dtS` instead, so this field keeps one meaning for every consumer.
   */
  speedMps: number
  /**
   * True when the source knows the car's world pose itself and `x`, `z`,
   * `yawRad` are set - the engine recording, whose cars are placed where the
   * engine put them. False for the synthetic field and the replay, which are
   * placed by `(s, d)` through `toWorld`. Every source writes this on every call:
   * `Grid` reuses one `MotionState` across a source switch.
   */
  posed: boolean
  /** Three.js world x, metres. Only meaningful when `posed`. */
  x: number
  /** Three.js world z, metres (`-y` of the engine plan). Only when `posed`. */
  z: number
  /** Rotation of the mesh about +y, radians; 0 faces -Z. Only when `posed`. */
  yawRad: number
}

export type SourceKind = 'synthetic' | 'replay' | 'engine'

/**
 * In the order the panel and the `m` key present them. A track offers
 * `synthetic` plus at most one of `replay` (our Monza) or `engine` (a
 * recording), never both: each was made against exactly one centreline.
 */
export const SOURCE_KINDS: readonly SourceKind[] = ['synthetic', 'replay', 'engine']

export interface MotionSource {
  readonly kind: SourceKind
  readonly cars: CarIdentity[]
  /** Seconds of content. `Infinity` for the synthetic field, which never ends. */
  readonly durationS: number
  /**
   * Motion at replay time `tSeconds`. Pure: the same `t` must give the same
   * answer, so that scrubbing is repeatable and a paused frame is stable.
   */
  sampleInto(tSeconds: number, carIndex: number, out: MotionState): MotionState
  /** `sUnwrapped` at `t = 0`, so the wheel odometer is derived, not integrated. */
  originM(carIndex: number): number
}

export function newMotionState(): MotionState {
  return { sUnwrapped: 0, d: 0, speedMps: 0, posed: false, x: 0, z: 0, yawRad: 0 }
}
