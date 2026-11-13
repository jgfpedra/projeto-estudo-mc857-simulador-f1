/**
 * The twenty-car field: who is where, how fast, and what colour.
 *
 * Pure and deterministic \u2014 no `Math.random`, so the grid is identical on every
 * reload and a screenshot means something. This is the stand-in described in
 * `docs/3d-design.md` section 6A: fixed offsets, no strategy, no overtaking
 * logic. Cars pass each other only because their speeds differ slightly, which
 * is enough to make the field evolve instead of moving as one block.
 */

import type { CarIdentity, MotionSource, MotionState } from './motion'

/** Cars in the field. Twenty, as a real grid is. */
export const CAR_COUNT = 20

/** Base speed, m/s. ~96 s a lap on Monza's 5756.9 m. */
export const BASE_SPEED_MPS = 60

/**
 * Ten colours, two cars each, the way a real grid is ten pairs.
 *
 * Colours only, and generic names for them: CLAUDE.md rules out liveries,
 * badges, sponsor marks and official-style numbers, and a flat colour is none
 * of those. They are approximate by intent \u2014 close enough that the field reads
 * as varied, not close enough to be anyone's asset.
 */
export const PALETTE: { name: string; hex: string }[] = [
  { name: 'teal', hex: '#12c2b4' },
  { name: 'scarlet', hex: '#e2062c' },
  { name: 'indigo', hex: '#2c37d4' },
  { name: 'papaya', hex: '#ff7a1a' },
  { name: 'forest', hex: '#1f8a4c' },
  { name: 'azure', hex: '#3ba7e8' },
  { name: 'magenta', hex: '#d6248c' },
  { name: 'bone', hex: '#d9dbe0' },
  { name: 'navy', hex: '#163a7a' },
  { name: 'amber', hex: '#f2c230' },
]

export interface CarSpec extends CarIdentity {
  /** Arc length at t = 0, metres. */
  s0: number
  /** Lateral offset, metres, positive to the right of the direction of travel. */
  d: number
  speedMps: number
}

/**
 * Deterministic pseudo-random in [0, 1). An integer hash rather than
 * `Math.sin(i)` tricks: it is reproducible across engines, and the point of
 * this whole module is that two runs give the same grid.
 */
function hash01(i: number, salt: number): number {
  let h = Math.imul(i + 1, 0x9e3779b1) ^ Math.imul(salt + 1, 0x85ebca6b)
  h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d)
  h ^= h >>> 12
  return (h >>> 0) / 4294967296
}

/**
 * Lay the field out around the lap.
 *
 * `s` is spread over the whole lap rather than packed into a starting grid, so
 * that cars are visible in several corners at once from the default near-plan
 * camera \u2014 a tight grid would be one clump of pixels. The jitter is a fraction
 * of the spacing, enough to break the metronome regularity without letting two
 * cars overlap at t = 0.
 *
 * `trackWidthM` bounds `d`: the cars are kept inside the ribbon with a margin
 * of half a car plus a little, so nothing hangs over the edge.
 */
export function buildField(lengthM: number, trackWidthM: number, carWidthM: number): CarSpec[] {
  const gap = lengthM / CAR_COUNT
  const dLimit = Math.max(0, trackWidthM / 2 - carWidthM / 2 - 0.4)
  return Array.from({ length: CAR_COUNT }, (_, i) => {
    const pair = Math.floor(i / 2)
    const colour = PALETTE[pair % PALETTE.length]
    return {
      index: i,
      label: `#${i + 1}`,
      colourName: colour.name,
      hex: colour.hex,
      s0: (i * gap + (hash01(i, 1) - 0.5) * gap * 0.5 + lengthM) % lengthM,
      // Spread across the ribbon, alternating sides so team-mates are not
      // stacked on the same line.
      d: (((i % 5) / 4) * 2 - 1) * dLimit * (i % 2 === 0 ? 1 : -0.72),
      // +/- 5%. Small enough to look like one class of car, large enough that
      // the order visibly changes over a minute or two.
      speedMps: BASE_SPEED_MPS * (0.95 + hash01(i, 2) * 0.1),
    }
  })
}

/**
 * The synthetic field as a `MotionSource`.
 *
 * Closed form in `t` rather than integrated: `buildField` already describes the
 * whole motion as `s0 + speed * t` with a fixed `d`, so there was never any
 * state worth carrying between frames. Writing it this way is what lets `Grid`
 * drop its two accumulators and treat both sources identically.
 *
 * `durationS` is `Infinity`, which is the honest answer — the synthetic field
 * never ends — and the timeline reads it to disable the scrubber rather than
 * offering a scrub over a range that does not exist.
 *
 * Note this does **not** make `MAX_DELTA_S` redundant. The cap moves to the
 * clock, where it caps the one quantity that advances instead of twenty; drop
 * it and a hidden tab still hands back a single enormous delta and still jumps
 * the field several laps, which is the artefact M3 existed to rule out.
 */
export function syntheticSource(field: CarSpec[]): MotionSource {
  return {
    kind: 'synthetic',
    cars: field,
    durationS: Infinity,
    sampleInto(tSeconds: number, carIndex: number, out: MotionState): MotionState {
      out.wheelTravelM = undefined
      const car = field[carIndex]
      out.sUnwrapped = car.s0 + car.speedMps * tSeconds
      out.d = car.d
      out.speedMps = car.speedMps
      out.posed = false
      return out
    },
    originM(carIndex: number): number {
      return field[carIndex].s0
    },
  }
}

/**
 * Cap on a single integration step, seconds.
 *
 * `requestAnimationFrame` stops while the tab is hidden, so the first frame back
 * carries the whole away-time in one `delta`. `wrapS` keeps that arithmetically
 * correct, but cars that advance four laps between two frames read on screen as
 * the start/finish jump M3 existed to rule out.
 *
 * It lives here rather than in `Grid.tsx` because the camera rig integrates
 * against the same clock and must cap against the same number: two constants
 * that have to agree is one more than there should be.
 */
export const MAX_DELTA_S = 0.1
