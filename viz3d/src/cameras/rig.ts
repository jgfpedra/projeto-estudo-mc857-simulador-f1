/**
 * Camera rig maths: where the chase and onboard cameras sit, and where they aim.
 *
 * Pure, and deliberately free of React and react-three-fiber so it can be swept
 * around the lap under `vitest` — which runs in the node environment here, with
 * no jsdom and no setup file. `CameraRig.tsx` is the thin layer that calls this
 * once a frame and copies the result onto the camera.
 *
 * **The invariant this module exists to hold.** Every arc length here is
 * *unwrapped* — metres travelled since the session began, growing without
 * bound, never passed through `wrapS`. Only `toWorld` wraps, internally, at the
 * moment it evaluates the spline. That is the same trick that keeps the wheels
 * from snapping back once a lap in `Grid.tsx`, and it is what makes the
 * start/finish seam a non-event: nothing here ever subtracts two wrapped values,
 * so there is no quantity that can jump by a lap length when `s` crosses zero.
 *
 * Float64 holds this comfortably. An hour at 60 m/s is 216 km, where the gap
 * between representable doubles is about 3e-11 m.
 */

import { MathUtils, Vector3 } from 'three'
import { curvatureAt, toWorld } from '../track/frame'
import type { TrackFrame } from '../track/frame'
import { MAX_DELTA_S } from '../cars/field'

/** Flat circuit, so this is also the surface normal everywhere on Monza. */
const WORLD_UP = new Vector3(0, 1, 0)

/** Standard gravity, m/s^2. Only used to express the roll gain in units of g. */
const G = 9.80665

/**
 * The three cameras, in the order the panel and the number keys present them.
 * Declared here rather than in `CameraRig.tsx` so `CameraPanel` — plain DOM,
 * outside the Canvas — can name a mode without importing anything from r3f.
 */
export type CameraMode = 'orbit' | 'chase' | 'onboard'
export const CAMERA_MODES: readonly CameraMode[] = ['orbit', 'chase', 'onboard']

/** The followed car's live state, written once a frame by `Grid`. */
export interface FollowState {
  /** Wrapped arc length, metres. For the readout; the rig does not use it. */
  s: number
  /**
   * Unwrapped arc length, metres: the car's `s0` plus its odometer. This is the
   * quantity the rig follows, and the reason the seam is not a special case.
   */
  sUnwrapped: number
  /** Lateral offset, metres, positive to the right of the direction of travel. */
  d: number
  speedMps: number
  /** Which car this is, so the rig can tell a selection change from motion. */
  carIndex: number
  /**
   * The car's own world pose, copied from `MotionState` (see there). When
   * `posed` - the engine recording - the T-cam is bolted to this pose and the
   * chase camera is anchored on its position; otherwise both follow `(s, d)`
   * and `x`, `z`, `yawRad` are ignored.
   */
  posed: boolean
  x: number
  z: number
  yawRad: number
}

/** Everything the rig carries between frames. Mutated in place, never allocated. */
export interface RigState {
  /** The chase camera's own unwrapped arc length. Lags the car by `trailM`. */
  u: number
  /** Roll about the view direction, radians. Onboard only. */
  roll: number
  /** The car `u` and `roll` were last stepped for. `-1` means unseeded. */
  carIndex: number
}

export interface CameraPose {
  position: Vector3
  target: Vector3
  up: Vector3
  /**
   * The point on the ground the camera is following: the car. `toWorld(s, d)`
   * for a source placed by `(s, d)`, the car's own position for a posed one.
   * Not used to aim the camera; written so tests can hold the rig to the car.
   */
  anchor: Vector3
}

export interface ChaseConfig {
  /** How far behind the car the camera rides, metres along the centreline. */
  trailM: number
  /** Height above the track surface, metres. */
  heightM: number
  /** How far *ahead* of the car the aim point sits, metres. */
  lookaheadM: number
  targetHeightM: number
  /** Damping time constant, seconds. */
  tauS: number
  fovDeg: number
}

