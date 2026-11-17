import { useEffect, useMemo } from 'react'
import type { LivePitLane } from './track'
import { buildPitEdges, buildPitRibbon } from './pitRibbon'

/** A via dos boxes e seus contornos usam a mesma geometria do backend. */
export function PitLaneRibbon({ lane }: { lane: LivePitLane }) {
  const { surface, edges } = useMemo(() => {
    const surface = buildPitRibbon(lane.points, lane.widthM)
    return { surface, edges: buildPitEdges(surface) }
  }, [lane])
  useEffect(() => () => { surface.dispose(); edges.dispose() }, [surface, edges])
  return <group name="pit-lane">
    <mesh geometry={surface}>
      <meshStandardMaterial color="#a1a1aa" roughness={0.9} metalness={0} polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1} />
    </mesh>
    <lineSegments geometry={edges}>
      <lineBasicMaterial color="#facc15" />
    </lineSegments>
  </group>
}
