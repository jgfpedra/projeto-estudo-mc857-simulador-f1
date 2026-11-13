import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Matrix4, Vector3 } from 'three'
import { buildFrame, toWorld } from '../track/frame'
import { poseMatrix } from '../cars/instance'
import { newMotionState } from '../cars/motion'
import { geometrySha256, parseRecording, trackFromRecording } from './load'
import { engineSource, engineYaw, lapAtTime, positionAt, progressAt } from './source'

/**
 * The engine recording, end to end in TypeScript, on the committed fixture
 * (`public/recordings/engine-interlagos-seed42.jsonl`, the first 41.9 s of the
 * seed-42 race, trimmed from `.cache/recordings/` by `trim_recording.py`).
 *
 * `scripts/check_recording.py` measures the same things in Python on the full
 * race. This file crosses the language boundary: `s_m` / `d_m` came out of the
 * Python refined projector, and the assertion is that the viewer's own `toWorld`
 * lands back on the engine's `position_xy`.
 */
const TEXT = readFileSync(
  fileURLToPath(new URL('../../public/recordings/engine-interlagos-seed42.jsonl', import.meta.url)),
  'utf8',
)
const rec = parseRecording(TEXT)
const track = trackFromRecording(rec)
const frame = buildFrame(track)
const N = rec.cars.length
const HALF_W = rec.track.widthM / 2

describe('engine recording fixture', () => {
  it('interpolates wheel travel from physical poses and rewinds consistently', () => {
    const source = engineSource(rec)
    const state = newMotionState()
    source.sampleInto(rec.dtS, 0, state)
    const first = state.wheelTravelM!
    source.sampleInto(2 * rec.dtS, 0, state)
    const second = state.wheelTravelM!
    source.sampleInto(1.5 * rec.dtS, 0, state)
    expect(state.wheelTravelM).toBeCloseTo((first + second) / 2, 9)
    source.sampleInto(rec.dtS, 0, state)
    expect(state.wheelTravelM).toBeCloseTo(first, 9)
    expect(first).toBeCloseTo(rec.wheelTravelM[N], 9)
  })
  it('parses: ten cars in grid order, uniform 10 Hz ticks', () => {
    expect(rec.cars.map((c) => c.gridPosition)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(rec.ticks).toBeGreaterThan(400)
    expect(rec.dtS).toBeCloseTo(0.1, 9)
    expect(rec.t0S).toBeCloseTo(0.1, 9)
    expect(TEXT.length).toBeLessThanOrEqual(1_000_000)
  })

  it("the waypoints hash to the race block's geometry_sha256, and an edit is refused", async () => {
    expect(await geometrySha256(rec)).toBe(rec.track.geometrySha256)
    const tampered = parseRecording(TEXT)
    tampered.track.waypoints[100] += 0.001
    expect(await geometrySha256(tampered)).not.toBe(rec.track.geometrySha256)
  })

  it('the track is the race block rolled to the start/finish waypoint, with three.z = -y', () => {
    const sf = rec.track.startFinishWaypoint
    expect(track.points[0].x).toBe(rec.track.waypoints[2 * sf])
    expect(track.points[0].z).toBe(-rec.track.waypoints[2 * sf + 1])
    expect(Math.abs(frame.lengthM - rec.track.lengthM)).toBeLessThan(1e-6)
  })

  it('round trip: toWorld(s_m, d_m) lands on position_xy, on- and off-track', () => {
    const p = new Vector3()
    let worstOn = 0
    let worstOff = 0
    let off = 0
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        const i = k * N + c
        toWorld(frame, rec.sM[i], rec.dM[i], 0, p)
        const err = Math.hypot(p.x - rec.x[i], p.z + rec.y[i])
        if (Math.abs(rec.dM[i]) > HALF_W) {
          off++
          worstOff = Math.max(worstOff, err)
        } else {
          worstOn = Math.max(worstOn, err)
        }
      }
    }
    console.log(`round trip: worst ${worstOn.toExponential(2)} m on-track, ${worstOff.toExponential(2)} m over ${off} off-track samples`)
    // position_xy is stored to 1 cm and s_m / d_m to 1 mm, computed from the
    // stored position: the residual is the millimetre rounding, nothing more.
    expect(worstOn).toBeLessThan(2e-3)
    // The fixture keeps Sainz's excursion so the off-track path is exercised.
    expect(off).toBeGreaterThan(0)
    expect(worstOff).toBeLessThan(2e-3)
  })

  it('progress_m is non-decreasing for every car in the fixture', () => {
    for (let c = 0; c < N; c++) {
      for (let k = 1; k < rec.ticks; k++) {
        expect(rec.progressM[k * N + c]).toBeGreaterThanOrEqual(rec.progressM[(k - 1) * N + c])
      }
    }
  })

  it("running order from interpolated progress_m reproduces the engine's position at every tick", () => {
    let changes = 0
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        expect(positionAt(rec, k * rec.dtS, c)).toBe(rec.position[k * N + c])
        if (k > 0 && rec.position[k * N + c] !== rec.position[(k - 1) * N + c]) changes++
      }
    }
    expect(changes).toBeGreaterThan(0) // the order really does change in the window
  })

  it('lap counter and progress interpolate between ticks, exact at them', () => {
    const k = 200
    expect(progressAt(rec, k * rec.dtS, 3)).toBeCloseTo(rec.progressM[k * N + 3], 9)
    const mid = progressAt(rec, (k + 0.5) * rec.dtS, 3)
    expect(mid).toBeCloseTo((rec.progressM[k * N + 3] + rec.progressM[(k + 1) * N + 3]) / 2, 9)
    expect(lapAtTime(rec, k * rec.dtS, 3)).toBe(rec.lap[k * N + 3])
  })
})