export interface OnboardConfig {
  /** Offset from the car centre along the track, metres. Negative is behind. */
  fwdM: number
  heightM: number
  lookaheadM: number
  targetHeightM: number
  /** Damping time constant for the roll, seconds. */
  rollTauS: number
  /** Roll at saturation, radians. */
  maxRollRad: number
  /** Lateral acceleration at which the roll reaches `maxRollRad`, m/s^2. */
  refLatAccelMps2: number
  /** Half-width of the curvature low-pass, metres. */
  curvatureSpanM: number
  fovDeg: number
}

/**
 * Behind and above, aimed 25 m up the road.
 *
 * `lookaheadM` is an order of magnitude larger than `heightM` on purpose: the
 * view direction has to stay well away from world up, or `Matrix4.lookAt` starts
 * amplifying float noise into roll. Measured worst case over a lap is 85.4
 * degrees off vertical, and `rig.test.ts` asserts a 10 degree floor.
 */
export const CHASE: ChaseConfig = {
  trailM: 9,
  heightM: 3.2,
  lookaheadM: 25,
  targetHeightM: 0.8,
  tauS: 0.3,
  fovDeg: 45,
}

/**
 * T-cam: above and just behind the car, looking along its length.
 *
 * `fwdM` is negative — *behind* the car's centre — which is what puts the whole
 * car in frame. The camera sits 2.6 m back and 2.1 m up, so the model's nose
 * (half-length 1.85 m, y ~ 0.3) is 18 degrees below the view axis and the front
 * wheels, sidepods and engine cover all read, with the rear wing behind the
 * camera and out of shot.
 *
 * The first attempt was 0.9 m back and 1.25 m up, from the airbox height of a
 * real car. It was unusable, and the reason is a property of *this* model rather
 * than of the idea: scaled to a 2.0 m width it stands 1.09 m tall, so a camera
 * at 1.25 m was 16 cm above its own roll hoop and the bodywork filled the frame.
 * A placeholder that is 3.69 m long where a real car is 5.6 m does not get to
 * keep the real car's camera positions.
 *
 * Aiming at the surface 30 m ahead rather than at eye height tilts the axis down
 * by 3.7 degrees, which is what lifts the car off the bottom edge. `heightM` and
 * `fwdM` were settled by looking at the render; everything else follows.
 */
export const ONBOARD: OnboardConfig = {
  fwdM: -2.6,
  heightM: 2.1,
  lookaheadM: 30,
  targetHeightM: 0.0,
  rollTauS: 0.35,
  maxRollRad: MathUtils.degToRad(6),
  // 4 g. The field holds 60 m/s through every corner — there is no curvature
  // slowdown yet, see design doc section 6A — so the honest lateral
  // acceleration peaks at 18.7 g at Rettifilo and this clamp is load-bearing,
  // not a safety net. Against the *smoothed* curvature the lap's p90 is 3.2 g
  // and its p99 is 7.7 g, so 4 g leaves the roll saturated over 7.0% of the lap:
  // every real corner, and nothing else. `rig.test.ts` pins that budget.
  refLatAccelMps2: 4 * G,
  curvatureSpanM: 15,
  fovDeg: 72,
}

export function newRigState(): RigState {
  return { u: 0, roll: 0, carIndex: -1 }
}

export function newPose(): CameraPose {
  return {
    position: new Vector3(),
    target: new Vector3(),
    up: new Vector3(0, 1, 0),
    anchor: new Vector3(),
  }
}

/** Taps in the curvature low-pass. Odd, so one of them lands on `s` itself. */
const CURVATURE_TAPS = 7

/**
 * Curvature at `s`, low-passed over +/- `spanM` of arc length.
 *
 * Smoothing in *distance* rather than in time, which is the part that matters.
 * `curvatureAt` interpolates linearly between 5 m samples, so the raw signal is
 * piecewise linear with a kink at every sample — twelve a second at 60 m/s — and
 * the centreline underneath it is a median of racing lines, which carries noise
 * at that same scale. Damping in time cannot substitute: a first-order lag
 * attenuates the kinks without removing them, and widening it enough to try
 * drags the corner entry with it. Seven taps over +/-15 m lands one tap on each
 * centreline sample and cuts the peak target-roll rate over a lap from 124 to
 * 83 deg/s, while still resolving Rettifilo, which is about 50 m long.
 *
 * Monza's main straight turns out not to have needed this. The raw curvature
 * there peaks at 0.00028 /m — a tenth of a g at 60 m/s, 0.15 degrees of roll —
 * so the horizon was never going to tilt on it. This is for the kinks, not for a
 * wander that is not there.
 */
