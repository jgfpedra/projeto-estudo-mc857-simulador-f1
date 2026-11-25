/**
 * Geometria servida pelo backend para o espaço do Three.js.
 *
 * Portado de `viz3d/src/live/track.ts` (`trackFromLive`, `pitLaneFromLive`,
 * `startLineEndpoints`), lendo os tipos já convertidos do frontend. Sem
 * suavização nem reamostragem: desenhamos exatamente os pontos que a engine
 * simulou, só rotacionados para que `startFinishWaypoint` seja s = 0.
 */
import { Vector3 } from "three"

import type { RacePitLane, RaceTrack } from "@/types/race"
import { TRACK_WIDTH_M } from "../../../../helpers/race-live.ts"

/** Rotaciona uma volta fechada para começar em `start` (módulo o tamanho). */
export function rotateToStart<T>(points: readonly T[], start: number): T[] {
  const n = points.length
  if (n === 0) return []
  const k = ((Math.trunc(start) % n) + n) % n
  return [...points.slice(k), ...points.slice(0, k)]
}

/** Ponto do backend `(x, y)` para `(x, 0, -y)`. */
export function toThree([x, y]: readonly [number, number], h = 0): Vector3 {
  return new Vector3(x, h, -y)
}

export type SceneTrack = {
  name: string
  widthM: number
  /** s = 0 na linha de chegada, sentido da corrida, laço aberto. */
  points: Vector3[]
}

export function trackFromRace(track: RaceTrack): SceneTrack {
  return {
    name: track.name,
    widthM: track.widthM ?? TRACK_WIDTH_M,
    points: rotateToStart(track.waypoints, track.startFinishWaypoint).map((p) => toThree(p)),
  }
}

export type ScenePitLane = {
  points: Vector3[]
  widthM: number
  source: string | null
}

/** Via dos boxes aberta. Pontos consecutivos iguais não definem tangente e são descartados. */
export function pitLaneFromRace(pit: RacePitLane | null): ScenePitLane | null {
  if (!pit) return null
  const points: Vector3[] = []
  for (const p of pit.waypoints) {
    const next = toThree(p)
    if (!points.length || points[points.length - 1].distanceToSquared(next) > 1e-12) points.push(next)
  }
  if (points.length < 2) return null
  return { points, widthM: pit.widthM, source: pit.source }
}

/** Extremos da linha de chegada, na mesma tangente média que o grid do backend usa. */
export function startLineEndpoints(track: SceneTrack): [Vector3, Vector3] {
  const pts = track.points
  const first = pts[0]
  const tangent = pts[1].clone().sub(pts[pts.length - 1]).normalize()
  const side = new Vector3(-tangent.z, 0, tangent.x).multiplyScalar(track.widthM / 2)
  return [first.clone().add(side), first.clone().sub(side)]
}

export type Overview = {
  position: Vector3
  target: Vector3
  /** Distância da câmera ao centro, para ajustar near/far. */
  distance: number
}

/**
 * Câmera de visão geral que enquadra uma esfera de raio `radius` em torno de
 * `center`. A altura e a inclinação seguem a do viz3d (`(0, D, 0.3 D)`), com o
 * norte do plano (+y) para cima na tela, como no 2D; a distância usa o menor
 * campo de visão (vertical ou horizontal) para caber também em telas estreitas.
 */
export function overviewPose(center: Vector3, radius: number, fovDeg: number, aspect: number): Overview {
  const vHalf = (fovDeg * Math.PI) / 360
  const hHalf = Math.atan(Math.tan(vHalf) * Math.max(aspect, 1e-3))
  const half = Math.min(vHalf, hHalf)
  const distance = (Math.max(radius, 1) / Math.sin(half)) * 1.05
  const dir = new Vector3(0, 1, 0.3).normalize()
  return {
    position: center.clone().addScaledVector(dir, distance),
    target: center.clone(),
    distance,
  }
}
