import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { buildFrame, toWorld } from '../track/frame'
import type { TrackFrame } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { Vector3 } from 'three'

/**
 * `world -> (s, d)` and `(s, d) -> world` agree, across two implementations.
 *
 * This is the test M6 exists for. Every other test in the project exercises the
 * forward direction: `toWorld` is given `(s, d)` and its output is checked for
 * continuity, handedness or determinant. Nothing has ever checked that the
 * inverse exists, or that anything *else* computing it arrives at the same
 * place — and the whole architectural bet in `docs/3d-design.md` section 3 is
 * that the simulator emits `(s, d)` while only the renderer knows about
 * coordinates.
 *
 * The rows come from `scripts/extract_replay.py`, which projects real 2024
 * Italian GP position samples onto the committed centreline. It has its own port
 * of `buildFrame` and `sampleAt` and its own round-trip check, but that check
 * can only prove the projector agrees with *Python's* idea of `toWorld`. This
 * one crosses the language boundary: the fixture carries the world point the
 * projector started from and the `(s, d)` it produced, and the assertion is that
 * the renderer's own `toWorld` lands back on that point.
 *
 * **Why matching the world point pins `(s, d)` uniquely.** Within the band the
 * data occupies the mapping is a bijection: it is singular only at the centre of
 * curvature, and the extractor's check M measures `max |d * kappa| = 0.041`
 * against the 1.0 where the fold would be. So there is no second `(s, d)` that
 * could produce the same world point and pass — a self-consistent but wrong
 * projector cannot hide here.
 *
 * Plan view only, and that is structural rather than a caveat: the fixture
 * stores two columns, not three. The committed centreline's `y` is identically 0
 * (`--elevation zero`, Monza is flat) while telemetry `Z` sits around 188 m
 * above sea level, so a three-dimensional residual would measure Monza's
 * altitude and nothing about the projection.
 */

interface FixtureRow {
  /** Three.js plan `(x, z)`, metres. */
  w: [number, number]
  s: number
  d: number
  region: string
  stratum: string
}

interface Fixture {
  source: string
  note: string
  trackLengthM: number
  rows: FixtureRow[]
}

/** Same artifact and same parse path as `src/track/frame.test.ts`. */
function loadMonza(): TrackFrame {
  const url = new URL('../../public/tracks/monza.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as TrackJson
  return buildFrame(parseTrack(raw))
}

function loadFixture(): Fixture {
  const url = new URL('../../scripts/fixtures/roundtrip-monza-2024.json', import.meta.url)
  return JSON.parse(readFileSync(fileURLToPath(url), 'utf8')) as Fixture
}

/**
 * Tolerance on the round trip, metres.
 *
 * The projection is an *identity*, not an approximation — with `y = 0` the
 * tangent and `right` span the plane, so solving for a foot point perpendicular
 * to the interpolated tangent reproduces the original point exactly. Python
 * measures its own side at 1.0e-12 m over 22,145 probes.
 *
 * So this bound is set by the fixture's own six-decimal rounding and nothing
 * else: 1e-6 m on each of `w`, `s` and `d` contributes about 3e-6 m, and 1e-4
 * leaves a factor of 30. It is deliberately **not** loosened to absorb the
 * geometry, because there is no geometry left to absorb — anything at centimetre
 * scale here means the two implementations disagree.
 *
 * For scale, the failure this is really guarding: a flipped sign in Python's
 * `right` moves the point by `2 * |d|`, which is 0.07 m even in the smallest
 * stratum and 2.1 m in the largest.
 */
const ROUNDTRIP_TOL_M = 1e-4

/** Lap length agreement, metres. Both sides round `lengthM` to four decimals. */
const LENGTH_TOL_M = 0.001

/** Metres either side of `s = 0` that count as a seam row. Matches the extractor. */
const SEAM_SPAN_M = 30

interface Probe {
  index: number
  error: number
  s: number
  d: number
  region: string
}

function probe(frame: TrackFrame, rows: FixtureRow[]): Probe[] {
  const got = new Vector3()
  return rows.map((row, index) => {
    toWorld(frame, row.s, row.d, 0, got)
    // Plan distance only: `got.y` is whatever the centreline's own y is, which
    // is 0 here, and the fixture has no third column to compare it against.
    const dx = got.x - row.w[0]
    const dz = got.z - row.w[1]
    return {
      index,
      error: Math.hypot(dx, dz),
      s: row.s,
      d: row.d,
      region: row.region,
    }
  })
}

function percentile(sorted: number[], p: number): number {
  return sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))]
}

