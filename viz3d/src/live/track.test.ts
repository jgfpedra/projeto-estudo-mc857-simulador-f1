import { describe, expect, it } from 'vitest'
import { newMotionState } from '../cars/motion'
import { applyLivePose } from './pose'
import { startLineEndpoints, trackFromLive } from './track'

describe('live track geometry', () => {
  it('maps the same engine start and car position into Three.js, rolling around the finish index', () => {
    const track = trackFromLive({ name: 'test', source: 'test', length_m: 40, width_m: 12,
      start_finish_waypoint: 1, waypoints: [[0, 0], [10, 0], [10, 10], [0, 10]] })
    expect(track.points[0].toArray()).toEqual([10, 0, -0])
    const car = applyLivePose({ position_xy: [10, 0], heading_deg: 90, velocity_mps: 0, progress_m: 0 }, newMotionState())
    expect([car.x, car.z]).toEqual([track.points[0].x, track.points[0].z])
    const [a, b] = startLineEndpoints(track)
    expect(a.distanceTo(b)).toBeCloseTo(12)
    expect(a.clone().add(b).multiplyScalar(0.5).distanceTo(track.points[0])).toBeCloseTo(0)
  })
})
