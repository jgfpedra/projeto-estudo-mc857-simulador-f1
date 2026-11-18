import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Matrix4, Vector3 } from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { buildFrame, toWorld } from '../track/frame'
import type { TrackFrame } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { carGeometry } from './model'
import type { CarGeometry } from './model'
import { carMatrix, wheelAngle, wheelMatrix } from './instance'
import { BASE_SPEED_MPS, CAR_COUNT, buildField } from './field'

/** Roundoff on a compose/multiply chain of rigid transforms, plus margin. */
const EPS = 1e-9

const RIDE_HEIGHT_M = 0.01
const TRACK_WIDTH_M = 13
const CAR_WIDTH_M = 2

/** Same artifact and same parse path as `src/track/frame.test.ts`. */
function loadMonza(): TrackFrame {
  const url = new URL('../../public/tracks/monza.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

function loadCar(): Promise<CarGeometry> {
  const url = new URL('../../public/models/raceCarRed.glb', import.meta.url)
  const buf = readFileSync(fileURLToPath(url))
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
  return new Promise((resolve, reject) => {
    new GLTFLoader().parse(
      ab as ArrayBuffer,
      '',
      (gltf) => resolve(carGeometry(gltf.scene)),
      reject,
    )
  })
}

describe('instance matrices', () => {
  it('never mirror, for any car at any point of the lap', async () => {
    /*
     * The headline assertion for the grid. `carBasis` guarantees a right-handed
     * rotation, but instancing *composes* matrices instead of assigning them,
     * and a single negative scale component would mirror all twenty cars while
     * every data check in verify.ts still passed. Rigid transforms throughout,
     * so the determinant is not merely positive but exactly 1.
     */
    const frame = loadMonza()
    const parts = await loadCar()
    const field = buildField(frame.lengthM, TRACK_WIDTH_M, CAR_WIDTH_M)
    const car = new Matrix4()
    const wheel = new Matrix4()
    const STEPS = 240
    let checked = 0

    for (let step = 0; step < STEPS; step++) {
      const travelled = (step / STEPS) * frame.lengthM * 3
      for (const spec of field) {
        const s = (spec.s0 + travelled) % frame.lengthM
        carMatrix(frame, s, spec.d, RIDE_HEIGHT_M, car)
        expect(car.determinant()).toBeCloseTo(1, 9)
        checked++
        for (const w of parts.wheels) {
          wheelMatrix(car, w, wheelAngle(travelled, w.radiusM), wheel)
          expect(wheel.determinant()).toBeCloseTo(1, 9)
          checked++
        }
      }
    }
    // Guard the guard: a loop that never ran would pass all of the above.
    expect(checked).toBe(STEPS * CAR_COUNT * (1 + parts.wheels.length))
    expect(parts.wheels).toHaveLength(4)
  })

  it('takes its position from toWorld and nowhere else', () => {
    const frame = loadMonza()
    const car = new Matrix4()
    for (const s of [0, 137.5, 2000, 5000, frame.lengthM - 1]) {
      carMatrix(frame, s, 3.25, RIDE_HEIGHT_M, car)
      const from = new Vector3().setFromMatrixPosition(car)
      const want = toWorld(frame, s, 3.25, RIDE_HEIGHT_M, new Vector3())
      expect(from.distanceTo(want)).toBeLessThan(EPS)
    }
  })

  it('spins a wheel about its axle without moving it', async () => {
    // If the spin translated the wheel, it would orbit the car instead of
    // turning — the classic symptom of baking geometry off its own centre.
    const frame = loadMonza()
    const parts = await loadCar()
    const car = new Matrix4()
    const wheel = new Matrix4()
    carMatrix(frame, 1200, 0, RIDE_HEIGHT_M, car)
    for (const w of parts.wheels) {
      const hub = w.centre.clone().applyMatrix4(car)
      for (const angle of [0, 0.7, -2.4, 31.9]) {
        wheelMatrix(car, w, angle, wheel)
        const at = new Vector3().setFromMatrixPosition(wheel)
        expect(at.distanceTo(hub)).toBeLessThan(EPS)
      }
    }
  })

  it('derives a wheel radius that rolls without slipping', async () => {
    const parts = await loadCar()
    for (const w of parts.wheels) {
      // Measured off the model, not written down: 0.7745 m across.
      expect(w.radiusM).toBeCloseTo(0.3872, 4)
      // The wheel centre sits exactly one radius above the datum, which is only
      // true if the adapter put the contact plane where it claims.
      expect(w.centre.y).toBeCloseTo(w.radiusM, 6)
      // One circumference of travel is exactly one turn, backwards.
      expect(wheelAngle(2 * Math.PI * w.radiusM, w.radiusM)).toBeCloseTo(-2 * Math.PI, 12)
    }
  })

  it('rolls the wheels forwards, not backwards', () => {
    /*
     * The sign of the spin. A still frame cannot settle this and a low-poly
     * tyre has no tread to give it away, so assert it: as the car travels, the
     * top of the wheel must move towards the car's forward, which is local -Z.
     * Backwards wheels are the kind of thing that survives to a demo.
     */
    const r = 0.4
    const wheel = { name: 'w', centre: new Vector3(0.8, r, -0.9), radiusM: r, axle: new Vector3(1, 0, 0), parts: [] }
    const identity = new Matrix4()
    const top = new Vector3(0, r, 0)
    const m = new Matrix4()
    const at = (travelled: number) =>
      top.clone().applyMatrix4(wheelMatrix(identity, wheel, wheelAngle(travelled, r), m))

    const start = at(0)
    const rolled = at(0.05)
    expect(rolled.z).toBeLessThan(start.z)
    // The hub itself must not drift while the rim turns.
    expect(new Vector3().setFromMatrixPosition(m).distanceTo(wheel.centre)).toBeLessThan(EPS)
    // Quarter of a turn of travel is a quarter turn of wheel: no slipping.
    const quarter = at((2 * Math.PI * r) / 4)
    expect(quarter.y).toBeCloseTo(wheel.centre.y, 9)
    expect(quarter.z).toBeCloseTo(wheel.centre.z - r, 9)
  })

  it('splits the model into one paint primitive and leaves the rest alone', async () => {
    const parts = await loadCar()
    expect(parts.body.filter((p) => p.paint)).toHaveLength(1)
    // Trim, glass and both wheel materials must not be recoloured per car.
    expect(parts.body.filter((p) => !p.paint).length).toBeGreaterThan(0)
    for (const w of parts.wheels) expect(w.parts.every((p) => !p.paint)).toBe(true)
  })
})

describe('buildField', () => {
  it('is deterministic', () => {
    const a = buildField(5756.9, TRACK_WIDTH_M, CAR_WIDTH_M)
    const b = buildField(5756.9, TRACK_WIDTH_M, CAR_WIDTH_M)
    expect(a).toEqual(b)
  })

  it('keeps every car on the ribbon and around the lap', () => {
    const L = 5756.9
    const field = buildField(L, TRACK_WIDTH_M, CAR_WIDTH_M)
    expect(field).toHaveLength(CAR_COUNT)
    const limit = TRACK_WIDTH_M / 2 - CAR_WIDTH_M / 2
    for (const c of field) {
      expect(c.s0).toBeGreaterThanOrEqual(0)
      expect(c.s0).toBeLessThan(L)
      // Half a car from the edge, so no bodywork overhangs the ribbon.
      expect(Math.abs(c.d)).toBeLessThanOrEqual(limit)
      expect(c.speedMps).toBeGreaterThan(BASE_SPEED_MPS * 0.94)
      expect(c.speedMps).toBeLessThan(BASE_SPEED_MPS * 1.06)
    }
  })

  it('spreads the cars out rather than clumping them', () => {
    const L = 5756.9
    const s = buildField(L, TRACK_WIDTH_M, CAR_WIDTH_M)
      .map((c) => c.s0)
      .sort((a, b) => a - b)
    const gaps = s.map((v, i) => (i === 0 ? v + L - s[s.length - 1] : v - s[i - 1]))
    // No two cars on top of each other at t = 0, and none more than double the
    // even spacing away, so the field is visible all round the circuit.
    expect(Math.min(...gaps)).toBeGreaterThan(CAR_WIDTH_M * 4)
    expect(Math.max(...gaps)).toBeLessThan((L / CAR_COUNT) * 2)
  })

  it('gives each colour to exactly two cars', () => {
    const counts = new Map<string, number>()
    for (const c of buildField(5756.9, TRACK_WIDTH_M, CAR_WIDTH_M)) {
      counts.set(c.hex, (counts.get(c.hex) ?? 0) + 1)
    }
    expect(counts.size).toBe(CAR_COUNT / 2)
    expect([...counts.values()].every((n) => n === 2)).toBe(true)
  })
})
