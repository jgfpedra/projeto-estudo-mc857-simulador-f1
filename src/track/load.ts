import { MathUtils, Vector3 } from 'three'
import type { Track, TrackJson } from './types'

function fail(msg: string): never {
  throw new Error(`track JSON: ${msg}`)
}

/**
 * Parse a track JSON that has already been read from somewhere. This is the
 * one place degrees become radians and number triples become Vector3
 * (CLAUDE.md: convert at the load boundary, not scattered through the render
 * code).
 *
 * Validation here is structural only — "is this the file we think it is". The
 * geometric checks (mirrored, reversed, corner order) live in `verify.ts`,
 * because they are about whether the geometry is *right*, not well-formed.
 *
 * Split from `loadTrack` so tests can build a `Track` from disk without
 * needing `fetch` — and so they exercise this exact code path rather than a
 * parallel one written for the test.
 */
export function parseTrack(raw: TrackJson): Track {
  if (!Array.isArray(raw.centerline) || raw.centerline.length < 3) {
    fail('centerline missing or too short')
  }
  const points = raw.centerline.map((p, i) => {
    if (!Array.isArray(p) || p.length !== 3 || !p.every(Number.isFinite)) {
      fail(`centerline[${i}] is not a finite [x, y, z]`)
    }
    return new Vector3(p[0], p[1], p[2])
  })
  if (points[0].distanceTo(points[points.length - 1]) < 1e-6) {
    fail('centerline duplicates its first point; the loop should be open')
  }
  if (!Number.isFinite(raw.lengthM) || raw.lengthM <= 0) fail('lengthM invalid')
  if (!Number.isFinite(raw.widthM) || raw.widthM <= 0) fail('widthM invalid')

  const corners = [...raw.corners].map((c) => ({
    number: c.number,
    name: c.name,
    s: c.s,
  }))

  return {
    name: raw.name,
    year: raw.year,
    lengthM: raw.lengthM,
    spacingM: raw.spacingM,
    widthM: raw.widthM,
    rotationRad: MathUtils.degToRad(raw.rotationDeg),
    points,
    corners,
    startFinishS: raw.startFinishS,
  }
}

/** Fetch a track JSON over HTTP and parse it. */
export async function loadTrack(url: string): Promise<Track> {
  const res = await fetch(url)
  if (!res.ok) fail(`${url} -> HTTP ${res.status}`)
  return parseTrack((await res.json()) as TrackJson)
}
