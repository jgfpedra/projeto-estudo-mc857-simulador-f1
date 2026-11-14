import { describe, expect, it } from 'vitest'
import { newMotionState } from '../cars/motion'
import { LiveBuffer } from './buffer'
import type { LiveTick } from './buffer'

function tick(time: number, x: number, heading = 0, collisions: LiveTick['collisions'] = []): LiveTick {
  return { type: 'tick', sim_ts: time, collisions, positions: [
    { driver_id: 'a', position: 1, lap: 0, position_xy: [x, -2 * x], heading_deg: heading, velocity_mps: x, progress_m: x * 2 },
    { driver_id: 'b', position: 2, lap: 0, position_xy: [100 + x, x], heading_deg: 0, velocity_mps: x, progress_m: x },
  ] }
}

function start(buffer: LiveBuffer) {
  const out = newMotionState()
  buffer.push(tick(0, 0, 350))
  buffer.sampleInto('a', 0, out)
  buffer.push(tick(0.1, 10, 10, [{ drv_a: 'a', drv_b: 'b' }]))
  buffer.sampleInto('a', 100, out)
  buffer.sampleInto('a', 200, out)
  buffer.push(tick(0.2, 20, 20))
  buffer.sampleInto('a', 200, out)
  return out
}

describe('live snapshot buffer', () => {
  it('interpolates all cars on the same delayed simulation clock and rotates across 360 degrees', () => {
    const buffer = new LiveBuffer()
    const a = start(buffer)
    buffer.sampleInto('a', 250, a)
    const b = buffer.sampleInto('b', 250, newMotionState())
    expect(a.x).toBeCloseTo(5)
    expect(a.z).toBeCloseTo(10)
    expect(a.speedMps).toBeCloseTo(5)
    expect(a.sUnwrapped).toBeCloseTo(10)
    expect(Math.sin(a.yawRad)).toBeCloseTo(-1)
    expect(Math.cos(a.yawRad)).toBeCloseTo(0)
    expect(b.x).toBeCloseTo(105)
    expect(buffer.displayTick(250)?.sim_ts).toBe(0)
    expect(buffer.displayTick(300)?.collisions).toEqual([{ drv_a: 'a', drv_b: 'b' }])
  })

  it('holds the last state when ticks stop and buffers again when they resume', () => {
    const buffer = new LiveBuffer()
    const out = start(buffer)
    buffer.sampleInto('a', 1000, out)
    expect(out.x).toBeCloseTo(20)
    buffer.sampleInto('a', 2000, out)
    expect(out.x).toBeCloseTo(20)
    buffer.push(tick(0.3, 30))
    buffer.sampleInto('a', 2100, out)
    expect(out.x).toBeCloseTo(20)
    buffer.push(tick(0.4, 40))
    buffer.sampleInto('a', 2100, out)
    buffer.sampleInto('a', 2150, out)
    expect(out.x).toBeCloseTo(25)
  })

  it('uses pose displacement for wheel travel, independent of track progress', () => {
    const buffer = new LiveBuffer(0.1)
    const out = newMotionState()
    const a = tick(0, 0)
    const b = tick(0.1, 0)
    b.positions[0].progress_m = 50 // projection jumped but the car did not move
    buffer.push(a)
    buffer.sampleInto('a', 0, out)
    buffer.push(b)
    buffer.sampleInto('a', 0, out)
    buffer.sampleInto('a', 100, out)
    expect(out.sUnwrapped).toBeCloseTo(50)
    expect(out.wheelTravelM).toBeCloseTo(0)
    const c = tick(0.2, -2)
    buffer.push(c)
    buffer.sampleInto('a', 100, out)
    buffer.sampleInto('a', 200, out)
    expect(out.wheelTravelM).toBeCloseTo(-2)
    buffer.disconnected()
    buffer.push(tick(1, 100))
    buffer.sampleInto('a', 300, out)
    expect(out.wheelTravelM).toBeCloseTo(-2) // do not invent distance across a gap
  })

  it('keeps the last displayed wheel phase across a reconnect', () => {
    const buffer = new LiveBuffer(0.1)
    const out = newMotionState()
    buffer.push(tick(0, 0))
    buffer.sampleInto('a', 0, out)
    buffer.push(tick(0.1, 1))
    buffer.push(tick(0.2, 2))
    buffer.sampleInto('a', 50, out)
    expect(out.wheelTravelM).toBeCloseTo(0.5)
    buffer.disconnected()
    buffer.push(tick(0.3, 30))
    buffer.sampleInto('a', 100, out)
    expect(out.wheelTravelM).toBeCloseTo(0.5)
  })

  it('plays the final buffered interval when the race ends', () => {
    const buffer = new LiveBuffer()
    const out = newMotionState()
    buffer.push(tick(0, 0))
    buffer.sampleInto('a', 0, out)
    buffer.push(tick(0.1, 10))
    buffer.sampleInto('a', 100, out)
    expect(out.x).toBe(0)
    buffer.finish()
    buffer.sampleInto('a', 150, out)
    expect(out.x).toBeCloseTo(5)
    buffer.sampleInto('a', 200, out)
    expect(out.x).toBeCloseTo(10)
  })

  it('ignores duplicate or out-of-order ticks and cuts on reconnect or a missing span', () => {
    const buffer = new LiveBuffer()
    const out = start(buffer)
    expect(buffer.push(tick(0.2, 999))).toBe(false)
    expect(buffer.push(tick(0.1, 999))).toBe(false)
    buffer.disconnected()
    expect(buffer.push(tick(0.3, 30))).toBe(true)
    expect(buffer.sampleInto('a', 300, out).x).toBe(30)
    buffer.push(tick(2, 200))
    expect(buffer.sampleInto('a', 400, out).x).toBe(200)
  })
})
