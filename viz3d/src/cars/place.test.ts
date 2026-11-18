import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Matrix4, Quaternion, Vector3 } from 'three'
import { buildFrame, curvatureAt, sampleAt, toWorld } from '../track/frame'
import type { Sample, TrackFrame } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { carBasis, placeCar } from './place'

/** Same artifact and same parse path as `src/track/frame.test.ts`. */
function loadMonza(): TrackFrame {
  const url = new URL('../../public/tracks/monza.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

/** Every ~2.9 m around the lap: straights, chicanes and long corners alike. */
const STEP_M = 2.9
/**
 * Axis agreement is exact up to roundoff — `carBasis` puts the frame's own
 * vectors straight into the matrix columns and never rebuilds them — so this
 * is roundoff plus margin, not a fudge factor. Anything that actually goes
 * wrong here (a swapped column, a missing negation) is off by 90 or 180
 * degrees, not by 1e-9.
 */
const DOT_TOL = 1e-9
/** Lateral test offset. Inside Monza's 13 m ribbon, well clear of zero. */
const TEST_D = 3.0
/** Curvature past which a sample counts as a real corner rather than a straight. */
const CORNER_CURVATURE = 0.005

function newSample(): Sample {
  return {
    position: new Vector3(),
    tangent: new Vector3(),
    right: new Vector3(),
    up: new Vector3(),
  }
}

interface Placement {
  s: number
  curvature: number
  /** Car's local +X, +Y and forward (-Z) in world space. */
  localX: Vector3
  localY: Vector3
  forward: Vector3
  /** The frame's own vectors at the same `s`, for comparison. */
  right: Vector3
  up: Vector3
  tangent: Vector3
  determinant: number
}

function walkLap(frame: TrackFrame): Placement[] {
  const out: Placement[] = []
  const m = new Matrix4()
  for (let s = 0; s < frame.lengthM; s += STEP_M) {
    const sample = sampleAt(frame, s, newSample())
    carBasis(frame, s, m)
    const localX = new Vector3()
    const localY = new Vector3()
    const localZ = new Vector3()
    m.extractBasis(localX, localY, localZ)
    out.push({
      s,
      curvature: curvatureAt(frame, s),
      localX,
      localY,
      forward: localZ.clone().negate(),
      right: sample.right,
      up: sample.up,
      tangent: sample.tangent,
      determinant: m.determinant(),
    })
  }
  return out
}

/** Worst (smallest) alignment in the lap, with where it happened. */
function worstDot(places: Placement[], a: keyof Placement, b: keyof Placement) {
  return places.reduce((acc, p) => {
    const dot = (p[a] as Vector3).dot(p[b] as Vector3)
    return dot < acc.dot ? { dot, s: p.s } : acc
  }, { dot: Infinity, s: -1 })
}

/**
 * The car's orientation is the one thing in M3 that a still frame cannot settle
 * and an argument can always be talked around. `verify.ts` proves the *track*
 * is not mirrored; these prove the thing standing on it agrees with the track's
 * own frame rather than with some re-derivation of it.
 */
describe('carBasis', () => {
  const frame = loadMonza()
  const places = walkLap(frame)

  it('walks a corner of each hand and a straight', () => {
    // Guards the test: a sweep that only saw the main straight would pass every
    // assertion below while proving nothing about the chicanes, which is where
    // a frame built the textbook way inverts.
    expect(places.some((p) => p.curvature > CORNER_CURVATURE)).toBe(true)
    expect(places.some((p) => p.curvature < -CORNER_CURVATURE)).toBe(true)
    expect(places.some((p) => Math.abs(p.curvature) < CORNER_CURVATURE / 10)).toBe(true)
    expect(places.length).toBeGreaterThan(1900)
  })

  it('points the car forward, not backward', () => {
    const worst = worstDot(places, 'forward', 'tangent')
    expect(
      worst.dot,
      `local -Z vs tangent: worst ${worst.dot.toFixed(12)} at s=${worst.s.toFixed(1)}`,
    ).toBeGreaterThan(1 - DOT_TOL)
  })

  it('aligns local +X with the frame right and +Y with the frame up', () => {
    const x = worstDot(places, 'localX', 'right')
    const y = worstDot(places, 'localY', 'up')
    expect(x.dot, `local +X vs right: worst ${x.dot.toFixed(12)} at s=${x.s.toFixed(1)}`)
      .toBeGreaterThan(1 - DOT_TOL)
    expect(y.dot, `local +Y vs up: worst ${y.dot.toFixed(12)} at s=${y.s.toFixed(1)}`)
      .toBeGreaterThan(1 - DOT_TOL)
  })

  it('does not mirror the car', () => {
    // `(right, up, tangent)` is left-handed and would land here as -1. Same
    // failure mode as TrackRibbon's scene-graph determinant check, one level
    // down: invisible on a symmetric box, a lie the moment it is not one.
    const worst = places.reduce((a, b) => (b.determinant < a.determinant ? b : a))
    expect(
      worst.determinant,
      `worst determinant ${worst.determinant.toFixed(9)} at s=${worst.s.toFixed(1)}`,
    ).toBeGreaterThan(0.999999)
  })
})

describe('placeCar', () => {
  const frame = loadMonza()
  const places = walkLap(frame)

  it('puts positive d to the right of the direction of travel', () => {
    // The convention from CLAUDE.md, asserted rather than commented. The slider
    // in CarPanel is this same claim in a form you can see.
    const centre = new Vector3()
    const offset = new Vector3()
    const q = new Quaternion()
    const worst = places.reduce(
      (acc, p) => {
        placeCar(frame, p.s, 0, 0, centre, q)
        placeCar(frame, p.s, TEST_D, 0, offset, q)
        const delta = offset.clone().sub(centre)
        const dot = delta.clone().normalize().dot(p.localX)
        const distErr = Math.abs(delta.length() - TEST_D)
        return dot < acc.dot ? { dot, distErr, s: p.s } : acc
      },
      { dot: Infinity, distErr: 0, s: -1 },
    )
    expect(
      worst.dot,
      `+${TEST_D} m displacement vs car's own right: worst ${worst.dot.toFixed(12)} ` +
        `at s=${worst.s.toFixed(1)}`,
    ).toBeGreaterThan(1 - DOT_TOL)
    expect(worst.distErr, `offset magnitude error ${worst.distErr}`).toBeLessThan(1e-9)
  })

  it('takes its position from toWorld and nowhere else', () => {
    // A second path into world space is the failure this guards: any
    // reconstruction from the basis vectors would agree here to millimetres and
    // drift somewhere else. Bit-for-bit equality is the only useful bar.
    const viaPlace = new Vector3()
    const viaToWorld = new Vector3()
    const q = new Quaternion()
    for (const p of places) {
      placeCar(frame, p.s, TEST_D, 0.55, viaPlace, q)
      toWorld(frame, p.s, TEST_D, 0.55, viaToWorld)
      expect(viaPlace.toArray(), `at s=${p.s.toFixed(1)}`).toEqual(viaToWorld.toArray())
    }
  })
})