export function smoothCurvature(frame: TrackFrame, s: number, spanM: number): number {
  let sum = 0
  for (let k = 0; k < CURVATURE_TAPS; k++) {
    const t = (k / (CURVATURE_TAPS - 1)) * 2 - 1
    sum += curvatureAt(frame, s + t * spanM)
  }
  return sum / CURVATURE_TAPS
}

/**
 * The roll the onboard camera would settle at right now, radians.
 *
 * Driven by lateral acceleration, `curvature * speed^2`, rather than by
 * curvature alone: it stays right when M6's telemetry replay brings real speed
 * variation, where a corner taken slowly should not bank like one taken flat.
 * Positive curvature is a right-hand turn, and a positive roll about the view
 * direction rolls the camera clockwise, so the camera banks *into* the corner.
 */
export function targetRoll(
  frame: TrackFrame,
  follow: FollowState,
  cfg: OnboardConfig,
): number {
  const lateral =
    smoothCurvature(frame, follow.sUnwrapped, cfg.curvatureSpanM) *
    follow.speedMps *
    follow.speedMps
  return cfg.maxRollRad * MathUtils.clamp(lateral / cfg.refLatAccelMps2, -1, 1)
}

/**
 * Advance the rig by `dtS` seconds.
 *
 * **The feed-forward term is not optional.** `MathUtils.damp` is
 * `dx/dt = lambda (y - x)`, and the target here is a *ramp*: it advances at the
 * car's speed. A first-order lag chasing a ramp settles a constant `v * tau`
 * behind it, which at 60 m/s with tau = 0.3 s is 15 m of trail nobody asked for
 * — set `trailM` to 9 and film from 24 m back, then "fix" it by shrinking
 * `trailM` until the transient behaviour is wrong instead. Riding the ramp first
 * and damping only the residual leaves no steady-state error while keeping
 * exactly the transient the damping exists for, which is what will matter in M6
 * when the speed stops being constant.
 *
 * The step is capped for the same reason `Grid` caps its own: a hidden tab hands
 * back one enormous `delta`, and the rig would otherwise resolve hundreds of
 * metres of stale target in a single frame.
 */
export function stepRig(
  state: RigState,
  frame: TrackFrame,
  follow: FollowState,
  dtS: number,
  chase: ChaseConfig = CHASE,
  onboard: OnboardConfig = ONBOARD,
): void {
  // `Grid`'s `useFrame` returns early until a passive effect has seeded its
  // arrays, and StrictMode runs that path twice, so the first frames can hand
  // over a zeroed readout. Seeding off one of those would put the camera at the
  // world origin and then damp it across the circuit.
  if (follow.speedMps <= 0) return

  const roll = targetRoll(frame, follow, onboard)

  if (state.carIndex !== follow.carIndex) {
    state.carIndex = follow.carIndex
    state.u = follow.sUnwrapped - chase.trailM
    state.roll = roll
    return
  }

  const dt = Math.min(dtS, MAX_DELTA_S)
  state.u += follow.speedMps * dt
  state.u = MathUtils.damp(state.u, follow.sUnwrapped - chase.trailM, 1 / chase.tauS, dt)
  state.roll = MathUtils.damp(state.roll, roll, 1 / onboard.rollTauS, dt)
}

/** Reused by the pose functions. `toWorld` keeps its own and consumes it before returning. */
const view = new Vector3()
const shift = new Vector3()
const forward = new Vector3()

