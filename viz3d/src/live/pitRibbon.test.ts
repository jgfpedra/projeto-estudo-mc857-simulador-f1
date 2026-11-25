import { describe, expect, it } from 'vitest'
import { Vector3 } from 'three'
import { newMotionState } from '../cars/motion'
import { applyLivePose } from './pose'
import { buildPitEdges, buildPitRibbon } from './pitRibbon'
import { pitLaneFromLive } from './track'

describe('via dos boxes na corrida ao vivo', () => {
  it('usa as coordenadas e a largura da engine, com a mesma conversão dos carros', () => {
    const lane = pitLaneFromLive({ waypoints: [[10, 20], [30, 20], [40, 10]], width_m: 6, source: 'estimated' })!
    expect(lane.source).toBe('estimated')
    const car = applyLivePose({ position_xy: [30, 20], heading_deg: 0, velocity_mps: 0, progress_m: 0 }, newMotionState())
    expect(lane.points[1].toArray()).toEqual([car.x, 0, car.z])
    const geometry = buildPitRibbon(lane.points, lane.widthM)
    const positions = geometry.getAttribute('position')
    expect(positions.count).toBe(6)
    for (let i = 0; i < lane.points.length; i++) {
      const a = new Vector3().fromBufferAttribute(positions, i * 2)
      const b = new Vector3().fromBufferAttribute(positions, i * 2 + 1)
      expect(a.distanceTo(b)).toBeCloseTo(6)
      expect(a.clone().add(b).multiplyScalar(.5).x).toBeCloseTo(lane.points[i].x)
      expect(a.clone().add(b).multiplyScalar(.5).z).toBeCloseTo(lane.points[i].z)
      expect(a.y).toBeCloseTo(.03)
    }
    // Duas faces por segmento, sem ligar o último ponto ao primeiro.
    expect(Array.from(geometry.index!.array)).toEqual([0, 1, 2, 1, 3, 2, 2, 3, 4, 3, 5, 4])
    for (let i = 0; i < positions.count; i++) expect(geometry.getAttribute('normal').getY(i)).toBeGreaterThan(0)
    const edges = buildPitEdges(geometry)
    expect(edges.getAttribute('position').count).toBe(8)
    expect(edges.getAttribute('position').getY(0)).toBeCloseTo(.05)
    expect(edges.getAttribute('position').getX(0)).toBeCloseTo(positions.getX(0))
    expect(edges.getAttribute('position').getZ(0)).toBeCloseTo(positions.getZ(0))
    edges.dispose()
    geometry.dispose()
  })

  it('aceita corridas antigas sem boxes e ignora dados incompletos sem criar uma via fictícia', () => {
    for (const input of [undefined, null, {},
      { waypoints: [[0, 0], [1, 2]], width_m: 0 },
      { waypoints: [[0, 0], [NaN, 2]], width_m: 6 },
      { waypoints: [[0, 0], [0, 0]], width_m: 6 },
      { waypoints: [[0, 0]], width_m: 6 },
    ]) expect(pitLaneFromLive(input)).toBeNull()
  })

  it('remove apenas pontos duplicados consecutivos e mantém a via aberta', () => {
    const lane = pitLaneFromLive({ waypoints: [[0, 0], [0, 0], [10, 0]], width_m: 4 })!
    expect(lane.points).toHaveLength(2)
    const geometry = buildPitRibbon(lane.points, lane.widthM)
    expect(geometry.index!.count).toBe(6)
    geometry.dispose()
  })
})
