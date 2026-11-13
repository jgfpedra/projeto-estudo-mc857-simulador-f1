import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Vector3 } from 'three'
import { buildFrame, toWorld, wrapS } from '../track/frame'
import { newMotionState } from '../cars/motion'
import type { MotionState } from '../cars/motion'
import { CHASE, ONBOARD, chasePose, newPose, newRigState, onboardPose, stepRig } from '../cameras/rig'
import type { FollowState } from '../cameras/rig'
import { parseRecording, trackFromRecording } from './load'
import { engineSource } from './source'

/**
 * The follow cameras on a posed source, over the committed fixture.
 *
 * The engine places its cars by pose, and `progress_m` - what the cameras used
 * to follow - sits up to a few tenths of a metre from that pose on the ground.
 * So the T-cam is bolted to the pose itself and the chase camera's anchor is
 * the car's position (`rig.ts`, `chasePose` / `onboardPose`). The expected
 * values here are built from the recording's raw `position_xy` / `heading_deg`
 * with the engine's own convention, not from `engineYaw`, so a sign slip in
 * either the source or the rig shows up.
 */
const TEXT = readFileSync(
  fileURLToPath(new URL('../../public/recordings/engine-interlagos-seed42.jsonl', import.meta.url)),
  'utf8',
)
const rec = parseRecording(TEXT)
const frame = buildFrame(trackFromRecording(rec))
const source = engineSource(rec)
const N = rec.cars.length

/** The spec: within 1 cm of the car. The maths is exact to ~1e-12. */
const TOL_M = 0.01

function followFrom(m: MotionState, carIndex: number, out: FollowState): FollowState {
  out.s = wrapS(frame, m.sUnwrapped)
  out.sUnwrapped = m.sUnwrapped
  out.d = m.d
  out.speedMps = m.speedMps
  out.carIndex = carIndex
  out.posed = m.posed
  out.x = m.x
  out.z = m.z
  out.yawRad = m.yawRad
  return out
}

function newFollow(): FollowState {
  return { s: 0, sUnwrapped: 0, d: 0, speedMps: 0, carIndex: -1, posed: false, x: 0, z: 0, yawRad: 0 }
}

/** Where the T-cam must be at tick `k` for car `c`: engine plan, then three.z = -y. */
function expectedOnboard(k: number, c: number, position: Vector3, target: Vector3) {
  const i = k * N + c
  const h = rec.headingRad[i]
  const fx = Math.cos(h)
  const fz = -Math.sin(h)
  position.set(rec.x[i] + ONBOARD.fwdM * fx, ONBOARD.heightM, -rec.y[i] + ONBOARD.fwdM * fz)
  target.set(rec.x[i] + ONBOARD.lookaheadM * fx, ONBOARD.targetHeightM, -rec.y[i] + ONBOARD.lookaheadM * fz)
}

