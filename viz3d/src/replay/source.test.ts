import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { buildFrame, wrapS } from '../track/frame'
import { parseTrack } from '../track/load'
import type { TrackJson } from '../track/types'
import { newMotionState } from '../cars/motion'
import { lapAt, parseReplay } from './load'
import type { ReplayJson } from './types'
import { replaySource } from './source'
import { newClock, seekClock, setRate, stepClock, togglePlay } from './clock'

/**
 * The replay channels, the clock, and the sampler that joins them.
 *
 * The committed artifact, through the real `parseReplay`, for the same reason
 * `frame.test.ts` reads the committed `monza.json`: a synthetic replay would not
 * have the properties under test, which are that *this* file decodes to a
 * monotone unwrapped arc length and that its derived speed is physical.
 */
function load() {
  const trackUrl = new URL('../../public/tracks/monza.json', import.meta.url)
  const frame = buildFrame(
    parseTrack(JSON.parse(readFileSync(fileURLToPath(trackUrl), 'utf8')) as TrackJson),
  )
  const replayUrl = new URL('../../public/replays/monza-2024-race.json', import.meta.url)
  const raw = JSON.parse(readFileSync(fileURLToPath(replayUrl), 'utf8')) as ReplayJson
  return { frame, replay: parseReplay(raw, frame.lengthM) }
}

/** Monza's real peak is about 98 m/s; the extractor guards the same bound. */
const MAX_SPEED_MPS = 105

/**
 * Agreement between the derived speed and the rate `sUnwrapped` advances, m/s.
 *
 * Not a tolerance on physics but on arithmetic: `deriveSpeed` is a central
 * difference of the same array, so the only reason these differ at all is that a
 * central difference over `2 * dt` is not the same as a forward one over `dt`
 * where the speed is changing. Under 5 g of braking that is `a * dt / 2` = 5 m/s.
 */
const SPEED_CONSISTENCY_MPS = 6

