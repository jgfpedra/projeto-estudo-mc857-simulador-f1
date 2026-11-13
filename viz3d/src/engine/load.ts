import { MathUtils, Vector3 } from 'three'
import { PALETTE } from '../cars/field'
import type { Track } from '../track/types'
import type { EngineCar, RaceBlockJson, Recording, TickJson } from './types'

const fail = (why: string): never => {
  throw new Error(`recording: ${why}`)
}

/** Ticks must sit on one uniform grid; the source indexes it directly. */
const DT_SLACK_S = 1e-6

/**
 * Parse the JSONL text of an engine recording.
 *
 * The one place the engine's conventions become ours: degrees to radians, and
 * race-ordered tick lists to per-car channels. Engine `(x, y)` stays as it is
 * here - the mapping to Three.js (`x`, `-y`) happens in exactly two places,
 * `trackFromRecording` for the centreline and `engineSource` for the cars, so
 * the two cannot disagree about the sign.
 *
 * Split from `loadRecording` for the same reason as `parseTrack` and
 * `parseReplay`: tests read the committed fixture through this exact path.
 */
export function parseRecording(text: string): Recording {
  const lines = text.split('\n').filter((l) => l.trim() !== '')
  if (lines.length < 3) fail(`${lines.length} lines; need the race block and at least two ticks`)
  const block = JSON.parse(lines[0]) as RaceBlockJson
  const t = block.track
  if (!t || !Array.isArray(t.waypoints) || t.waypoints.length < 3) fail('track block has no waypoints')
  if (!(t.width_m > 0)) fail(`width_m is ${t.width_m}`)
  const nWp = t.waypoints.length
  if (!Number.isInteger(t.start_finish_waypoint) || t.start_finish_waypoint < 0 || t.start_finish_waypoint >= nWp) {
    fail(`start_finish_waypoint ${t.start_finish_waypoint} outside 0..${nWp - 1}`)
  }
  const waypoints = new Float64Array(nWp * 2)
  t.waypoints.forEach((p, i) => {
    if (!Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite)) fail(`waypoints[${i}] is not [x, y]`)
    waypoints[2 * i] = p[0]
    waypoints[2 * i + 1] = p[1]
  })

  const drivers = [...block.drivers].sort((a, b) => a.grid_position - b.grid_position)
  if (drivers.length === 0) fail('no drivers')
  const slot = new Map(drivers.map((d, i) => [d.driver_id, i]))
  const cars: EngineCar[] = drivers.map((d, index) => {
    // Colour by grid slot from the viewer's palette, two cars per colour, as
    // `buildField` and `parseReplay` assign it. The engine's own team colours
    // are not used: CLAUDE.md rules out liveries.
    const colour = PALETTE[Math.floor(index / 2) % PALETTE.length]
    return {
      index,
      label: d.driver_id,
      name: d.name,
      colourName: colour.name,
      hex: colour.hex,
      driverId: d.driver_id,
      gridPosition: d.grid_position,
    }
  })

  const nCars = cars.length
  const nTicks = lines.length - 1
  const size = nTicks * nCars
  const x = new Float64Array(size)
  const y = new Float64Array(size)
  const headingRad = new Float64Array(size)
  const velocityMps = new Float64Array(size)
  const progressM = new Float64Array(size)
  const sM = new Float64Array(size)
  const dM = new Float64Array(size)
  const position = new Int16Array(size)
  const lap = new Int16Array(size)
  const pitting = new Uint8Array(size)
  const tyreLifePct = new Float32Array(size)
  const tyreCompound = new Uint8Array(size)
  const compounds: string[] = []
  const times = new Float64Array(nTicks)

  for (let k = 0; k < nTicks; k++) {
    const tick = JSON.parse(lines[k + 1]) as TickJson
    times[k] = tick.sim_ts
    if (tick.positions.length !== nCars) fail(`tick ${k}: ${tick.positions.length} cars, race block has ${nCars}`)
    const seen = new Set<number>()
    tick.positions.forEach((p, rank) => {
      const c = slot.get(p.driver_id)
      if (c === undefined) fail(`tick ${k}: unknown driver ${p.driver_id}`)
      if (p.position !== rank + 1) fail(`tick ${k}: ${p.driver_id} listed ${rank + 1} but says P${p.position}`)
      seen.add(c as number)
      const i = k * nCars + (c as number)
      x[i] = p.position_xy[0]
      y[i] = p.position_xy[1]
      headingRad[i] = MathUtils.degToRad(p.heading_deg)
      velocityMps[i] = p.velocity_mps
      progressM[i] = p.progress_m
      sM[i] = p.s_m
      dM[i] = p.d_m
      position[i] = p.position
      lap[i] = p.lap
      pitting[i] = p.pitting ? 1 : 0
      tyreLifePct[i] = p.tyre_life_pct
      let ci = compounds.indexOf(p.tyre_compound)
      if (ci < 0) ci = compounds.push(p.tyre_compound) - 1
      tyreCompound[i] = ci
    })
    if (seen.size !== nCars) fail(`tick ${k}: a driver is listed twice`)
  }

  const dtS = (times[nTicks - 1] - times[0]) / (nTicks - 1)
  if (!(dtS > 0)) fail('sim_ts does not advance')
  for (let k = 1; k < nTicks; k++) {
    if (Math.abs(times[k] - times[k - 1] - dtS) > DT_SLACK_S) {
      fail(`tick ${k}: sim_ts step ${(times[k] - times[k - 1]).toFixed(6)} s, grid is ${dtS.toFixed(6)} s`)
    }
  }

  // Pace: the rate `progress_m` advances. Fed forward into the chase camera's
  // anchor, which follows `progress_m`; the car's physical `velocity_mps` would
  // leave the camera a steady offset behind wherever the two disagree
  // (docs/3d-design.md section 7, the feed-forward note).
  const paceMps = new Float64Array(size)
  for (let c = 0; c < nCars; c++) {
    for (let k = 0; k < nTicks; k++) {
      const a = Math.max(k - 1, 0)
      const b = Math.min(k + 1, nTicks - 1)
      paceMps[k * nCars + c] = (progressM[b * nCars + c] - progressM[a * nCars + c]) / ((b - a) * dtS)
    }
  }

  return {
    raceId: block.race_id,
    numLaps: block.num_laps,
    track: {
      name: t.name,
      source: t.source,
      geometrySha256: t.geometry_sha256,
      lengthM: t.length_m,
      widthM: t.width_m,
      startFinishWaypoint: t.start_finish_waypoint,
      waypoints,
    },
    cars,
    ticks: nTicks,
    t0S: times[0],
    dtS,
    durationS: (nTicks - 1) * dtS,
    x,
    y,
    headingRad,
    velocityMps,
    progressM,
    paceMps,
    sM,
    dM,
    position,
    lap,
    pitting,
    tyreLifePct,
    tyreCompound,
    compounds,
    meta: block.recording ?? {},
  }
}

