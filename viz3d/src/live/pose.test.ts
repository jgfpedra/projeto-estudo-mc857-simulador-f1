import { describe, expect, it } from 'vitest'
import { newMotionState } from '../cars/motion'
import { applyLivePose } from './pose'

describe('live engine pose', () => {
  it('maps engine coordinates and heading to the same Three.js frame as the track', () => {
    const out = applyLivePose({ position_xy: [24.2, -8.4], heading_deg: 90, velocity_mps: 12, progress_m: 31 }, newMotionState())
    expect(out.x).toBe(24.2)
    expect(out.z).toBe(8.4)
    expect(out.yawRad).toBeCloseTo(0)
    expect(out.sUnwrapped).toBe(31)
    expect(out.speedMps).toBe(12)
    expect(out.posed).toBe(true)
  })
  it('uses the post-contact pose supplied by the engine without predicting motion', () => {
    const out = newMotionState()
    applyLivePose({ position_xy: [1, 2], heading_deg: 0, velocity_mps: 20, progress_m: 5 }, out)
    applyLivePose({ position_xy: [-3, 7], heading_deg: 180, velocity_mps: 2, progress_m: 6 }, out)
    expect([out.x, out.z]).toEqual([-3, -7])
    expect(out.yawRad).toBeCloseTo(Math.PI / 2)
    expect(out.speedMps).toBe(2)
  })
})
