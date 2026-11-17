import { Vector3 } from 'three'
import type { Track } from '../track/types'

export interface LiveTrack {
  name: string
  source: string
  geometry_sha256?: string
  length_m: number
  width_m: number
  start_finish_waypoint: number
  waypoints: [number, number][]
  /** Via aberta no mesmo referencial da pista; ausente em corridas antigas. */
  pit_lane?: {
    waypoints: [number, number][]
    width_m: number
    source?: string
  } | null
}

export interface LivePitLane {
  points: Vector3[]
  widthM: number
  source: string | null
}

/** Converte a via dos boxes exatamente como as posições da engine: (x,y) -> (x,0,-y). */
export function pitLaneFromLive(raw: unknown): LivePitLane | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const lane = raw as Record<string, unknown>
  if (typeof lane.width_m !== 'number' || !Number.isFinite(lane.width_m) || lane.width_m <= 0 ||
      !Array.isArray(lane.waypoints) || lane.waypoints.length < 2) return null
  const points: Vector3[] = []
  for (const point of lane.waypoints) {
    if (!Array.isArray(point) || point.length !== 2 ||
        typeof point[0] !== 'number' || !Number.isFinite(point[0]) ||
        typeof point[1] !== 'number' || !Number.isFinite(point[1])) return null
    const next = new Vector3(point[0], 0, -point[1])
    // Pontos consecutivos iguais não alteram a via, mas não definem tangente.
    if (!points.length || points[points.length - 1].distanceToSquared(next) > 1e-12) points.push(next)
  }
  if (points.length < 2) return null
  return { points, widthM: lane.width_m, source: typeof lane.source === 'string' ? lane.source : null }
}

/** Build the visual track from the same engine waypoints, with s=0 at the line. */
export function trackFromLive(t: LiveTrack): Track {
  const points = t.waypoints.map((_, k) => {
    const [x, y] = t.waypoints[(k + t.start_finish_waypoint) % t.waypoints.length]
    return new Vector3(x, 0, -y)
  })
  return { circuit: '', name: t.name, variant: t.source, year: null, lengthM: t.length_m,
    spacingM: t.length_m / points.length, widthM: t.width_m, rotationRad: 0, points, corners: [], startFinishS: 0 }
}

/** Line endpoints follow the same averaged start tangent as the backend grid. */
export function startLineEndpoints(track: Track): [Vector3, Vector3] {
  const first = track.points[0]
  const tangent = track.points[1].clone().sub(track.points[track.points.length - 1]).normalize()
  const side = new Vector3(-tangent.z, 0, tangent.x).multiplyScalar(track.widthM / 2)
  return [first.clone().add(side), first.clone().sub(side)]
}