describe('the (s, d) round trip against real projected telemetry', () => {
  const frame = loadMonza()
  const fixture = loadFixture()
  const probes = probe(frame, fixture.rows)
  const worst = probes.reduce((a, b) => (b.error > a.error ? b : a))
  const sorted = probes.map((p) => p.error).sort((a, b) => a - b)

  it('was built against this centreline', () => {
    // Without this, re-extracting the track would silently invalidate every row
    // below and the suite would fail with a confusing distance instead of a
    // clear statement that the fixture is stale.
    expect(
      Math.abs(fixture.trackLengthM - frame.lengthM),
      `fixture says ${fixture.trackLengthM} m, monza.json measures ${frame.lengthM.toFixed(4)} m` +
        ` — re-run scripts/extract_replay.py`,
    ).toBeLessThanOrEqual(LENGTH_TOL_M)
  })

  it('returns every projected sample to the point it came from', () => {
    expect(
      worst.error,
      `worst ${(worst.error * 1e6).toFixed(2)} um at s=${worst.s.toFixed(1)} d=${worst.d.toFixed(3)}` +
        ` (${worst.region}); p50 ${(percentile(sorted, 50) * 1e6).toFixed(2)}` +
        ` p90 ${(percentile(sorted, 90) * 1e6).toFixed(2)}` +
        ` p99 ${(percentile(sorted, 99) * 1e6).toFixed(2)} um over ${probes.length} rows`,
    ).toBeLessThanOrEqual(ROUNDTRIP_TOL_M)
  })

  it('puts d on the side the projector meant', () => {
    // The one failure the distribution above could hide if the tolerance were
    // ever loosened to centimetre scale: a flipped `right` in the Python port.
    // Asserted as its own claim, with its own margin, on the rows where |d| is
    // largest and the consequence therefore clearest.
    const wide = probes.filter((p) => Math.abs(p.d) > 0.5)
    const worstWide = wide.reduce((a, b) => (b.error > a.error ? b : a))
    expect(wide.length, 'fixture has rows with |d| > 0.5 m to test the sign on').toBeGreaterThan(20)
    expect(
      worstWide.error,
      `worst ${(worstWide.error * 1e6).toFixed(2)} um at d=${worstWide.d.toFixed(3)} m, where a` +
        ` flipped sign would read ${(2 * Math.abs(worstWide.d)).toFixed(2)} m`,
    ).toBeLessThanOrEqual(ROUNDTRIP_TOL_M)
  })

  it('covers the lap rather than one corner of it', () => {
    // Guard against a vacuous suite: 140 rows that all sat on the main straight
    // would pass every assertion above while testing nothing about the corners,
    // where the interpolated tangent and the segment direction diverge most and
    // where the naive projection is wrong by 0.89 m.
    const regions = new Set(probes.map((p) => p.region))
    const corners = [...regions].filter((r) => r.startsWith('T'))
    const wrapped = probes.map((p) => ((p.s % frame.lengthM) + frame.lengthM) % frame.lengthM)
    const crossesSeam = wrapped.some(
      (s) => s <= SEAM_SPAN_M || s >= frame.lengthM - SEAM_SPAN_M,
    )
    const strata = new Set(fixture.rows.map((r) => r.stratum))

    expect(corners.length, `corner regions present: ${corners.sort().join(', ')}`).toBeGreaterThanOrEqual(6)
    expect(regions.has('straight'), 'a straight is represented').toBe(true)
    expect(crossesSeam, `rows within ${SEAM_SPAN_M} m of the start/finish line`).toBe(true)
    expect(strata.size, `lateral strata: ${[...strata].sort().join(', ')}`).toBeGreaterThanOrEqual(3)
  })
})
