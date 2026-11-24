import { useEffect, useMemo } from "react"
import { DoubleSide } from "three"

import { buildPitEdges, buildPitRibbon, buildRibbonGeometry, buildStartLine } from "./geometry"
import type { ScenePitLane, SceneTrack } from "./race-track"
import type { TrackFrame } from "./track-frame"

/** Superfície da pista em cor única (`viz3d/src/track/TrackRibbon.tsx`, sem a verificação de espelhamento). */
export function TrackRibbon({ frame, widthM }: { frame: TrackFrame; widthM: number }) {
  const geometry = useMemo(() => buildRibbonGeometry(frame, widthM), [frame, widthM])
  useEffect(() => () => geometry.dispose(), [geometry])
  return (
    <mesh geometry={geometry} name="track">
      <meshStandardMaterial color="#3a3a42" roughness={0.9} metalness={0} />
    </mesh>
  )
}

/** Via dos boxes com contorno amarelo (`viz3d/src/live/PitLaneRibbon.tsx`). */
export function PitLaneRibbon({ lane }: { lane: ScenePitLane }) {
  const { surface, edges } = useMemo(() => {
    const surface = buildPitRibbon(lane.points, lane.widthM)
    return { surface, edges: buildPitEdges(surface) }
  }, [lane])
  useEffect(
    () => () => {
      surface.dispose()
      edges.dispose()
    },
    [surface, edges],
  )
  return (
    <group name="pit-lane">
      <mesh geometry={surface}>
        <meshStandardMaterial
          color="#a1a1aa"
          roughness={0.9}
          metalness={0}
          polygonOffset
          polygonOffsetFactor={-1}
          polygonOffsetUnits={-1}
        />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color="#facc15" />
      </lineSegments>
    </group>
  )
}

/** Linha de chegada no waypoint `startFinishWaypoint` (`viz3d/src/live/StartFinishLine.tsx`). */
export function StartFinishLine({ track }: { track: SceneTrack }) {
  const geometry = useMemo(() => buildStartLine(track), [track])
  useEffect(() => () => geometry.dispose(), [geometry])
  return (
    <mesh geometry={geometry} name="start-finish">
      <meshBasicMaterial color="white" side={DoubleSide} polygonOffset polygonOffsetFactor={-2} polygonOffsetUnits={-2} />
    </mesh>
  )
}
