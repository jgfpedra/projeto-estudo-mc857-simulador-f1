import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { MathUtils, Matrix4, Quaternion, Vector3 } from 'three'
import { buildFrame, sampleAt, toWorld, wrapS } from '../track/frame'
import type { Sample, TrackFrame } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { carBasis, placeCar } from '../cars/place'
import {
  CHASE,
  ONBOARD,
  chasePose,
  newPose,
  newRigState,
  onboardPose,
  stepRig,
  targetRoll,
} from './rig'
import type { FollowState, RigState } from './rig'

/**
 * The committed track, read off disk through the real `parseTrack` — the same
 * idiom as `frame.test.ts` and for the same reason. A synthetic loop would not
 * have the property under test, which is that the seam between the last sample
 * and sample 0 is not a special case for anything the camera does.
 */
function loadMonza(): TrackFrame {
  const url = new URL('../../public/tracks/monza.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

/** `Grid` owns this; duplicated here as `grid.test.ts` already duplicates it. */
const RIDE_HEIGHT_M = 0.01

const SPEED_MPS = 60
const DT_S = 1 / 60
/** A representative lateral offset, matching `place.test.ts`'s `TEST_D`. */
const TEST_D = 3.0

/**
 * Steady-state trail error allowed, metres. Measured 9e-13 — at constant speed
 * the feed-forward term cancels the target's motion exactly and the damper has
 * nothing left to do. The number this has to stay well under is `v * tau` = 18 m,
 * which is where a plain `damp` against the moving target would sit.
 */
const TRAIL_TOL_M = 0.05

/**
 * Per-step error in the chase camera's world displacement, metres, for the seam
 * sweep. The seam is on the main straight, where the measured value is under a
 * millimetre. A whip across the start/finish line is three orders of magnitude
 * bigger than this, so the tolerance only has to exclude the chord effect below.
 */
const SEAM_POS_TOL_M = 0.02

/**
 * The same quantity over a whole lap, where it is dominated by a real effect
 * rather than by error: a point held `d` metres off the centreline covers
 * `(1 - curvature * d)` of the centreline's arc length. At Rettifilo, with
 * `|curvature| = 0.051` and `d = 3`, that is 15% — 0.163 m measured against a
 * 1.0 m step. The camera is a camera, not an odometer; this is a bound, not a
 * defect.
 */
const LAP_POS_TOL_M = 0.25

/**
 * `Matrix4.lookAt` only guards *exact* parallelism between the view direction
 * and `up` (`_x.lengthSq() === 0`). A degree off, it is fine; a microdegree off,
 * it amplifies float noise into violent roll. Measured worst over a lap is 85.4
 * degrees for the chase camera and 89.1 for the T-cam, so this floor is loose by
 * most of a right angle and still excludes the unstable region entirely.
 */
const MIN_LOOK_ANGLE_DEG = 10

/**
 * Peak rate of change of the *undamped* roll target, deg/s. This is what the
 * curvature low-pass is for: measured 83 deg/s smoothed against 124 deg/s raw,
 * so this threshold is the one assertion that would notice `curvatureSpanM`
 * being set to zero. Asserting the damped roll instead would prove nothing —
 * the damper bounds its own rate whatever it is fed.
 */
const MAX_TARGET_ROLL_RATE_DEG_PER_S = 100

/**
 * Roll allowed on the main straight, degrees. Measured 0.067. The horizon being
 * level on the straights is the property a viewer would notice first, and a sign
 * error or a missing clamp blows straight through this.
 */
const STRAIGHT_ROLL_TOL_DEG = 0.5
/** Clean straight between the start/finish line and the Rettifilo braking zone. */
const STRAIGHT_FROM_M = 150
const STRAIGHT_TO_M = 700

/**
 * Fraction of the lap the roll may spend pinned at the clamp. Measured 0.070.
 * This is what pins `refLatAccelMps2`: too low a reference and the roll is a
 * square wave carrying no information about which corner you are in.
 */
const SATURATION_BUDGET = 0.1

/**
 * Agreement between the T-cam and `placeCar`, metres.
 *
 * These two place the camera by different routes on purpose. `onboardPose` asks
 * the spline for a point `fwdM` further along at the same `d`; `placeCar` puts
 * the car rigidly on its own basis. Over the 2.6 m between them the road frame
 * rotates by 7.6 degrees at Rettifilo and the offset path covers
 * `(1 - curvature * d)` of the centreline's arc, so the two disagree by 0.421 m
 * longitudinally and 0.181 m laterally at the worst point on the lap.
 *
 * That is a real 16% variation in how far back the camera sits, and it is
 * confined to the tightest corner on the circuit. It is the price of routing
 * every world position through `toWorld`, which is the property worth keeping:
 * a rigid mount would need a second path from `(s, d)` into world space, and
 * then there would be two of them to keep honest.
 */
const ON_CAR_TOL_M = 0.6

const EPS = 1e-9

/** Placed by `(s, d)`, as the synthetic field and the replay are. */
const UNPOSED = { posed: false, x: 0, z: 0, yawRad: 0 }

function newFollow(sUnwrapped: number, carIndex = 0): FollowState {
  return { s: 0, sUnwrapped, d: TEST_D, speedMps: SPEED_MPS, carIndex, ...UNPOSED }
}

function newSample(): Sample {
  return {
    position: new Vector3(),
    tangent: new Vector3(),
    right: new Vector3(),
    up: new Vector3(),
  }
}

function angleDeg(a: Vector3, b: Vector3): number {
  return (Math.acos(Math.min(1, Math.max(-1, a.dot(b)))) * 180) / Math.PI
}

const WORLD_UP = new Vector3(0, 1, 0)

interface Step {
  /** Wrapped arc length of the car, for the assertion messages. */
  s: number
  /** How far the chase camera's trail deviates from `CHASE.trailM`, metres. */
  trailError: number
  /** Deviation of the chase camera's world displacement from `speed * dt`. */
  posError: number
  /** Angle between the chase view direction and world up, folded to [0, 90]. */
  chaseLookAngle: number
  onboardLookAngle: number
  /** Is the aim point ahead of the car along the direction of travel? */
  leads: boolean
  /** Damped roll, degrees. */
  rollDeg: number
  /** Rate of change of the *undamped* roll target, deg/s. */
  targetRollRate: number
  saturated: boolean
  /** Signed longitudinal offset of the T-cam from `placeCar`, metres. */
  onCarLong: number
  /** Lateral offset of the T-cam from `placeCar`, metres. */
  onCarLat: number
  finite: boolean
  /** True on the step where the chase anchor's wrapped `s` went backwards. */
  crossedSeam: boolean
}

/**
 * Drive a car from `s0` for `distanceM` at constant speed and record everything
 * both cameras do. One sweep, reduced many ways — the same shape as
 * `place.test.ts`'s `walkLap`.
 */
function drive(frame: TrackFrame, s0: number, distanceM: number): Step[] {
  const follow = newFollow(s0)
  const state = newRigState()
  const chase = newPose()
  const onboard = newPose()
  const sample = newSample()

  const prevChase = new Vector3()
  const carPos = new Vector3()
  const carQuat = new Quaternion()
  const basis = new Matrix4()
  const right = new Vector3()
  const forward = new Vector3()
  const delta = new Vector3()
  const dir = new Vector3()
  const lead = new Vector3()

  let prevWrappedU = 0
  let prevTargetRoll = 0
  const steps: Step[] = []

  for (let k = 0; k * DT_S * SPEED_MPS <= distanceM; k++) {
    follow.sUnwrapped = s0 + k * DT_S * SPEED_MPS
    follow.s = wrapS(frame, follow.sUnwrapped)

    stepRig(state, frame, follow, DT_S)
    chasePose(frame, state, follow, CHASE, chase)
    onboardPose(frame, state, follow, ONBOARD, onboard)

    const wrappedU = wrapS(frame, state.u)
    const raw = targetRoll(frame, follow, ONBOARD)

    // Does the aim point lead the car? Measured against the car's own tangent.
    toWorld(frame, follow.sUnwrapped, follow.d, 0, carPos)
    sampleAt(frame, follow.sUnwrapped, sample)
    lead.subVectors(chase.target, carPos)

    // And is it where `placeCar` would put a camera bolted to the car?
    placeCar(frame, follow.s, follow.d, RIDE_HEIGHT_M, carPos, carQuat)
    carBasis(frame, follow.s, basis)
    right.setFromMatrixColumn(basis, 0)
    forward.setFromMatrixColumn(basis, 2).negate()
    delta.subVectors(onboard.position, carPos)

    dir.subVectors(chase.target, chase.position).normalize()
    const chaseAngle = angleDeg(dir, WORLD_UP)
    dir.subVectors(onboard.target, onboard.position).normalize()
    const onboardAngle = angleDeg(dir, WORLD_UP)

    steps.push({
      s: follow.s,
      trailError: Math.abs(follow.sUnwrapped - state.u - CHASE.trailM),
      posError: k === 0 ? 0 : Math.abs(prevChase.distanceTo(chase.position) - SPEED_MPS * DT_S),
      chaseLookAngle: Math.min(chaseAngle, 180 - chaseAngle),
      onboardLookAngle: Math.min(onboardAngle, 180 - onboardAngle),
      leads: lead.dot(sample.tangent) > 0,
      rollDeg: MathUtils.radToDeg(state.roll),
      targetRollRate: k === 0 ? 0 : Math.abs(MathUtils.radToDeg(raw - prevTargetRoll)) / DT_S,
      saturated: Math.abs(raw) >= ONBOARD.maxRollRad - 1e-12,
      onCarLong: delta.dot(forward),
      onCarLat: delta.dot(right),
      finite:
        [chase.position, chase.target, chase.up, onboard.position, onboard.target, onboard.up]
          .flatMap((v) => v.toArray())
          .every(Number.isFinite) && Number.isFinite(state.u) && Number.isFinite(state.roll),
      crossedSeam: k > 0 && wrappedU < prevWrappedU,
    })

    prevChase.copy(chase.position)
    prevWrappedU = wrappedU
    prevTargetRoll = raw
  }
  return steps
}

const worstBy = (steps: Step[], pick: (s: Step) => number) =>
  steps.reduce((a, b) => (pick(b) > pick(a) ? b : a))
const leastBy = (steps: Step[], pick: (s: Step) => number) =>
  steps.reduce((a, b) => (pick(b) < pick(a) ? b : a))

/**
 * The seam is this milestone's stated risk, and it is a *different* risk from
 * the one `frame.test.ts` retired. `sampleAt` was already proven continuous
 * across `s = 0`; what is new here is state that persists between frames and is
 * measured in arc length. Damp a wrapped `s` towards another wrapped `s` and the
 * camera flies an entire lap backwards the moment the car crosses the line. The
 * rig avoids it by never wrapping anything it stores — this asserts that it
 * really does.
 */
describe('the chase camera across the start/finish seam', () => {
  const frame = loadMonza()
  // 300 m either side of the line: enough for the damper to have long settled
  // before the crossing, and short enough to stay on the main straight.
  const steps = drive(frame, frame.lengthM - 300, 600)

  it('crosses the seam exactly once', () => {
    // Guards the test itself. Three green assertions that never reached the
    // seam would be worse than no test at all.
    const crossings = steps.filter((step) => step.crossedSeam).length
    expect(crossings, `${crossings} seam crossings in ${steps.length} steps`).toBe(1)
  })

  it('advances a constant distance per step', () => {
    const worst = worstBy(steps, (s) => s.posError)
    expect(
      worst.posError,
      `worst step error ${(worst.posError * 1000).toFixed(3)} mm at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(SEAM_POS_TOL_M)
  })

  it('holds its trail through the crossing', () => {
    const worst = worstBy(steps, (s) => s.trailError)
    expect(
      worst.trailError,
      `worst trail error ${worst.trailError.toExponential(3)} m at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(TRAIL_TOL_M)
  })
})

describe('the chase camera around a lap', () => {
  const frame = loadMonza()
  const steps = drive(frame, 0, frame.lengthM)

  it('walks the whole lap', () => {
    expect(steps.length).toBe(Math.floor(frame.lengthM / (SPEED_MPS * DT_S)) + 1)
    expect(steps.some((s) => s.s > frame.lengthM - 100)).toBe(true)
  })

  /**
   * The assertion that catches the one arithmetic error in this module worth
   * catching. `MathUtils.damp` is a first-order lag, and a first-order lag
   * chasing a *ramp* settles `v * tau` behind it — 18 m here, twice the trail
   * that was asked for. `stepRig` rides the ramp forward first and damps only
   * the residual, so the steady-state error is zero.
   */
  it('keeps the trail it was configured with, not v times tau', () => {
    const worst = worstBy(steps, (s) => s.trailError)
    expect(
      worst.trailError,
      `worst trail error ${worst.trailError.toExponential(3)} m at s=${worst.s.toFixed(2)} ` +
        `(a plain damp would sit ${(SPEED_MPS * CHASE.tauS).toFixed(1)} m out)`,
    ).toBeLessThanOrEqual(TRAIL_TOL_M)
  })

  it('moves smoothly everywhere, not only at the seam', () => {
    const worst = worstBy(steps, (s) => s.posError)
    expect(
      worst.posError,
      `worst step error ${(worst.posError * 1000).toFixed(1)} mm at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(LAP_POS_TOL_M)
  })

  it('aims ahead of the car, all the way round', () => {
    const behind = steps.filter((s) => !s.leads)
    expect(
      behind.length,
      behind.length === 0 ? '' : `aim point fell behind the car at s=${behind[0].s.toFixed(2)}`,
    ).toBe(0)
  })

  /**
   * `Matrix4.lookAt` builds its basis as `up x viewDir`. Its degenerate guard
   * fires on an exact zero cross product, so the dangerous region is *near*
   * parallel rather than parallel: the cross product is tiny but non-zero, and
   * normalising it amplifies whatever float noise is in it.
   */
  it('never points the view direction near the up axis', () => {
    const chase = leastBy(steps, (s) => s.chaseLookAngle)
    expect(
      chase.chaseLookAngle,
      `chase view ${chase.chaseLookAngle.toFixed(2)} deg from up at s=${chase.s.toFixed(2)}`,
    ).toBeGreaterThan(MIN_LOOK_ANGLE_DEG)
    const onboard = leastBy(steps, (s) => s.onboardLookAngle)
    expect(
      onboard.onboardLookAngle,
      `T-cam view ${onboard.onboardLookAngle.toFixed(2)} deg from up at s=${onboard.s.toFixed(2)}`,
    ).toBeGreaterThan(MIN_LOOK_ANGLE_DEG)
  })

  it('produces no NaN anywhere', () => {
    const bad = steps.filter((s) => !s.finite)
    expect(bad.length, bad.length === 0 ? '' : `first at s=${bad[0].s.toFixed(2)}`).toBe(0)
  })
})

describe('the T-cam', () => {
  const frame = loadMonza()
  const steps = drive(frame, 0, frame.lengthM)

  it('walks a corner of each hand and a straight', () => {
    // Guards the roll assertions below: a sweep that only ever saw straight
    // track would pass every one of them without exercising anything.
    expect(steps.some((s) => s.rollDeg > 1)).toBe(true)
    expect(steps.some((s) => s.rollDeg < -1)).toBe(true)
    expect(steps.some((s) => Math.abs(s.rollDeg) < 0.1)).toBe(true)
  })

  it('sits on the car, where placeCar would put it', () => {
    const long = worstBy(steps, (s) => Math.abs(s.onCarLong - ONBOARD.fwdM))
    expect(
      Math.abs(long.onCarLong - ONBOARD.fwdM),
      `longitudinal offset ${long.onCarLong.toFixed(3)} m against ` +
        `${ONBOARD.fwdM.toFixed(3)} m at s=${long.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(ON_CAR_TOL_M)
    const lat = worstBy(steps, (s) => Math.abs(s.onCarLat))
    expect(
      Math.abs(lat.onCarLat),
      `lateral offset ${lat.onCarLat.toFixed(3)} m at s=${lat.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(ON_CAR_TOL_M)
  })

  it('stays inside the roll clamp', () => {
    const worst = worstBy(steps, (s) => Math.abs(s.rollDeg))
    expect(
      Math.abs(worst.rollDeg),
      `roll ${worst.rollDeg.toFixed(3)} deg at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(MathUtils.radToDeg(ONBOARD.maxRollRad) + EPS)
  })

  /**
   * Deliberately on the *undamped* target rather than on `state.roll`. The
   * damper bounds its own output rate no matter how ragged its input, so
   * asserting the damped value would pass with the low-pass deleted.
   */
  it('has a roll target that does not snap between centreline samples', () => {
    const worst = worstBy(steps, (s) => s.targetRollRate)
    expect(
      worst.targetRollRate,
      `roll target moving ${worst.targetRollRate.toFixed(1)} deg/s at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(MAX_TARGET_ROLL_RATE_DEG_PER_S)
  })

  it('keeps the horizon level on the main straight', () => {
    const straight = steps.filter((s) => s.s >= STRAIGHT_FROM_M && s.s <= STRAIGHT_TO_M)
    expect(straight.length).toBeGreaterThan(100)
    const worst = worstBy(straight, (s) => Math.abs(s.rollDeg))
    expect(
      Math.abs(worst.rollDeg),
      `roll ${worst.rollDeg.toFixed(3)} deg on the straight at s=${worst.s.toFixed(2)}`,
    ).toBeLessThanOrEqual(STRAIGHT_ROLL_TOL_DEG)
  })

  it('saturates the roll only in corners', () => {
    const fraction = steps.filter((s) => s.saturated).length / steps.length
    expect(
      fraction,
      `roll pinned at the clamp over ${(fraction * 100).toFixed(1)}% of the lap`,
    ).toBeLessThan(SATURATION_BUDGET)
  })
})

/**
 * `tauS` is documented as seconds, and a damper written as
 * `x += (y - x) * 0.1` per frame would be indistinguishable from one at 60 Hz
 * and wrong at every other rate. The only way to tell them apart is to run the
 * same disturbance over the same *wall clock* at two different step sizes.
 */
describe('damping is a time constant, not a per-frame fraction', () => {
  const frame = loadMonza()
  /** Initial error to recover from, metres. Large enough to be unambiguous. */
  const DISTURB_M = 20
  const RECOVER_S = 0.6
  /** Agreement between two step sizes, metres. Measured 0.006. */
  const RATE_TOL_M = 0.05

  function recover(dtS: number): number {
    const follow = newFollow(1000)
    const state: RigState = newRigState()
    stepRig(state, frame, follow, dtS)
    state.u -= DISTURB_M
    for (let k = 1; k * dtS <= RECOVER_S + 1e-12; k++) {
      follow.sUnwrapped = 1000 + k * dtS * SPEED_MPS
      stepRig(state, frame, follow, dtS)
    }
    return follow.sUnwrapped - state.u - CHASE.trailM
  }

  const coarse = recover(1 / 30)
  const fine = recover(1 / 240)
  /** A first-order lag: the error left after `t` is `e0 * exp(-t / tau)`. */
  const expected = DISTURB_M * Math.exp(-RECOVER_S / CHASE.tauS)

  it('recovers the same amount at 30 Hz and at 240 Hz', () => {
    expect(
      Math.abs(coarse - fine),
      `30 Hz left ${coarse.toFixed(4)} m, 240 Hz left ${fine.toFixed(4)} m`,
    ).toBeLessThanOrEqual(RATE_TOL_M)
  })

  it('recovers at the rate the time constant says', () => {
    expect(
      Math.abs(fine - expected),
      `left ${fine.toFixed(4)} m against exp(-${RECOVER_S}/${CHASE.tauS}) = ${expected.toFixed(4)} m`,
    ).toBeLessThanOrEqual(RATE_TOL_M)
  })
})

/**
 * Selecting a different car moves the thing being followed by kilometres in one
 * frame. That is not a disturbance to damp out — damping it would fly the camera
 * round the circuit for several seconds — so the rig re-seeds instead, and the
 * only way it can tell the two apart is `carIndex`.
 */
describe('switching the followed car', () => {
  const frame = loadMonza()

  it('cuts to the new car rather than sweeping to it', () => {
    const state = newRigState()
    const follow = newFollow(1000, 0)
    for (let k = 0; k < 120; k++) {
      follow.sUnwrapped = 1000 + k * DT_S * SPEED_MPS
      stepRig(state, frame, follow, DT_S)
    }

    follow.carIndex = 13
    follow.sUnwrapped = 4200
    stepRig(state, frame, follow, DT_S)

    const error = Math.abs(follow.sUnwrapped - state.u - CHASE.trailM)
    expect(error, `${error.toExponential(3)} m behind the new car after one step`).toBeLessThanOrEqual(EPS)
  })

  it('does not seed from a readout that is not live yet', () => {
    // `Grid` seeds its arrays from a passive effect and returns early until it
    // has, and StrictMode runs that path twice, so the first frames can arrive
    // zeroed. Seeding from one would drop the camera at the world origin.
    const state = newRigState()
    stepRig(state, frame, { s: 0, sUnwrapped: 0, d: 0, speedMps: 0, carIndex: 0, ...UNPOSED }, DT_S)
    expect(state.carIndex, 'seeded from a stationary car').toBe(-1)
  })
})