describe('follow cameras on the engine source', () => {
  const m = newMotionState()
  const follow = newFollow()
  const pose = newPose()
  const wantPos = new Vector3()
  const wantTarget = new Vector3()
  const dir = new Vector3()
  const wantDir = new Vector3()

  it('T-cam: the car pose plus its local offset, aimed along the nose, at every tick', () => {
    const state = newRigState()
    let worstPos = 0
    let worstDir = 0
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        source.sampleInto(k * rec.dtS, c, m)
        onboardPose(frame, state, followFrom(m, c, follow), ONBOARD, pose)
        expectedOnboard(k, c, wantPos, wantTarget)
        worstPos = Math.max(worstPos, pose.position.distanceTo(wantPos))
        dir.subVectors(pose.target, pose.position).normalize()
        wantDir.subVectors(wantTarget, wantPos).normalize()
        worstDir = Math.max(worstDir, dir.distanceTo(wantDir))
      }
    }
    console.log(`T-cam vs pose + local offset: worst ${worstPos.toExponential(2)} m, direction ${worstDir.toExponential(2)}`)
    expect(worstPos).toBeLessThan(TOL_M)
    expect(worstDir).toBeLessThan(1e-6)
  })

  it('T-cam between ticks: still at the interpolated pose plus the local offset', () => {
    const state = newRigState()
    let worst = 0
    const local = new Vector3()
    for (let k = 0; k < rec.ticks - 1; k++) {
      for (let c = 0; c < N; c++) {
        source.sampleInto((k + 0.37) * rec.dtS, c, m)
        onboardPose(frame, state, followFrom(m, c, follow), ONBOARD, pose)
        // back into the car's frame: x right, y up, -z forward
        local.set(pose.position.x - m.x, pose.position.y, pose.position.z - m.z)
        local.applyAxisAngle(new Vector3(0, 1, 0), -m.yawRad)
        worst = Math.max(worst, local.distanceTo(new Vector3(0, ONBOARD.heightM, -ONBOARD.fwdM)))
      }
    }
    expect(worst).toBeLessThan(TOL_M)
  })

  it('chase: the anchor is the car, and the trail and aim are the track geometry moved with it', () => {
    let worstAnchor = 0
    let worstTrail = 0
    let worstDir = 0
    const trackPos = new Vector3()
    const trackTarget = new Vector3()
    const trackAnchor = new Vector3()
    for (let c = 0; c < N; c++) {
      const state = newRigState()
      for (let k = 0; k < rec.ticks; k++) {
        source.sampleInto(k * rec.dtS, c, m)
        followFrom(m, c, follow)
        stepRig(state, frame, follow, rec.dtS) // seeds on k = 0, then damps
        chasePose(frame, state, follow, CHASE, pose)
        const i = k * N + c
        worstAnchor = Math.max(worstAnchor, Math.hypot(pose.anchor.x - rec.x[i], pose.anchor.z + rec.y[i]))

        // The same damped `u` and lookahead as a car placed by (s, d) ...
        toWorld(frame, state.u, follow.d, CHASE.heightM, trackPos)
        toWorld(frame, follow.sUnwrapped + CHASE.lookaheadM, follow.d, CHASE.targetHeightM, trackTarget)
        toWorld(frame, follow.sUnwrapped, follow.d, 0, trackAnchor)
        // ... so relative to the anchor, nothing about the chase camera changed.
        worstTrail = Math.max(
          worstTrail,
          dir.subVectors(pose.position, pose.anchor).distanceTo(wantDir.subVectors(trackPos, trackAnchor)),
        )
        dir.subVectors(pose.target, pose.position).normalize()
        wantDir.subVectors(trackTarget, trackPos).normalize()
        worstDir = Math.max(worstDir, dir.distanceTo(wantDir))
      }
    }
    console.log(`chase anchor vs position_xy: worst ${worstAnchor.toExponential(2)} m`)
    expect(worstAnchor).toBeLessThan(TOL_M)
    expect(worstTrail).toBeLessThan(1e-9)
    expect(worstDir).toBeLessThan(1e-9)
  })

  it('the old progress_m anchoring fails the same T-cam check, so the test has teeth', () => {
    const state = newRigState()
    let worst = 0
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        source.sampleInto(k * rec.dtS, c, m)
        followFrom(m, c, follow).posed = false // what the rig did before
        onboardPose(frame, state, follow, ONBOARD, pose)
        expectedOnboard(k, c, wantPos, wantTarget)
        worst = Math.max(worst, pose.position.distanceTo(wantPos))
      }
    }
    console.log(`progress_m-anchored T-cam vs pose + offset: worst ${worst.toFixed(3)} m`)
    expect(worst).toBeGreaterThan(10 * TOL_M)
  })

  it('an unposed follow ignores x, z and yaw entirely (synthetic and replay unchanged)', () => {
    const state = newRigState()
    const a = newFollow()
    const b = newFollow()
    Object.assign(a, { sUnwrapped: 1234.5, d: 1.5, speedMps: 50, carIndex: 0 })
    Object.assign(b, a, { x: 99, z: -42, yawRad: 2 })
    stepRig(state, frame, a, 0)
    const chaseA = chasePose(frame, state, a, CHASE, newPose())
    const chaseB = chasePose(frame, state, b, CHASE, newPose())
    const onA = onboardPose(frame, state, a, ONBOARD, newPose())
    const onB = onboardPose(frame, state, b, ONBOARD, newPose())
    for (const [pa, pb] of [[chaseA, chaseB], [onA, onB]]) {
      expect(pb.position.toArray()).toEqual(pa.position.toArray())
      expect(pb.target.toArray()).toEqual(pa.target.toArray())
    }
    // and exactly the (s, d) formulas, bit for bit
    expect(onA.position.toArray()).toEqual(toWorld(frame, 1234.5 + ONBOARD.fwdM, 1.5, ONBOARD.heightM).toArray())
    expect(chaseA.position.toArray()).toEqual(toWorld(frame, state.u, 1.5, CHASE.heightM).toArray())
  })
})
