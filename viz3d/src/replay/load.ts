import { PALETTE } from '../cars/field'
import type { Replay, ReplayCar, ReplayJson } from './types'

const fail = (why: string): never => {
  throw new Error(`replay: ${why}`)
}

/**
 * Derive along-track speed from the committed `s`, m/s.
 *
 * A central difference and nothing else, matching `derive_speed` in
 * `scripts/extract_replay.py` exactly — including the one-sided ends, which is
 * what `numpy.gradient` does.
 *
 * **Speed is derived rather than stored, and that is the point.** `rig.ts` feeds
 * `speedMps` forward into the chase camera's anchor, so a stored speed that
 * disagreed with the rate `s` actually advances would leave the camera at a
 * steady-state offset from the car. Derived this way, `speed` *is* the rate `s`
 * advances, and the two cannot drift apart.
 *
 * No smoothing, because none is needed: `s` comes out of a smoothing spline in
 * the extractor, and against FastF1's independent `Speed` channel a plain
 * central difference agrees as well as any boxcar did (sd 1.99 against 2.02
 * m/s). So there is no smoothing constant here that would have to be kept
 * identical in two languages.
 */
function deriveSpeed(s: Float64Array, dtS: number): Float64Array {
  const n = s.length
  const v = new Float64Array(n)
  if (n < 2) return v
  v[0] = (s[1] - s[0]) / dtS
  v[n - 1] = (s[n - 1] - s[n - 2]) / dtS
  for (let i = 1; i < n - 1; i++) v[i] = (s[i + 1] - s[i - 1]) / (2 * dtS)
  return v
}

/**
 * Parse raw replay JSON.
 *
 * Split from `loadReplay` so tests can build a `Replay` from disk without
 * needing `fetch` — and so they exercise this exact code path rather than a
 * parallel one written for the test. The same split, for the same reason, as
 * `parseTrack` in `src/track/load.ts`.
 *
 * `trackLengthM` is checked against the frame the viewer actually built. A replay
 * projected against a different centreline would still wrap and still render; it
 * would just be wrong, by a little, everywhere — which is the kind of failure
 * worth refusing at the boundary rather than debugging on screen.
 */
export function parseReplay(raw: ReplayJson, frameLengthM: number): Replay {
  const samples = raw.samples
  if (!Number.isFinite(samples) || samples < 2) fail(`samples is ${samples}`)
  if (!(raw.hz > 0)) fail(`hz is ${raw.hz}`)
  if (!raw.cars?.length) fail('no cars')

  const slack = 0.01
  if (Math.abs(raw.trackLengthM - frameLengthM) > slack) {
    fail(
      `projected against a ${raw.trackLengthM} m centreline but the loaded track ` +
        `measures ${frameLengthM.toFixed(4)} m — re-run scripts/extract_replay.py`,
    )
  }

  const dtS = 1 / raw.hz
  const cars: ReplayCar[] = raw.cars.map((car, index) => {
    if (car.dsMm.length !== samples - 1) {
      fail(`${car.code} has ${car.dsMm.length} deltas, expected ${samples - 1}`)
    }
    if (car.dCm.length !== samples) {
      fail(`${car.code} has ${car.dCm.length} offsets, expected ${samples}`)
    }

    // Prefix-sum the millimetre deltas back into metres. This is the decode the
    // extractor's check O measures the round trip through, so it has to match.
    const sUnwrapped = new Float64Array(samples)
    sUnwrapped[0] = car.s0M
    for (let i = 1; i < samples; i++) {
      sUnwrapped[i] = sUnwrapped[i - 1] + car.dsMm[i - 1] / 1000
    }

    const d = new Float64Array(samples)
    for (let i = 0; i < samples; i++) d[i] = car.dCm[i] / 100

    // Colour from the viewer's own palette, by position in the file — which the
    // extractor orders by the running order at the window start. Ten colours,
    // two cars each, exactly as `buildField` assigns them, so a replay and the
    // synthetic field read in the same visual language. Team colours are
    // deliberately not used: CLAUDE.md allows an approximate palette and rules
    // out liveries.
    const colour = PALETTE[Math.floor(index / 2) % PALETTE.length]

    return {
      index,
      code: car.code,
      label: car.code,
      name: car.name,
      colourName: colour.name,
      hex: colour.hex,
      sUnwrapped,
      d,
      speedMps: deriveSpeed(sUnwrapped, dtS),
      lapNumber: car.lapNumber,
      lapStartS: Float64Array.from(car.lapStartS),
      lapStartT: Float64Array.from(car.lapStartT),
    }
  })

  return {
    name: raw.name,
    year: raw.year,
    session: raw.session,
    trackLengthM: raw.trackLengthM,
    hz: raw.hz,
    dtS,
    samples,
    // The last sample is the end: `samples - 1` steps of `dtS`.
    durationS: (samples - 1) * dtS,
    fromLap: raw.fromLap,
    toLap: raw.toLap,
    pitAbsDM: raw.pitAbsDM,
    cars,
  }
}

/** Fetch a replay JSON over HTTP and parse it. */
export async function loadReplay(url: string, frameLengthM: number): Promise<Replay> {
  const res = await fetch(url)
  if (!res.ok) fail(`${url} -> HTTP ${res.status}`)
  return parseReplay((await res.json()) as ReplayJson, frameLengthM)
}

/**
 * Official lap number at an unwrapped arc length.
 *
 * `lapStartS` is ascending, so this is a search rather than arithmetic — and it
 * has to be, because the official boundary and the geometric `s = 0` crossing are
 * up to 13 m apart and `floor(s / L)` would answer a different question.
 */
export function lapAt(car: ReplayCar, sUnwrapped: number): number {
  // One *before* the first recorded boundary, not the first boundary itself: the
  // window opens partway through a lap, so a car has not yet started the lap its
  // first boundary names. Getting this wrong puts every car a lap ahead for the
  // first few seconds, which looks like a rounding quirk rather than an off-by-one.
  let lap = (car.lapNumber[0] ?? 1) - 1
  for (let i = 0; i < car.lapStartS.length; i++) {
    if (car.lapStartS[i] <= sUnwrapped) lap = car.lapNumber[i]
    else break
  }
  return lap
}
