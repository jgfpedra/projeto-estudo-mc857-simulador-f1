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
