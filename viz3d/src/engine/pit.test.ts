import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Vector3 } from 'three'
import { buildFrame, toWorld } from '../track/frame'
import { geometrySha256, parseRecording, trackFromRecording } from './load'
import { engineSource, pitStateAt, pitText, positionAt, tyreText } from './source'
import { newMotionState } from '../cars/motion'
import { signedWheelTravel } from '../cars/odometry'
import type { TickJson } from './types'

/**
 * Phase 3b: the pit-stop fixture, `public/recordings/engine-interlagos2023-seed42-pit.jsonl`,
 * a window of the 15-lap seed-42 race on our own Interlagos export
 * (`exports/interlagos_2023_v1.json`), trimmed around the first stop.
 *
 * What a stop is in the engine (docs/phase3b-longer-races.md section 4): one
 * tick, at the lap line, on which tyres and fuel change and `pit_stops` goes
 * up. The car does not stop and `pitting` stays false; the pit time waits in
 * `pit_penalty_pending_s` until the next lap completes.
 */
const read = (name: string) =>
  readFileSync(fileURLToPath(new URL(`../../public/recordings/${name}`, import.meta.url)), 'utf8')
const TEXT = read('engine-interlagos2023-seed42-pit.jsonl')
const rec = parseRecording(TEXT)
const lines = TEXT.split('\n').filter((l) => l.trim())
const header = JSON.parse(lines[0])
const ticks = lines.slice(1).map((l) => JSON.parse(l) as TickJson)
const N = rec.cars.length