/**
 * Where the chase camera is and what it looks at.
 *
 * Position comes from the rig's own damped anchor; the aim point comes from the
 * car's arc length plus the lookahead, so the camera leads the car up the road
 * rather than staring at it. Both go through `toWorld` and nothing else —
 * `frame.ts` stays the one place `(s, d)` becomes world coordinates.
 *
 * **A posed car** (the engine recording) is not where `toWorld(s, d)` says:
 * `progress_m` is the engine's own along-track measure, and on the ground it
 * sits up to 0.86 m from the car (seed 42; docs/phase3-engine-race.md
 * section 4). So the whole pose above is translated by the car's position
 * minus `toWorld(s, d)`. That puts the anchor on the car and leaves everything
 * else as it was: the view direction is still the track's, `progress_m` plus
 * the lookahead, and the trail is still the damped `u`. Taking the direction
 * from the car's heading instead would swing the camera through 70 degrees as
 * a stopped car turns back onto the track, which is the one thing a chase
 * camera must not do.
 */
export function chasePose(
  frame: TrackFrame,
  state: RigState,
  follow: FollowState,
  cfg: ChaseConfig,
  out: CameraPose,
): CameraPose {
  toWorld(frame, state.u, follow.d, cfg.heightM, out.position)
  toWorld(frame, follow.sUnwrapped + cfg.lookaheadM, follow.d, cfg.targetHeightM, out.target)
  toWorld(frame, follow.sUnwrapped, follow.d, 0, out.anchor)
  if (follow.posed) {
    shift.set(follow.x - out.anchor.x, 0, follow.z - out.anchor.z)
    out.anchor.add(shift)
    out.position.add(shift)
    out.target.add(shift)
  }
  out.up.copy(WORLD_UP)
  return out
}

/**
 * The T-cam bolted to a posed car: its offsets taken in the car's own frame.
 *
 * `fwdM` and `lookaheadM` run along the nose, `heightM` and `targetHeightM` are
 * above the ground under the car (`toWorld(s, d)`'s height; the engine's track
 * is flat), and there is no lateral offset - the car is on its own centreline.
 * The mesh faces local -Z and `yawRad` turns it about +y, so the nose points
 * along `(-sin yaw, 0, -cos yaw)`.
 */
function posedOnboard(follow: FollowState, groundY: number, cfg: OnboardConfig, out: CameraPose) {
  forward.set(-Math.sin(follow.yawRad), 0, -Math.cos(follow.yawRad))
  out.anchor.set(follow.x, groundY, follow.z)
  out.position.copy(out.anchor).addScaledVector(forward, cfg.fwdM)
  out.position.y += cfg.heightM
  out.target.copy(out.anchor).addScaledVector(forward, cfg.lookaheadM)
  out.target.y += cfg.targetHeightM
}

/**
 * Where the T-cam is and what it looks at.
 *
 * Undamped in position: it is bolted to the car, and the only thing that eases
 * is the roll. `up` is rebuilt from world up on every call rather than rotated
 * incrementally, so the roll cannot compound. Rotating about the view direction
 * is also what keeps it safe — that rotation preserves the angle between `up`
 * and the view direction by construction, so no amount of roll can drive
 * `Matrix4.lookAt` towards its degenerate case.
 *
 * For a posed car, position and aim come from the car's own pose instead
 * (`posedOnboard`), so the camera stays 2.6 m behind the car's centre and looks
 * along its nose even where `progress_m` disagrees with the pose or the car is
 * at an angle to the track. The roll is unchanged: still banked on the track's
 * curvature at `progress_m`.
 */
export function onboardPose(
  frame: TrackFrame,
  state: RigState,
  follow: FollowState,
  cfg: OnboardConfig,
  out: CameraPose,
): CameraPose {
  toWorld(frame, follow.sUnwrapped, follow.d, 0, out.anchor)
  if (follow.posed) {
    posedOnboard(follow, out.anchor.y, cfg, out)
  } else {
    toWorld(frame, follow.sUnwrapped + cfg.fwdM, follow.d, cfg.heightM, out.position)
    toWorld(frame, follow.sUnwrapped + cfg.lookaheadM, follow.d, cfg.targetHeightM, out.target)
  }
  view.subVectors(out.target, out.position).normalize()
  out.up.copy(WORLD_UP).applyAxisAngle(view, state.roll)
  return out
}