describe('engine motion source', () => {
  const source = engineSource(rec)
  const m = newMotionState()
  const car = new Matrix4()
  const fwd = new Vector3()

  it('places every car at position_xy with its heading, determinant +1, at every tick', () => {
    let worstPos = 0
    let worstDir = 0
    let worstDet = Infinity
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        const i = k * N + c
        source.sampleInto(k * rec.dtS, c, m)
        expect(m.posed).toBe(true)
        expect(m.sUnwrapped).toBeCloseTo(rec.progressM[i], 9)
        expect(m.d).toBeCloseTo(rec.dM[i], 9)
        poseMatrix(m.x, m.z, m.yawRad, 0, car)
        const e = car.elements
        worstPos = Math.max(worstPos, Math.hypot(e[12] - rec.x[i], e[14] + rec.y[i]))
        // local -Z (the nose) must point along the engine heading
        fwd.set(-e[8], -e[9], -e[10])
        const h = rec.headingRad[i]
        worstDir = Math.max(worstDir, Math.hypot(fwd.x - Math.cos(h), fwd.y, fwd.z + Math.sin(h)))
        worstDet = Math.min(worstDet, car.determinant())
      }
    }
    expect(worstPos).toBeLessThan(1e-9)
    expect(worstDir).toBeLessThan(1e-9)
    expect(worstDet).toBeCloseTo(1, 9)
  })

  it('heading interpolates the short way round across +-180 degrees', () => {
    // engineYaw is affine, so check the angle a car would face halfway between
    // a heading just under +180 and one just over -180: it must stay near 180.
    const a = Math.PI - 0.01
    const b = -Math.PI + 0.01
    const d = Math.atan2(Math.sin(b - a), Math.cos(b - a))
    expect(Math.abs(d)).toBeCloseTo(0.02, 9)
    expect(engineYaw(Math.PI / 2)).toBe(0) // heading +y (engine) faces -Z (three)
  })

  it('a dropped minus on y would be caught: the mirrored pose misses the track', () => {
    // Sanity of the test above: placing at (x, +y) instead lands metres away.
    let worst = 0
    const p = new Vector3()
    for (let c = 0; c < N; c++) {
      const i = 100 * N + c
      toWorld(frame, rec.sM[i], rec.dM[i], 0, p)
      worst = Math.max(worst, Math.hypot(p.x - rec.x[i], p.z - rec.y[i]))
    }
    expect(worst).toBeGreaterThan(10)
  })
})
