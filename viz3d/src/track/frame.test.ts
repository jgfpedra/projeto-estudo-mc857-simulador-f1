import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Vector3 } from 'three'
import { buildFrame, sampleAt } from './frame'
import type { Sample, TrackFrame } from './frame'
import { parseTrack } from './load'
import type { TrackJson } from './types'

/**
 * The committed track, read straight off disk through the real `parseTrack`.
 * Deliberately the shipped artifact rather than a synthetic loop: a hand-made
 * circle would not have the one property under test, which is that the seam
 * between the last sample and sample 0 behaves like every other segment.
 */
function loadTrack(file: string): TrackFrame {
  const url = new URL(`../../public/tracks/${file}`, import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

const STEP_M = 0.05
const SPAN_M = 1.0
/** A step may deviate from `STEP_M` by this much. Catches jumps and stalls. */
const POS_TOL_M = 0.005
/**
 * Per-step tangent swing allowed. Monza's tightest corner turns 0.156 deg per
 * 0.05 m, and the seam is on the main straight where the true value is
 * ~0.0002 deg, so this is loose by three orders of magnitude and still tight
 * enough that any real discontinuity blows straight through it.
 */
const TAN_TOL_DEG = 0.1

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

interface Step {
  /** Arc length of the later of the two samples, wrapped into [0, L). */
  s: number
  /** How far the step deviates from `STEP_M`, metres. */
  posError: number
  /** Angle between consecutive tangents, degrees. */
  tanSwing: number
}

/** Walk `sampleAt` across `s = 0` and report every step. */
function sweepSeam(frame: TrackFrame): Step[] {
  const buffers = [newSample(), newSample()]
  const steps: Step[] = []
  let prev = sampleAt(frame, frame.lengthM - SPAN_M, buffers[0])
  for (let k = 1; ; k++) {
    const s = frame.lengthM - SPAN_M + k * STEP_M
    if (s > frame.lengthM + SPAN_M + 1e-9) break
    const cur = sampleAt(frame, s, buffers[k % 2])
    steps.push({
      s: s % frame.lengthM,
      posError: Math.abs(prev.position.distanceTo(cur.position) - STEP_M),
      tanSwing: angleDeg(prev.tangent, cur.tangent),
    })
    prev = cur
  }
  return steps
}

const worstBy = (steps: Step[], key: 'posError' | 'tanSwing') =>
  steps.reduce((a, b) => (b[key] > a[key] ? b : a))

/**
 * The ribbon indexing back into sample 0 proves the *geometry* shares an edge
 * at start/finish. It says nothing about `sampleAt`, which is a different code
 * path: the wrap in `wrapS`, the binary search landing on the last segment,
 * and the segment length computed modulo lap length all have to agree.
 *
 * `sampleAt` is the path a moving car takes. A mistake here shows up as a jump
 * or a flick of heading once per lap, at the most visible point on track.
 *
 * Every committed track, not just ours: the engine tracks are rolled so their
 * `sf_idx` becomes sample 0 (scripts/convert_frozen_track.py), which puts the
 * seam somewhere new on a loop with non-uniform 2-4 m spacing.
 */
describe.each(['monza.json', 'monza_v1.json', 'interlagos_v2.json'])(
  'sampleAt across the start/finish seam: %s',
  (file) => {
    const frame = loadTrack(file)
    const steps = sweepSeam(frame)

    it('sweeps the whole span', () => {
      expect(steps).toHaveLength(Math.round((2 * SPAN_M) / STEP_M))
    })

    it('advances a constant distance per step', () => {
      const worst = worstBy(steps, 'posError')
      expect(
        worst.posError,
        `worst step error ${(worst.posError * 1000).toFixed(3)} mm at s=${worst.s.toFixed(2)}`,
      ).toBeLessThanOrEqual(POS_TOL_M)
    })

    it('does not kink the tangent', () => {
      const worst = worstBy(steps, 'tanSwing')
      expect(
        worst.tanSwing,
        `worst tangent swing ${worst.tanSwing.toFixed(4)} deg at s=${worst.s.toFixed(2)}`,
      ).toBeLessThanOrEqual(TAN_TOL_DEG)
    })

    it('crosses the seam rather than stopping short of it', () => {
      // Guards the test itself: if the sweep never wrapped past s = 0 the three
      // assertions above would pass without having looked at the seam at all.
      expect(steps.some((step) => step.s < SPAN_M)).toBe(true)
      expect(steps.some((step) => step.s > frame.lengthM - SPAN_M)).toBe(true)
    })
  },
)