describe('pit-stop fixture (our Interlagos, seed 42)', () => {
  it('is at most 1 MB, carries the phase 3b fields, and its track hashes and measures right', async () => {
    expect(TEXT.length).toBeLessThanOrEqual(1_000_000)
    expect(rec.hasPitFields).toBe(true)
    expect(rec.track.name).toContain('viz3d 2023')
    expect(header.recording.interlagos_tuning.applied).toBe(false)
    expect(await geometrySha256(rec)).toBe(rec.track.geometrySha256)
    const frame = buildFrame(trackFromRecording(rec))
    expect(Math.abs(frame.lengthM - rec.track.lengthM)).toBeLessThan(1e-6)
  })

  it('round trip: toWorld(s_m, d_m) lands on position_xy within 1 mm', () => {
    const frame = buildFrame(trackFromRecording(rec))
    const p = new Vector3()
    let worst = 0
    for (let k = 0; k < rec.ticks; k++) {
      for (let c = 0; c < N; c++) {
        const j = k * N + c
        toWorld(frame, rec.sM[j], rec.dM[j], 0, p)
        worst = Math.max(worst, Math.hypot(p.x - rec.x[j], p.z + rec.y[j]))
      }
    }
    expect(worst).toBeLessThan(1e-3)
  })

  it('holds at least one stop, and every stop matches the recorder\'s own pit_events', () => {
    expect(rec.pitEvents.length).toBeGreaterThan(0)
    const first = header.recording.trimmed.first_tick as number
    for (const e of rec.pitEvents) {
      const logged = header.recording.pit_events.find(
        (p: { driver_id: string; tick: number }) =>
          p.driver_id === rec.cars[e.car].driverId && p.tick === first + e.tick,
      )
      expect(logged, `${rec.cars[e.car].driverId} tick ${e.tick}`).toBeTruthy()
      expect(e.lap).toBe(logged.lap)
      // tyre life is a Float32Array channel: equal to the logged 0.1 % to float32 precision
      expect(e.compoundBefore).toBe(logged.tyre_before[0])
      expect(e.lifeBefore).toBeCloseTo(logged.tyre_before[1], 5)
      expect(e.compoundAfter).toBe(logged.tyre_after[0])
      expect(e.lifeAfter).toBeCloseTo(logged.tyre_after[1], 5)
      expect(e.penaltyS).toBe(logged.penalty_s)
    }
  })

  it('a stop is one tick at the lap line: lap +1, fresh tyres, the car keeps moving, pitting stays false', () => {
    for (const e of rec.pitEvents) {
      const a = (e.tick - 1) * N + e.car
      const b = e.tick * N + e.car
      expect(rec.lap[b]).toBe(rec.lap[a] + 1)
      expect(e.lifeAfter).toBe(100)
      // The tick before carries the life before that lap's wear, so it can sit
      // above the 18% threshold; the stop itself proves the worn value did not.
      expect(e.lifeBefore).toBeGreaterThan(0)
      expect(e.lifeBefore).toBeLessThan(40)
      expect(e.penaltyS).toBe(22)
      expect(rec.velocityMps[b]).toBeGreaterThan(20)
      expect(rec.progressM[b]).toBeGreaterThan(rec.progressM[a])
    }
    expect(rec.pitting.every((v) => v === 0)).toBe(true)
  })

  it('pitStateAt: pending from the stop tick until the end of the window or the next lap', () => {
    const e = rec.pitEvents[0]
    const before = pitStateAt(rec, (e.tick - 1) * rec.dtS, e.car)
    const at = pitStateAt(rec, e.tick * rec.dtS, e.car)
    expect(before.active).toBeNull()
    expect(pitText(before)).toBe('')
    expect(at.active).toBe(e)
    expect(at.stops).toBe(before.stops + 1)
    expect(tyreText(at)).toBe(`${e.compoundAfter} 100.0% · ${at.stops} stop${at.stops === 1 ? '' : 's'}`)
    expect(pitText(at)).toBe(
      `PIT end of lap ${e.lap}: ${e.compoundBefore} (${e.lifeBefore.toFixed(1)}% before that lap) → ` +
        `${e.compoundAfter} 100.0%, +22.0 s on lap ${e.lap + 1}'s time (car not stopped)`,
    )
    // Pending exactly while the lap after the stop is being driven.
    for (let k = e.tick; k < rec.ticks; k++) {
      const st = pitStateAt(rec, k * rec.dtS, e.car)
      const sameLap = rec.lap[k * N + e.car] === e.lap
      expect(st.active !== null, `tick ${k}`).toBe(sameLap)
    }
  })

  it('keeps wheel travel continuous through the recorded pit event and while scrubbing', () => {
    const event = rec.pitEvents[0]
    const beforeIndex = event.tick * N + event.car
    const afterIndex = beforeIndex + N
    const expected = signedWheelTravel(rec.x[beforeIndex], rec.y[beforeIndex], rec.headingRad[beforeIndex],
      rec.x[afterIndex], rec.y[afterIndex], rec.headingRad[afterIndex])
    expect(rec.wheelTravelM[afterIndex] - rec.wheelTravelM[beforeIndex]).toBeCloseTo(expected, 8)
    const source = engineSource(rec)
    const state = newMotionState()
    const time = (event.tick + 0.5) * rec.dtS
    source.sampleInto(time, event.car, state)
    const travel = state.wheelTravelM!
    expect(travel).toBeCloseTo((rec.wheelTravelM[beforeIndex] + rec.wheelTravelM[afterIndex]) / 2, 8)
    source.sampleInto(time + 1, event.car, state)
    source.sampleInto(time, event.car, state)
    expect(state.wheelTravelM).toBeCloseTo(travel, 8)
  })

  it('positionAt still reproduces the recorded order at every tick', () => {
    for (let k = 0; k < rec.ticks; k++) {
      for (const p of ticks[k].positions) {
        const c = rec.cars.findIndex((car) => car.driverId === p.driver_id)
        expect(positionAt(rec, k * rec.dtS, c)).toBe(p.position)
      }
    }
  })
})

describe('phase 3 fixture: no pit fields', () => {
  it('parses with hasPitFields false and no stops, so nothing pit-related shows', () => {
    const old = parseRecording(read('engine-interlagos-seed42.jsonl'))
    expect(old.hasPitFields).toBe(false)
    expect(old.pitEvents).toEqual([])
    const st = pitStateAt(old, 10, 0)
    expect(st.active).toBeNull()
    expect(pitText(st)).toBe('')
  })
})