describe('the committed replay', () => {
  const { frame, replay } = load()

  it('decodes to the shape its header claims', () => {
    expect(replay.cars.length, `cars: ${replay.cars.map((c) => c.code).join(' ')}`).toBe(19)
    expect(replay.hz).toBe(5)
    expect(replay.durationS).toBeCloseTo((replay.samples - 1) / replay.hz, 9)
    for (const car of replay.cars) {
      expect(car.sUnwrapped.length, car.code).toBe(replay.samples)
      expect(car.d.length, car.code).toBe(replay.samples)
      expect(car.speedMps.length, car.code).toBe(replay.samples)
    }
  })

  it('carries real drivers, and a colour per car from the viewer palette', () => {
    // The replay file has no colour channel: CLAUDE.md's rule about liveries
    // belongs to the renderer, so the palette is assigned here and the file only
    // says who is who.
    for (const car of replay.cars) {
      expect(car.code, `code ${car.code}`).toMatch(/^[A-Z]{3}$/)
      expect(car.label).toBe(car.code)
      expect(car.name?.length ?? 0, `${car.code} has a driver name`).toBeGreaterThan(3)
      expect(car.hex, `${car.code} colour`).toMatch(/^#[0-9a-f]{6}$/i)
    }
  })

  it('never runs backwards and never exceeds a physical speed', () => {
    // The property the whole extraction pipeline exists to deliver. The source
    // position stream has a jittery clock that makes consecutive samples imply
    // 130-150 m/s; if any of that survived into the file, a car would visibly
    // jump here.
    let worstBack = { step: Infinity, code: '', s: 0 }
    let worstFast = { speed: 0, code: '', s: 0 }
    for (const car of replay.cars) {
      for (let i = 1; i < replay.samples; i++) {
        const step = car.sUnwrapped[i] - car.sUnwrapped[i - 1]
        if (step < worstBack.step) worstBack = { step, code: car.code, s: car.sUnwrapped[i] }
        const speed = step / replay.dtS
        if (speed > worstFast.speed) worstFast = { speed, code: car.code, s: car.sUnwrapped[i] }
      }
    }
    expect(
      worstBack.step,
      `most negative step ${worstBack.step.toFixed(4)} m (${worstBack.code} at s=${worstBack.s.toFixed(0)})`,
    ).toBeGreaterThanOrEqual(0)
    expect(
      worstFast.speed,
      `fastest ${worstFast.speed.toFixed(1)} m/s (${worstFast.code} at s=${worstFast.s.toFixed(0)})`,
    ).toBeLessThanOrEqual(MAX_SPEED_MPS)
  })

  it('derives a speed that matches the rate s advances', () => {
    // The consistency `rig.ts` depends on: it integrates `speedMps` forward and
    // damps towards `sUnwrapped`, so if the two disagreed the chase camera would
    // settle at an offset from the car rather than at its configured trail.
    let worst = { gap: 0, code: '', i: 0 }
    for (const car of replay.cars) {
      for (let i = 1; i < replay.samples; i++) {
        const rate = (car.sUnwrapped[i] - car.sUnwrapped[i - 1]) / replay.dtS
        const gap = Math.abs(rate - car.speedMps[i])
        if (gap > worst.gap) worst = { gap, code: car.code, i }
      }
    }
    expect(
      worst.gap,
      `worst ${worst.gap.toFixed(3)} m/s for ${worst.code} at sample ${worst.i}`,
    ).toBeLessThanOrEqual(SPEED_CONSISTENCY_MPS)
  })

  it('crosses the start/finish line, so the seam is actually exercised', () => {
    // Without this the suite could pass on a replay that never wrapped, and the
    // one discontinuity the (s, d) model has to survive would go untested.
    const car = replay.cars[0]
    let crossings = 0
    for (let i = 1; i < replay.samples; i++) {
      if (wrapS(frame, car.sUnwrapped[i]) < wrapS(frame, car.sUnwrapped[i - 1])) crossings++
    }
    expect(crossings, `${car.code} crosses s = 0 this many times`).toBeGreaterThanOrEqual(4)
  })

  it('reports the official lap, not the geometric one', () => {
    const car = replay.cars[0]
    expect(car.lapNumber.length).toBeGreaterThanOrEqual(5)
    // Ascending, and `lapAt` agrees with the table at each boundary.
    for (let i = 1; i < car.lapNumber.length; i++) {
      expect(car.lapNumber[i], `${car.code} lap ${i}`).toBe(car.lapNumber[i - 1] + 1)
      expect(car.lapStartS[i]).toBeGreaterThan(car.lapStartS[i - 1])
    }
    for (let i = 0; i < car.lapNumber.length; i++) {
      expect(lapAt(car, car.lapStartS[i] + 1)).toBe(car.lapNumber[i])
    }
    // Before the first boundary the car is still on the previous lap. The window
    // opens partway round, so this is the state every car starts in — and
    // reporting the first boundary's number here would put the whole field a lap
    // ahead for the first few seconds.
    expect(
      lapAt(car, car.lapStartS[0] - 1),
      `${car.code} before its first boundary`,
    ).toBe(car.lapNumber[0] - 1)
    // And it is genuinely not `floor(s / L)`: the official boundary sits a few
    // metres from the geometric crossing, which is why both are kept.
    const offsets = Array.from(car.lapStartS, (s) => s - Math.round(s / frame.lengthM) * frame.lengthM)
    const worst = offsets.reduce((a, b) => (Math.abs(b) > Math.abs(a) ? b : a))
    expect(Math.abs(worst), `worst boundary offset ${worst.toFixed(2)} m`).toBeGreaterThan(0.01)
    expect(Math.abs(worst), `worst boundary offset ${worst.toFixed(2)} m`).toBeLessThan(50)
  })
})

describe('replaySource', () => {
  const { replay } = load()
  const source = replaySource(replay)
  const out = newMotionState()

  it('is pure in t', () => {
    // Scrubbing has to be repeatable, and a paused frame has to be stable. If
    // this were stateful, the wheel odometer — which is now derived from
    // `sUnwrapped` rather than accumulated — would depend on how you got here.
    const a = { ...source.sampleInto(31.4, 3, out) }
    source.sampleInto(99.9, 3, out)
    const b = { ...source.sampleInto(31.4, 3, out) }
    expect(b).toEqual(a)
  })

  it('lands exactly on a sample at an exact grid time', () => {
    const car = replay.cars[2]
    for (const i of [0, 1, 500, replay.samples - 1]) {
      source.sampleInto(i * replay.dtS, 2, out)
      expect(out.sUnwrapped, `sample ${i}`).toBeCloseTo(car.sUnwrapped[i], 6)
      expect(out.d, `sample ${i}`).toBeCloseTo(car.d[i], 6)
    }
  })

  it('interpolates between samples and holds past the ends', () => {
    const car = replay.cars[0]
    source.sampleInto(0.5 * replay.dtS, 0, out)
    expect(out.sUnwrapped).toBeCloseTo((car.sUnwrapped[0] + car.sUnwrapped[1]) / 2, 6)

    source.sampleInto(-5, 0, out)
    expect(out.sUnwrapped, 'held at the first sample').toBeCloseTo(car.sUnwrapped[0], 6)
    source.sampleInto(replay.durationS + 5, 0, out)
    expect(out.sUnwrapped, 'held at the last sample').toBeCloseTo(
      car.sUnwrapped[replay.samples - 1],
      6,
    )
  })

  it('never reports a speed the camera rig would refuse to seed on', () => {
    // `stepRig` returns early on `speedMps <= 0`, so a stationary car would
    // freeze the camera rather than be followed.
    let worst = Infinity
    for (let i = 0; i < replay.cars.length; i++) {
      for (let k = 0; k < replay.samples; k += 7) {
        source.sampleInto(k * replay.dtS, i, out)
        worst = Math.min(worst, out.speedMps)
      }
    }
    expect(worst, `slowest reported speed ${worst.toExponential(2)} m/s`).toBeGreaterThan(0)
  })

  it('derives the wheel odometer origin from the data', () => {
    for (let i = 0; i < replay.cars.length; i++) {
      expect(source.originM(i), replay.cars[i].code).toBe(replay.cars[i].sUnwrapped[0])
    }
  })
})

describe('the replay clock', () => {
  const duration = 100

  it('advances at the rate, and caps a single step', () => {
    const clock = newClock()
    stepClock(clock, 0.1, duration)
    expect(clock.tS).toBeCloseTo(0.1, 9)
    setRate(clock, 0.25)
    stepClock(clock, 0.1, duration)
    expect(clock.tS).toBeCloseTo(0.125, 9)
    // A hidden tab hands back one enormous delta. Uncapped, the field jumps
    // several laps, which reads as the seam discontinuity M3 ruled out.
    setRate(clock, 1)
    clock.tS = 0
    stepClock(clock, 30, duration)
    expect(clock.tS, 'a 30 s delta is capped').toBeLessThanOrEqual(0.1)
  })

  it('does not advance while paused', () => {
    const clock = newClock()
    togglePlay(clock)
    stepClock(clock, 0.1, duration)
    expect(clock.playing).toBe(false)
    expect(clock.tS).toBe(0)
  })

  it('counts a loop and a seek as cuts, and a rate change as not one', () => {
    // `CameraRig` cuts on this rather than damping. The distinction is the point:
    // a scrub or a loop moves the camera's target by a lap or more, while a rate
    // change leaves it continuous.
    const clock = newClock()
    clock.tS = duration - 0.01
    const before = clock.cuts
    stepClock(clock, 0.1, duration)
    expect(clock.cuts, 'looping is a cut').toBe(before + 1)
    expect(clock.tS, 'and lands just past the start').toBeLessThan(0.1)

    seekClock(clock, 42, duration)
    expect(clock.cuts).toBe(before + 2)
    expect(clock.tS).toBe(42)

    setRate(clock, 0.5)
    expect(clock.cuts, 'a rate change is not a cut').toBe(before + 2)
  })

  it('clamps a seek to the replay', () => {
    const clock = newClock()
    seekClock(clock, -10, duration)
    expect(clock.tS).toBe(0)
    seekClock(clock, 1e6, duration)
    expect(clock.tS).toBe(duration)
  })

  it('still caps an infinite duration, for the synthetic source', () => {
    const clock = newClock()
    stepClock(clock, 30, Infinity)
    expect(clock.tS).toBeLessThanOrEqual(0.1)
  })
})