/**
 * The track a recording was driven on, built from its own track block.
 *
 * Rolled so that point 0 is the start/finish waypoint: then the frame's `s = 0`
 * is the engine's start/finish line, `progress_m` *is* an unwrapped `s` on this
 * frame, and `s_m` is a wrapped one. Rolling a closed polyline changes no
 * segment, so nothing about the geometry moves.
 *
 * `circuit` is `interlagos` because that is the circuit `load_track_frozen`
 * resolves, so the published-length and rotation-sense checks apply. The block
 * carries no corners, so the corner checks report SKIP rather than pass.
 */
export function trackFromRecording(rec: Recording): Track {
  const wp = rec.track.waypoints
  const n = wp.length / 2
  const sf = rec.track.startFinishWaypoint
  const points: Vector3[] = []
  for (let k = 0; k < n; k++) {
    const i = (sf + k) % n
    // CLAUDE.md: three.x = x, three.z = -y. The minus is not optional.
    points.push(new Vector3(wp[2 * i], 0, -wp[2 * i + 1]))
  }
  return {
    circuit: 'interlagos',
    name: rec.track.name,
    variant: `engine race · ${rec.track.source} ${rec.track.geometrySha256}`,
    year: null,
    lengthM: rec.track.lengthM,
    spacingM: rec.track.lengthM / n,
    widthM: rec.track.widthM,
    rotationRad: 0,
    points,
    corners: [],
    startFinishS: 0,
  }
}

/**
 * `track_identity`'s hash: sha256 of the waypoints as little-endian float64, in
 * file order, first 16 hex characters. Recomputed at load so a recording whose
 * waypoints were edited, or re-serialised with lost precision, is refused
 * rather than rendered slightly wrong.
 */
export async function geometrySha256(rec: Recording): Promise<string> {
  const bytes = new Uint8Array(rec.track.waypoints.length * 8)
  const view = new DataView(bytes.buffer)
  rec.track.waypoints.forEach((v, i) => view.setFloat64(i * 8, v, true))
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 16)
}

/** Fetch, parse and verify a recording. */
export async function loadRecording(url: string): Promise<Recording> {
  const res = await fetch(url)
  if (!res.ok) fail(`${url} -> HTTP ${res.status}`)
  const rec = parseRecording(await res.text())
  const sha = await geometrySha256(rec)
  if (sha !== rec.track.geometrySha256) {
    fail(`waypoints hash to ${sha}, the race block says ${rec.track.geometrySha256}`)
  }
  return rec
}
