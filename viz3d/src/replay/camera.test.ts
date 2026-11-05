import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { buildFrame } from '../track/frame'
import type { TrackFrame } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { CHASE, newRigState, stepRig } from '../cameras/rig'
import type { FollowState } from '../cameras/rig'

/**
 * How a replay drives the camera rig, without changing the rig.
 *
 * `rig.ts` was written for a field that moves at a constant speed and never
 * stops. A replay can be paused, scrubbed and run at a different rate, and each
 * of those breaks an assumption the rig made. The two decisions that let it go
 * on being used unchanged are asserted here, each against the failure it avoids —
 * because neither can be settled by looking at a still frame, and the camera is
 * the one part of this milestone a screenshot cannot prove.
 *
 * Both live in `CameraRig.tsx`, which calls `stepRig(…, delta * rate)` and
 * invalidates `carIndex` on a discontinuity. This file tests the properties of
 * `rig.ts` those decisions depend on, so that if a later change to the rig
 * invalidates one, it fails here rather than on screen.
 */

function loadMonza(): TrackFrame {
  const url = new URL('../../public/tracks/monza.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

/** Realistic racing speed, and the frame time the rig is normally stepped at. */
const SPEED_MPS = 70
const FRAME_S = 1 / 60

function follow(sUnwrapped: number, speedMps = SPEED_MPS): FollowState {
  return { s: sUnwrapped, sUnwrapped, d: 0, speedMps, carIndex: 0 }
}

/**
 * Settle the rig by running it for `seconds` of wall clock at a playback `rate`.
 *
 * The car advances at `speed * rate` per second of wall clock, which is what a
 * replay does, and the rig is stepped with `delta * rate`, which is what
 * `CameraRig` does.
 */
function run(
  frame: TrackFrame,
  { rate, seconds, s0 = 2000 }: { rate: number; seconds: number; s0?: number },
) {
  const state = newRigState()
  let s = s0
  // Seed, so the measurement is of the settled behaviour and not of the cut.
  stepRig(state, frame, follow(s), FRAME_S * rate)
  for (let t = 0; t < seconds; t += FRAME_S) {
    s += SPEED_MPS * rate * FRAME_S
    stepRig(state, frame, follow(s), FRAME_S * rate)
  }
  return { trail: s - state.u, state, s }
}

describe('the camera rig driven at a replay rate', () => {
  const frame = loadMonza()

  it('holds the configured trail at every playback rate', () => {
    // The feed-forward term in `stepRig` integrates the reported speed. Scaling
    // `dtS` makes `speed * dt` equal the rate the car's arc length actually
    // advances in wall-clock time, so the trail is right at any rate — which is
    // the whole reason the rate is applied here rather than to `speedMps`.
    for (const rate of [0.25, 0.5, 1, 2]) {
      const { trail } = run(frame, { rate, seconds: 6 })
      expect(
        Math.abs(trail - CHASE.trailM),
        `at rate ${rate} the camera settled ${trail.toFixed(3)} m behind, configured ${CHASE.trailM} m`,
      ).toBeLessThan(0.01)
    }
  })

  it('does not creep while paused, and would have crept by 18 m otherwise', () => {
    // Paused, `CameraRig` passes `dtS = 0`, so both of `stepRig`'s damps are
    // no-ops and the anchor is frozen.
    const held = newRigState()
    const paused = follow(2000)
    stepRig(held, frame, paused, FRAME_S)
    const seeded = held.u
    for (let i = 0; i < 600; i++) stepRig(held, frame, paused, 0)
    expect(
      Math.abs(held.u - seeded),
      `anchor moved ${(held.u - seeded).toExponential(2)} m over ten seconds of pause`,
    ).toBe(0)

    // The rejected alternative: keep stepping real time while the car is static,
    // which is what reporting the physical speed without scaling `dtS` does. The
    // feed-forward rides a ramp that is not there, and the damping settles it
    // `v * tau` past the target — the car ends up behind the camera.
    const crept = newRigState()
    stepRig(crept, frame, paused, FRAME_S)
    for (let i = 0; i < 600; i++) stepRig(crept, frame, paused, FRAME_S)
    const overshoot = crept.u - (paused.sUnwrapped - CHASE.trailM)
    expect(
      overshoot,
      `the alternative drifts ${overshoot.toFixed(1)} m past the car (v * tau = ${(
        SPEED_MPS * CHASE.tauS
      ).toFixed(1)} m)`,
    ).toBeGreaterThan(SPEED_MPS * CHASE.tauS * 0.9)
  })

  it('cuts on a scrub instead of damping across it', () => {
    // A scrub moves the followed car by a lap or more. `CameraRig` invalidates
    // `carIndex`, which is the same signal the rig already uses for a change of
    // car, so the next step re-seeds rather than chasing the new target from the
    // old anchor.
    const state = newRigState()
    stepRig(state, frame, follow(2000), FRAME_S)
    const before = state.u

    const scrubbed = follow(2000 + 3 * frame.lengthM)
    // Without the cut: a first-order lag crawls towards a target three laps away.
    const damped = { ...state }
    stepRig(damped, frame, scrubbed, FRAME_S)
    expect(
      damped.u - before,
      'damping alone would still be most of three laps from the car',
    ).toBeLessThan(frame.lengthM)

    // With the cut.
    state.carIndex = -1
    stepRig(state, frame, scrubbed, FRAME_S)
    expect(
      Math.abs(scrubbed.sUnwrapped - state.u - CHASE.trailM),
      `after the cut the camera sits ${(scrubbed.sUnwrapped - state.u).toFixed(2)} m behind`,
    ).toBeLessThan(1e-9)
  })

  it('still refuses to seed on a readout that is not live', () => {
    // The guard the replay source works around with a speed floor: a genuinely
    // stationary car would otherwise freeze the camera rather than be followed.
    const state = newRigState()
    stepRig(state, frame, follow(2000, 0), FRAME_S)
    expect(state.carIndex, 'a zero speed leaves the rig unseeded').toBe(-1)
    stepRig(state, frame, follow(2000, 1e-3), FRAME_S)
    expect(state.carIndex, 'the replay source floors the speed so this seeds').toBe(0)
  })
})
